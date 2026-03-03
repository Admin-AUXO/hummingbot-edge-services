import os
import sys
import time

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import AlphaConfig
from scorer import build_new_listing_payload, build_signal_payload, is_new_listing, score_token
from shared.base_service import BaseService


MAX_SEEN = 5000


class AlphaService(BaseService):
    name = "alpha"

    def __init__(self):
        super().__init__(AlphaConfig())
        self.seen_signals = set()
        self.seen_listings = set()

    def fetch_solana_pairs(self):
        try:
            resp = requests.get(self.config.dex_search_url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            pairs = data.get("pairs", [])
            return [p for p in pairs if p.get("chainId") == "solana"]
        except Exception as e:
            self.logger.error(f"DexScreener fetch failed: {e}")
            return []

    def fetch_strict_list(self):
        try:
            resp = requests.get("https://token.jup.ag/strict", timeout=15)
            resp.raise_for_status()
            data = resp.json()
            return {t.get("address") for t in data if isinstance(t, dict)}
        except Exception as e:
            self.logger.error(f"Jupiter Strict fetch failed: {e}")
            return set()

    def _cap_seen(self):
        if len(self.seen_signals) > MAX_SEEN:
            self.seen_signals.clear()
        if len(self.seen_listings) > MAX_SEEN:
            self.seen_listings.clear()

    def scan_and_publish(self):
        self._cap_seen()
        pairs = self.fetch_solana_pairs()
        strict_list = self.fetch_strict_list()
        self.logger.info(f"Fetched {len(pairs)} Solana pairs, {len(strict_list)} strict tokens")

        for pair in pairs:
            pair_addr = pair.get("pairAddress", "")
            base_token_addr = pair.get("baseToken", {}).get("address", "")
            token_symbol = pair.get("baseToken", {}).get("symbol", "?")

            is_verified = base_token_addr in strict_list
            if is_verified:
                token_symbol = f"✅ {token_symbol}"

            score, breakdown = score_token(pair, self.config)

            if is_verified:
                score += 2
                breakdown["verified"] = "Jupiter Strict List"

            if score >= self.config.min_score and pair_addr not in self.seen_signals:
                payload = build_signal_payload(pair, score, breakdown)
                if is_verified:
                    payload["token"] = token_symbol
                topic = f"{self.config.mqtt_topic_prefix}/signal/{token_symbol.replace('✅ ', '')}"
                self.publish(topic, payload)
                self.seen_signals.add(pair_addr)
                self.logger.info(f"SIGNAL: {token_symbol} score={score} liq=${payload['liquidity']:,.0f}")

            if is_new_listing(pair, self.config) and pair_addr not in self.seen_listings:
                payload = build_new_listing_payload(pair)
                if is_verified:
                    payload["token"] = token_symbol
                topic = f"{self.config.mqtt_topic_prefix}/new_listing/{token_symbol.replace('✅ ', '')}"
                self.publish(topic, payload)
                self.seen_listings.add(pair_addr)
                self.logger.info(f"NEW LISTING: {token_symbol} age={payload['age_hours']}h liq=${payload['liquidity']:,.0f}")

    def run(self):
        self.connect_mqtt()
        self.logger.info(f"Alpha service started, polling every {self.config.poll_interval_seconds}s")

        while self.running:
            try:
                self.scan_and_publish()
            except Exception as e:
                self.logger.error(f"Scan error: {e}")
            self.sleep_loop(self.config.poll_interval_seconds)

        self.shutdown_mqtt()


if __name__ == "__main__":
    AlphaService().run()
