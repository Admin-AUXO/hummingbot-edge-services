import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_config import BaseServiceConfig


class ArbConfig(BaseServiceConfig):
    mqtt_topic_prefix: str = "hbot/arb"
    poll_interval_seconds: int = 30

    dex_token_url: str = "https://api.dexscreener.com/latest/dex/tokens/"
    tokens_file: str = "./tokens.json"

    # --- Filters (higher = fewer but better opportunities) ---
    min_arb_pct: float = 10.31         # $10 net on $100 after 0.3% slippage + gas
    min_net_profit_100: float = 10.0   # $10 min net profit per $100
    min_liquidity: float = 10000.0     # Min liquidity per side (was 5000)
    min_dex_count: int = 2             # Min DEXs with liquidity
    min_volume_24h: float = 5000.0     # Min 24h volume per pool
    max_pool_age_hours: float = 0      # 0 = no filter; filter very new pools

    # --- Sizing ---
    max_trade_pct_of_liq: float = 0.02  # Max 2% of pool liquidity per trade
    est_slippage_pct: float = 0.3       # Estimated slippage
    gas_cost_usd: float = 0.01          # Solana gas per swap

    model_config = {"env_prefix": "ARB_"}
