import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_config import BaseServiceConfig


class MigrationConfig(BaseServiceConfig):
    mqtt_topic_prefix: str = "hbot/migration"
    poll_interval_seconds: int = 300

    events_file: str = "./events.json"
    dex_search_url: str = "https://api.dexscreener.com/latest/dex/search?q=SOL"

    new_pool_max_age_minutes: int = 60
    new_pool_min_liquidity: float = 5000.0
    new_pool_min_volume: float = 1000.0

    pre_event_hours: int = 24
    post_event_hours: int = 48

    model_config = {"env_prefix": "MIG_"}
