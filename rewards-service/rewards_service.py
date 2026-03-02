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

    def fetch_token_data(self, address):
        try:
            resp = requests.get(f"{self.config.dex_token_url}{address}", timeout=15)
            resp.raise_for_status()
            data = resp.json()
            pairs = data.get("pairs", [])
            for pair in pairs:
                if pair.get("chainId") == "solana":
                    return {
                        "volume_24h": float(pair.get("volume", {}).get("h24", 0)),
                        "liquidity": float(pair.get("liquidity", {}).get("usd", 0)),
                    }
        except Exception as e:
            self.logger.error(f"DexScreener fetch failed for {address}: {e}")
        return {"volume_24h": 0, "liquidity": 0}

    def scan_and_publish(self):
        pools = self.load_pools()
        payloads = []

        for pool in pools:
            if pool.get("risk_score", 10) > self.config.max_risk_score:
                continue

            address = pool.get("address", "")
            market_data = self.fetch_token_data(address)
            volume_24h = market_data["volume_24h"]
            liquidity = market_data["liquidity"]

            if liquidity < self.config.min_liquidity:
                continue

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
