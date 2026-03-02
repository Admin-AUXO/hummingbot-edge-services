import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import SessionConfig
from shared.base_service import BaseService


class SessionService(BaseService):
    name = "session"

    def __init__(self):
        super().__init__(SessionConfig())
        self.last_session = None

    def classify_session(self, utc_hour):
        if utc_hour >= self.config.night_start_hour or utc_hour < self.config.asia_start_hour:
            return "NIGHT", self.config.night_spread_mult
        elif utc_hour < self.config.eu_start_hour:
            return "ASIA", self.config.asia_spread_mult
        elif utc_hour < self.config.us_start_hour:
            return "EU", self.config.eu_spread_mult
        else:
            return "US", self.config.us_spread_mult

    def publish_session(self, payload):
        topic = f"{self.config.mqtt_topic_prefix}/{self.config.target_pair}"
        self.publish(topic, payload)

        session = payload["session"]
        if session != self.last_session:
            self.logger.info(f"SESSION CHANGE: {self.last_session} -> {session} | Mult={payload['spread_mult']}")
            self.last_session = session
        else:
            self.logger.info(f"Session: {session} | Mult={payload['spread_mult']}")

    def run(self):
        self.connect_mqtt()
        self.logger.info(f"Monitoring trading sessions for {self.config.target_pair} every {self.config.poll_interval_seconds}s")

        while self.running:
            try:
                now = datetime.now(timezone.utc)
                session, mult = self.classify_session(now.hour)

                payload = {
                    "target": self.config.target_pair,
                    "session": session,
                    "spread_mult": mult,
                    "utc_hour": now.hour,
                    "timestamp": time.time(),
                }
                self.publish_session(payload)

            except Exception as e:
                self.logger.error(f"Session error: {e}")

            self.sleep_loop(self.config.poll_interval_seconds)

        self.shutdown_mqtt()


if __name__ == "__main__":
    SessionService().run()
