import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_config import BaseServiceConfig


class InventoryConfig(BaseServiceConfig):
    api_base_url: str = "http://localhost:8000"
    poll_interval_seconds: int = 60

    mqtt_topic_prefix: str = "hbot/inventory"

    target_pair: str = "sol_usdc"
    base_token: str = "SOL"
    quote_token: str = "USDC"
    target_base_pct: float = 0.5

    account_name: str = "master_account"
    connector_name: str = "raydium_clmm"

    max_inventory_skew: float = 0.3
    max_drawdown_pct: float = 0.05
    drawdown_lookback_hours: int = 24

    max_skew_bias: float = 0.5
    skew_sensitivity: float = 1.0

    model_config = {"env_prefix": "INV_"}
