import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_config import BaseServiceConfig


class FundingScannerConfig(BaseServiceConfig):
    mqtt_topic_prefix: str = "hbot/funding_scan"
    poll_interval_seconds: int = 300

    binance_url: str = "https://fapi.binance.com/fapi/v1/premiumIndex"
    symbols_file: str = "./symbols.json"

    # Auto-discovery: also scan ALL Binance perps for extreme rates
    auto_discover_all: bool = True
    auto_discover_min_apr: float = 50.0  # Only alert non-watchlist if APR > 50%

    high_rate_threshold: float = 0.0003
    extreme_rate_threshold: float = 0.001
    min_annualized_apr: float = 30.0

    model_config = {"env_prefix": "FSCAN_"}
