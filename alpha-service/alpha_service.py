import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import AlphaConfig
from scorer import build_new_listing_payload, build_signal_payload, is_new_listing, score_token
from shared.base_service import BaseService
from shared.utils import TTLCache


class AlphaService(BaseService):
    name = "alpha"

    def __init__(self):
        super().__init__(AlphaConfig())
        self.seen_signals = TTLCache(7200)
        self.seen_listings = TTLCache(14400)
        self._strict_list = set()
        self._last_strict_fetch = 0

    def fetch_solana_pairs(self):
        try:
            resp = self.session.get(self.config.dex_search_url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            pairs = data.get("pairs", [])
            return [p for p in pairs if p.get("chainId") == "solana"]
        except Exception as e:
            self.logger.error(f"DexScreener fetch failed: {e}")
            return []

    def fetch_strict_list(self):
        now = time.time()
        if now - self._last_strict_fetch < 3600 and self._strict_list:
            return self._strict_list
            
        try:
            resp = self.session.get("https://token.jup.ag/strict", timeout=15)
            resp.raise_for_status()
            data = resp.json()
            self._strict_list = {t.get("address") for t in data if isinstance(t, dict)}
            self._last_strict_fetch = now
            return self._strict_list
        except Exception as e:
            self.logger.error(f"Jupiter Strict fetch failed (using cache): {e}")
            return self._strict_list

    def _cap_seen(self):
        self.seen_signals.clear_expired()
        self.seen_listings.clear_expired()

    def on_tick(self):
        self._cap_seen()
        pairs = self.fetch_solana_pairs()
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

        with ThreadPoolExecutor(max_workers=5) as ex:
            ex.map(process_pair, pairs)


if __name__ == "__main__":
    AlphaService().run()
