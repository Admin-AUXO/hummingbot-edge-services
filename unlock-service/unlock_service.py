import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import UnlockConfig
from shared.base_service import BaseService
from unlock_checker import (
    POST_UNLOCK,
    PRE_UNLOCK,
    auto_cleanup_unlocks,
    build_post_unlock_payload,
    build_pre_unlock_payload,
    classify_unlock,
    load_unlocks,
)


class UnlockService(BaseService):
    name = "unlock"

    def __init__(self):
        super().__init__(UnlockConfig())
        self.last_signals = {}

    def check_unlocks(self):
        # Auto-clean expired entries from the JSON file
        auto_cleanup_unlocks(self.config.data_file, self.config.post_unlock_hours)

        unlocks = load_unlocks(self.config.data_file)
        self.logger.info(f"Loaded {len(unlocks)} unlock entries")

        for unlock in unlocks:
            pair = unlock.get("pair", "")
            token = unlock.get("token", "?")
            status, hours = classify_unlock(unlock, self.config)

            key = f"{pair}:{unlock.get('unlock_time', '')}"
            prev_status = self.last_signals.get(key)

            if status == PRE_UNLOCK:
                payload = build_pre_unlock_payload(unlock, hours, self.config)
                topic = f"{self.config.mqtt_topic_prefix}/pre/{pair}"
                self.publish(topic, payload)
                if prev_status != PRE_UNLOCK:
                    self.logger.info(f"PRE_UNLOCK: {token} ({pair}) in {hours}h, {unlock.get('unlock_pct')}%")
                self.last_signals[key] = PRE_UNLOCK

            elif status == POST_UNLOCK:
                payload = build_post_unlock_payload(unlock, hours, self.config)
                topic = f"{self.config.mqtt_topic_prefix}/post/{pair}"
                self.publish(topic, payload)
                if prev_status != POST_UNLOCK:
                    self.logger.info(f"POST_UNLOCK: {token} ({pair}) {hours}h ago, {unlock.get('unlock_pct')}%")
                self.last_signals[key] = POST_UNLOCK

            else:
                if prev_status:
                    self.logger.info(f"{status}: {token} ({pair}) — clearing signal")
                self.last_signals[key] = status

    def run(self):
        self.connect_mqtt()
        self.logger.info(f"Unlock service started, polling every {self.config.poll_interval_seconds}s")

        while self.running:
            try:
                self.check_unlocks()
            except Exception as e:
                self.logger.error(f"Check error: {e}")
            self.sleep_loop(self.config.poll_interval_seconds)

        self.shutdown_mqtt()


if __name__ == "__main__":
    UnlockService().run()
