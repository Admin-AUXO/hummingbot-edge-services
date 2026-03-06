import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_config import BaseServiceConfig


class NarrativeConfig(BaseServiceConfig):
    mqtt_topic_prefix: str = "hbot/narrative"
    poll_interval_seconds: int = 1800

    dex_search_url: str = "https://api.dexscreener.com/latest/dex/search"
    narratives_file: str = "./narratives.json"

    min_volume_24h: float = 50000.0
    min_volume_spike: float = 2.0
    min_price_change_1h: float = 1.0
    min_liquidity: float = 20000.0

    max_workers: int = 5
    alerted_tokens_limit: int = 5000
    prev_volumes_limit: int = 10000

    model_config = {"env_prefix": "NARR_"}
