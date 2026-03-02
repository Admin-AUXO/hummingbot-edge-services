import os
import sys
import time

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import InventoryConfig
from risk_calculator import (
    calc_drawdown,
    calc_inventory_skew,
    calc_skew_bias,
    classify_inventory,
    should_kill,
)
from shared.base_service import BaseService


class InventoryService(BaseService):
    name = "inventory"

    def __init__(self):
        super().__init__(InventoryConfig())
        self.last_signal = None
        self.peak_value = 0.0
        self.peak_timestamp = 0.0

    def fetch_portfolio_state(self):
        url = f"{self.config.api_base_url}/portfolio/state"
        payload = {
            "account_names": [self.config.account_name],
            "connector_names": [self.config.connector_name],
        }
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def extract_token_values(self, state):
        account_data = state.get(self.config.account_name, {})
        connector_data = account_data.get(self.config.connector_name, [])

        base_value = 0.0
        quote_value = 0.0

        for token_info in connector_data:
            token = token_info.get("token", "")
            value = float(token_info.get("value", 0))
            if token.upper() == self.config.base_token.upper():
                base_value = value
            elif token.upper() == self.config.quote_token.upper():
                quote_value = value

        return base_value, quote_value

    def update_peak(self, total_value):
        now = time.time()
        lookback_seconds = self.config.drawdown_lookback_hours * 3600

        if self.peak_timestamp > 0 and (now - self.peak_timestamp) > lookback_seconds:
            self.peak_value = total_value
            self.peak_timestamp = now

        if total_value >= self.peak_value:
            self.peak_value = total_value
            self.peak_timestamp = now

    def publish_inventory(self, payload):
        topic = f"{self.config.mqtt_topic_prefix}/{self.config.target_pair}"
        self.publish(topic, payload)

        new_signal = payload["signal"]
        if new_signal != self.last_signal:
            self.logger.info(f"SIGNAL CHANGE: {self.last_signal} -> {new_signal} | Skew={payload['inventory_skew']:.4f} Bias={payload['skew_bias']:.4f}")
            self.last_signal = new_signal
        else:
            self.logger.info(f"Signal: {new_signal} | Skew={payload['inventory_skew']:.4f} | Bias={payload['skew_bias']:.4f} | DD={payload['drawdown_pct']:.4f} | Kill={payload['kill']}")

    def run(self):
        self.connect_mqtt()
        self.logger.info(f"Monitoring {self.config.base_token}/{self.config.quote_token} on {self.config.connector_name} every {self.config.poll_interval_seconds}s")

        while self.running:
            try:
                state = self.fetch_portfolio_state()
                base_value, quote_value = self.extract_token_values(state)

                if base_value == 0 and quote_value == 0:
                    self.logger.warning(f"Tokens {self.config.base_token}/{self.config.quote_token} not found, skipping")
                else:
                    total_value = base_value + quote_value
                    self.update_peak(total_value)

                    skew = calc_inventory_skew(base_value, quote_value, self.config.target_base_pct)
                    sig = classify_inventory(skew, self.config.max_inventory_skew)
                    bias = calc_skew_bias(skew, self.config.max_inventory_skew, self.config.max_skew_bias, self.config.skew_sensitivity)
                    dd = calc_drawdown(total_value, self.peak_value)
                    kill = should_kill(dd, self.config.max_drawdown_pct)

                    payload = {
                        "target": self.config.target_pair,
                        "base_token": self.config.base_token,
                        "quote_token": self.config.quote_token,
                        "base_value": round(base_value, 4),
                        "quote_value": round(quote_value, 4),
                        "total_value": round(total_value, 4),
                        "inventory_skew": round(skew, 4),
                        "signal": sig,
                        "skew_bias": round(bias, 4),
                        "drawdown_pct": round(dd, 4),
                        "peak_value": round(self.peak_value, 4),
                        "kill": kill,
                        "timestamp": time.time(),
                    }
                    self.publish_inventory(payload)

            except Exception as e:
                self.logger.error(f"Inventory error: {e}")

            self.sleep_loop(self.config.poll_interval_seconds)

        self.shutdown_mqtt()


if __name__ == "__main__":
    InventoryService().run()
