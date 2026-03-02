import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_config import BaseServiceConfig


class SessionConfig(BaseServiceConfig):
    mqtt_topic_prefix: str = "hbot/session"

    target_pair: str = "sol_usdc"
    poll_interval_seconds: int = 60

    asia_start_hour: int = 4
    eu_start_hour: int = 8
    us_start_hour: int = 14
    night_start_hour: int = 20

    asia_spread_mult: float = 1.2
    eu_spread_mult: float = 1.0
    us_spread_mult: float = 0.8
    night_spread_mult: float = 1.5

    model_config = {"env_prefix": "SESSION_"}
