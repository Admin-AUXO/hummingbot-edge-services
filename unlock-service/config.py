import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_config import BaseServiceConfig


class UnlockConfig(BaseServiceConfig):
    mqtt_topic_prefix: str = "hbot/unlock"
    poll_interval_seconds: int = 3600

    data_file: str = "./unlocks.json"
    pre_unlock_hours: int = 24
    post_unlock_hours: int = 48
    min_unlock_pct: float = 2.0

    pre_unlock_buy_spread_mult: float = 1.5
    pre_unlock_sell_spread_mult: float = 0.8
    post_unlock_buy_spread_mult: float = 0.8
    post_unlock_sell_spread_mult: float = 1.0

    model_config = {"env_prefix": "UNLOCK_"}
