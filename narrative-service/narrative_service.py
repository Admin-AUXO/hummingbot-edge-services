import json
import os
import sys
import time

import requests

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
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load narratives: {e}")
            return []

    def search_dex(self, keyword):
        try:
            resp = requests.get(
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

    def scan_and_publish(self):
        narratives = self.load_narratives()
        total_signals = 0

        for narrative in narratives:
            scored = self.scan_narrative(narrative)
            spiking = filter_spiking_tokens(scored, self.config)

            for token_data in spiking:
                key = f"{token_data['category']}:{token_data['token']}"
                if key in self.alerted_tokens:
                    continue

                topic = f"{self.config.mqtt_topic_prefix}/{token_data['category']}/{token_data['token']}"
                self.publish(topic, token_data)
                self.alerted_tokens.add(key)
                total_signals += 1
                self.logger.info(
                    f"NARRATIVE: [{token_data['category']}] {token_data['token']} "
                    f"vol_spike={token_data['volume_spike']}x "
                    f"vol=${token_data['volume_24h']:,.0f} "
                    f"5m={token_data['price_change_5m']}%"
                )

        if len(self.alerted_tokens) > 5000:
            self.alerted_tokens.clear()
        if len(self.prev_volumes) > 10000:
            self.prev_volumes.clear()

        self.logger.info(f"Scanned {len(narratives)} narratives, {total_signals} new signals")

    def run(self):
        self.connect_mqtt()
        self.logger.info(f"Narrative scanner started, polling every {self.config.poll_interval_seconds}s")

        while self.running:
            try:
                self.scan_and_publish()
            except Exception as e:
                self.logger.error(f"Scan error: {e}")
            self.sleep_loop(self.config.poll_interval_seconds)

        self.shutdown_mqtt()


if __name__ == "__main__":
    NarrativeService().run()
