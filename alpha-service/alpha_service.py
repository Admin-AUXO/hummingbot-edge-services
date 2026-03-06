import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import AlphaConfig
from scorer import build_new_listing_payload, build_signal_payload, is_new_listing, score_token
from shared.base_service import BaseService
from shared.utils import TTLCache, chain_address_key, normalize_chain_id, parse_csv_list, parse_json_mapping


class AlphaService(BaseService):
    name = "alpha"

    def __init__(self):
        super().__init__(AlphaConfig())
        self.seen_signals = TTLCache(self.config.signal_ttl_seconds, max_size=self.config.cache_max_size)
        self.seen_listings = TTLCache(self.config.listing_ttl_seconds, max_size=self.config.cache_max_size)
        self._strict_list = set()
        self._last_strict_fetch = 0
        self.supported_chains = [normalize_chain_id(chain) for chain in parse_csv_list(self.config.supported_chains)] or ["solana"]
        self.search_queries = self._load_search_queries()

    def _load_search_queries(self):
        default_queries = {chain: [self.config.dex_search_query] for chain in self.supported_chains}
        raw_queries = parse_json_mapping(self.config.dex_search_queries_json, default=default_queries)
        queries = {}
        for chain in self.supported_chains:
            raw = raw_queries.get(chain, [self.config.dex_search_query])
            if isinstance(raw, str):
                raw = [raw]
            queries[chain] = [str(item).strip() for item in raw if str(item).strip()] or [self.config.dex_search_query]
        return queries

    def fetch_pairs(self):
        discovered = {}
        chain_counts = {chain: 0 for chain in self.supported_chains}

        for chain in self.supported_chains:
            for query in self.search_queries.get(chain, []):
                try:
                    resp = self.session.get(
                        self.config.dex_search_url,
                        params={"q": query},
                        timeout=15,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    pairs = data.get("pairs", [])
                    for pair in pairs:
                        pair_chain = normalize_chain_id(pair.get("chainId"))
                        if pair_chain != chain:
                            continue
                        key = pair.get("pairAddress") or chain_address_key(chain, pair.get("baseToken", {}).get("address", ""))
                        liq = float(pair.get("liquidity", {}).get("usd", 0) or 0)
                        if key not in discovered or liq > float(discovered[key].get("liquidity", {}).get("usd", 0) or 0):
                            discovered[key] = pair
                except Exception as e:
                    self.logger.error(f"DexScreener fetch failed for {chain}/{query}: {e}")

        for pair in discovered.values():
            chain = normalize_chain_id(pair.get("chainId"))
            chain_counts[chain] = chain_counts.get(chain, 0) + 1

        return list(discovered.values()), chain_counts

    def fetch_strict_list(self):
        now = time.time()
        if now - self._last_strict_fetch < self.config.strict_list_ttl_seconds and self._strict_list:
            return self._strict_list

        urls = [
            "https://tokens.jup.ag/tokens?tags=strict",
            "https://token.jup.ag/strict"
        ]
        
        for url in urls:
            try:
                resp = self.session.get(url, timeout=15)
                resp.raise_for_status()
                data = resp.json()

                addrs = set()
                for item in data:
                    if isinstance(item, dict):
                        addr = item.get("address") or item.get("mint")
                        if addr: addrs.add(addr)
                
                if addrs:
                    self._strict_list = addrs
                    self._last_strict_fetch = now
                    self.logger.info(f"Updated strict list ({len(addrs)} tokens) from {url}")
                    return self._strict_list
            except Exception as e:
                self.logger.error(f"Jupiter fetch failed from {url}: {e}")

        return self._strict_list

    def _cap_seen(self):
        self.seen_signals.clear_expired()
        self.seen_listings.clear_expired()

    def on_tick(self):
        self._cap_seen()
        pairs, chain_counts = self.fetch_pairs()
        if not pairs:
            self.logger.info("Fetched 0 pairs across configured chains")
            return
        strict_list = self.fetch_strict_list()
        counts_str = ", ".join(f"{chain}={count}" for chain, count in sorted(chain_counts.items()))
        self.logger.info(f"Fetched {len(pairs)} pairs ({counts_str}), {len(strict_list)} strict Solana tokens")

        def process_pair(pair):
            chain = normalize_chain_id(pair.get("chainId"))
            base_token = pair.get("baseToken", {})
            addr, sym = base_token.get("address", ""), base_token.get("symbol", "?")
            verified = chain == "solana" and addr in strict_list
            if verified: sym = f"✅ {sym}"
            cache_key = chain_address_key(chain, addr)
            volume_24h = float(pair.get("volume", {}).get("h24", 0) or 0)
            min_signal_volume = self.config.min_signal_volume_for(chain)
            min_listing_volume = self.config.min_new_listing_volume_for(chain)
            min_listing_score = self.config.min_new_listing_score_for(chain)

            score, breakdown = score_token(pair, self.config)
            if verified:
                score += 2
                breakdown["verified"] = "Jupiter Strict List"

            if score >= self.config.min_score and volume_24h >= min_signal_volume and cache_key not in self.seen_signals:
                p = build_signal_payload(pair, score, breakdown)
                if verified: p["token"] = sym
                self.publish(f"{self.config.mqtt_topic_prefix}/{chain}/signal/{sym.replace('✅ ', '')}", p)
                self.seen_signals.add(cache_key)
                self.logger.info(f"SIGNAL: [{chain}] {sym} score={score} liq=${p['liquidity']:,.0f}")

            if (
                is_new_listing(pair, self.config)
                and score >= min_listing_score
                and volume_24h >= min_listing_volume
                and cache_key not in self.seen_listings
            ):
                p = build_new_listing_payload(pair)
                if verified: p["token"] = sym
                self.publish(f"{self.config.mqtt_topic_prefix}/{chain}/new_listing/{sym.replace('✅ ', '')}", p)
                self.seen_listings.add(cache_key)
                self.logger.info(f"NEW LISTING: [{chain}] {sym} age={p['age_hours']}h liq=${p['liquidity']:,.0f}")

        workers = max(1, min(self.config.max_workers, len(pairs)))
        with ThreadPoolExecutor(max_workers=workers) as ex:
            list(ex.map(process_pair, pairs))


if __name__ == "__main__":
    AlphaService().run()
