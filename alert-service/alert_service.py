import json
import os
import sys
import time

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import AlertConfig
from shared.base_service import BaseService


class AlertService(BaseService):
    name = "alert"

    def __init__(self):
        super().__init__(AlertConfig())
        self.state = {}

    def send_telegram(self, message):
        if not self.config.telegram_bot_token or not self.config.telegram_chat_id:
            self.logger.warning(f"Telegram not configured, alert: {message}")
            return
        url = f"https://api.telegram.org/bot{self.config.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": self.config.telegram_chat_id,
            "text": message,
            "parse_mode": "HTML",
        }
        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            self.logger.error(f"Telegram send failed: {e}")

    def _handle_regime(self, data, topic):
        key = f"regime:{topic}"
        prev = self.state.get(key)
        current = data.get("regime")
        if prev and prev != current and self.config.alert_on_regime_change:
            self.send_telegram(
                f"<b>Regime Change</b>\n"
                f"{prev} → <b>{current}</b>\n"
                f"NATR: {data.get('natr', 0):.4f} | BBW: {data.get('bb_width', 0):.4f}"
            )
        self.state[key] = current

    def _handle_correlation(self, data, topic):
        key = f"corr:{topic}"
        prev = self.state.get(key)
        current = data.get("signal")
        if prev and prev != current and self.config.alert_on_correlation_change:
            self.send_telegram(
                f"<b>Correlation Signal</b>\n"
                f"{prev} → <b>{current}</b>\n"
                f"Z: {data.get('avg_z_score', 0):.4f} | Bias: {data.get('spread_bias', 0):.4f}"
            )
        self.state[key] = current

    def _handle_inventory(self, data, topic):
        key_signal = f"inv:{topic}"
        key_kill = f"kill:{topic}"
        prev_signal = self.state.get(key_signal)
        prev_kill = self.state.get(key_kill)
        current_signal = data.get("signal")
        current_kill = data.get("kill", False)
        drawdown = data.get("drawdown_pct", 0)

        if prev_signal and prev_signal != current_signal and self.config.alert_on_inventory_change:
            self.send_telegram(
                f"<b>Inventory Signal</b>\n"
                f"{prev_signal} → <b>{current_signal}</b>\n"
                f"Skew: {data.get('inventory_skew', 0):.4f} | Bias: {data.get('skew_bias', 0):.4f}\n"
                f"Base: {data.get('base_value', 0):.2f} | Quote: {data.get('quote_value', 0):.2f}"
            )

        if current_kill and not prev_kill and self.config.alert_on_kill_switch:
            self.send_telegram(
                f"🚨 <b>KILL SWITCH ACTIVATED</b>\n"
                f"Drawdown: {drawdown:.4f} | Total: {data.get('total_value', 0):.2f}\n"
                f"All orders paused!"
            )
        elif not current_kill and prev_kill and self.config.alert_on_kill_switch:
            self.send_telegram(f"✅ <b>Kill switch cleared</b>\nDrawdown recovered: {drawdown:.4f}")

        if drawdown >= self.config.drawdown_warning_threshold and self.config.alert_on_drawdown_warning:
            prev_dd = self.state.get(f"dd_warned:{topic}", False)
            if not prev_dd:
                self.send_telegram(
                    f"⚠️ <b>Drawdown Warning</b>\n"
                    f"DD: {drawdown:.4f} (threshold: {self.config.drawdown_warning_threshold})\n"
                    f"Peak: {data.get('peak_value', 0):.2f} | Current: {data.get('total_value', 0):.2f}"
                )
                self.state[f"dd_warned:{topic}"] = True
        else:
            self.state[f"dd_warned:{topic}"] = False

        self.state[key_signal] = current_signal
        self.state[key_kill] = current_kill

    def _handle_session(self, data, topic):
        key = f"session:{topic}"
        prev = self.state.get(key)
        current = data.get("session")
        if prev and prev != current and self.config.alert_on_session_change:
            self.send_telegram(
                f"<b>Session Change</b>\n"
                f"{prev} → <b>{current}</b>\n"
                f"Spread mult: {data.get('spread_mult', 1.0)}"
            )
        self.state[key] = current

    def _handle_funding(self, data, topic):
        key = f"funding:{topic}"
        prev = self.state.get(key)
        current = data.get("signal")
        if prev and prev != current and self.config.alert_on_funding_change:
            self.send_telegram(
                f"<b>Funding Signal</b>\n"
                f"{prev} → <b>{current}</b>\n"
                f"Rate: {data.get('funding_rate', 0):.6f} | APR: {data.get('annualized_rate', 0):.2f}%\n"
                f"Bias: {data.get('spread_bias', 0):.4f}"
            )
        self.state[key] = current

    def _handle_analytics(self, data, topic):
        if not self.config.alert_on_analytics:
            return
        target = data.get("target", "?")
        win_rate = data.get("win_rate", 0)
        sharpe = data.get("sharpe_ratio", 0)
        total_pnl = data.get("total_pnl", 0)
        total = data.get("total_executors", 0)
        drawdown = data.get("max_drawdown", 0)
        best = data.get("best_combo", "N/A")
        worst = data.get("worst_combo", "N/A")

        alerts = []
        if win_rate < self.config.min_win_rate_alert:
            alerts.append(f"Win rate {win_rate:.1%} below threshold {self.config.min_win_rate_alert:.1%}")
        if sharpe < 0:
            alerts.append(f"Negative Sharpe ratio: {sharpe:.2f}")

        if alerts:
            self.send_telegram(
                f"⚠️ <b>PnL Warning — {target}</b>\n"
                + "\n".join(alerts)
                + f"\nPnL: {total_pnl:.2f} | Executors: {total} | DD: {drawdown:.4f}"
            )
        else:
            self.send_telegram(
                f"📊 <b>PnL Report — {target}</b>\n"
                f"Executors: {total} | PnL: {total_pnl:.2f}\n"
                f"WR: {win_rate:.1%} | Sharpe: {sharpe:.2f} | PF: {data.get('profit_factor', 0):.2f}\n"
                f"Best: {best} | Worst: {worst}"
            )

    def _handle_backtest(self, data, topic):
        if not self.config.alert_on_backtest:
            return
        target = data.get("target", "?")
        tested = data.get("total_configs_tested", 0)
        successful = data.get("successful_runs", 0)
        top = data.get("top_config")

        if top:
            self.send_telegram(
                f"🧪 <b>Backtest Sweep — {target}</b>\n"
                f"Tested: {tested} | Successful: {successful}\n"
                f"<b>Best config:</b>\n"
                f"Spread: {top.get('params', {}).get('buy_spreads', 'N/A')} | "
                f"SL: {top.get('params', {}).get('stop_loss', 'N/A')} | "
                f"TP: {top.get('params', {}).get('take_profit', 'N/A')}\n"
                f"Sharpe: {top.get('sharpe_ratio', 0):.2f} | PnL: {top.get('net_pnl', 0):.2f} | "
                f"Accuracy: {top.get('accuracy', 0):.1%}"
            )
        else:
            self.send_telegram(
                f"🧪 <b>Backtest Sweep — {target}</b>\n"
                f"Tested: {tested} | No valid results"
            )

    def _handle_hedge(self, data, topic):
        if not self.config.alert_on_hedge:
            return
        key = f"hedge:{topic}"
        prev = self.state.get(key)
        current = data.get("status")
        order_placed = data.get("order_placed", False)

        if prev and prev != current:
            self.send_telegram(
                f"<b>Hedge Status</b>\n"
                f"{prev} → <b>{current}</b>\n"
                f"Delta: {data.get('net_delta', 0):.4f} | Ratio: {data.get('hedge_ratio', 0):.4f}\n"
                f"Spot: {data.get('spot_balance', 0):.4f} | Short: {data.get('perp_short_size', 0):.4f}"
            )

        if order_placed:
            self.send_telegram(
                f"<b>Hedge Order Placed</b>\n"
                f"Action: {data.get('action')} | {data.get('target')}\n"
                f"Delta: {data.get('net_delta', 0):.4f} | PnL: {data.get('unrealized_pnl', 0):.4f}"
            )

        self.state[key] = current

    def _handle_lab(self, data, topic):
        if not self.config.alert_on_lab:
            return
        active = data.get("active_experiments", [])
        by_status = data.get("by_status", {})
        killed = by_status.get("KILLED", 0)

        key_killed = f"lab_killed:{topic}"
        prev_killed = self.state.get(key_killed, 0)

        if killed > prev_killed:
            new_kills = killed - prev_killed
            self.send_telegram(
                f"<b>Experiment Killed</b>\n"
                f"{new_kills} experiment(s) auto-killed\n"
                f"Running: {by_status.get('RUNNING', 0)} | Killed: {killed}"
            )

        promoted = by_status.get("PROMOTED", 0)
        key_promoted = f"lab_promoted:{topic}"
        prev_promoted = self.state.get(key_promoted, 0)

        if promoted > prev_promoted:
            self.send_telegram(
                f"<b>Experiment Promoted</b>\n"
                f"Running: {by_status.get('RUNNING', 0)} | Promoted: {promoted}"
            )

        self.state[key_killed] = killed
        self.state[key_promoted] = promoted

    def _handle_alpha(self, data, topic):
        if "/new_listing/" in topic:
            if not self.config.alert_on_new_listing:
                return
            token = data.get("token", "?")
            key = f"new_listing:{data.get('pair', topic)}"
            if self.state.get(key):
                return
            self.send_telegram(
                f"<b>New Listing Detected</b>\n"
                f"Token: <b>{token}</b>\n"
                f"Age: {data.get('age_hours', 0)}h | Liq: ${data.get('liquidity', 0):,.0f}\n"
                f"Vol 24H: ${data.get('volume_24h', 0):,.0f} | Price: ${data.get('price', 0)}"
            )
            self.state[key] = True
        else:
            if not self.config.alert_on_alpha:
                return
            token = data.get("token", "?")
            score = data.get("score", 0)
            key = f"alpha:{data.get('pair', topic)}"
            if self.state.get(key):
                return
            self.send_telegram(
                f"<b>Alpha Signal</b>\n"
                f"Token: <b>{token}</b> | Score: {score}/10\n"
                f"Liq: ${data.get('liquidity', 0):,.0f} | Vol: ${data.get('volume_24h', 0):,.0f}\n"
                f"MCap: ${data.get('mcap', 0):,.0f} | Price: ${data.get('price', 0)}"
            )
            self.state[key] = True

    def _handle_unlock(self, data, topic):
        if not self.config.alert_on_unlock:
            return
        token = data.get("token", "?")
        pair = data.get("pair", "")
        status = data.get("status", "")
        key = f"unlock:{pair}:{status}"
        prev = self.state.get(key)
        if prev == status:
            return

        if status == "PRE_UNLOCK":
            hours = data.get("hours_until_unlock", 0)
            self.send_telegram(
                f"<b>Token Unlock Approaching</b>\n"
                f"Token: <b>{token}</b> ({pair})\n"
                f"Unlock in: {hours}h | Size: {data.get('unlock_pct', 0)}%\n"
                f"Buy spread: x{data.get('buy_spread_mult', 1)} | Sell spread: x{data.get('sell_spread_mult', 1)}"
            )
        elif status == "POST_UNLOCK":
            hours = data.get("hours_since_unlock", 0)
            self.send_telegram(
                f"<b>Post-Unlock Window</b>\n"
                f"Token: <b>{token}</b> ({pair})\n"
                f"Unlocked: {hours}h ago | Size: {data.get('unlock_pct', 0)}%\n"
                f"Mean reversion window active\n"
                f"Buy spread: x{data.get('buy_spread_mult', 1)} | Sell spread: x{data.get('sell_spread_mult', 1)}"
            )

        self.state[key] = status

    def _handle_arb(self, data, topic):
        if not self.config.alert_on_arb:
            return
        token = data.get("token", "?")
        key = f"arb:{data.get('buy_dex', '')}:{data.get('sell_dex', '')}:{token}"
        if self.state.get(key):
            return
        self.send_telegram(
            f"<b>Arb Opportunity</b>\n"
            f"Token: <b>{token}</b> | Spread: {data.get('spread_pct', 0)}%\n"
            f"Buy: {data.get('buy_dex', '?')} @ ${data.get('buy_price', 0)}\n"
            f"Sell: {data.get('sell_dex', '?')} @ ${data.get('sell_price', 0)}\n"
            f"Max size: ${data.get('max_size_usd', 0):,.0f}"
        )
        self.state[key] = True

    def _handle_funding_scan(self, data, topic):
        if not self.config.alert_on_funding_scan:
            return
        if "/summary" in topic:
            return
        symbol = data.get("symbol", "?")
        key = f"fscan:{symbol}:{data.get('signal', '')}"
        if self.state.get(key):
            return
        self.send_telegram(
            f"<b>Funding Spike</b>\n"
            f"Symbol: <b>{symbol}</b> | {data.get('signal', '?')}\n"
            f"Rate: {data.get('funding_rate', 0):.6f} | APR: {data.get('annualized_apr', 0):.1f}%\n"
            f"Direction: {data.get('direction', '?')}"
        )
        self.state[key] = True

    def _handle_narrative(self, data, topic):
        if not self.config.alert_on_narrative:
            return
        token = data.get("token", "?")
        category = data.get("category", "?")
        key = f"narr:{category}:{token}"
        if self.state.get(key):
            return
        self.send_telegram(
            f"<b>Narrative Signal</b>\n"
            f"[{category}] <b>{token}</b>\n"
            f"Vol spike: {data.get('volume_spike', 0)}x | Vol: ${data.get('volume_24h', 0):,.0f}\n"
            f"5m: {data.get('price_change_5m', 0)}% | 1h: {data.get('price_change_1h', 0)}% | 24h: {data.get('price_change_24h', 0)}%\n"
            f"Liq: ${data.get('liquidity', 0):,.0f}"
        )
        self.state[key] = True

    def _handle_swarm(self, data, topic):
        if not self.config.alert_on_swarm:
            return
        if "/deploy/" in topic:
            token = data.get("token", "?")
            status = data.get("status", "?")
            self.send_telegram(
                f"<b>Swarm {'Deploy' if status == 'ACTIVE' else 'Recommendation'}</b>\n"
                f"Token: <b>{token}</b> | Score: {data.get('score', 0)}\n"
                f"Capital: ${data.get('capital', 0)} @ ${data.get('entry_price', 0)}\n"
                f"DEX: {data.get('dex', '?')}"
            )
        elif "/status" in topic:
            active = data.get("active_bots", 0)
            total_pnl = data.get("total_pnl", 0)
            deployed = data.get("total_capital_deployed", 0)
            by_status = data.get("by_status", {})
            killed = by_status.get("KILLED", 0)
            key_killed = "swarm_killed"
            prev_killed = self.state.get(key_killed, 0)
            if killed > prev_killed:
                self.send_telegram(
                    f"<b>Swarm Update</b>\n"
                    f"Active: {active} | Deployed: ${deployed:.0f}\n"
                    f"PnL: ${total_pnl:.2f} | Killed: {killed - prev_killed} new"
                )
            self.state[key_killed] = killed

    def _handle_clmm(self, data, topic):
        if not self.config.alert_on_clmm:
            return
        if not data.get("should_rebalance"):
            return
        self.send_telegram(
            f"<b>CLMM Rebalance</b>\n"
            f"Range: ${data.get('range_lower', 0):.2f} - ${data.get('range_upper', 0):.2f} ({data.get('range_pct', 0)}%)\n"
            f"Price: ${data.get('price', 0):.2f} | Util: {data.get('utilization_pct', 0)}%\n"
            f"Regime: {data.get('regime', '?')} | Session: {data.get('session', '?')}"
        )

    def _handle_migration(self, data, topic):
        if not self.config.alert_on_migration:
            return
        token = data.get("token", "?")
        if "/new_pool/" in topic:
            key = f"new_pool:{data.get('pair', topic)}"
            if self.state.get(key):
                return
            self.send_telegram(
                f"<b>New Pool Detected</b>\n"
                f"Token: <b>{token}</b> on {data.get('dex', '?')}\n"
                f"Age: {data.get('age_minutes', 0)} min | Liq: ${data.get('liquidity', 0):,.0f}\n"
                f"Vol: ${data.get('volume_24h', 0):,.0f} | Price: ${data.get('price', 0)}"
            )
            self.state[key] = True
        elif "/event/" in topic:
            status = data.get("status", "")
            key = f"event:{token}:{status}"
            if self.state.get(key) == status:
                return
            self.send_telegram(
                f"<b>Migration/Airdrop {status}</b>\n"
                f"Token: <b>{token}</b> | Type: {data.get('event_type', '?')}\n"
                f"{'In' if status == 'ACTIVE' else ''} {data.get('hours', 0)}h {'until' if status == 'ACTIVE' else 'ago'}\n"
                f"{data.get('description', '')}"
            )
            self.state[key] = status

    def _handle_rewards(self, data, topic):
        if not self.config.alert_on_rewards:
            return
        if "/summary" in topic:
            top = data.get("top_pools", [])
            if not top:
                return
            lines = [f"<b>Top LP Rewards</b>"]
            for p in top[:3]:
                lines.append(
                    f"  {p.get('pair', '?')} ({p.get('dex', '?')}): "
                    f"{p.get('effective_apr', 0)}% APR "
                    f"(risk-adj: {p.get('risk_adjusted_apr', 0)}%)"
                )
            key = f"rewards_top:{top[0].get('pair', '')}"
            if self.state.get(key):
                return
            self.send_telegram("\n".join(lines))
            self.state[key] = True

    def _on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            topic = msg.topic

            if "/regime/" in topic:
                self._handle_regime(data, topic)
            elif "/correlation/" in topic:
                self._handle_correlation(data, topic)
            elif "/inventory/" in topic:
                self._handle_inventory(data, topic)
            elif "/session/" in topic:
                self._handle_session(data, topic)
            elif "/funding_scan/" in topic:
                self._handle_funding_scan(data, topic)
            elif "/funding/" in topic:
                self._handle_funding(data, topic)
            elif "/analytics/" in topic:
                self._handle_analytics(data, topic)
            elif "/backtest/" in topic:
                self._handle_backtest(data, topic)
            elif "/hedge/" in topic:
                self._handle_hedge(data, topic)
            elif "/clmm/" in topic:
                self._handle_clmm(data, topic)
            elif "/alpha/" in topic:
                self._handle_alpha(data, topic)
            elif "/unlock/" in topic:
                self._handle_unlock(data, topic)
            elif "/arb/" in topic:
                self._handle_arb(data, topic)
            elif "/narrative/" in topic:
                self._handle_narrative(data, topic)
            elif "/swarm/" in topic:
                self._handle_swarm(data, topic)
            elif "/migration/" in topic:
                self._handle_migration(data, topic)
            elif "/rewards/" in topic:
                self._handle_rewards(data, topic)
            elif "/lab/" in topic and "/cmd/" not in topic:
                self._handle_lab(data, topic)
        except Exception as e:
            self.logger.error(f"Message handler error: {e}")

    def run(self):
        self.connect_mqtt(subscriptions=[self.config.mqtt_topic], on_message=self._on_message)
        self.send_telegram("🤖 <b>Alert Service Started</b>\nMonitoring all trading signals.")

        while self.running:
            time.sleep(1)

        self.shutdown_mqtt()


if __name__ == "__main__":
    AlertService().run()
