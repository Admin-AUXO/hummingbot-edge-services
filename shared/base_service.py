import json
import logging
import signal
import time

import paho.mqtt.client as mqtt


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class BaseService:
    name = "service"

    def __init__(self, config):
        self.config = config
        self.running = True
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        self.logger = logging.getLogger(self.name)
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
