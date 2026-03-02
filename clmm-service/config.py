import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_config import BaseServiceConfig


class ClmmConfig(BaseServiceConfig):
    mqtt_topic_prefix: str = "hbot/clmm"
    eval_interval_seconds: int = 120

    target_pair: str = "sol_usdc"
    base_range_pct: float = 2.0

    regime_multipliers: dict = {
        "SIDEWAYS": 0.5,
        "BULL": 1.0,
        "BEAR": 1.0,
        "SPIKE": 2.5,
    }

    session_multipliers: dict = {
        "US": 0.8,
        "EU": 0.9,
        "ASIA": 1.1,
        "NIGHT": 1.5,
    }

    rebalance_threshold_pct: float = 70.0
    natr_tight_threshold: float = 0.015
    natr_wide_threshold: float = 0.035

    model_config = {"env_prefix": "CLMM_"}
