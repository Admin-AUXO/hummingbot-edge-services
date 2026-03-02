import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import LabConfig
from experiment import (
    build_lab_status,
    create_experiment,
    evaluate_kill,
    evaluate_promotion,
    generate_experiment_id,
    load_experiments,
    save_experiments,
    update_metrics,
)
from shared.base_service import BaseService


class LabService(BaseService):
    name = "lab"

    def __init__(self):
        config = LabConfig()
        super().__init__(config)
        self.experiments = load_experiments(self.config.data_file)
        self.analytics_cache = {}

    def on_shutdown(self):
        self.logger.info("Saving experiments...")
        save_experiments(self.experiments, self.config.data_file)

    def _on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            topic = msg.topic

            if "/analytics/" in topic:
                pair = topic.split("/")[-1]
                self.analytics_cache[pair] = data
                self.logger.info(f"Cached analytics for {pair}")
            elif topic == "hbot/lab/cmd/create":
                self._handle_create(data)
            elif topic == "hbot/lab/cmd/kill":
                self._handle_kill(data)
            elif topic == "hbot/lab/cmd/promote":
                self._handle_promote(data)
        except Exception as e:
            self.logger.error(f"Message handler error: {e}")

    def _handle_create(self, data):
        exp = create_experiment(data, self.config)
        exp["id"] = generate_experiment_id(self.experiments)
        self.experiments.append(exp)
        save_experiments(self.experiments, self.config.data_file)
        self.logger.info(f"Created experiment {exp['id']}: {exp['hypothesis']} [{exp['tier']}]")

    def _handle_kill(self, data):
        exp_id = data.get("id")
        reason = data.get("reason", "Manual kill")
        for exp in self.experiments:
            if exp["id"] == exp_id and exp["status"] in ("RUNNING", "PENDING"):
                exp["status"] = "KILLED"
                exp["ended_at"] = time.time()
                exp["post_mortem"] = reason
                save_experiments(self.experiments, self.config.data_file)
                self.logger.info(f"Killed experiment {exp_id}: {reason}")
                return
        self.logger.warning(f"Experiment {exp_id} not found or not active")

    def _handle_promote(self, data):
        exp_id = data.get("id")
        tier_order = ["EXPLORATION", "TESTING", "PRODUCTION"]
        for exp in self.experiments:
            if exp["id"] == exp_id and exp["status"] == "RUNNING":
                current_idx = tier_order.index(exp["tier"]) if exp["tier"] in tier_order else -1
                if current_idx < len(tier_order) - 1:
                    old_tier = exp["tier"]
                    exp["tier"] = tier_order[current_idx + 1]
                    exp["status"] = "PROMOTED"
                    save_experiments(self.experiments, self.config.data_file)
                    self.logger.info(f"Promoted {exp_id}: {old_tier} -> {exp['tier']}")
                else:
                    self.logger.warning(f"{exp_id} already at highest tier")
                return
        self.logger.warning(f"Experiment {exp_id} not found or not running")

    def eval_cycle(self):
        changed = False
        for exp in self.experiments:
            if exp["status"] not in ("RUNNING", "PENDING"):
                continue

            pair = exp.get("pair")
            analytics = self.analytics_cache.get(pair)
            if analytics:
                update_metrics(exp, analytics)
                changed = True

            if exp["status"] == "RUNNING":
                should_kill, reason = evaluate_kill(exp)
                if should_kill:
                    exp["status"] = "KILLED"
                    exp["ended_at"] = time.time()
                    exp["post_mortem"] = reason
                    self.logger.info(f"Auto-killed {exp['id']}: {reason}")
                    changed = True
                    continue

                should_promote, reason = evaluate_promotion(exp)
                if should_promote:
                    self.logger.info(f"Promotion recommended for {exp['id']}: {reason}")

        if changed:
            save_experiments(self.experiments, self.config.data_file)

    def publish_status(self):
        status = build_lab_status(self.experiments)
        pairs = set(e.get("pair", "unknown") for e in self.experiments)
        for pair in pairs:
            topic = f"hbot/lab/{pair}"
            self.publish(topic, status)
        if not pairs:
            self.publish("hbot/lab/status", status)
        self.logger.info(f"Published lab status: {status['by_status']}")

    def run(self):
        self.connect_mqtt(subscriptions=["hbot/analytics/#", "hbot/lab/cmd/#"], on_message=self._on_message)
        self.logger.info(f"Lab service started, {len(self.experiments)} experiments loaded, eval every {self.config.eval_interval_seconds}s")

        last_eval = 0.0
        while self.running:
            now = time.time()
            if (now - last_eval) >= self.config.eval_interval_seconds:
                self.eval_cycle()
                self.publish_status()
                last_eval = now

            self.sleep_loop(min(10, self.config.eval_interval_seconds))

        self.shutdown_mqtt()


if __name__ == "__main__":
    LabService().run()
