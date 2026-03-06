import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_config import BaseServiceConfig
from shared.utils import normalize_chain_id, parse_json_mapping


class AlphaConfig(BaseServiceConfig):
    mqtt_topic_prefix: str = "hbot/alpha"
    poll_interval_seconds: int = 900
    default_chain_id: str = "solana"
    supported_chains: str = "solana,base,bsc,arbitrum"
    dex_search_queries_json: str = '{"solana": ["SOL", "USDC"], "base": ["WETH", "USDC"], "bsc": ["WBNB", "USDT"], "arbitrum": ["WETH", "USDC"]}'

    min_score: int = 8
    min_liquidity: float = 50000.0
    min_signal_volume_24h: float = 75000.0
    min_signal_volume_24h_json: str = '{"solana": 110000, "base": 85000, "bsc": 90000, "arbitrum": 85000}'
    min_new_listing_volume_24h: float = 50000.0
    min_new_listing_volume_24h_json: str = '{"solana": 90000, "base": 70000, "bsc": 70000, "arbitrum": 70000}'
    min_new_listing_score: int = 7
    min_new_listing_score_json: str = '{"solana": 9, "base": 6, "bsc": 7, "arbitrum": 6}'
    new_listing_max_age_hours: int = 48

    vol_mcap_threshold: float = 0.5
    h1_vol_ratio_threshold: float = 0.20
    buy_sell_ratio_threshold: float = 1.5

    dex_search_url: str = "https://api.dexscreener.com/latest/dex/search"
    dex_search_query: str = "SOL"

    max_workers: int = 6
    strict_list_ttl_seconds: int = 3600
    signal_ttl_seconds: int = 7200
    listing_ttl_seconds: int = 14400
    cache_max_size: int = 20000

    model_config = {"env_prefix": "ALPHA_"}

    def min_signal_volume_for(self, chain_id: str) -> float:
        overrides = parse_json_mapping(self.min_signal_volume_24h_json)
        chain = normalize_chain_id(chain_id)
        return float(overrides.get(chain, self.min_signal_volume_24h))

    def min_new_listing_volume_for(self, chain_id: str) -> float:
        overrides = parse_json_mapping(self.min_new_listing_volume_24h_json)
        chain = normalize_chain_id(chain_id)
        return float(overrides.get(chain, self.min_new_listing_volume_24h))

    def min_new_listing_score_for(self, chain_id: str) -> int:
        overrides = parse_json_mapping(self.min_new_listing_score_json)
        chain = normalize_chain_id(chain_id)
        return int(overrides.get(chain, self.min_new_listing_score))
