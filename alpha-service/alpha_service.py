import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import AlphaConfig
from scorer import build_new_listing_payload, build_signal_payload, is_new_listing, score_token
from shared.base_service import BaseService
from shared.utils import TTLCache


class AlphaService(BaseService):
    name = "alpha"

    def __init__(self):
        super().__init__(AlphaConfig())
        self.seen_signals = TTLCache(self.config.signal_ttl_seconds, max_size=self.config.cache_max_size)
        self.seen_listings = TTLCache(self.config.listing_ttl_seconds, max_size=self.config.cache_max_size)
        self._strict_list = set()
        self._last_strict_fetch = 0

    def fetch_solana_pairs(self):
        try:
            resp = self.session.get(
                self.config.dex_search_url,
                params={"q": self.config.dex_search_query},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            pairs = data.get("pairs", [])
            return [p for p in pairs if p.get("chainId") == "solana"]
        except Exception as e:
            self.logger.error(f"DexScreener fetch failed: {e}")
            return []

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
        pairs = self.fetch_solana_pairs()
        if not pairs:
            self.logger.info("Fetched 0 Solana pairs")
            return
        strict_list = self.fetch_strict_list()
        self.logger.info(f"Fetched {len(pairs)} Solana pairs, {len(strict_list)} strict tokens")

        def process_pair(pair):
            base_token = pair.get("baseToken", {})
            addr, sym = base_token.get("address", ""), base_token.get("symbol", "?")
            verified = addr in strict_list
            if verified: sym = f"✅ {sym}"

            score, breakdown = score_token(pair, self.config)
            if verified:
                score += 2
                breakdown["verified"] = "Jupiter Strict List"

            if score >= self.config.min_score and addr not in self.seen_signals:
                p = build_signal_payload(pair, score, breakdown)
                if verified: p["token"] = sym
                self.publish(f"{self.config.mqtt_topic_prefix}/signal/{sym.replace('✅ ', '')}", p)
                self.seen_signals.add(addr)
                self.logger.info(f"SIGNAL: {sym} score={score} liq=${p['liquidity']:,.0f}")

            if is_new_listing(pair, self.config) and addr not in self.seen_listings:
                p = build_new_listing_payload(pair)
                if verified: p["token"] = sym
                self.publish(f"{self.config.mqtt_topic_prefix}/new_listing/{sym.replace('✅ ', '')}", p)
                self.seen_listings.add(addr)
                self.logger.info(f"NEW LISTING: {sym} age={p['age_hours']}h liq=${p['liquidity']:,.0f}")

        workers = max(1, min(self.config.max_workers, len(pairs)))
        with ThreadPoolExecutor(max_workers=workers) as ex:
            list(ex.map(process_pair, pairs))


if __name__ == "__main__":
    AlphaService().run()
