import json
import os
import sys
import time
from datetime import datetime, timezone

from concurrent.futures import ThreadPoolExecutor
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import AlertConfig
from shared.base_service import BaseService
from shared.utils import (
    TTLCache,
    bar,
    dex_link,
    fmt_hours,
    fmt_pct,
    fmt_price,
    fmt_usd,
    rank_emoji,
    sign,
    token_link,
)


MIN_PROFIT_100 = 10
MIN_ARB_NET_PROFIT = 10.0
SOLANA_GAS = 0.01
EST_SLIPPAGE_PCT = 0.3


class AlertService(BaseService):
    name = "alert"

    def __init__(self):
        super().__init__(AlertConfig())
        self.state = {}
        self.cache = TTLCache(3600 * 6)
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        self.handlers = {
            "/inventory/": self._handle_inventory,
            "/session/": self._handle_session,
            "/analytics/": self._handle_analytics,
            "/hedge/": self._handle_hedge,
            "/watchlist/": self._handle_watchlist,
            "/clmm/": self._handle_clmm,
            "/alpha/": self._handle_alpha,
            "/arb/": self._handle_arb,
            "/narrative/": self._handle_narrative,
            "/rewards/": self._handle_rewards,
        }

    def _should_alert(self, key, current, config_toggle):
        if not getattr(self.config, config_toggle, True): return False, None
        prev = self.state.get(key)
        if prev == current: return False, prev
        self.state[key] = current
        return (prev is not None), prev

    def _should_alert_numeric(self, key, current, config_toggle, threshold=0.0):
        if not getattr(self.config, config_toggle, True): return False, 0.0
        prev = float(self.state.get(key, 0))
        if abs(current - prev) < threshold: 
            self.state[key] = current
            return False, prev
        self.state[key] = current
        return (prev != 0), prev

    def _fmt_meta(self, data):
        liq = data.get("liquidity") or data.get("buy_liquidity", 0)
        vol = data.get("volume_24h") or data.get("buy_volume", 0)
        return f"Liq: {fmt_usd(liq)} | Vol: {fmt_usd(vol)}"

    def send_telegram(self, message):
        if not self.config.telegram_bot_token or not self.config.telegram_chat_id:
            self.logger.warning(f"Telegram not configured, alert: {message}")
            return
        self.executor.submit(self._send_telegram_sync, message)

    def _send_telegram_sync(self, message):
        url = f"https://api.telegram.org/bot{self.config.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": self.config.telegram_chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        try:
            resp = self.session.post(url, json=payload, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            self.logger.error(f"Telegram send failed: {e}")

    def _handle_inventory(self, data, topic):
        key_signal = f"inv:{topic}"
        key_kill = f"kill:{topic}"
        prev_signal = self.state.get(key_signal)
        prev_kill = self.state.get(key_kill)
        current_signal = data.get("signal")
        current_kill = data.get("kill", False)
        drawdown = float(data.get("drawdown_pct", 0))
        total_val = float(data.get("total_value", 0))
        peak_val = float(data.get("peak_value", 0))
        base_val = float(data.get("base_value", 0))
        quote_val = float(data.get("quote_value", 0))
        skew = float(data.get("inventory_skew", 0))
        bias = float(data.get("skew_bias", 0))
        target = data.get("target", topic.split("/")[-1])
        base_pct = (base_val / total_val * 100) if total_val > 0 else 0
        loss_usd = peak_val - total_val if peak_val > total_val else 0

        if prev_signal and prev_signal != current_signal and self.config.alert_on_inventory_change:
            skew_bar = "L" + "█" * int(abs(skew) * 5) if skew < 0 else "█" * int(skew * 5) + "R"
            self.send_telegram(
                f"📦 <b>Inventory — {target}</b>\n"
                f"Status: <b>{current_signal}</b> | Skew: {skew:+.2f} ({skew_bar})\n"
                f"Value: <b>{fmt_usd(total_val)}</b> (Base: {fmt_usd(base_val)} / Quote: {fmt_usd(quote_val)})\n"
                f"Exposure: {base_pct:.0f}% Base | DD: {fmt_pct(drawdown * 100)} from Peak"
            )

        if current_kill and not prev_kill and self.config.alert_on_kill_switch:
            self.send_telegram(
                f"🚨 <b>KILL SWITCH — {target}</b>\n"
                f"Drawdown: {fmt_pct(drawdown * 100)} ({fmt_usd(loss_usd)} loss)\n"
                f"Peak: {fmt_usd(peak_val)} → Current: {fmt_usd(total_val)}\n"
                f"<b>ALL ORDERS PAUSED</b>"
            )
        elif not current_kill and prev_kill and self.config.alert_on_kill_switch:
            self.send_telegram(
                f"✅ <b>Kill Switch Cleared — {target}</b>\n"
                f"DD recovered to {fmt_pct(drawdown * 100)} | Value: {fmt_usd(total_val)}\n"
                f"Orders resuming"
            )

        if drawdown >= self.config.drawdown_warning_threshold and self.config.alert_on_drawdown_warning:
            prev_dd = self.state.get(f"dd_warned:{topic}", False)
            if not prev_dd:
                self.send_telegram(
                    f"⚠️ <b>Drawdown Warning — {target}</b>\n"
                    f"DD: {fmt_pct(drawdown * 100)} (threshold: {fmt_pct(self.config.drawdown_warning_threshold * 100)})\n"
                    f"Loss: {fmt_usd(loss_usd)} | Peak: {fmt_usd(peak_val)} → {fmt_usd(total_val)}"
                )
                self.state[f"dd_warned:{topic}"] = True
        else:
            self.state[f"dd_warned:{topic}"] = False

        self.state[key_signal] = current_signal
        self.state[key_kill] = current_kill

    def _handle_session(self, data, topic):
        current = data.get("session")
        ok, prev = self._should_alert(f"session:{topic}", current, "alert_on_session_change")
        if ok:
            target = data.get("target", topic.split("/")[-1])
            spread_mult = float(data.get("spread_mult", 1.0))
            utc_hour = data.get("utc_hour", "?")
            SESSION = {
                "NIGHT": ("🌙", "Low liquidity — wider spreads or pause",        "1.5-3% spreads or idle. Collect funding rates passively"),
                "ASIA":  ("🌏", "Moderate vol — SOL & Asia meme narratives hot", "0.5-1% spreads. Watch narrative alerts for Asia tokens"),
                "EU":    ("🌍", "High vol — best window for arb + tight PMM",    "0.3-0.8% spreads. Prime arb-scanning window"),
                "US":    ("🌎", "Peak vol — momentum sniping most effective",    "Tight spreads + follow alpha/narrative spikes"),
            }.get(current, ("🕐", "", "Monitor"))
            emoji, desc, strategy = SESSION
            mult_str = f"x{spread_mult:.2f} ({'wider' if spread_mult > 1 else 'tighter' if spread_mult < 1 else 'std'})"
            self.send_telegram(
                f"{emoji} <b>Session: {prev} → {current}</b> ({target})\n"
                f"UTC {utc_hour}:00 | Spread mult: {mult_str}\n"
                f"<i>{desc}</i>\n"
                f"⚡ {strategy}"
            )

    def _handle_analytics(self, data, topic):
        if not self.config.alert_on_analytics:
            return
        target = data.get("target", "?")
        win_rate = float(data.get("win_rate", 0))
        sharpe = float(data.get("sharpe_ratio", 0))
        total_pnl = float(data.get("total_pnl", 0))
        total = int(data.get("total_executors", 0))
        drawdown = float(data.get("max_drawdown", 0))
        pf = float(data.get("profit_factor", 0))
        best = data.get("best_combo", "N/A")
        worst = data.get("worst_combo", "N/A")
        period = data.get("period_hours", 24)
        avg_pnl = float(data.get("avg_pnl", total_pnl / total if total > 0 else 0))
        by_regime = data.get("by_regime", {})
        by_session = data.get("by_session", {})

        alerts = []
        if win_rate < self.config.min_win_rate_alert:
            alerts.append(f"Win rate {win_rate:.1%} < {self.config.min_win_rate_alert:.1%}")
        if sharpe < 0:
            alerts.append(f"Negative Sharpe: {sharpe:.2f}")
        if pf > 0 and pf < 1.0:
            alerts.append(f"Profit factor {pf:.2f} < 1.0 (losing)")

        regime_parts = []
        for r, rd in sorted(by_regime.items(), key=lambda x: x[1].get("pnl", 0), reverse=True):
            regime_parts.append(f"  {r}: {fmt_usd(rd.get('pnl', 0))} ({rd.get('count', 0)} trades)")
        regime_str = "\n".join(regime_parts[:3]) if regime_parts else ""

        if alerts:
            self.send_telegram(
                f"⚠️ <b>Performance Warning — {target}</b>\n"
                + "\n".join(f"  • {a}" for a in alerts)
                + f"\nPnL: <b>{fmt_usd(total_pnl)}</b> | WR: {win_rate:.1%}\n"
                f"Sharpe: {sharpe:.2f} | PF: {pf:.2f} | Max DD: {fmt_pct(drawdown * 100)}\n"
                + (f"\n<b>Top Regimes:</b>\n{regime_str}" if regime_str else "")
            )
        else:
            pnl_emoji = "🟢" if total_pnl > 0 else "🔴" if total_pnl < 0 else "⚪"
            self.send_telegram(
                f"{pnl_emoji} <b>PnL Report ({period}h) — {target}</b>\n"
                f"Total PnL: <b>{fmt_usd(total_pnl)}</b> | WR: {win_rate:.1%}\n"
                f"Sharpe: {sharpe:.2f} | PF: {pf:.2f} | Avg: {fmt_usd(avg_pnl)}/tr\n"
                f"Best: {best} | Worst: {worst}\n"
                + (f"\n<b>Top Regimes:</b>\n{regime_str}" if regime_str else "")
            )

    def _handle_hedge(self, data, topic):
        current = data.get("status")
        ok, prev = self._should_alert(f"hedge:{topic}", current, "alert_on_hedge")
        order_placed = data.get("order_placed", False)
        target = data.get("target", topic.split("/")[-1])
        spot = float(data.get("spot_balance", 0))
        delta = float(data.get("net_delta", 0))
        delta_pct = (delta / spot * 100) if spot > 0 else 0
        ratio = float(data.get("hedge_ratio", 0))

        if ok:
            short = float(data.get("perp_short_size", 0))
            upnl = float(data.get("unrealized_pnl", 0))
            coverage = (short / spot * 100) if spot > 0 else 0
            self.send_telegram(
                f"🛡️ <b>Hedge — {target}</b>\n"
                f"Status: <b>{current}</b> | Ratio: {ratio:.2f}\n"
                f"Exposure: {delta_pct:+.1f}% Delta ({fmt_usd(delta * data.get('price', 1))})\n"
                f"Spot: {spot:.2f} | Short: {short:.2f} ({coverage:.0f}% covered)\n"
                f"uPnL: <b>{sign(upnl)}{fmt_usd(abs(upnl))}</b>"
            )

        if order_placed:
            action = data.get("action", "?")
            self.send_telegram(
                f"📉 <b>Hedge Order — {target}</b>\n"
                f"Action: <b>{action}</b> | Ratio → {ratio:.2f}\n"
                f"Net Delta: {delta:+.4f} ({delta_pct:+.1f}%)"
            )

    def _handle_alpha(self, data, topic):
        is_listing = "/new_listing/" in topic
        addr = data.get("pair_address") or data.get("address", "")
        key = f"alpha:{'nl' if is_listing else 'sig'}:{addr}"
        if key in self.cache: return

        token = data.get("token", "?")
        liq, vol = float(data.get("liquidity", 0)), float(data.get("volume_24h", 0))
        age = float(data.get("age_hours", 0))
        price = data.get("price", 0)

        if is_listing:
            vol_liq = (vol / liq) if liq > 0 else 0
            rating = "🟢 HOT" if vol_liq > 3 else "🟡 WARM" if vol_liq > 1 else "⚪ EARLY"
            self.send_telegram(
                f"🆕 <b>New Listing — {token}</b> [{rating}]{dex_link(addr)}\n"
                f"Dex: {data.get('dex', '?')} | Age: {fmt_hours(age)}\n"
                f"{self._fmt_meta(data)} ({vol_liq:.1f}x ratio)\n"
                f"Price: {fmt_price(price)} | 💰 Est. high-vol first-day moves"
            )
        else:
            score = int(data.get("score", 0))
            p5m, p1h = float(data.get("price_change_5m", 0)), float(data.get("price_change_1h", 0))
            momentum = "🔥 STRONG UP" if p5m > 2 and p1h > 5 else "📈 Climbing" if p5m > 0.5 and p1h > 2 else "➡️ Flat"
            self.send_telegram(
                f"🎯 <b>Alpha Signal — {token}</b>{token_link(addr)}\n"
                f"Score: <b>{score}/10</b> {bar(score)} | {momentum}\n"
                f"{self._fmt_meta(data)} | Price: {fmt_price(price)}\n"
                f"Change: 5m {sign(p5m)}% | 1h {sign(p1h)}%\n"
                f"💰 <b>$100 → {fmt_usd(float(data.get('est_profit_pct', 0)))}</b> est. profit"
            )
        self.cache.add(key)

    def _handle_arb(self, data, topic):
        token = data.get("token", "?")
        buy_dex, sell_dex = data.get("buy_dex", ""), data.get("sell_dex", "")
        key = f"arb:{buy_dex}:{sell_dex}:{token}"
        if key in self.cache: return

        spread = float(data.get("spread_pct", 0))
        net_prof = (100 * spread / 100) - (100 * EST_SLIPPAGE_PCT / 100) - SOLANA_GAS
        if net_prof < MIN_ARB_NET_PROFIT: return

        buy_p, sell_p = float(data.get("buy_price", 0)), float(data.get("sell_price", 0))
        max_size = float(data.get("max_size_usd", 0))
        buy_addr = data.get("buy_pair", "")
        rating = "🟢 HIGH VALUE" if net_prof >= 25 else "🟡 GOOD" if net_prof >= 15 else "⚪ NORMAL"
        
        self.send_telegram(
            f"⚡ <b>Arb — {token}</b> [{rating}]{dex_link(buy_addr)}\n"
            f"Spread: <b>{fmt_pct(spread)}</b> | Buy: {buy_dex} ({fmt_price(buy_p)})\n"
            f"Net/$100: <b>{fmt_usd(net_prof)}</b> | Max: {fmt_usd(max_size)}\n"
            f"Sell: {sell_dex} ({fmt_price(sell_p)})\n"
            f"<i>Strategy: Execution via aggregator or direct Jito tip</i>"
        )
        self.cache.add(key)

    def _handle_narrative(self, data, topic):
        token, category = data.get("token", "?"), data.get("category", "?")
        key = f"narr:{category}:{token}"
        if key in self.cache: return

        keyword = data.get("keyword", "")
        spike, p1h, p5m = float(data.get("volume_spike", 0)), float(data.get("price_change_1h", 0)), float(data.get("price_change_5m", 0))
        trend = "Bullish" if p5m > 0 and p1h > 0 else "Bearish" if p5m < 0 and p1h < 0 else "Mixed"
        rating = "🟢 HIGH" if spike >= 5 and p1h > 5 else "🟡 MID" if spike >= 3 else "⚪ LOW"
        
        self.send_telegram(
            f"📡 <b>Narrative — {token}</b> [{category}]{token_link(data.get('address', ''))}\n"
            f"Spike: <b>{spike:.1f}x</b> [{rating}] | Keyword: {keyword}\n"
            f"{self._fmt_meta(data)}\n"
            f"Change: 1h {sign(p1h)}% | 5m {sign(p5m)}% | Trend: {trend}\n"
            f"💰 <b>$100 → {fmt_usd(max(p1h * 0.5, 0))}</b> (extrapolated trend)"
        )
        self.cache.add(key)

    def _handle_clmm(self, data, topic):
        if not self.config.alert_on_clmm or not data.get("should_rebalance"): return
        
        target = topic.split("/")[-1]
        price, lower, upper = float(data.get("price", 0)), float(data.get("range_lower", 0)), float(data.get("range_upper", 0))
        range_pct, util = float(data.get("range_pct", 0)), float(data.get("utilization_pct", 0))
        regime, session = data.get("regime", "?"), data.get("session", "?")
        natr = float(data.get("natr", 0))
        
        mid = (upper + lower) / 2
        range_width = upper - lower
        off_center = ((price - mid) / (range_width / 2) * 100) if range_width > 0 else 0
        edge = "upper" if price > mid else "lower"
        
        est_daily_fees = float(data.get("volume_24h", 0)) * 0.003 / max(float(data.get("liquidity", 1)), 1)
        self.send_telegram(
            f"🔄 <b>CLMM Rebalance — {target}</b>\n"
            f"Price: <b>{fmt_price(price)}</b> ({off_center:+.0f}% off-center, {edge} edge)\n"
            f"New range: {fmt_price(lower)} – {fmt_price(upper)} ({fmt_pct(range_pct)})\n"
            f"Util: {fmt_pct(util)} | NATR: {fmt_pct(natr*100)} | {regime}/{session}\n"
            f"Est. fees: <b>{fmt_usd(est_daily_fees * 100)}/day</b> per $100 LP"
        )

    def _handle_watchlist(self, data, topic):
        if not self.config.alert_on_watchlist: return
        sym = data.get("symbol", data.get("token", "?"))
        parts = topic.split("/")
        entry_type = parts[-2]
        
        if "/added/" in topic:
            addr = data.get("address", "")
            source = data.get("source", "?")
            self.send_telegram(
                f"➕ <b>Watchlist: {sym} Added</b> ({entry_type.title()}){token_link(addr)}\n"
                f"Via: {source} | {self._fmt_meta(data)}\n"
                f"<i>⚡ Monitoring for active opportunities</i>"
            )
        elif "/removed/" in topic:
            cycles = data.get("consecutive_stale_cycles", 0)
            self.send_telegram(
                f"➖ <b>Watchlist: {sym} Removed</b>\n"
                f"Stale for {cycles} cycles — volume dried up"
            )

    def _handle_rewards(self, data, topic):
        if "/summary" in topic:
            top = [p for p in data.get("top_pools", []) if 100 * float(p.get("effective_apr", 0)) / 3650 >= MIN_PROFIT_100]
            if not top: return
            if f"rtop:{top[0].get('pair')}" in self.cache: return

            lines = [f"🏆 <b>Top LP Rewards</b> ({len(top)} pools)"]
            for i, p in enumerate(top[:5]):
                eff = float(p.get("effective_apr", 0))
                earn = 100 * eff / 36500
                lines.append(
                    f"{rank_emoji(i)} <b>{p.get('pair','?')}</b> ({p.get('dex','?')}){token_link(p.get('address'))}\n"
                    f"   <b>{fmt_pct(eff)}</b> Est. APR | Income ($100): <b>{fmt_usd(earn)}/day</b>"
                )
            self.send_telegram("\n\n".join(lines))
            self.cache.add(f"rtop:{top[0].get('pair')}")
        else:
            token = data.get("token", "?")
            eff_apr = float(data.get("effective_apr", 0))
            ok, prev = self._should_alert_numeric(f"rev:{token}", eff_apr, "alert_on_rewards", threshold=5.0)
            if not ok: return
            
            pair, dex, addr = data.get("pair", "?"), data.get("dex", "?"), data.get("address", "")
            earn_day = 100 * eff_apr / 36500
            trend = "📈" if eff_apr > prev else "📉"
            self.send_telegram(
                f"{trend} <b>LP Reward — {pair}</b> ({dex}){token_link(addr)}\n"
                f"APR: <b>{fmt_pct(eff_apr)}</b> ({sign(eff_apr - prev)}%) | Risk: {data.get('risk_score')}/10\n"
                f"Income ($100): <b>{fmt_usd(earn_day)}/day</b>\n"
                f"{self._fmt_meta(data)}"
            )

    def _on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            topic = msg.topic
            
            if "/cmd/" in topic: return
            
            for key, handler in self.handlers.items():
                if key in topic:
                    handler(data, topic)
                    break
        except Exception as e:
            self.logger.error(f"Message handler error: {e}")

    def run(self):
        self.connect_mqtt(subscriptions=[self.config.mqtt_topic], on_message=self._on_message)
        self.send_telegram(
            "🤖 <b>Edge Services Online</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "📡 Monitoring: Session\n"
            "⚡ Scanning:   Arb | Alpha | Narrative\n"
            "🛡️ Managing:   Hedge | Inventory | PnL\n"
            "🎯 Optimizing: CLMM | Rewards | Watchlist\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"All signals routing to Telegram. Min arb: {fmt_usd(MIN_ARB_NET_PROFIT)} 💰"
        )

        while self.running:
            time.sleep(1)

        self.shutdown_mqtt()


if __name__ == "__main__":
    AlertService().run()
