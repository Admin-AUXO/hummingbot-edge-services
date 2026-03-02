import json
import os
import sys
import time

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from arb_scanner import find_arb_opportunities
from config import ArbConfig
from shared.base_service import BaseService


class ArbService(BaseService):
    name = "arb"

    def __init__(self):
        super().__init__(ArbConfig())
        self.seen_arbs = set()

    def load_tokens(self):
        try:
            with open(self.config.tokens_file, "r") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load tokens: {e}")
            return []

    def fetch_token_pairs(self, address):
        try:
            resp = requests.get(f"{self.config.dex_token_url}{address}", timeout=15)
            resp.raise_for_status()
            data = resp.json()
            pairs = data.get("pairs", [])
            return [p for p in pairs if p.get("chainId") == "solana"]
        except Exception as e:
            self.logger.error(f"DexScreener fetch failed for {address}: {e}")
            return []

    def scan_and_publish(self):
        tokens = self.load_tokens()
        total_opps = 0

        for token_entry in tokens:
            symbol = token_entry["symbol"]
            address = token_entry["address"]
            pairs = self.fetch_token_pairs(address)

            if not pairs:
                continue

            opportunities = find_arb_opportunities(symbol, pairs, self.config)

            for opp in opportunities:
                key = f"{opp['buy_dex']}:{opp['sell_dex']}:{symbol}"
                if key in self.seen_arbs:
                    continue

                topic = f"{self.config.mqtt_topic_prefix}/{symbol}"
                self.publish(topic, opp)
                self.seen_arbs.add(key)
                total_opps += 1
                self.logger.info(
                    f"ARB: {symbol} {opp['spread_pct']}% "
                    f"buy@{opp['buy_dex']}=${opp['buy_price']} "
                    f"sell@{opp['sell_dex']}=${opp['sell_price']}"
                )

        if len(self.seen_arbs) > 5000:
            self.seen_arbs.clear()

        self.logger.info(f"Scanned {len(tokens)} tokens, {total_opps} new opportunities")

    def run(self):
        self.connect_mqtt()
        self.logger.info(f"Arb scanner started, polling every {self.config.poll_interval_seconds}s")

        while self.running:
            try:
                self.scan_and_publish()
            except Exception as e:
                self.logger.error(f"Scan error: {e}")
            self.sleep_loop(self.config.poll_interval_seconds)

        self.shutdown_mqtt()


if __name__ == "__main__":
    ArbService().run()
