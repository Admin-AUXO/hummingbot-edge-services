import json
import os
import sys

from pydantic import field_validator
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import Union
from shared.base_config import BaseServiceConfig


class CorrelationConfig(BaseServiceConfig):
    mqtt_topic_prefix: str = "hbot/correlation"

    target_pair: str = "sol_usdc"
    target_binance_symbol: str = "SOLUSDT"
    reference_pairs: Union[list, str] = ["ETHUSDT", "BTCUSDT"]
    reference_labels: Union[list, str] = ["sol_eth", "sol_btc"]

    @field_validator("reference_pairs", "reference_labels", mode="before")
    @classmethod
    def parse_list(cls, value):
        if isinstance(value, str):
            if value.startswith("[") and value.endswith("]"):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    pass
            return [s.strip() for s in value.split(",")]
        return value

    candle_interval: str = "5m"
    candle_limit: int = 300
    lookback_period: int = 200

    z_score_overbought: float = 1.5
    z_score_oversold: float = -1.5
    min_correlation: float = 0.5
    max_spread_bias: float = 0.3

    poll_interval_seconds: int = 300

    model_config = {"env_prefix": "CORR_"}
