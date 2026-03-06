import json
import os
import sys
import time

from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import NarrativeConfig
from narrative_scanner import filter_spiking_tokens, score_narrative_token
from shared.base_service import BaseService


class NarrativeService(BaseService):
    name = "narrative"

    def __init__(self):
        super().__init__(NarrativeConfig())
        self.prev_volumes = {}
        self.alerted_tokens = set()

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
        try:
            resp = self.session.get(
                self.config.dex_search_url,
                params={"q": keyword},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            pairs = data.get("pairs", [])
            return [p for p in pairs if p.get("chainId") == "solana"]
        except Exception as e:
            self.logger.error(f"DexScreener search failed for '{keyword}': {e}")
            return []

    def scan_narrative(self, narrative):
        keyword = narrative["keyword"]
        category = narrative["category"]
        watch_tokens = set(t.upper() for t in narrative.get("tokens", []))

        pairs = self.search_dex(keyword)
        scored = []

        for pair in pairs:
            symbol = pair.get("baseToken", {}).get("symbol", "").upper()
            if watch_tokens and symbol not in watch_tokens:
                continue

            pair_addr = pair.get("pairAddress", "")
            prev_vol = self.prev_volumes.get(pair_addr, 0)
            result = score_narrative_token(pair, prev_vol, self.config)

            if result:
                result["category"] = category
                result["keyword"] = keyword
                scored.append(result)
                self.prev_volumes[pair_addr] = result["volume_24h"]

        return scored

    def on_tick(self):
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

        for t in all_spiking:
            key = f"{t['category']}:{t['token']}"
            if key not in self.alerted_tokens:
                self.publish(f"{self.config.mqtt_topic_prefix}/{t['category']}/{t['token']}", t)
                self.alerted_tokens.add(key)
                self.logger.info(f"NARRATIVE: [{t['category']}] {t['token']} {t['volume_spike']}x vol=${t['volume_24h']:,.0f}")

        if len(self.alerted_tokens) > self.config.alerted_tokens_limit:
            self.alerted_tokens.clear()
        if len(self.prev_volumes) > self.config.prev_volumes_limit:
            self.prev_volumes.clear()
        self.logger.info(f"Scanned {len(narratives)} narratives, {len(all_spiking)} signals")


if __name__ == "__main__":
    NarrativeService().run()
