import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_config import BaseServiceConfig


class LabConfig(BaseServiceConfig):
    data_file: str = "./experiments.json"
    eval_interval_seconds: int = 300

    production_capital_pct: float = 0.70
    testing_capital_pct: float = 0.20
    exploration_capital_pct: float = 0.10

    default_trial_hours: int = 72
    default_kill_loss: float = 5.0
    default_kill_drawdown: float = 0.10
    default_min_win_rate: float = 0.40
    default_success_daily_pnl: float = 0.30

    model_config = {"env_prefix": "LAB_"}
