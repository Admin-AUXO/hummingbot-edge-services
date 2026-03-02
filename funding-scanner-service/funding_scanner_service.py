import json
import os
import sys
import time

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import FundingScannerConfig
from shared.base_service import BaseService


def classify_rate(rate, config):
    abs_rate = abs(rate)
    if abs_rate >= config.extreme_rate_threshold:
        return "EXTREME"
    if abs_rate >= config.high_rate_threshold:
        return "HIGH"
    return "NORMAL"


class FundingScannerService(BaseService):
    name = "funding_scan"

    def __init__(self):
        super().__init__(FundingScannerConfig())
        self.last_signals = {}

    def load_symbols(self):
        path = os.path.join(os.path.dirname(__file__), self.config.symbols_file)
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load symbols file: {e}")
            return []

    def fetch_all_funding(self):
        try:
            resp = requests.get(self.config.binance_url, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self.logger.error(f"Binance funding fetch failed: {e}")
            return []

    def scan_and_publish(self):
        all_rates = self.fetch_all_funding()
        watch_set = set(self.load_symbols())
        opportunities = []

        for entry in all_rates:
            symbol = entry.get("symbol", "")
            if symbol not in watch_set:
                continue

            rate = float(entry.get("lastFundingRate", 0))
            annualized = rate * 3 * 365 * 100
            signal = classify_rate(rate, self.config)
            next_time = int(entry.get("nextFundingTime", 0))

            if abs(annualized) >= self.config.min_annualized_apr:
                opportunities.append({
                    "symbol": symbol,
                    "rate": rate,
                    "annualized_apr": round(annualized, 2),
                    "signal": signal,
                    "direction": "SHORT_PAYS" if rate > 0 else "LONG_PAYS",
                    "next_funding_time": next_time,
                })

            prev = self.last_signals.get(symbol)
            if signal != "NORMAL" and prev != signal:
                payload = {
                    "symbol": symbol,
                    "funding_rate": round(rate, 8),
                    "annualized_apr": round(annualized, 2),
                    "signal": signal,
                    "direction": "SHORT_PAYS" if rate > 0 else "LONG_PAYS",
                    "next_funding_time": next_time,
                    "timestamp": time.time(),
                }
                topic = f"{self.config.mqtt_topic_prefix}/{symbol}"
                self.publish(topic, payload)
                self.logger.info(
                    f"FUNDING SPIKE: {symbol} rate={rate:.6f} "
                    f"APR={annualized:.1f}% ({signal})"
                )
            self.last_signals[symbol] = signal

        if opportunities:
            ranked = sorted(opportunities, key=lambda x: abs(x["annualized_apr"]), reverse=True)
            summary = {
                "total_opportunities": len(ranked),
                "top_rates": ranked[:5],
                "timestamp": time.time(),
            }
            self.publish(f"{self.config.mqtt_topic_prefix}/summary", summary)
            self.logger.info(f"Found {len(ranked)} funding opportunities above {self.config.min_annualized_apr}% APR")
        else:
            self.logger.info(f"No funding opportunities above threshold")

    def run(self):
        self.connect_mqtt()
        symbols = self.load_symbols()
        self.logger.info(
            f"Funding scanner started, monitoring {len(symbols)} symbols "
            f"every {self.config.poll_interval_seconds}s"
        )

        while self.running:
            try:
                self.scan_and_publish()
            except Exception as e:
                self.logger.error(f"Scan error: {e}")
            self.sleep_loop(self.config.poll_interval_seconds)

        self.shutdown_mqtt()


if __name__ == "__main__":
    FundingScannerService().run()
