import json
import logging
import signal
import time

import paho.mqtt.client as mqtt
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class BaseService:
    name = "service"

    def __init__(self, config):
        self.config = config
        self.running = True
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        self.logger = logging.getLogger(self.name)
        self.session = requests.Session()
        retry = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=0.3,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET", "POST"]),
        )
        adapter = HTTPAdapter(pool_connections=20, pool_maxsize=40, max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.auth = (self.config.api_username, self.config.api_password)
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

    def _build_dex_tokens_url(self, token_addresses):
        base_url = getattr(
            self.config,
            "dex_token_url",
            "https://api.dexscreener.com/tokens/v1/solana",
        )
        addresses = ",".join(token_addresses)
        if "/tokens/v1/" in base_url:
            return f"{base_url.rstrip('/')}/{addresses}"
        if base_url.endswith("/"):
            return f"{base_url}{addresses}"
        return f"{base_url}/{addresses}"

    def fetch_market_data(self, addresses):
        if not addresses:
            return {}
        addresses = list(dict.fromkeys(addresses))
        results = {}
        batch_size = max(1, min(30, int(getattr(self.config, "dex_batch_size", 30))))
        for i in range(0, len(addresses), batch_size):
            chunk = addresses[i : i + batch_size]
            try:
                url = self._build_dex_tokens_url(chunk)
                resp = self.session.get(url, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                pairs = data.get("pairs") if isinstance(data, dict) else data
                if not pairs:
                    continue
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
