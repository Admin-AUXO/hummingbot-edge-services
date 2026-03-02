import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_config import BaseServiceConfig


class CorrelationConfig(BaseServiceConfig):
    mqtt_topic_prefix: str = "hbot/correlation"

    target_pair: str = "sol_usdc"
    target_binance_symbol: str = "SOLUSDT"
    reference_pairs: list = ["ETHUSDT", "BTCUSDT"]
    reference_labels: list = ["sol_eth", "sol_btc"]

    candle_interval: str = "5m"
    candle_limit: int = 300
    lookback_period: int = 200

    z_score_overbought: float = 1.5
    z_score_oversold: float = -1.5
    min_correlation: float = 0.5
    max_spread_bias: float = 0.3

    poll_interval_seconds: int = 300

    model_config = {"env_prefix": "CORR_"}
