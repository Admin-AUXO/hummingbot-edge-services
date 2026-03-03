import os
import sys
import time

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import HedgeConfig
from hedge_calculator import (
    calc_hedge_action,
    calc_hedge_ratio,
    calc_net_delta,
    clamp_order_size,
    classify_hedge_status,
)
from shared.base_service import BaseService


class HedgeService(BaseService):
    name = "hedge"

    def __init__(self):
        super().__init__(HedgeConfig())
        self.last_status = None
        self.last_order_time = 0.0

    def fetch_spot_balance(self):
        url = f"{self.config.api_base_url}/portfolio/state"
        payload = {
            "account_names": [self.config.spot_account_name],
            "connector_names": [self.config.spot_connector_name],
        }
        resp = self.session.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        state = resp.json()

        account_data = state.get(self.config.spot_account_name, {})
        connector_data = account_data.get(self.config.spot_connector_name, [])
        for token_info in connector_data:
            if token_info.get("token", "").upper() == "SOL":
                return float(token_info.get("amount", 0))
        return 0.0

    def fetch_perp_position(self):
        url = f"{self.config.api_base_url}/trading/positions"
        payload = {
            "account_names": [self.config.perp_account_name],
            "connector_names": [self.config.perp_connector_name],
        }
        resp = self.session.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        positions = data.get("data", []) if isinstance(data, dict) else data

        for pos in positions:
            if pos.get("trading_pair") == self.config.perp_trading_pair:
                return abs(float(pos.get("amount", 0))), float(pos.get("unrealized_pnl", 0))
        return 0.0, 0.0

    def place_hedge_order(self, action, size):
        if action == "INCREASE_SHORT":
            trade_type = "SELL"
            position_action = "OPEN"
        else:
            trade_type = "BUY"
            position_action = "CLOSE"

        url = f"{self.config.api_base_url}/trading/orders"
        payload = {
            "account_name": self.config.perp_account_name,
            "connector_name": self.config.perp_connector_name,
            "trading_pair": self.config.perp_trading_pair,
            "trade_type": trade_type,
            "amount": size,
            "order_type": self.config.order_type,
            "position_action": position_action,
            "leverage": self.config.hedge_leverage,
        }
        resp = self.session.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        self.logger.info(f"Hedge order placed: {action} {size} {self.config.perp_trading_pair}")
        return resp.json()

    def publish_status(self, payload):
        topic = f"{self.config.mqtt_topic_prefix}/{self.config.target_pair}"
        self.publish(topic, payload)

        status = payload["status"]
        if status != self.last_status:
            self.logger.info(f"STATUS CHANGE: {self.last_status} -> {status} | Delta={payload['net_delta']:.4f} Ratio={payload['hedge_ratio']:.4f}")
            self.last_status = status
        else:
            self.logger.info(f"Status: {status} | Delta={payload['net_delta']:.4f} | Ratio={payload['hedge_ratio']:.4f} | Action={payload['action']}")

    def run(self):
        self.connect_mqtt()
        self.logger.info(f"Hedging {self.config.spot_connector_name} spot with {self.config.perp_connector_name} perp, threshold={self.config.delta_threshold}")

        while self.running:
            try:
                spot_balance = self.fetch_spot_balance()
                perp_short_size, unrealized_pnl = self.fetch_perp_position()

                delta = calc_net_delta(spot_balance, perp_short_size)
                action, desired_size = calc_hedge_action(delta, self.config.delta_threshold)
                ratio = calc_hedge_ratio(spot_balance, perp_short_size)
                status = classify_hedge_status(ratio)

                order_placed = False
                now = time.time()

                if spot_balance == 0 and perp_short_size > 0:
                    action = "REDUCE_SHORT"
                    desired_size = perp_short_size
                    self.logger.warning("No spot inventory, unwinding short position")

                if action != "HOLD" and (now - self.last_order_time) >= self.config.cooldown_seconds:
                    clamped = clamp_order_size(
                        desired_size,
                        self.config.max_hedge_order_size,
                        perp_short_size,
                        self.config.max_position_size,
                        action,
                    )
                    if clamped > 0:
                        self.place_hedge_order(action, clamped)
                        self.last_order_time = now
                        order_placed = True

                payload = {
                    "target": "sol_usdc",
                    "spot_balance": round(spot_balance, 4),
                    "perp_short_size": round(perp_short_size, 4),
                    "net_delta": round(delta, 4),
                    "hedge_ratio": round(ratio, 4),
                    "status": status,
                    "action": action,
                    "order_placed": order_placed,
                    "unrealized_pnl": round(unrealized_pnl, 4),
                    "timestamp": now,
                }
                self.publish_status(payload)

            except Exception as e:
                self.logger.error(f"Hedge error: {e}")

            self.sleep_loop(self.config.poll_interval_seconds)

        self.shutdown_mqtt()


if __name__ == "__main__":
    HedgeService().run()
