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
        self.seen_arbs = {}  # key -> timestamp (for TTL expiry)
        self.last_discovery = 0

    def load_tokens(self):
        try:
            with open(self.config.tokens_file, "r") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load tokens: {e}")
            return []

    def discover_trending_tokens(self):
        """Auto-discover trending Solana tokens from DexScreener."""
        try:
            resp = requests.get(
                "https://api.dexscreener.com/latest/dex/search?q=SOL",
                timeout=15,
            )
            resp.raise_for_status()
            pairs = resp.json().get("pairs") or []

            discovered = {}
            for pair in pairs:
                if pair.get("chainId") != "solana":
                    continue
                base = pair.get("baseToken", {})
                symbol = base.get("symbol", "")
                address = base.get("address", "")
                liq = float(pair.get("liquidity", {}).get("usd", 0))
                vol = float(pair.get("volume", {}).get("h24", 0))

                if not symbol or not address or liq < 10000 or vol < 5000:
                    continue

                # Keep highest liquidity entry per token
                if symbol not in discovered or liq > discovered[symbol]["liq"]:
                    discovered[symbol] = {
                        "symbol": symbol,
                        "address": address,
                        "liq": liq,
                    }

            new_tokens = [
                {"symbol": d["symbol"], "address": d["address"]}
                for d in sorted(discovered.values(), key=lambda x: x["liq"], reverse=True)[:50]
            ]
            self.logger.info(f"Auto-discovered {len(new_tokens)} trending Solana tokens")
            return new_tokens

        except Exception as e:
            self.logger.error(f"Token discovery failed: {e}")
            return []

    def get_tokens(self):
        """Get tokens from file + auto-discovery (refreshed every 30 min)."""
        static_tokens = self.load_tokens()
        static_addresses = {t["address"] for t in static_tokens}

        now = time.time()
        if now - self.last_discovery > 1800:  # Refresh discovery every 30 min
            dynamic = self.discover_trending_tokens()
            # Merge: static tokens first, then discovered ones not already in list
            for d in dynamic:
                if d["address"] not in static_addresses:
                    static_tokens.append(d)
                    static_addresses.add(d["address"])
            self.last_discovery = now
            self._merged_tokens = static_tokens

        return getattr(self, "_merged_tokens", static_tokens)

    def fetch_token_pairs(self, address):
        try:
            resp = requests.get(f"{self.config.dex_token_url}{address}", timeout=15)
            resp.raise_for_status()
            data = resp.json()
            pairs = data.get("pairs") or []
            return [p for p in pairs if p.get("chainId") == "solana"]
        except Exception as e:
            self.logger.error(f"DexScreener fetch failed for {address}: {e}")
            return []

    def _cleanup_seen(self):
        """Remove seen arbs older than 10 minutes so opportunities can re-appear."""
        now = time.time()
        expired = [k for k, ts in self.seen_arbs.items() if now - ts > 600]
        for k in expired:
            del self.seen_arbs[k]

    def scan_and_publish(self):
        self._cleanup_seen()
        tokens = self.get_tokens()
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
                self.seen_arbs[key] = time.time()
                total_opps += 1
                self.logger.info(
                    f"ARB: {symbol} {opp['spread_pct']}% "
                    f"buy@{opp['buy_dex']}=${opp['buy_price']} "
                    f"sell@{opp['sell_dex']}=${opp['sell_price']} "
                    f"net/100=${opp['net_profit_100']} score={opp['score']}"
                )

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
