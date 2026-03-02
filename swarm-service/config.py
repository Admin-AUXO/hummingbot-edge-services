import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_config import BaseServiceConfig


class SwarmConfig(BaseServiceConfig):
    mqtt_topic_prefix: str = "hbot/swarm"
    eval_interval_seconds: int = 300

    state_file: str = "./swarm_state.json"
    max_active_bots: int = 50
    capital_per_bot: float = 10.0
    total_swarm_capital: float = 500.0

    min_alpha_score: int = 7
    min_liquidity: float = 30000.0
    max_age_hours: int = 72
    bot_ttl_hours: int = 48
    kill_loss_pct: float = 0.20

    auto_deploy: bool = False

    model_config = {"env_prefix": "SWARM_"}
