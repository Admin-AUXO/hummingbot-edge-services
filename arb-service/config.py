import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_config import BaseServiceConfig


class ArbConfig(BaseServiceConfig):
    mqtt_topic_prefix: str = "hbot/arb"
    poll_interval_seconds: int = 60

    dex_token_url: str = "https://api.dexscreener.com/latest/dex/tokens/"
    tokens_file: str = "./tokens.json"

    min_arb_pct: float = 0.5
    min_liquidity: float = 5000.0
    min_dex_count: int = 2

    model_config = {"env_prefix": "ARB_"}
