import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_config import BaseServiceConfig


class AlertConfig(BaseServiceConfig):
    mqtt_topic: str = "hbot/#"

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    alert_on_inventory_change: bool = True
    alert_on_kill_switch: bool = True
    alert_on_session_change: bool = True
    alert_on_drawdown_warning: bool = True
    drawdown_warning_threshold: float = 0.03

    alert_on_analytics: bool = True
    min_win_rate_alert: float = 0.4

    alert_on_hedge: bool = True
    alert_on_clmm: bool = True
    alert_on_rewards: bool = True
    alert_on_watchlist: bool = True

    min_alert_arb_net_profit_100: float = 12.0
    min_alert_alpha_score: int = 6
    min_alert_narrative_spike: float = 3.0
    min_alert_rewards_apr: float = 40.0

    model_config = {"env_prefix": "ALERT_", "env_file": ".env"}
