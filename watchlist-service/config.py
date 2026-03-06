import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_config import BaseServiceConfig


class WatchlistConfig(BaseServiceConfig):
    mqtt_topic_prefix: str = "hbot/watchlist"
    eval_interval_seconds: int = 300

    arb_tokens_file: str = "../arb-service/tokens.json"
    rewards_pools_file: str = "../rewards-service/pools.json"
    funding_symbols_file: str = "./funding_symbols.json"
    state_file: str = "./watchlist_state.json"

    dex_boosts_url: str = "https://api.dexscreener.com/token-boosts/latest/v1"
    dex_profiles_url: str = "https://api.dexscreener.com/token-profiles/latest/v1"
    dex_token_url: str = "https://api.dexscreener.com/tokens/v1/solana"
    boost_poll_seconds: int = 900
    profile_poll_seconds: int = 1800

    min_liquidity_arb: float = 50000.0
    min_liquidity_rewards: float = 100000.0
    min_volume_24h: float = 100000.0

    max_arb_tokens: int = 40
    max_rewards_pools: int = 20
    max_funding_symbols: int = 20

    stale_cycles_threshold: int = 3
    stale_volume_threshold: float = 10000.0
    stale_liquidity_threshold: float = 5000.0

    model_config = {"env_prefix": "WL_"}
