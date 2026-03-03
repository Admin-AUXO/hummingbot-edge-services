import json
import os
import sys
import time

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import PnlConfig
from metrics import (
    calc_max_drawdown,
    calc_profit_factor,
    calc_sharpe,
    calc_win_rate,
    group_by_signal,
)
from shared.base_service import BaseService


MAX_SIGNAL_LOG = 10000


class PnlService(BaseService):
    name = "pnl"

    def __init__(self):
        super().__init__(PnlConfig())
        self.signal_log = []
        self.current_state = {}

    def _on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            topic = msg.topic
            changed = False

            if "/regime/" in topic:
                val = data.get("regime")
                if val != self.current_state.get("regime"):
                    self.current_state["regime"] = val
                    changed = True
            elif "/correlation/" in topic:
                val = data.get("signal")
                if val != self.current_state.get("correlation"):
                    self.current_state["correlation"] = val
                    changed = True
            elif "/inventory/" in topic:
                val = data.get("signal")
                if val != self.current_state.get("inventory"):
                    self.current_state["inventory"] = val
                    changed = True
            elif "/session/" in topic:
                val = data.get("session")
                if val != self.current_state.get("session"):
                    self.current_state["session"] = val
                    changed = True
            elif "/funding/" in topic:
                val = data.get("signal")
                if val != self.current_state.get("funding"):
                    self.current_state["funding"] = val
                    changed = True

            if changed:
                entry = {"timestamp": time.time(), **self.current_state.copy()}
                self.signal_log.append(entry)
                if len(self.signal_log) > MAX_SIGNAL_LOG:
                    self.signal_log = self.signal_log[-MAX_SIGNAL_LOG // 2:]
                self.logger.info(f"Signal state updated: {self.current_state}")
        except Exception as e:
            self.logger.error(f"MQTT message error: {e}")

    def _fetch_executors(self):
        url = f"{self.config.api_base_url}/executors/search"
        cutoff = time.time() - self.config.lookback_hours * 3600
        payload = {
            "account_names": [self.config.account_name],
            "connector_names": [self.config.connector_name],
            "status": "TERMINATED",
        }
        try:
            resp = self.session.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            executors = resp.json()
            return [e for e in executors if e.get("close_timestamp", 0) >= cutoff]
        except Exception as e:
            self.logger.error(f"Executor fetch failed: {e}")
            return None

    def _build_report(self, executors):
        if not executors:
            return {
                "target": self.config.target_pair,
                "period_hours": self.config.lookback_hours,
                "total_executors": 0,
                "total_pnl": 0,
                "win_rate": 0,
                "sharpe_ratio": 0,
                "profit_factor": 0,
                "max_drawdown": 0,
                "avg_pnl": 0,
                "by_regime": {},
                "by_session": {},
                "best_combo": "NONE",
                "worst_combo": "NONE",
                "timestamp": int(time.time()),
            }

        pnl_list = [e.get("net_pnl_quote", 0) for e in executors]
        cumulative = []
        running = 0
        for p in pnl_list:
            running += p
            cumulative.append(running)

        signal_data = group_by_signal(executors, self.signal_log)

        return {
            "target": self.config.target_pair,
            "period_hours": self.config.lookback_hours,
            "total_executors": len(executors),
            "total_pnl": round(sum(pnl_list), 4),
            "win_rate": round(calc_win_rate(executors), 4),
            "sharpe_ratio": round(calc_sharpe(pnl_list), 4),
            "profit_factor": round(calc_profit_factor(executors), 4),
            "max_drawdown": round(calc_max_drawdown(cumulative), 4),
            "avg_pnl": round(sum(pnl_list) / len(pnl_list), 4),
            "by_regime": signal_data["by_regime"],
            "by_session": signal_data["by_session"],
            "best_combo": signal_data["best_combo"],
            "worst_combo": signal_data["worst_combo"],
            "timestamp": int(time.time()),
        }

    def _publish_report(self, report):
        topic = f"{self.config.report_topic}/{self.config.target_pair}"
        self.publish(topic, report)
        self.logger.info(
            f"Published report: {report['total_executors']} executors, "
            f"PnL={report['total_pnl']}, WR={report['win_rate']}, "
            f"Sharpe={report['sharpe_ratio']}"
        )

    def run(self):
        self.connect_mqtt(subscriptions=["hbot/#"], on_message=self._on_message)
        self.logger.info("PnL Service started, subscribed to hbot/#")

        last_poll = 0
        while self.running:
            now = time.time()
            if now - last_poll >= self.config.poll_interval_seconds:
                executors = self._fetch_executors()
                if executors is not None:
                    report = self._build_report(executors)
                    self._publish_report(report)
                last_poll = now
            time.sleep(1)

        self.shutdown_mqtt()


if __name__ == "__main__":
    PnlService().run()
