import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import SwarmConfig
from shared.base_service import BaseService
from swarm_manager import (
    build_swarm_status,
    create_bot_entry,
    evaluate_bots,
    load_state,
    save_state,
    should_deploy,
)


class SwarmService(BaseService):
    name = "swarm"

    def __init__(self):
        super().__init__(SwarmConfig())
        self.bots = load_state(self.config.state_file)
        self.pending_signals = []

    def on_shutdown(self):
        save_state(self.bots, self.config.state_file)

    def _active_bots(self):
        return [b for b in self.bots if b["status"] in ("ACTIVE", "RECOMMENDED")]

    def _on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            topic = msg.topic

            if "/alpha/signal/" in topic:
                self.pending_signals.append(data)
            elif "/alpha/new_listing/" in topic:
                data["score"] = self.config.min_alpha_score
                self.pending_signals.append(data)
        except Exception as e:
            self.logger.error(f"Message handler error: {e}")

    def process_signals(self):
        active = self._active_bots()

        for signal in self.pending_signals:
            eligible, reason = should_deploy(signal, self.config, active)
            if not eligible:
                continue

            entry = create_bot_entry(signal, self.config)
            self.bots.append(entry)
            active.append(entry)

            topic = f"{self.config.mqtt_topic_prefix}/deploy/{entry['token']}"
            self.publish(topic, entry)
            self.logger.info(
                f"{'DEPLOY' if self.config.auto_deploy else 'RECOMMEND'}: "
                f"{entry['token']} score={entry['score']} "
                f"${entry['capital']} @ ${entry['entry_price']}"
            )

        self.pending_signals.clear()

    def eval_cycle(self):
        self.process_signals()

        changes = evaluate_bots(self.bots, self.config)
        for change in changes:
            self.logger.info(change)

        status = build_swarm_status(self.bots, self.config)
        self.publish(f"{self.config.mqtt_topic_prefix}/status", status)
        self.logger.info(
            f"Swarm: {status['active_bots']} active, "
            f"${status['total_capital_deployed']} deployed, "
            f"PnL=${status['total_pnl']:.2f}"
        )

        save_state(self.bots, self.config.state_file)

    def run(self):
        self.connect_mqtt(
            subscriptions=["hbot/alpha/#"],
            on_message=self._on_message,
        )
        self.logger.info(
            f"Swarm service started, max {self.config.max_active_bots} bots, "
            f"${self.config.capital_per_bot} each, "
            f"auto_deploy={self.config.auto_deploy}"
        )

        last_eval = 0.0
        while self.running:
            now = time.time()
            if (now - last_eval) >= self.config.eval_interval_seconds:
                self.eval_cycle()
                last_eval = now
            self.sleep_loop(min(10, self.config.eval_interval_seconds))

        self.shutdown_mqtt()


if __name__ == "__main__":
    SwarmService().run()
