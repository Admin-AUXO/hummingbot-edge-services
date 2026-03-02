import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_config import BaseServiceConfig


class AlphaConfig(BaseServiceConfig):
    mqtt_topic_prefix: str = "hbot/alpha"
    poll_interval_seconds: int = 900

    min_score: int = 7
    min_liquidity: float = 50000.0
    new_listing_max_age_hours: int = 48

    vol_mcap_threshold: float = 0.5
    h1_vol_ratio_threshold: float = 0.20
    buy_sell_ratio_threshold: float = 1.5

    dex_search_url: str = "https://api.dexscreener.com/latest/dex/search?q=SOL"

    model_config = {"env_prefix": "ALPHA_"}
