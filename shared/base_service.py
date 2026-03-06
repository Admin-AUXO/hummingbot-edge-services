import json
import logging
import signal
import time

import paho.mqtt.client as mqtt
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from shared.utils import chain_address_key, normalize_chain_id


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

    def _default_chain_id(self):
        return normalize_chain_id(getattr(self.config, "default_chain_id", "solana"))

    def _chain_key(self, chain_id, address):
        return chain_address_key(chain_id, address)

    def _item_chain_and_address(self, item):
        if isinstance(item, dict):
            chain_id = normalize_chain_id(item.get("chainId") or item.get("chain_id") or item.get("chain"))
            return chain_id, item.get("address", "")
        return self._default_chain_id(), str(item or "")

    def _build_dex_tokens_url(self, token_addresses, chain_id=None):
        base_url = getattr(
            self.config,
            "dex_token_url",
            "https://api.dexscreener.com/tokens/v1",
        )
        chain_id = normalize_chain_id(chain_id or self._default_chain_id())
        addresses = ",".join(token_addresses)
        if "/tokens/v1/" in base_url:
            return f"{base_url.rstrip('/')}/{addresses}"
        if base_url.rstrip("/").endswith("/tokens/v1"):
            return f"{base_url.rstrip('/')}/{chain_id}/{addresses}"
        if base_url.endswith("/"):
            return f"{base_url}{addresses}"
        return f"{base_url}/{addresses}"

    def fetch_market_data(self, items):
        if not items:
            return {}

        grouped = {}
        for item in items:
            chain_id, address = self._item_chain_and_address(item)
            if not address:
                continue
            grouped.setdefault(chain_id, [])
            if address not in grouped[chain_id]:
                grouped[chain_id].append(address)

        results = {}
        batch_size = max(1, min(30, int(getattr(self.config, "dex_batch_size", 30))))
        for chain_id, addresses in grouped.items():
            for i in range(0, len(addresses), batch_size):
                chunk = addresses[i : i + batch_size]
                try:
                    url = self._build_dex_tokens_url(chunk, chain_id=chain_id)
                    resp = self.session.get(url, timeout=15)
                    resp.raise_for_status()
                    data = resp.json()
                    pairs = data.get("pairs") if isinstance(data, dict) else data
                    if not pairs:
                        continue
                    for p in pairs:
                        pair_chain = normalize_chain_id(p.get("chainId"))
                        if pair_chain != chain_id:
                            continue
                        addr = p.get("baseToken", {}).get("address", "")
                        key = self._chain_key(pair_chain, addr)
                        liq = float(p.get("liquidity", {}).get("usd", 0))
                        if key not in results or liq > results[key].get("liquidity", 0):
                            results[key] = {
                                "chainId": pair_chain,
                                "address": addr,
                                "symbol": p.get("baseToken", {}).get("symbol", "?"),
                                "volume_24h": float(p.get("volume", {}).get("h24", 0)),
                                "liquidity": liq,
                                "price": float(p.get("priceUsd", 0)),
                                "pair_address": p.get("pairAddress", ""),
                                "dex": p.get("dexId", ""),
                            }
                except Exception as e:
                    self.logger.error(f"Market data fetch failed for {chain_id} chunk {i}: {e}")
        return results
