import json
import os
import sys
from typing import Union

from pydantic import field_validator

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_config import BaseServiceConfig


class BacktestConfig(BaseServiceConfig):
    api_base_url: str = "http://localhost:8000"

    report_topic: str = "hbot/backtest"

    target_pair: str = "sol_usdc"
    controller_name: str = "pmm_correlation"
    controller_config_path: str = "A:/Trading/hummingbot-api/bots/conf/controllers/pmm_correlation_sol_usdc.yml"

    start_time: int = 1735689600
    end_time: int = 1738368000
    backtesting_resolution: str = "1m"
    trade_cost: float = 0.0006

    spread_values: Union[list, str] = [0.5, 1.0, 1.5, 2.0]
    stop_loss_values: Union[list, str] = [0.015, 0.02, 0.03]
    take_profit_values: Union[list, str] = [0.01, 0.015, 0.02]
    time_limit_values: Union[list, str] = [900, 1800, 2700]

    @field_validator("spread_values", "stop_loss_values", "take_profit_values", "time_limit_values", mode="before")
    @classmethod
    def parse_list(cls, value):
        if isinstance(value, str):
            if value.startswith("[") and value.endswith("]"):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    pass
            return [val.strip() for val in value.split(",")]
        return value

    output_dir: str = "./results"
    top_n: int = 10

    model_config = {"env_prefix": "BT_"}
