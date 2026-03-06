import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_config import BaseServiceConfig
from shared.utils import normalize_chain_id, parse_json_mapping


class WatchlistConfig(BaseServiceConfig):
    mqtt_topic_prefix: str = "hbot/watchlist"
    eval_interval_seconds: int = 300
    default_chain_id: str = "solana"
    supported_chains: str = "solana,base,bsc,arbitrum"

    arb_tokens_file: str = "../arb-service/tokens.json"
    rewards_pools_file: str = "../rewards-service/pools.json"
    funding_symbols_file: str = "./funding_symbols.json"
    state_file: str = "./watchlist_state.json"

    dex_boosts_url: str = "https://api.dexscreener.com/token-boosts/latest/v1"
    dex_profiles_url: str = "https://api.dexscreener.com/token-profiles/latest/v1"
    dex_token_url: str = "https://api.dexscreener.com/tokens/v1"
    boost_poll_seconds: int = 900
    profile_poll_seconds: int = 1800

    min_liquidity_arb: float = 50000.0
    min_liquidity_rewards: float = 100000.0
    min_volume_24h: float = 100000.0

    max_arb_tokens: int = 40
    max_rewards_pools: int = 20
    max_funding_symbols: int = 20

    max_signals_per_cycle: int = 500
    max_signals_per_cycle_json: str = '{"solana": 180, "base": 220, "bsc": 120, "arbitrum": 220}'
    signal_dedupe_ttl_seconds: int = 900
    min_signal_alpha_score: float = 6.0
    min_signal_alpha_score_json: str = '{"solana": 7.5, "base": 5.5, "bsc": 6.0, "arbitrum": 5.5}'
    min_signal_narrative_spike: float = 2.5
    min_signal_narrative_spike_json: str = '{"solana": 3.2, "base": 2.2, "bsc": 2.5, "arbitrum": 2.2}'

    stale_cycles_threshold: int = 3
    stale_volume_threshold: float = 10000.0
    stale_liquidity_threshold: float = 5000.0

    model_config = {"env_prefix": "WL_"}

    def min_signal_alpha_score_for(self, chain_id: str) -> float:
        overrides = parse_json_mapping(self.min_signal_alpha_score_json)
        chain = normalize_chain_id(chain_id)
        return float(overrides.get(chain, self.min_signal_alpha_score))

    def max_signals_per_cycle_for(self, chain_id: str) -> int:
        overrides = parse_json_mapping(self.max_signals_per_cycle_json)
        chain = normalize_chain_id(chain_id)
        return int(overrides.get(chain, self.max_signals_per_cycle))

    def min_signal_narrative_spike_for(self, chain_id: str) -> float:
        overrides = parse_json_mapping(self.min_signal_narrative_spike_json)
        chain = normalize_chain_id(chain_id)
        return float(overrides.get(chain, self.min_signal_narrative_spike))
