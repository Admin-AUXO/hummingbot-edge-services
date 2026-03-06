import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_config import BaseServiceConfig
from shared.utils import normalize_chain_id, parse_json_mapping


class ArbConfig(BaseServiceConfig):
    mqtt_topic_prefix: str = "hbot/arb"
    poll_interval_seconds: int = 30
    default_chain_id: str = "solana"
    supported_chains: str = "solana,base,bsc,arbitrum"
    dex_search_queries_json: str = '{"solana": ["SOL", "USDC"], "base": ["WETH", "USDC"], "bsc": ["WBNB", "USDT"], "arbitrum": ["WETH", "USDC"]}'
    gas_cost_usd_json: str = '{"solana": 0.02, "base": 0.10, "bsc": 0.12, "arbitrum": 0.12}'
    est_slippage_pct_json: str = '{"solana": 0.3, "base": 0.35, "bsc": 0.4, "arbitrum": 0.35}'
    min_arb_pct_json: str = '{"solana": 15.5, "base": 3.0, "bsc": 4.8, "arbitrum": 3.0}'
    slippage_liquidity_impact_factor: float = 60.0
    slippage_volatility_impact_factor: float = 0.08

    dex_token_url: str = "https://api.dexscreener.com/tokens/v1"
    dex_search_url: str = "https://api.dexscreener.com/latest/dex/search"
    dex_search_query: str = "SOL"
    dex_batch_size: int = 30
    tokens_file: str = "./tokens.json"
    auto_update_tokens_file: bool = True
    tokens_refresh_interval_seconds: int = 21600
    tokens_max_per_chain: int = 10
    tokens_max_per_chain_json: str = '{"solana": 6, "base": 12, "bsc": 8, "arbitrum": 12}'
    tokens_min_liquidity_usd: float = 50000.0
    tokens_min_liquidity_usd_json: str = '{"solana": 150000, "base": 120000, "bsc": 150000, "arbitrum": 120000}'
    tokens_min_volume_24h_usd: float = 25000.0
    tokens_min_volume_24h_usd_json: str = '{"solana": 110000, "base": 80000, "bsc": 90000, "arbitrum": 80000}'

    max_workers: int = 10
    discovery_interval_seconds: int = 1800
    seen_arb_ttl_seconds: int = 600
    cache_max_size: int = 30000

    min_arb_pct: float = 14.0
    min_net_profit_100: float = 10.0
    min_publish_score: float = 12.0
    min_publish_score_json: str = '{"solana": 18.0, "base": 10.0, "bsc": 12.0, "arbitrum": 10.0}'
    min_publish_max_size_usd: float = 75.0
    min_publish_max_size_usd_json: str = '{"solana": 120.0, "base": 65.0, "bsc": 85.0, "arbitrum": 65.0}'
    max_publish_per_cycle: int = 25
    max_publish_per_cycle_json: str = '{"solana": 6, "base": 10, "bsc": 5, "arbitrum": 10}'
    min_liquidity: float = 10000.0
    min_dex_count: int = 2
    min_volume_24h: float = 5000.0
    max_pool_age_hours: float = 0

    max_spread_pct: float = 100.0

    max_trade_pct_of_liq: float = 0.02
    est_slippage_pct: float = 0.3
    gas_cost_usd: float = 0.01

    model_config = {"env_prefix": "ARB_"}

    def gas_cost_for(self, chain_id: str) -> float:
        overrides = parse_json_mapping(self.gas_cost_usd_json)
        chain = normalize_chain_id(chain_id)
        return float(overrides.get(chain, self.gas_cost_usd))

    def est_slippage_for(self, chain_id: str) -> float:
        overrides = parse_json_mapping(self.est_slippage_pct_json)
        chain = normalize_chain_id(chain_id)
        return float(overrides.get(chain, self.est_slippage_pct))

    def min_arb_for(self, chain_id: str) -> float:
        overrides = parse_json_mapping(self.min_arb_pct_json)
        chain = normalize_chain_id(chain_id)
        return float(overrides.get(chain, self.min_arb_pct))

    def tokens_max_per_chain_for(self, chain_id: str) -> int:
        overrides = parse_json_mapping(self.tokens_max_per_chain_json)
        chain = normalize_chain_id(chain_id)
        return int(overrides.get(chain, self.tokens_max_per_chain))

    def tokens_min_liquidity_for(self, chain_id: str) -> float:
        overrides = parse_json_mapping(self.tokens_min_liquidity_usd_json)
        chain = normalize_chain_id(chain_id)
        return float(overrides.get(chain, self.tokens_min_liquidity_usd))

    def tokens_min_volume_for(self, chain_id: str) -> float:
        overrides = parse_json_mapping(self.tokens_min_volume_24h_usd_json)
        chain = normalize_chain_id(chain_id)
        return float(overrides.get(chain, self.tokens_min_volume_24h_usd))

    def min_publish_score_for(self, chain_id: str) -> float:
        overrides = parse_json_mapping(self.min_publish_score_json)
        chain = normalize_chain_id(chain_id)
        return float(overrides.get(chain, self.min_publish_score))

    def min_publish_max_size_for(self, chain_id: str) -> float:
        overrides = parse_json_mapping(self.min_publish_max_size_usd_json)
        chain = normalize_chain_id(chain_id)
        return float(overrides.get(chain, self.min_publish_max_size_usd))

    def max_publish_per_cycle_for(self, chain_id: str) -> int:
        overrides = parse_json_mapping(self.max_publish_per_cycle_json)
        chain = normalize_chain_id(chain_id)
        return int(overrides.get(chain, self.max_publish_per_cycle))
