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

    def fetch_defillama_pools(self):
        try:
            resp = self.session.get("https://yields.llama.fi/pools", timeout=30)
            resp.raise_for_status()
            data = resp.json().get("data", [])
            return [p for p in data if p.get("chain", "").lower() == "solana"]
        except Exception as e:
            self.logger.error(f"DeFiLlama fetch failed: {e}")
            return []

    def on_tick(self):
        pools = self.load_pools()
        payloads, llama_pools = [], self.fetch_defillama_pools()

        llama_map = {}
        for lp in llama_pools:
            symbol = (lp.get("symbol") or "").upper()
            if symbol not in llama_map: llama_map[symbol] = []
            llama_map[symbol].append(lp)

        addresses = [p.get("address", "") for p in pools if p.get("address")]
        md_batch = self.fetch_market_data(addresses)

        for pool in pools:
            if pool.get("risk_score", 10) > self.config.max_risk_score: continue
            
            addr = pool.get("address", "")
            md = md_batch.get(addr, {"volume_24h": 0, "liquidity": 0})
            vol, liq = md["volume_24h"], md["liquidity"]
            if liq < self.config.min_liquidity: continue

            dex, pair = pool.get("dex", "").lower(), pool.get("pair", "")
            s1, s2 = pair.replace("/", "-"), "-".join(pair.split("/")[::-1])

            best_llama = None
            for matched_symbol in [s1, s2]:
                if matched_symbol in llama_map:
                    for lp in llama_map[matched_symbol]:
                        if dex in lp.get("project", "").lower():
                            if not best_llama or lp.get("tvlUsd", 0) > best_llama.get("tvlUsd", 0):
                                best_llama = lp

            if best_llama:
                fee_apr = float(best_llama.get("apyBase", 0) or 0)
                reward_apr = float(best_llama.get("apyReward", 0) or 0)
                liq = max(liq, float(best_llama.get("tvlUsd", 0)))
            else:
                fee_apr = estimate_fee_apr(vol, liq, pool.get("fee_tier", 0.25))
                reward_apr = pool.get("reward_apr", 0)

            eff = calc_effective_apr(fee_apr, reward_apr)
            risk_adj = calc_risk_adjusted_apr(eff, pool.get("risk_score", 5))
            if eff < self.config.min_effective_apr: continue

            p = build_pool_payload(pool, fee_apr, eff, risk_adj, vol, liq)
            payloads.append(p)
            self.publish(f"{self.config.mqtt_topic_prefix}/{pool.get('token', 'unknown')}", p)

        ranked = rank_pools(payloads)
        self.publish(f"{self.config.mqtt_topic_prefix}/summary", {"total_pools": len(ranked), "top_pools": ranked[:5], "timestamp": time.time()})

        if ranked:
            top = ranked[0]
            self.logger.info(f"Top pool: {top['pair']} on {top['dex']} APR={top['effective_apr']}% liq=${top['liquidity']:,.0f}")
        self.logger.info(f"Scanned {len(pools)} pools, {len(ranked)} qualify")


if __name__ == "__main__":
    RewardsService().run()
