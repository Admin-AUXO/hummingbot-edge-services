import json
import os
import sys
import time

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import ClmmConfig
from range_calculator import (
    build_range_payload,
    calc_optimal_range,
    calc_range_utilization,
    should_rebalance,
)
from shared.base_service import BaseService


class ClmmService(BaseService):
    name = "clmm"

    def __init__(self):
        super().__init__(ClmmConfig())
        self.current_regime = "SIDEWAYS"
        self.current_session = "US"
        self.current_natr = 0.02
        self.current_lower = 0.0
        self.current_upper = 0.0
        self.last_rebalance_state = None

    def _on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            topic = msg.topic

            if "/regime/" in topic:
                self.current_regime = data.get("regime", self.current_regime)
                self.current_natr = data.get("natr", self.current_natr)
            elif "/session/" in topic:
                self.current_session = data.get("session", self.current_session)
        except Exception as e:
            self.logger.error(f"Message handler error: {e}")

    def fetch_current_price(self):
        url = "https://api.binance.com/api/v3/ticker/price"
        params = {"symbol": "SOLUSDT"}
        resp = self.session.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return float(resp.json()["price"])

    def eval_cycle(self):
        price = self.fetch_current_price()

        lower, upper, effective_range = calc_optimal_range(
            price,
            self.config.base_range_pct,
            self.current_regime,
            self.current_session,
            self.current_natr,
            self.config,
        )

        if self.current_lower > 0 and self.current_upper > 0:
            utilization = calc_range_utilization(price, self.current_lower, self.current_upper)
        else:
            utilization = 100.0
            self.current_lower = lower
            self.current_upper = upper

        rebalance = should_rebalance(utilization, self.config.rebalance_threshold_pct)

        if rebalance:
            self.current_lower = lower
            self.current_upper = upper
            utilization = calc_range_utilization(price, lower, upper)

        payload = build_range_payload(
            price, self.current_lower, self.current_upper,
            effective_range, utilization,
            self.current_regime, self.current_session,
            self.current_natr, rebalance,
        )

        topic = f"{self.config.mqtt_topic_prefix}/{self.config.target_pair}"
        self.publish(topic, payload)

        if rebalance and self.last_rebalance_state != (self.current_regime, self.current_session):
            self.logger.info(
                f"REBALANCE: {self.current_regime}/{self.current_session} "
                f"range={effective_range}% [{lower:.2f}-{upper:.2f}] "
                f"price={price:.2f} natr={self.current_natr:.4f}"
            )
            self.last_rebalance_state = (self.current_regime, self.current_session)
        else:
            self.logger.info(
                f"Range: [{self.current_lower:.2f}-{self.current_upper:.2f}] "
                f"util={utilization}% price={price:.2f} regime={self.current_regime}"
            )

    def run(self):
        self.connect_mqtt(
            subscriptions=["hbot/regime/#", "hbot/session/#"],
            on_message=self._on_message,
        )
        self.logger.info(f"CLMM optimizer started for {self.config.target_pair}, eval every {self.config.eval_interval_seconds}s")

        last_eval = 0.0
        while self.running:
            now = time.time()
            if (now - last_eval) >= self.config.eval_interval_seconds:
                try:
                    self.eval_cycle()
                except Exception as e:
                    self.logger.error(f"Eval error: {e}")
                last_eval = now
            self.sleep_loop(min(10, self.config.eval_interval_seconds))

        self.shutdown_mqtt()


if __name__ == "__main__":
    ClmmService().run()
