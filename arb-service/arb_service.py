import json
import os
import sys
import time

from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from arb_scanner import find_arb_opportunities
from config import ArbConfig
from shared.base_service import BaseService
from shared.utils import TTLCache


class ArbService(BaseService):
    name = "arb"

    def __init__(self):
        super().__init__(ArbConfig())
        self.seen_arbs = TTLCache(self.config.seen_arb_ttl_seconds, max_size=self.config.cache_max_size)
        self.last_discovery = 0

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
                if not address or not symbol or address in seen_addresses:
                    continue
                seen_addresses.add(address)
                deduped.append({"symbol": symbol, "address": address})
            return deduped
        except Exception as e:
            self.logger.error(f"Failed to load tokens: {e}")
            return []

    def discover_trending_tokens(self):
        try:
            resp = self.session.get(
                self.config.dex_search_url,
                params={"q": self.config.dex_search_query},
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
        static_tokens = self.load_tokens()
        static_addresses = {t["address"] for t in static_tokens}

        now = time.time()
        if now - self.last_discovery > self.config.discovery_interval_seconds:
            dynamic = self.discover_trending_tokens()
            for d in dynamic:
                if d["address"] not in static_addresses:
                    static_tokens.append(d)
                    static_addresses.add(d["address"])
            self.last_discovery = now
            self._merged_tokens = static_tokens

        return getattr(self, "_merged_tokens", static_tokens)

    def fetch_all_token_pairs_batch(self, addresses):
        if not addresses:
            return {}
        results = {}
        batch_size = max(1, min(30, self.config.dex_batch_size))
        for i in range(0, len(addresses), batch_size):
            batch = addresses[i : i + batch_size]
            try:
                url = self._build_dex_tokens_url(batch)
                resp = self.session.get(url, timeout=20)
                resp.raise_for_status()
                data = resp.json()
                pairs = data.get("pairs") if isinstance(data, dict) else data
                if not pairs:
                    continue
                for p in pairs:
                    if p.get("chainId") == "solana":
                        base_addr = p.get("baseToken", {}).get("address", "")
                        results.setdefault(base_addr, []).append(p)
            except Exception as e:
                self.logger.error(f"Batch fetch failed at chunk {i}: {e}")
        return results

    def _cleanup_seen(self):
        self.seen_arbs.clear_expired()

    def on_tick(self):
        self._cleanup_seen()
        tokens = self.get_tokens()
        if not tokens:
            self.logger.info("Scanned 0 tokens, 0 new opportunities")
            return

        addresses = list(dict.fromkeys(t["address"] for t in tokens if t.get("address")))
        all_pairs_map = self.fetch_all_token_pairs_batch(addresses)
        if not all_pairs_map:
            self.logger.info(f"Scanned {len(tokens)} tokens, 0 new opportunities")
            return

        results = []
        workers = max(1, min(self.config.max_workers, len(all_pairs_map)))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            task_map = {
                executor.submit(find_arb_opportunities, t["symbol"], all_pairs_map.get(t["address"], []), self.config): t
                for t in tokens if t["address"] in all_pairs_map
            }
            for future in task_map:
                try:
                    results.extend(future.result())
                except Exception as e:
                    self.logger.error(f"Scan failed for {task_map[future]['symbol']}: {e}")

        new_opps = 0
        for opp in results:
            sym = opp["token"]
            key = f"{opp['buy_dex']}:{opp['sell_dex']}:{sym}"
            if key not in self.seen_arbs:
                self.publish(f"{self.config.mqtt_topic_prefix}/{sym}", opp)
                self.seen_arbs.add(key)
                new_opps += 1
                self.logger.info(f"ARB: {sym} {opp['spread_pct']}% buy@{opp['buy_dex']} sell@{opp['sell_dex']} net=${opp['net_profit_100']}")

        self.logger.info(f"Scanned {len(tokens)} tokens, {new_opps} new opportunities")


if __name__ == "__main__":
    ArbService().run()
