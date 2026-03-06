import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_config import BaseServiceConfig


class RewardsConfig(BaseServiceConfig):
    mqtt_topic_prefix: str = "hbot/rewards"
    poll_interval_seconds: int = 3600

    pools_file: str = "./pools.json"
    dex_token_url: str = "https://api.dexscreener.com/tokens/v1/solana"

    min_effective_apr: float = 20.0
    min_liquidity: float = 10000.0
    max_risk_score: int = 8

    model_config = {"env_prefix": "REWARDS_"}
