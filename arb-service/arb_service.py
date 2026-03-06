import json
import os
import sys
import time

from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from arb_scanner import find_arb_opportunities
from config import ArbConfig
from shared.base_service import BaseService
from shared.utils import TTLCache, chain_address_key, normalize_chain_id, parse_csv_list, parse_json_mapping


class ArbService(BaseService):
    name = "arb"

    def __init__(self):
        super().__init__(ArbConfig())
        self.seen_arbs = TTLCache(self.config.seen_arb_ttl_seconds, max_size=self.config.cache_max_size)
        self.last_discovery = 0
        self.last_tokens_refresh = 0
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

    def load_tokens(self):
        try:
            with open(self.config.tokens_file, "r") as f:
                raw_tokens = json.load(f)
            if not isinstance(raw_tokens, list):
                self.logger.error(f"Invalid tokens format in {self.config.tokens_file}: expected list")
                return []
            seen_addresses = set()
            deduped = []
            for token in raw_tokens:
                address = token.get("address")
                symbol = token.get("symbol")
                chain_id = normalize_chain_id(token.get("chainId") or token.get("chain_id") or token.get("chain") or self.config.default_chain_id)
                key = chain_address_key(chain_id, address)
                if not address or not symbol or key in seen_addresses:
                    continue
                seen_addresses.add(key)
                deduped.append({"symbol": symbol, "address": address, "chainId": chain_id})
            return deduped
        except Exception as e:
            self.logger.error(f"Failed to load tokens: {e}")
            return []

    def discover_trending_tokens(self):
        discovered = {}

        def fetch_chain_query(chain, query):
            try:
                resp = self.session.get(
                    self.config.dex_search_url,
                    params={"q": query},
                    timeout=15,
                )
                resp.raise_for_status()
                return chain, query, (resp.json().get("pairs") or [])
            except Exception as e:
                self.logger.error(f"Token discovery failed for {chain}/{query}: {e}")
                return chain, query, []

        jobs = [(chain, query) for chain in self.supported_chains for query in self.search_queries.get(chain, [])]
        workers = max(1, min(self.config.max_workers, len(jobs)))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(fetch_chain_query, chain, query) for chain, query in jobs]
            for future in futures:
                chain, _query, pairs = future.result()
                for pair in pairs:
                    pair_chain = normalize_chain_id(pair.get("chainId"))
                    if pair_chain != chain:
                        continue
                    liq = float(pair.get("liquidity", {}).get("usd", 0) or 0)
                    vol = float(pair.get("volume", {}).get("h24", 0) or 0)

                    min_liq = min(self.config.min_liquidity, self.config.tokens_min_liquidity_for(chain))
                    min_vol = min(self.config.min_volume_24h, self.config.tokens_min_volume_for(chain))
                    if liq < min_liq or vol < min_vol:
                        continue

                    pair_tokens = [pair.get("baseToken") or {}, pair.get("quoteToken") or {}]
                    score = (liq * 0.75) + (vol * 0.25)
                    for token in pair_tokens:
                        symbol = token.get("symbol", "")
                        address = token.get("address", "")
                        if not symbol or not address:
                            continue
                        key = chain_address_key(chain, address)
                        if key not in discovered or score > discovered[key]["score"]:
                            discovered[key] = {
                                "symbol": symbol,
                                "address": address,
                                "chainId": chain,
                                "liq": liq,
                                "vol": vol,
                                "score": score,
                            }

        try:
            new_tokens = [
                {
                    "symbol": d["symbol"],
                    "address": d["address"],
                    "chainId": d["chainId"],
                    "liq": d["liq"],
                    "vol": d["vol"],
                    "score": d["score"],
                }
                for d in sorted(discovered.values(), key=lambda x: x["score"], reverse=True)[:80]
            ]
            counts = {}
            for token in new_tokens:
                chain = token["chainId"]
                counts[chain] = counts.get(chain, 0) + 1
            self.logger.info(f"Auto-discovered {len(new_tokens)} trending tokens: {counts}")
            return new_tokens
        except Exception as e:
            self.logger.error(f"Token discovery failed: {e}")
            return []

    def _maybe_refresh_tokens_file(self, core_tokens, dynamic_tokens):
        if not self.config.auto_update_tokens_file:
            return

        now = time.time()
        if now - self.last_tokens_refresh < self.config.tokens_refresh_interval_seconds:
            return

        per_chain = {chain: [] for chain in self.supported_chains}
        seen = set()

        for token in core_tokens:
            chain = normalize_chain_id(token.get("chainId"))
            key = chain_address_key(chain, token.get("address"))
            if chain in per_chain and key not in seen:
                per_chain[chain].append({"symbol": token["symbol"], "address": token["address"], "chainId": chain})
                seen.add(key)

        ranked_dynamic = sorted(dynamic_tokens, key=lambda x: float(x.get("score", 0)), reverse=True)
        for token in ranked_dynamic:
            chain = normalize_chain_id(token.get("chainId"))
            if chain not in per_chain:
                continue
            liq = float(token.get("liq", 0) or 0)
            vol = float(token.get("vol", 0) or 0)
            if liq < self.config.tokens_min_liquidity_for(chain) or vol < self.config.tokens_min_volume_for(chain):
                continue

            key = chain_address_key(chain, token.get("address"))
            if key in seen:
                continue
            if len(per_chain[chain]) >= self.config.tokens_max_per_chain_for(chain):
                continue

            per_chain[chain].append({
                "symbol": token["symbol"],
                "address": token["address"],
                "chainId": chain,
            })
            seen.add(key)

        refreshed = []
        for chain in self.supported_chains:
            refreshed.extend(per_chain.get(chain, []))

        if refreshed:
            try:
                with open(self.config.tokens_file, "w") as f:
                    json.dump(refreshed, f, indent=2)
                self.last_tokens_refresh = now
                self.logger.info(f"Refreshed {self.config.tokens_file} with {len(refreshed)} curated tokens")
            except Exception as e:
                self.logger.error(f"Failed refreshing tokens file: {e}")

    def get_tokens(self):
        static_tokens = self.load_tokens()
        static_addresses = {chain_address_key(t.get("chainId"), t["address"]) for t in static_tokens}

        now = time.time()
        if now - self.last_discovery > self.config.discovery_interval_seconds:
            dynamic = self.discover_trending_tokens()
            for d in dynamic:
                key = chain_address_key(d.get("chainId"), d["address"])
                if key not in static_addresses:
                    static_tokens.append({"symbol": d["symbol"], "address": d["address"], "chainId": d["chainId"]})
                    static_addresses.add(key)
            self._maybe_refresh_tokens_file(static_tokens, dynamic)
            self.last_discovery = now
            self._merged_tokens = static_tokens

        return getattr(self, "_merged_tokens", static_tokens)

    def fetch_all_token_pairs_batch(self, tokens):
        if not tokens:
            return {}
        results = {}
        batch_size = max(1, min(30, self.config.dex_batch_size))
        tokens_by_chain = {}
        for token in tokens:
            chain = normalize_chain_id(token.get("chainId") or self.config.default_chain_id)
            tokens_by_chain.setdefault(chain, [])
            tokens_by_chain[chain].append(token)

        for chain, chain_tokens in tokens_by_chain.items():
            addresses = list(dict.fromkeys(t["address"] for t in chain_tokens if t.get("address")))
            address_set = set(addresses)
            pair_seen_by_token = {}
            for i in range(0, len(addresses), batch_size):
                batch = addresses[i : i + batch_size]
                try:
                    url = self._build_dex_tokens_url(batch, chain_id=chain)
                    resp = self.session.get(url, timeout=20)
                    resp.raise_for_status()
                    data = resp.json()
                    pairs = data.get("pairs") if isinstance(data, dict) else data
                    if not pairs:
                        continue
                    for p in pairs:
                        pair_chain = normalize_chain_id(p.get("chainId"))
                        if pair_chain != chain:
                            continue

                        pair_address = p.get("pairAddress", "")
                        base_addr = p.get("baseToken", {}).get("address", "")
                        quote_addr = p.get("quoteToken", {}).get("address", "")
                        matched_addresses = []
                        if base_addr in address_set:
                            matched_addresses.append(base_addr)
                        if quote_addr in address_set and quote_addr != base_addr:
                            matched_addresses.append(quote_addr)

                        for matched_address in matched_addresses:
                            key = chain_address_key(chain, matched_address)
                            seen_pairs = pair_seen_by_token.setdefault(key, set())
                            dedupe_key = pair_address or f"{p.get('dexId', '')}:{base_addr}:{quote_addr}:{p.get('priceUsd', '')}"
                            if dedupe_key in seen_pairs:
                                continue
                            seen_pairs.add(dedupe_key)
                            results.setdefault(key, []).append(p)
                except Exception as e:
                    self.logger.error(f"Batch fetch failed for {chain} chunk {i}: {e}")
        return results

    def _cleanup_seen(self):
        self.seen_arbs.clear_expired()

    def on_tick(self):
        self._cleanup_seen()
        tokens = self.get_tokens()
        if not tokens:
            self.logger.info("Scanned 0 tokens, 0 new opportunities")
            return

        all_pairs_map = self.fetch_all_token_pairs_batch(tokens)
        if not all_pairs_map:
            self.logger.info(f"Scanned {len(tokens)} tokens, 0 new opportunities")
            return

        results = []
        workers = max(1, min(self.config.max_workers, len(all_pairs_map)))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            task_map = {
                executor.submit(
                    find_arb_opportunities,
                    t["symbol"],
                    all_pairs_map.get(chain_address_key(t.get("chainId"), t["address"]), []),
                    self.config,
                    t.get("chainId"),
                ): t
                for t in tokens if chain_address_key(t.get("chainId"), t["address"]) in all_pairs_map
            }
            for future in task_map:
                try:
                    results.extend(future.result())
                except Exception as e:
                    self.logger.error(f"Scan failed for {task_map[future]['symbol']}: {e}")

        new_opps = 0
        published_by_chain = {}
        scored = sorted(results, key=lambda item: float(item.get("score", 0)), reverse=True)
        for opp in scored:
            chain = normalize_chain_id(opp.get("chainId"))
            per_chain_limit = max(1, int(self.config.max_publish_per_cycle_for(chain)))
            if published_by_chain.get(chain, 0) >= per_chain_limit:
                continue

            score = float(opp.get("score", 0) or 0)
            max_size = float(opp.get("max_size_usd", 0) or 0)
            if score < self.config.min_publish_score_for(chain):
                continue
            if max_size < self.config.min_publish_max_size_for(chain):
                continue

            sym = opp["token"]
            key = f"{chain}:{opp['buy_dex']}:{opp['sell_dex']}:{sym}"
            if key not in self.seen_arbs:
                self.publish(f"{self.config.mqtt_topic_prefix}/{chain}/{sym}", opp)
                self.seen_arbs.add(key)
                new_opps += 1
                published_by_chain[chain] = published_by_chain.get(chain, 0) + 1
                self.logger.info(f"ARB: [{chain}] {sym} {opp['spread_pct']}% buy@{opp['buy_dex']} sell@{opp['sell_dex']} net=${opp['net_profit_100']}")

        self.logger.info(f"Scanned {len(tokens)} tokens, {new_opps} new opportunities")


if __name__ == "__main__":
    ArbService().run()
