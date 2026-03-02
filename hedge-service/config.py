import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_config import BaseServiceConfig


class HedgeConfig(BaseServiceConfig):
    api_base_url: str = "http://localhost:8000"
    poll_interval_seconds: int = 30

    mqtt_topic_prefix: str = "hbot/hedge"
    target_pair: str = "sol_usdc"

    spot_account_name: str = "master_account"
    spot_connector_name: str = "raydium_clmm"

    perp_account_name: str = "master_account"
    perp_connector_name: str = "hyperliquid_perpetual"
    perp_trading_pair: str = "SOL-USD"

    delta_threshold: float = 0.5
    max_hedge_order_size: float = 10.0
    hedge_leverage: int = 5
    order_type: str = "MARKET"

    max_position_size: float = 50.0
    cooldown_seconds: int = 10

    model_config = {"env_prefix": "HEDGE_"}
