import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_config import BaseServiceConfig


class FundingConfig(BaseServiceConfig):
    mqtt_topic_prefix: str = "hbot/funding"

    target_pair: str = "sol_usdc"
    binance_symbol: str = "SOLUSDT"
    poll_interval_seconds: int = 300

    high_rate_threshold: float = 0.0003
    max_funding_rate: float = 0.01
    max_funding_bias: float = 0.3
    bias_sensitivity: float = 1.0

    model_config = {"env_prefix": "FUNDING_"}
