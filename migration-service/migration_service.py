import os
import sys
import time

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import MigrationConfig
from event_checker import (
    ACTIVE,
    POST_EVENT,
    auto_cleanup_events,
    build_event_payload,
    classify_event,
    detect_new_pools,
    load_events,
)
from shared.base_service import BaseService


class MigrationService(BaseService):
    name = "migration"

    def __init__(self):
        super().__init__(MigrationConfig())
        self.last_event_signals = {}
        self.seen_pools = set()

    def fetch_solana_pairs(self):
        try:
            resp = requests.get(self.config.dex_search_url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            pairs = data.get("pairs", [])
            return [p for p in pairs if p.get("chainId") == "solana"]
        except Exception as e:
            self.logger.error(f"DexScreener fetch failed: {e}")
            return []

    def check_events(self):
        # Auto-clean expired entries from the JSON file
        auto_cleanup_events(self.config.events_file, self.config.post_event_hours)

        events = load_events(self.config.events_file)

        for event in events:
            pair = event.get("pair", "")
            token = event.get("token", "?")
            status, hours = classify_event(event, self.config)

            key = f"{pair}:{event.get('event_time', '')}"
            prev = self.last_event_signals.get(key)

            if status in (ACTIVE, POST_EVENT):
                payload = build_event_payload(event, status, hours)
                topic = f"{self.config.mqtt_topic_prefix}/event/{token}"
                self.publish(topic, payload)
                if prev != status:
                    self.logger.info(
                        f"{status}: {token} ({event.get('event_type', '?')}) "
                        f"{'in' if status == ACTIVE else ''} {hours}h "
                        f"{'until' if status == ACTIVE else 'ago'}"
                    )
            self.last_event_signals[key] = status

    def check_new_pools(self):
        pairs = self.fetch_solana_pairs()
        new_pools = detect_new_pools(pairs, self.config)

        for pool in new_pools:
            pair_addr = pool["pair"]
            if pair_addr in self.seen_pools:
                continue

            topic = f"{self.config.mqtt_topic_prefix}/new_pool/{pool['token']}"
            self.publish(topic, pool)
            self.seen_pools.add(pair_addr)
            self.logger.info(
                f"NEW POOL: {pool['token']} on {pool['dex']} "
                f"age={pool['age_minutes']}min "
                f"liq=${pool['liquidity']:,.0f}"
            )

        if len(self.seen_pools) > 5000:
            self.seen_pools.clear()

    def run(self):
        self.connect_mqtt()
        self.logger.info(f"Migration service started, polling every {self.config.poll_interval_seconds}s")

        while self.running:
            try:
                self.check_events()
                self.check_new_pools()
            except Exception as e:
                self.logger.error(f"Check error: {e}")
            self.sleep_loop(self.config.poll_interval_seconds)

        self.shutdown_mqtt()


if __name__ == "__main__":
    MigrationService().run()
