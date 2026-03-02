import os
import sys
import time

import pandas as pd
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import RegimeConfig
from indicators import classify_regime
from shared.base_service import BaseService


class RegimeClassifier(BaseService):
    name = "regime"

    def __init__(self):
        super().__init__(RegimeConfig())
        self.last_regime = None

    def fetch_candles(self):
        url = "https://api.binance.com/api/v3/klines"
        params = {
            "symbol": self.config.binance_symbol,
            "interval": self.config.candle_interval,
            "limit": self.config.candle_limit,
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        df = pd.DataFrame(data, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "trades", "taker_buy_base",
            "taker_buy_quote", "ignore",
        ])
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
        return df

    def publish_regime(self, regime, natr, bb_width):
        topic = f"{self.config.mqtt_topic_prefix}/{self.config.trading_pair}"
        payload = {
            "regime": regime,
            "natr": round(natr, 6),
            "bb_width": round(bb_width, 6),
            "timestamp": time.time(),
            "symbol": self.config.binance_symbol,
        }
        self.publish(topic, payload)

        if regime != self.last_regime:
            self.logger.info(f"REGIME CHANGE: {self.last_regime} -> {regime} | NATR={natr:.4f} BBW={bb_width:.4f}")
            self.last_regime = regime
        else:
            self.logger.info(f"Regime: {regime} | NATR={natr:.4f} BBW={bb_width:.4f}")

    def run(self):
        self.connect_mqtt()
        self.logger.info(f"Monitoring {self.config.binance_symbol} every {self.config.poll_interval_seconds}s")

        while self.running:
            try:
                df = self.fetch_candles()
                regime, natr, bb_width = classify_regime(df, self.config)
                self.publish_regime(regime, natr, bb_width)
            except Exception as e:
                self.logger.error(f"Classification error: {e}")

            self.sleep_loop(self.config.poll_interval_seconds)

        self.shutdown_mqtt()


if __name__ == "__main__":
    RegimeClassifier().run()
