import os
import sys
import time

import numpy as np
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import CorrelationConfig
from correlator import (
    calc_price_ratio,
    calc_rolling_correlation,
    calc_rolling_z_score,
    calc_spread_bias,
    classify_signal,
)
from shared.base_service import BaseService


class CorrelationService(BaseService):
    name = "correlation"

    def __init__(self):
        super().__init__(CorrelationConfig())
        self.last_signal = None

    def fetch_candles(self, symbol):
        url = "https://api.binance.com/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": self.config.candle_interval,
            "limit": self.config.candle_limit,
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        closes = np.array([float(candle[4]) for candle in data])
        return closes

    def publish_correlation(self, payload):
        topic = f"{self.config.mqtt_topic_prefix}/{self.config.target_pair}"
        self.publish(topic, payload)

        new_signal = payload["signal"]
        if new_signal != self.last_signal:
            self.logger.info(f"SIGNAL CHANGE: {self.last_signal} -> {new_signal} | Z={payload['avg_z_score']:.4f} Bias={payload['spread_bias']:.4f}")
            self.last_signal = new_signal
        else:
            self.logger.info(f"Signal: {new_signal} | Z={payload['avg_z_score']:.4f} | Corr={payload['avg_correlation']:.4f} | Bias={payload['spread_bias']:.4f}")

    def run(self):
        self.connect_mqtt()
        self.logger.info(f"Monitoring {self.config.target_binance_symbol} vs {self.config.reference_pairs} every {self.config.poll_interval_seconds}s")

        while self.running:
            try:
                target_closes = self.fetch_candles(self.config.target_binance_symbol)

                z_scores = {}
                correlations = {}
                valid_z_scores = []

                for ref_symbol, label in zip(self.config.reference_pairs, self.config.reference_labels):
                    ref_closes = self.fetch_candles(ref_symbol)

                    min_len = min(len(target_closes), len(ref_closes))
                    tc = target_closes[-min_len:]
                    rc = ref_closes[-min_len:]

                    ratio = calc_price_ratio(tc, rc)
                    z = calc_rolling_z_score(ratio, self.config.lookback_period)

                    tr = np.diff(tc) / tc[:-1]
                    rr = np.diff(rc) / rc[:-1]
                    corr = calc_rolling_correlation(tr, rr, self.config.lookback_period)

                    z_scores[label] = round(z, 4)
                    correlations[label] = round(corr, 4)

                    if abs(corr) >= self.config.min_correlation:
                        valid_z_scores.append(z)

                avg_z = float(np.mean(valid_z_scores)) if valid_z_scores else 0.0
                avg_corr = float(np.mean(list(correlations.values())))

                sig = classify_signal(avg_z, self.config.z_score_overbought, self.config.z_score_oversold)
                bias = calc_spread_bias(avg_z, self.config.z_score_overbought, self.config.z_score_oversold, self.config.max_spread_bias)

                payload = {
                    "target": self.config.target_pair,
                    "z_scores": z_scores,
                    "avg_z_score": round(avg_z, 4),
                    "signal": sig,
                    "correlations": correlations,
                    "avg_correlation": round(avg_corr, 4),
                    "spread_bias": round(bias, 4),
                    "timestamp": time.time(),
                }
                self.publish_correlation(payload)

            except Exception as e:
                self.logger.error(f"Correlation error: {e}")

            self.sleep_loop(self.config.poll_interval_seconds)

        self.shutdown_mqtt()


if __name__ == "__main__":
    CorrelationService().run()
