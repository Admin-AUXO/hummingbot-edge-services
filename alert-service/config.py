import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_config import BaseServiceConfig


class AlertConfig(BaseServiceConfig):
    mqtt_topic: str = "hbot/#"

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    alert_on_regime_change: bool = True
    alert_on_correlation_change: bool = True
    alert_on_inventory_change: bool = True
    alert_on_kill_switch: bool = True
    alert_on_session_change: bool = True
    alert_on_funding_change: bool = True
    alert_on_drawdown_warning: bool = True
    drawdown_warning_threshold: float = 0.03

    alert_on_analytics: bool = True
    alert_on_backtest: bool = True
    min_win_rate_alert: float = 0.4

    alert_on_hedge: bool = True
    alert_on_lab: bool = True

    alert_on_alpha: bool = True
    alert_on_new_listing: bool = True
    alert_on_unlock: bool = True

    alert_on_arb: bool = True
    alert_on_funding_scan: bool = True
    alert_on_narrative: bool = True
    alert_on_swarm: bool = True
    alert_on_clmm: bool = True
    alert_on_migration: bool = True
    alert_on_rewards: bool = True
    alert_on_watchlist: bool = True

    model_config = {"env_prefix": "ALERT_", "env_file": ".env"}
