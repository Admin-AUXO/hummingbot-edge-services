import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_config import BaseServiceConfig


class PnlConfig(BaseServiceConfig):
    api_base_url: str = "http://localhost:8000"
    poll_interval_seconds: int = 300

    target_pair: str = "sol_usdc"
    account_name: str = "master_account"
    connector_name: str = "raydium_clmm"

    report_topic: str = "hbot/analytics"
    lookback_hours: int = 24

    model_config = {"env_prefix": "PNL_"}
