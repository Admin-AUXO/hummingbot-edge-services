import json
import os
import sys
import time

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import RewardsConfig
from reward_calculator import (
    build_pool_payload,
    calc_effective_apr,
    calc_risk_adjusted_apr,
    estimate_fee_apr,
    rank_pools,
)
from shared.base_service import BaseService


class RewardsService(BaseService):
    name = "rewards"

    def __init__(self):
        super().__init__(RewardsConfig())
        self.last_rankings = []

    def load_pools(self):
        try:
            with open(self.config.pools_file, "r") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load pools: {e}")
            return []

    def fetch_token_data_batch(self, addresses):
        if not addresses:
            return {}
        results = {}
        for i in range(0, len(addresses), 30):
            chunk = addresses[i:i+30]
            addr_str = ",".join(chunk)
            try:
                resp = requests.get(f"{self.config.dex_token_url}{addr_str}", timeout=15)
                resp.raise_for_status()
                data = resp.json()
                for pair in data.get("pairs", []):
                    if pair.get("chainId") == "solana":
                        addr = pair.get("baseToken", {}).get("address", "")
                        liq = float(pair.get("liquidity", {}).get("usd", 0))
                        if addr not in results or liq > results[addr].get("liquidity", 0):
                            results[addr] = {
                                "volume_24h": float(pair.get("volume", {}).get("h24", 0)),
                                "liquidity": liq,
                            }
            except Exception as e:
                self.logger.error(f"DexScreener batch fetch failed: {e}")
        return results

    def fetch_defillama_pools(self):
        try:
            resp = requests.get("https://yields.llama.fi/pools", timeout=30)
            resp.raise_for_status()
            data = resp.json().get("data", [])
            return [p for p in data if p.get("chain", "").lower() == "solana"]
        except Exception as e:
            self.logger.error(f"DeFiLlama fetch failed: {e}")
            return []

    def scan_and_publish(self):
        pools = self.load_pools()
        payloads = []
        llama_pools = self.fetch_defillama_pools()

        addresses = [p.get("address", "") for p in pools if p.get("address")]
        market_data_batch = self.fetch_token_data_batch(addresses)

        for pool in pools:
            if pool.get("risk_score", 10) > self.config.max_risk_score:
                continue

            address = pool.get("address", "")
            market_data = market_data_batch.get(address, {"volume_24h": 0, "liquidity": 0})
            volume_24h = market_data["volume_24h"]
            liquidity = market_data["liquidity"]

            if liquidity < self.config.min_liquidity:
                continue

            dex = pool.get("dex", "").lower()
            pair_name = pool.get("pair", "")
            symbol_match = pair_name.replace("/", "-")
            rev_symbol_match = "-".join(pair_name.split("/")[::-1])

            best_llama = None
            for lp in llama_pools:
                lp_project = lp.get("project", "").lower()
                if dex in lp_project:
                    lp_symbol = (lp.get("symbol") or "").upper()
                    if lp_symbol == symbol_match or lp_symbol == rev_symbol_match:
                        if best_llama is None or lp.get("tvlUsd", 0) > best_llama.get("tvlUsd", 0):
                            best_llama = lp

            if best_llama:
                fee_apr = float(best_llama.get("apyBase", 0) or 0)
                reward_apr = float(best_llama.get("apyReward", 0) or 0)
                liquidity = max(liquidity, float(best_llama.get("tvlUsd", 0)))
            else:
                fee_apr = estimate_fee_apr(volume_24h, liquidity, pool.get("fee_tier", 0.25))
                reward_apr = pool.get("reward_apr", 0)

            effective = calc_effective_apr(fee_apr, reward_apr)
            risk_adjusted = calc_risk_adjusted_apr(effective, pool.get("risk_score", 5))

            if effective < self.config.min_effective_apr:
                continue

            payload = build_pool_payload(pool, fee_apr, effective, risk_adjusted, volume_24h, liquidity)
            payloads.append(payload)

            topic = f"{self.config.mqtt_topic_prefix}/{pool.get('token', 'unknown')}"
            self.publish(topic, payload)

        ranked = rank_pools(payloads)
        summary = {
            "total_pools": len(ranked),
            "top_pools": ranked[:5],
            "timestamp": time.time(),
        }
        self.publish(f"{self.config.mqtt_topic_prefix}/summary", summary)

        if ranked:
            top = ranked[0]
            self.logger.info(
                f"Top pool: {top['pair']} on {top['dex']} "
                f"APR={top['effective_apr']}% (risk-adj={top['risk_adjusted_apr']}%) "
                f"liq=${top['liquidity']:,.0f}"
            )
        self.logger.info(f"Scanned {len(pools)} pools, {len(ranked)} qualify")

    def run(self):
        self.connect_mqtt()
        self.logger.info(f"Rewards tracker started, polling every {self.config.poll_interval_seconds}s")

        while self.running:
            try:
                self.scan_and_publish()
            except Exception as e:
                self.logger.error(f"Scan error: {e}")
            self.sleep_loop(self.config.poll_interval_seconds)

        self.shutdown_mqtt()


if __name__ == "__main__":
    RewardsService().run()
