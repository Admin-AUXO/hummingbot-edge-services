import json
import os
import sys
import time

from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import NarrativeConfig
from narrative_scanner import filter_spiking_tokens, score_narrative_token
from shared.base_service import BaseService
from shared.utils import TTLCache, normalize_chain_id, parse_csv_list


class NarrativeService(BaseService):
    name = "narrative"

    def __init__(self):
        super().__init__(NarrativeConfig())
        self.prev_volumes = {}
        self.alerted_tokens = TTLCache(self.config.alerted_tokens_ttl_seconds, max_size=self.config.alerted_tokens_limit)
        self.supported_chains = [normalize_chain_id(chain) for chain in parse_csv_list(self.config.supported_chains)] or ["solana"]
        self.search_cache = {}

    def load_narratives(self):
        try:
            with open(self.config.narratives_file, "r") as f:
                raw = json.load(f)
            if not isinstance(raw, list):
                self.logger.error(f"Invalid narratives format in {self.config.narratives_file}: expected list")
                return []
            seen = set()
            deduped = []
            for item in raw:
                keyword = item.get("keyword")
                category = item.get("category")
                key = (keyword, category)
                if not keyword or not category or key in seen:
                    continue
                seen.add(key)
                deduped.append(item)
            return deduped
        except Exception as e:
            self.logger.error(f"Failed to load narratives: {e}")
            return []

    def search_dex(self, keyword):
        cache_key = keyword.strip().lower()
        cached = self.search_cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            resp = self.session.get(
                self.config.dex_search_url,
                params={"q": keyword},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            pairs = data.get("pairs", [])
            filtered = [
                p for p in pairs
                if normalize_chain_id(p.get("chainId")) in self.supported_chains
            ]
            self.search_cache[cache_key] = filtered
            return filtered
        except Exception as e:
            self.logger.error(f"DexScreener search failed for '{keyword}': {e}")
            self.search_cache[cache_key] = []
            return []

    def scan_narrative(self, narrative):
        keyword = narrative["keyword"]
        category = narrative["category"]
        watch_tokens = set(t.upper() for t in narrative.get("tokens", []))

        query_terms = [keyword]
        if watch_tokens:
            query_terms.extend(sorted(watch_tokens)[: max(0, int(self.config.narrative_token_query_limit))])

        pair_map = {}
        for term in query_terms:
            for pair in self.search_dex(term):
                chain = normalize_chain_id(pair.get("chainId"))
                pair_addr = pair.get("pairAddress", "")
                if not pair_addr:
                    continue
                pair_map[f"{chain}:{pair_addr}"] = pair

        pairs = list(pair_map.values())
        scored = []

        for pair in pairs:
            chain = normalize_chain_id(pair.get("chainId"))
            base = pair.get("baseToken", {})
            quote = pair.get("quoteToken", {})
            base_symbol = base.get("symbol", "").upper()
            quote_symbol = quote.get("symbol", "").upper()

            matched_token = base
            if watch_tokens:
                if base_symbol in watch_tokens:
                    matched_token = base
                elif quote_symbol in watch_tokens:
                    matched_token = quote
                else:
                    continue

            pair_addr = pair.get("pairAddress", "")
            matched_addr = matched_token.get("address", "")
            prev_key = f"{chain}:{matched_addr or pair_addr}"
            prev_vol = self.prev_volumes.get(prev_key, 0)
            result = score_narrative_token(pair, prev_vol, self.config, token_override=matched_token)

            if result:
                result["category"] = category
                result["keyword"] = keyword
                scored.append(result)
                self.prev_volumes[prev_key] = result["volume_24h"]

        return scored

    def on_tick(self):
        self.search_cache.clear()
        narratives = self.load_narratives()
        if not narratives:
            self.logger.info("Scanned 0 narratives, 0 signals")
            return
        all_spiking = []

        workers = max(1, min(self.config.max_workers, len(narratives)))
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = [ex.submit(self.scan_narrative, n) for n in narratives]
            for f in futures:
                all_spiking.extend(filter_spiking_tokens(f.result(), self.config))

        best_by_key = {}
        for token in all_spiking:
            chain = normalize_chain_id(token.get("chainId"))
            token_key = f"{token['category']}:{chain}:{token.get('address') or token['token']}"
            rank_tuple = (
                float(token.get("volume_spike", 0)),
                float(token.get("price_change_1h", 0)),
                float(token.get("volume_24h", 0)),
            )
            prev = best_by_key.get(token_key)
            if not prev:
                best_by_key[token_key] = (rank_tuple, token)
            elif rank_tuple > prev[0]:
                best_by_key[token_key] = (rank_tuple, token)

        ranked_spiking = [item[1] for item in sorted(best_by_key.values(), key=lambda x: x[0], reverse=True)]

        published_by_chain = {}
        for t in ranked_spiking:
            chain = normalize_chain_id(t.get("chainId"))
            chain_limit = max(1, int(self.config.max_signals_per_cycle_for(chain)))
            if published_by_chain.get(chain, 0) >= chain_limit:
                continue

            key = f"{t['category']}:{chain}:{t.get('address') or t['token']}"
            if key not in self.alerted_tokens:
                self.publish(f"{self.config.mqtt_topic_prefix}/{chain}/{t['category']}/{t['token']}", t)
                self.alerted_tokens.add(key)
                published_by_chain[chain] = published_by_chain.get(chain, 0) + 1
                self.logger.info(f"NARRATIVE: [{chain}:{t['category']}] {t['token']} {t['volume_spike']}x vol=${t['volume_24h']:,.0f}")

        self.alerted_tokens.clear_expired()
        if len(self.prev_volumes) > self.config.prev_volumes_limit:
            self.prev_volumes.clear()
        self.logger.info(f"Scanned {len(narratives)} narratives, {len(all_spiking)} signals, published {sum(published_by_chain.values())}")


if __name__ == "__main__":
    NarrativeService().run()
