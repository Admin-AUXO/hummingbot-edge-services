import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_config import BaseServiceConfig


class ArbConfig(BaseServiceConfig):
    mqtt_topic_prefix: str = "hbot/arb"
    poll_interval_seconds: int = 30

    dex_token_url: str = "https://api.dexscreener.com/tokens/v1/solana"
    dex_search_url: str = "https://api.dexscreener.com/latest/dex/search"
    dex_search_query: str = "SOL"
    dex_batch_size: int = 30
    tokens_file: str = "./tokens.json"

    max_workers: int = 10
    discovery_interval_seconds: int = 1800
    seen_arb_ttl_seconds: int = 600
    cache_max_size: int = 30000

    min_arb_pct: float = 10.31
    min_net_profit_100: float = 10.0
    min_liquidity: float = 10000.0
    min_dex_count: int = 2
    min_volume_24h: float = 5000.0
    max_pool_age_hours: float = 0

    max_price_ratio: float = 5.0
    max_spread_pct: float = 100.0

    max_trade_pct_of_liq: float = 0.02
    est_slippage_pct: float = 0.3
    gas_cost_usd: float = 0.01

    model_config = {"env_prefix": "ARB_"}
