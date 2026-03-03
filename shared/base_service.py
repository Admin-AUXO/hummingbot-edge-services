import json
import logging
import signal
import time

import paho.mqtt.client as mqtt
import requests


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class BaseService:
    name = "service"

    def __init__(self, config):
        self.config = config
        self.running = True
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        self.logger = logging.getLogger(self.name)
        self.session = requests.Session()
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

    def _shutdown(self, signum, frame):
        self.logger.info("Shutting down...")
        self.on_shutdown()
        self.running = False

    def on_shutdown(self):
        pass

    def connect_mqtt(self, subscriptions=None, on_message=None):
        self.client.username_pw_set(self.config.mqtt_username, self.config.mqtt_password)
        if on_message:
            self.client.on_message = on_message
        self.client.connect(self.config.mqtt_host, self.config.mqtt_port)
        if subscriptions:
            for topic in subscriptions:
                self.client.subscribe(topic)
        self.client.loop_start()
        self.logger.info(f"Connected to MQTT at {self.config.mqtt_host}:{self.config.mqtt_port}")

    def publish(self, topic, payload, retain=True):
        self.client.publish(topic, json.dumps(payload), retain=retain)

    def sleep_loop(self, seconds):
        for _ in range(seconds):
            if not self.running:
                break
            time.sleep(1)

    def shutdown_mqtt(self):
        self.client.loop_stop()
        self.client.disconnect()
        self.logger.info("Shutdown complete")

    def get_target(self, topic):
        return topic.split("/")[-1]

    def run(self):
        self.connect_mqtt()
        interval = getattr(self.config, "poll_interval_seconds", 60)
        self.logger.info(f"{self.name} service started, interval={interval}s")
        while self.running:
            try:
                self.on_tick()
            except Exception as e:
                self.logger.error(f"Execution error: {e}")
            self.sleep_loop(interval)
        self.shutdown_mqtt()

    def on_tick(self):
        pass

    def fetch_market_data(self, addresses):
        if not addresses: return {}
        results = {}
        for i in range(0, len(addresses), 30):
            chunk = addresses[i : i + 30]
            try:
                base_url = getattr(self.config, "dex_token_url", "https://api.dexscreener.com/latest/dex/tokens/")
                resp = self.session.get(f"{base_url}{','.join(chunk)}", timeout=15)
                resp.raise_for_status()
                data = resp.json()
                pairs = data.get("pairs") if isinstance(data, dict) else data
                if not pairs: continue
                for p in pairs:
                    if p.get("chainId") == "solana":
                        addr = p.get("baseToken", {}).get("address", "")
                        liq = float(p.get("liquidity", {}).get("usd", 0))
                        if addr not in results or liq > results[addr].get("liquidity", 0):
                            results[addr] = {
                                "volume_24h": float(p.get("volume", {}).get("h24", 0)),
                                "liquidity": liq,
                                "price": float(p.get("priceUsd", 0)),
                                "pair_address": p.get("pairAddress", ""),
                                "dex": p.get("dexId", ""),
                            }
            except Exception as e:
                self.logger.error(f"Market data fetch failed for chunk {i}: {e}")
        return results
