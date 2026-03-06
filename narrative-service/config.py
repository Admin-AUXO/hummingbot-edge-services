import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.base_config import BaseServiceConfig
from shared.utils import normalize_chain_id, parse_json_mapping


class NarrativeConfig(BaseServiceConfig):
    mqtt_topic_prefix: str = "hbot/narrative"
    poll_interval_seconds: int = 1800
    default_chain_id: str = "solana"
    supported_chains: str = "solana,base,bsc,arbitrum"

    dex_search_url: str = "https://api.dexscreener.com/latest/dex/search"
    narratives_file: str = "./narratives.json"

    min_volume_24h: float = 50000.0
    min_volume_24h_json: str = '{"solana": 80000, "base": 50000, "bsc": 60000, "arbitrum": 50000}'
    min_volume_spike: float = 2.0
    min_volume_spike_json: str = '{"solana": 2.5, "base": 1.8, "bsc": 2.0, "arbitrum": 1.8}'
    min_price_change_1h: float = 1.0
    min_price_change_1h_json: str = '{"solana": 1.2, "base": 0.8, "bsc": 1.0, "arbitrum": 0.8}'
    min_liquidity: float = 20000.0
    min_liquidity_json: str = '{"solana": 50000, "base": 30000, "bsc": 35000, "arbitrum": 30000}'

    max_workers: int = 5
    narrative_token_query_limit: int = 2
    max_signals_per_cycle: int = 20
    max_signals_per_cycle_json: str = '{"solana": 6, "base": 8, "bsc": 6, "arbitrum": 8}'
    alerted_tokens_ttl_seconds: int = 14400
    alerted_tokens_limit: int = 5000
    prev_volumes_limit: int = 10000

    model_config = {"env_prefix": "NARR_"}

    def min_volume_for(self, chain_id: str) -> float:
        overrides = parse_json_mapping(self.min_volume_24h_json)
        chain = normalize_chain_id(chain_id)
        return float(overrides.get(chain, self.min_volume_24h))

    def min_spike_for(self, chain_id: str) -> float:
        overrides = parse_json_mapping(self.min_volume_spike_json)
        chain = normalize_chain_id(chain_id)
        return float(overrides.get(chain, self.min_volume_spike))

    def min_price_change_1h_for(self, chain_id: str) -> float:
        overrides = parse_json_mapping(self.min_price_change_1h_json)
        chain = normalize_chain_id(chain_id)
        return float(overrides.get(chain, self.min_price_change_1h))

    def min_liquidity_for(self, chain_id: str) -> float:
        overrides = parse_json_mapping(self.min_liquidity_json)
        chain = normalize_chain_id(chain_id)
        return float(overrides.get(chain, self.min_liquidity))

    def max_signals_per_cycle_for(self, chain_id: str) -> int:
        overrides = parse_json_mapping(self.max_signals_per_cycle_json)
        chain = normalize_chain_id(chain_id)
        return int(overrides.get(chain, self.max_signals_per_cycle))
