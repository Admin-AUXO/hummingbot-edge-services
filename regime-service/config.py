import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_config import BaseServiceConfig


class RegimeConfig(BaseServiceConfig):
    mqtt_topic_prefix: str = "hbot/regime"

    trading_pair: str = "sol_usdc"
    binance_symbol: str = "SOLUSDT"
    candle_interval: str = "4h"
    candle_limit: int = 100
    poll_interval_seconds: int = 300

    natr_period: int = 14
    bb_period: int = 20
    bb_std: float = 2.0
    ma_period: int = 20

    spike_natr_threshold: float = 0.03
    spike_bb_width_threshold: float = 0.06
    bull_ma_threshold: float = 1.01
    bear_ma_threshold: float = 0.99
    higher_highs_lookback: int = 3

    model_config = {"env_prefix": "REGIME_"}
