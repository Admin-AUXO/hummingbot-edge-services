import os
import sys
import time

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import FundingConfig
from shared.base_service import BaseService


def calc_funding_bias(rate, threshold, max_rate, max_bias, sensitivity):
    abs_rate = abs(rate)
    if abs_rate <= threshold:
        return 0.0
    excess = abs_rate - threshold
    max_excess = max_rate - threshold
    if max_excess <= 0:
        return 0.0
    ratio = min(excess / max_excess, 1.0)
    magnitude = ratio ** sensitivity * max_bias
    return magnitude if rate > 0 else -magnitude


def classify_funding(rate, threshold):
    if rate >= threshold:
        return "HIGH_POSITIVE"
    elif rate <= -threshold:
        return "HIGH_NEGATIVE"
    return "NEUTRAL"


class FundingService(BaseService):
    name = "funding"

    def __init__(self):
        super().__init__(FundingConfig())
        self.last_signal = None

    def fetch_funding_rate(self):
        url = "https://fapi.binance.com/fapi/v1/premiumIndex"
        params = {"symbol": self.config.binance_symbol}
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return float(data["lastFundingRate"]), int(data["nextFundingTime"])

    def publish_funding(self, payload):
        topic = f"{self.config.mqtt_topic_prefix}/{self.config.target_pair}"
        self.publish(topic, payload)

        new_signal = payload["signal"]
        if new_signal != self.last_signal:
            self.logger.info(f"SIGNAL CHANGE: {self.last_signal} -> {new_signal} | Rate={payload['funding_rate']:.6f} Bias={payload['spread_bias']:.4f}")
            self.last_signal = new_signal
        else:
            self.logger.info(f"Signal: {new_signal} | Rate={payload['funding_rate']:.6f} | APR={payload['annualized_rate']:.2f}% | Bias={payload['spread_bias']:.4f}")

    def run(self):
        self.connect_mqtt()
        self.logger.info(f"Monitoring {self.config.binance_symbol} funding rate every {self.config.poll_interval_seconds}s")

        while self.running:
            try:
                rate, next_time = self.fetch_funding_rate()
                sig = classify_funding(rate, self.config.high_rate_threshold)
                bias = calc_funding_bias(rate, self.config.high_rate_threshold, self.config.max_funding_rate, self.config.max_funding_bias, self.config.bias_sensitivity)
                annualized = rate * 3 * 365 * 100

                payload = {
                    "target": self.config.target_pair,
                    "symbol": self.config.binance_symbol,
                    "funding_rate": round(rate, 8),
                    "annualized_rate": round(annualized, 2),
                    "signal": sig,
                    "spread_bias": round(bias, 4),
                    "next_funding_time": next_time,
                    "timestamp": time.time(),
                }
                self.publish_funding(payload)

            except Exception as e:
                self.logger.error(f"Funding error: {e}")

            self.sleep_loop(self.config.poll_interval_seconds)

        self.shutdown_mqtt()


if __name__ == "__main__":
    FundingService().run()
