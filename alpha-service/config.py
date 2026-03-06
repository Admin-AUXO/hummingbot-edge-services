import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_config import BaseServiceConfig


class AlphaConfig(BaseServiceConfig):
    mqtt_topic_prefix: str = "hbot/alpha"
    poll_interval_seconds: int = 900

    min_score: int = 8
    min_liquidity: float = 50000.0
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
