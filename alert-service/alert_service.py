import json
import os
import sys
import time
from datetime import datetime, timezone

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import AlertConfig
from shared.base_service import BaseService


def _fmt_usd(v):
    v = float(v or 0)
    if abs(v) >= 1_000_000:
        return f"${v / 1_000_000:,.2f}M"
    if abs(v) >= 1_000:
        return f"${v / 1_000:,.1f}K"
    return f"${v:,.2f}"


def _fmt_pct(v, decimals=2):
    return f"{float(v or 0):.{decimals}f}%"


def _fmt_ts(epoch_ms):
    if not epoch_ms:
        return "?"
    ts = epoch_ms / 1000 if epoch_ms > 1e12 else epoch_ms
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%H:%M UTC")


def _fmt_hours(h):
    h = float(h or 0)
    if h >= 24:
        return f"{h / 24:.1f}d"
    return f"{h:.1f}h"


def _sign(v):
    v = float(v or 0)
    if v > 0:
        return f"+{v}"
    return str(v)


def _bar(score, max_score=10):
    filled = int(round(float(score or 0) / max_score * 5))
    return "█" * filled + "░" * (5 - filled)


def _dex_link(pair_address):
    if not pair_address or pair_address == "N/A":
        return ""
    return f' <a href="https://dexscreener.com/solana/{pair_address}">[DEX]</a>'


def _token_link(address):
    if not address or address == "N/A":
        return ""
    return f' <a href="https://dexscreener.com/solana/{address}">[DEX]</a>'


def _binance_link(symbol):
    if not symbol:
        return ""
    return f' <a href="https://www.binance.com/en/futures/{symbol}">[BN]</a>'


MIN_PROFIT_100 = 10
MIN_ARB_NET_PROFIT = 5.0
SOLANA_GAS = 0.01
EST_SLIPPAGE_PCT = 0.3


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
            "disable_web_page_preview": True,
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
            symbol = data.get("symbol", topic.split("/")[-1])
            natr = float(data.get("natr", 0))
            bbw = float(data.get("bb_width", 0))
            vol_label = "HIGH" if natr > 0.02 else "LOW" if natr < 0.008 else "MID"
            regime_info = {
                "UPTREND": {
                    "hint": "Tighten buys, widen sells — ride the trend",
                    "profit": f"Momentum plays: est. {natr * 100 * 5:.1f}-{natr * 100 * 15:.1f}% per swing",
                    "action": "BUY bias | Alpha & narrative signals high-value",
                },
                "DOWNTREND": {
                    "hint": "Widen buys, tighten sells — shed inventory",
                    "profit": "Short bias: funding rate likely positive (shorts earn)",
                    "action": "SELL bias | Watch funding-scan for delta-neutral plays",
                },
                "SIDEWAYS": {
                    "hint": "Symmetric tight spreads — best for market making",
                    "profit": f"PMM profit: est. {natr * 100 * 2:.2f}-{natr * 100 * 5:.2f}% per fill cycle",
                    "action": "NEUTRAL | Tighten spreads, increase order frequency",
                },
            }.get(current, {"hint": "Monitor conditions", "profit": "Unknown", "action": "Hold"})
            self.send_telegram(
                f"📊 <b>Regime Change — {symbol}</b>{_binance_link(symbol)}\n"
                f"{prev} → <b>{current}</b>\n"
                f"Volatility: {natr * 100:.2f}% NATR ({vol_label}) | BBW: {bbw:.4f}\n"
                f"<i>{regime_info['hint']}</i>\n"
                f"💰 {regime_info['profit']}\n"
                f"⚡ Action: {regime_info['action']}"
            )
        self.state[key] = current

    def _handle_correlation(self, data, topic):
        key = f"corr:{topic}"
        prev = self.state.get(key)
        current = data.get("signal")
        if prev and prev != current and self.config.alert_on_correlation_change:
            target = data.get("target", topic.split("/")[-1])
            binance_sym = data.get("target_binance", "SOLUSDT")
            avg_z = float(data.get("avg_z_score", 0))
            avg_corr = float(data.get("avg_correlation", 0))
            bias = float(data.get("spread_bias", 0))
            z_scores = data.get("z_scores", {})
            z_parts = [f"{k}: {v:+.2f}" for k, v in sorted(z_scores.items(), key=lambda x: abs(x[1]), reverse=True)[:3]]
            z_detail = " | ".join(z_parts) if z_parts else "N/A"
            bias_dir = "BUY wider" if bias > 0 else "SELL wider" if bias < 0 else "neutral"
            corr_action = {
                "DIVERGING": {
                    "hint": "Pairs diverging — mean reversion opportunity",
                    "profit": f"Est. reversion: {abs(avg_z) * 0.5:.1f}% if z-score normalizes",
                    "action": "Look for arb/spread trades between correlated pairs",
                },
                "CONVERGING": {
                    "hint": "Pairs re-aligning — trend confirmation",
                    "profit": "Trend likely to continue — momentum trades aligned",
                    "action": "Follow regime direction, increase position confidence",
                },
                "NEUTRAL": {
                    "hint": "Normal correlation — no cross-pair edge",
                    "profit": "Standard conditions",
                    "action": "Use other signals for direction",
                },
            }.get(current, {"hint": "", "profit": "", "action": "Monitor"})
            self.send_telegram(
                f"🔗 <b>Correlation — {target}</b>{_binance_link(binance_sym)}\n"
                f"{prev} → <b>{current}</b>\n"
                f"Avg Z: {avg_z:+.3f} | Avg Corr: {avg_corr:.3f}\n"
                f"Top Z-scores: {z_detail}\n"
                f"Skew bias: {bias:+.4f} ({bias_dir})\n"
                f"<i>{corr_action['hint']}</i>\n"
                f"💰 {corr_action['profit']}\n"
                f"⚡ Strategy: {corr_action['action']}"
            )
        self.state[key] = current

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
                f"Value: <b>{_fmt_usd(total_val)}</b> (Base: {_fmt_usd(base_val)} / Quote: {_fmt_usd(quote_val)})\n"
                f"Exposure: {base_pct:.0f}% Base | DD: {_fmt_pct(drawdown * 100)} from Peak"
            )

        if current_kill and not prev_kill and self.config.alert_on_kill_switch:
            self.send_telegram(
                f"🚨 <b>KILL SWITCH — {target}</b>\n"
                f"Drawdown: {_fmt_pct(drawdown * 100)} ({_fmt_usd(loss_usd)} loss)\n"
                f"Peak: {_fmt_usd(peak_val)} → Current: {_fmt_usd(total_val)}\n"
                f"<b>ALL ORDERS PAUSED</b>"
            )
        elif not current_kill and prev_kill and self.config.alert_on_kill_switch:
            self.send_telegram(
                f"✅ <b>Kill Switch Cleared — {target}</b>\n"
                f"DD recovered to {_fmt_pct(drawdown * 100)} | Value: {_fmt_usd(total_val)}\n"
                f"Orders resuming"
            )

        if drawdown >= self.config.drawdown_warning_threshold and self.config.alert_on_drawdown_warning:
            prev_dd = self.state.get(f"dd_warned:{topic}", False)
            if not prev_dd:
                self.send_telegram(
                    f"⚠️ <b>Drawdown Warning — {target}</b>\n"
                    f"DD: {_fmt_pct(drawdown * 100)} (threshold: {_fmt_pct(self.config.drawdown_warning_threshold * 100)})\n"
                    f"Loss: {_fmt_usd(loss_usd)} | Peak: {_fmt_usd(peak_val)} → {_fmt_usd(total_val)}"
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
        self.state[key] = current

    def _handle_funding(self, data, topic):
        key = f"funding:{topic}"
        prev = self.state.get(key)
        current = data.get("signal")
        if prev and prev != current and self.config.alert_on_funding_change:
            target = data.get("target", topic.split("/")[-1])
            symbol = data.get("symbol", target.upper().replace("_", ""))
            rate = float(data.get("funding_rate", 0))
            apr = float(data.get("annualized_rate", 0))
            bias = float(data.get("spread_bias", 0))
            next_ts = data.get("next_funding_time", 0)
            direction = "Shorts pay longs" if rate > 0 else "Longs pay shorts"
            per_8h_bps = rate * 10000
            earn_100_8h = abs(rate) * 100
            earn_100_day = earn_100_8h * 3
            earn_100_month = earn_100_day * 30
            if earn_100_month < MIN_PROFIT_100:
                self.state[key] = current
                return
            self.send_telegram(
                f"💰 <b>Funding — {target}</b>{_binance_link(symbol)}\n"
                f"{prev} → <b>{current}</b>\n"
                f"Rate: {rate:.6f} ({per_8h_bps:+.2f} bps/8h)\n"
                f"Annual: <b>{_fmt_pct(apr)}</b> | {direction}\n"
                f"Income ($100): {_fmt_usd(earn_100_8h)}/8h | {_fmt_usd(earn_100_day)}/day\n"
                f"Skew bias: {bias:+.4f} | Next: {_fmt_ts(next_ts)}"
            )
        self.state[key] = current

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
            regime_parts.append(f"  {r}: {_fmt_usd(rd.get('pnl', 0))} ({rd.get('count', 0)} trades)")
        regime_str = "\n".join(regime_parts[:3]) if regime_parts else ""

        if alerts:
            self.send_telegram(
                f"⚠️ <b>Performance Warning — {target}</b>\n"
                + "\n".join(f"  • {a}" for a in alerts)
                + f"\nPnL: <b>{_fmt_usd(total_pnl)}</b> | WR: {win_rate:.1%}\n"
                f"Sharpe: {sharpe:.2f} | PF: {pf:.2f} | Max DD: {_fmt_pct(drawdown * 100)}\n"
                + (f"\n<b>Top Regimes:</b>\n{regime_str}" if regime_str else "")
            )
        else:
            pnl_emoji = "🟢" if total_pnl > 0 else "🔴" if total_pnl < 0 else "⚪"
            self.send_telegram(
                f"{pnl_emoji} <b>PnL Report ({period}h) — {target}</b>\n"
                f"Total PnL: <b>{_fmt_usd(total_pnl)}</b> | WR: {win_rate:.1%}\n"
                f"Sharpe: {sharpe:.2f} | PF: {pf:.2f} | Avg: {_fmt_usd(avg_pnl)}/tr\n"
                f"Best: {best} | Worst: {worst}\n"
                + (f"\n<b>Top Regimes:</b>\n{regime_str}" if regime_str else "")
            )

    def _handle_backtest(self, data, topic):
        if not self.config.alert_on_backtest:
            return
        target = data.get("target", "?")
        tested = int(data.get("total_configs_tested", 0))
        successful = int(data.get("successful_runs", 0))
        success_rate = (successful / tested * 100) if tested > 0 else 0
        top = data.get("top_config")

        if top:
            params = top.get("params", {})
            sharpe = float(top.get("sharpe_ratio", 0))
            pnl = float(top.get("net_pnl", 0))
            pnl_emoji = "🟢" if pnl > 0 else "🔴"
            accuracy = float(top.get("accuracy", 0))
            time_limit = params.get("time_limit", "?")
            profit_factor = float(top.get("profit_factor", 1))
            self.send_telegram(
                f"🧪 <b>Backtest — {target}</b>\n"
                f"Tested: {tested} configs | Profitable: <b>{successful}</b> ({success_rate:.0f}%)\n"
                f"\n🏆 <b>Best Config:</b>\n"
                f"  Buy/Sell spreads: {params.get('buy_spreads','?')} / {params.get('sell_spreads','?')}\n"
                f"  SL: {params.get('stop_loss','?')} | TP: {params.get('take_profit','?')} | TTL: {time_limit}s\n"
                f"  {pnl_emoji} PnL: <b>{_fmt_usd(pnl)}</b> | Sharpe: {sharpe:.2f} | PF: {profit_factor:.2f}\n"
                f"  Accuracy: {accuracy:.1%}"
            )
        else:
            self.send_telegram(
                f"🧪 <b>Backtest — {target}</b>\n"
                f"⚠️ Tested {tested} configs — <b>no profitable setups found</b>\n"
                f"<i>Consider wider spread range or longer time limits</i>"
            )

    def _handle_hedge(self, data, topic):
        if not self.config.alert_on_hedge:
            return
        key = f"hedge:{topic}"
        prev = self.state.get(key)
        current = data.get("status")
        order_placed = data.get("order_placed", False)
        target = data.get("target", topic.split("/")[-1])
        delta = float(data.get("net_delta", 0))
        ratio = float(data.get("hedge_ratio", 0))
        spot = float(data.get("spot_balance", 0))
        short = float(data.get("perp_short_size", 0))
        upnl = float(data.get("unrealized_pnl", 0))
        coverage = (short / spot * 100) if spot > 0 else 0
        delta_pct = (delta / spot * 100) if spot > 0 else 0

        if prev and prev != current:
            self.send_telegram(
                f"🛡️ <b>Hedge — {target}</b>\n"
                f"Status: <b>{current}</b> | Ratio: {ratio:.2f}\n"
                f"Exposure: {delta_pct:+.1f}% Delta ({_fmt_usd(delta * data.get('price', 1))})\n"
                f"Spot: {spot:.2f} | Short: {short:.2f} ({coverage:.0f}% covered)\n"
                f"uPnL: <b>{_sign(upnl)}{_fmt_usd(abs(upnl))}</b>"
            )

        if order_placed:
            action = data.get("action", "?")
            self.send_telegram(
                f"📉 <b>Hedge Order — {target}</b>\n"
                f"Action: <b>{action}</b> | Ratio → {ratio:.2f}\n"
                f"Net Delta: {delta:+.4f} ({delta_pct:+.1f}%)"
            )

        self.state[key] = current

    def _handle_lab(self, data, topic):
        if not self.config.alert_on_lab:
            return
        active = data.get("active_experiments", [])
        by_status = data.get("by_status", {})
        by_tier = data.get("by_tier", {})
        killed = by_status.get("KILLED", 0)
        running = by_status.get("RUNNING", 0)
        pending = by_status.get("PENDING", 0)

        key_killed = f"lab_killed:{topic}"
        prev_killed = self.state.get(key_killed, 0)

        if killed > prev_killed:
            new_kills = killed - prev_killed
            killed_list = [e for e in active if e.get("status") == "KILLED"][-new_kills:]
            kill_lines = "\n".join(
                f"  ❌ {e.get('pair','?')} T{e.get('tier','?')}: {_fmt_usd(e.get('pnl',0))} over {e.get('days',0)}d"
                for e in killed_list
            ) if killed_list else ""
            self.send_telegram(
                f"💀 <b>Lab: {new_kills} Experiment(s) Killed</b>\n"
                f"Running: {running} | Pending: {pending} | Total killed: {killed}\n"
                + (f"\n{kill_lines}" if kill_lines else "")
            )

        promoted = by_status.get("PROMOTED", 0)
        key_promoted = f"lab_promoted:{topic}"
        prev_promoted = self.state.get(key_promoted, 0)

        if promoted > prev_promoted:
            new_promo = promoted - prev_promoted
            promo_list = [e for e in active if e.get("status") == "PROMOTED"][-new_promo:]
            promo_lines = "\n".join(
                f"  🏆 {e.get('pair','?')} T{e.get('tier','?')}: <b>{_fmt_usd(e.get('pnl',0))}</b> | Sharpe {e.get('sharpe',0):.2f}"
                for e in promo_list
            ) if promo_list else ""
            tier_summary = " | ".join(
                f"T{t}: {td.get('count',0)} runs, {_fmt_usd(td.get('total_pnl',0))} PnL"
                for t, td in sorted(by_tier.items())
            ) if by_tier else ""
            self.send_telegram(
                f"🏆 <b>Lab: {new_promo} Experiment(s) Promoted</b>\n"
                f"Running: {running} | Promoted: {promoted}\n"
                + (f"\n{promo_lines}" if promo_lines else "")
                + (f"\n<i>{tier_summary}</i>" if tier_summary else "")
            )

        self.state[key_killed] = killed
        self.state[key_promoted] = promoted

    def _handle_alpha(self, data, topic):
        if "/new_listing/" in topic:
            if not self.config.alert_on_new_listing:
                return
            token = data.get("token", "?")
            pair_addr = data.get("pair_address", "")
            key = f"new_listing:{pair_addr or data.get('pair', topic)}"
            if self.state.get(key):
                return
            pair = data.get("pair", "")
            dex = data.get("dex", "?")
            age_h = float(data.get("age_hours", 0))
            liq = float(data.get("liquidity", 0))
            vol = float(data.get("volume_24h", 0))
            price = data.get("price", 0)
            vol_liq = (vol / liq) if liq > 0 else 0
            if vol_liq > 3:
                nl_rating = "🟢 HOT"
                nl_est = "Est. 20-50% first-day moves common"
            elif vol_liq > 1:
                nl_rating = "🟡 WARM"
                nl_est = "Est. 10-20% first-day moves possible"
            else:
                nl_rating = "⚪ EARLY"
                nl_est = "Monitor — thin volume so far"
            self.send_telegram(
                f"🆕 <b>New Listing — {token}</b> [{nl_rating}]{_dex_link(pair_addr)}\n"
                f"Pair: {pair} on {dex} | Age: {_fmt_hours(age_h)}\n"
                f"Liq: {_fmt_usd(liq)} | Vol 24h: {_fmt_usd(vol)} ({vol_liq:.1f}x)\n"
                f"Price: ${price} | 💰 {nl_est}"
            )
            self.state[key] = True
        else:
            if not self.config.alert_on_alpha:
                return
            token = data.get("token", "?")
            addr = data.get("address", "")
            score = int(data.get("score", 0))
            key = f"alpha:{addr or data.get('pair', topic)}"
            if self.state.get(key):
                return
            pair = data.get("pair", "")
            dex = data.get("dex", "?")
            liq = float(data.get("liquidity", 0))
            vol = float(data.get("volume_24h", 0))
            mcap = float(data.get("mcap", 0))
            price = data.get("price", 0)
            vol_mcap = (vol / mcap) if mcap > 0 else 0
            breakdown = data.get("breakdown", {})
            est_profit_pct = float(data.get("est_profit_pct", 0))
            p5m = float(data.get("price_change_5m", 0))
            p1h = float(data.get("price_change_1h", 0))
            p24h = float(data.get("price_change_24h", 0))
            if p5m > 2 and p1h > 5:
                momentum = "🔥 STRONG UP"
            elif p5m > 0.5 and p1h > 2:
                momentum = "📈 Climbing"
            elif p5m < -2 or p1h < -5:
                momentum = "📉 Dumping"
            else:
                momentum = "➡️ Flat"
            if score >= 9 and est_profit_pct >= 5:
                rating = "🟢 HIGH CONVICTION"
            elif score >= 8 and est_profit_pct >= 2:
                rating = "🟡 MODERATE"
            else:
                rating = "⚪ SPECULATIVE"
            bd_parts = [f"{k}: {v}" for k, v in breakdown.items() if k != "est_profit_pct"][:3]
            self.send_telegram(
                f"🎯 <b>Alpha — {token}</b> [{rating}]{_token_link(addr)}\n"
                f"Score: <b>{score}/10</b> {_bar(score)} | {momentum}\n"
                f"MCap: {_fmt_usd(mcap)} | Liq: {_fmt_usd(liq)} | Vol/MCap: {vol_mcap:.2f}x\n"
                f"Change: 5m {_sign(p5m)}% | 1h {_sign(p1h)}% | 24h {_sign(p24h)}%\n"
                f"💰 <b>$100 → est. ${_fmt_usd(est_profit_pct)} profit</b> (trend extrapolation)"
                + (f"\n<i>Stats: {' | '.join(bd_parts)}</i>" if bd_parts else "")
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

        unlock_pct = float(data.get("unlock_pct", 0))
        unlock_amt = data.get("unlock_amount", "?")
        source = data.get("source", "")
        buy_mult = float(data.get("buy_spread_mult", 1))
        sell_mult = float(data.get("sell_spread_mult", 1))
        buy_adj = (buy_mult - 1) * 100
        sell_adj = (sell_mult - 1) * 100

        if status == "PRE_UNLOCK":
            hours = float(data.get("hours_until_unlock", 0))
            est_spread_profit = abs(buy_adj) * 0.01 * 100
            self.send_telegram(
                f"🔓 <b>Unlock Approaching — {token}</b>\n"
                f"Pair: {pair} | Unlock in <b>{_fmt_hours(hours)}</b>\n"
                f"Size: {unlock_pct}% ({unlock_amt})\n"
                f"Spread adjustment:\n"
                f"  Buy: x{buy_mult:.2f} ({buy_adj:+.0f}%) | Sell: x{sell_mult:.2f} ({sell_adj:+.0f}%)\n"
                f"<i>Expect sell pressure — widening spreads</i>\n"
                f"💰 Wider spreads est. +{est_spread_profit:.1f}% extra per fill"
                + (f"\nSource: {source}" if source else "")
            )
        elif status == "POST_UNLOCK":
            hours = float(data.get("hours_since_unlock", 0))
            self.send_telegram(
                f"🔓 <b>Post-Unlock — {token}</b>\n"
                f"Pair: {pair} | Unlocked <b>{_fmt_hours(hours)} ago</b>\n"
                f"Size: {unlock_pct}% ({unlock_amt})\n"
                f"Spread adjustment:\n"
                f"  Buy: x{buy_mult:.2f} ({buy_adj:+.0f}%) | Sell: x{sell_mult:.2f} ({sell_adj:+.0f}%)\n"
                f"<i>Mean reversion window — watching for bounce</i>\n"
                f"💰 Bounce trades: est. {unlock_pct * 0.3:.1f}% reversion if typical pattern"
            )

        self.state[key] = status

    def _handle_arb(self, data, topic):
        if not self.config.alert_on_arb:
            return
        token = data.get("token", "?")
        key = f"arb:{data.get('buy_dex', '')}:{data.get('sell_dex', '')}:{token}"
        if self.state.get(key):
            return
        buy_price = float(data.get("buy_price", 0))
        sell_price = float(data.get("sell_price", 0))
        spread = float(data.get("spread_pct", 0))
        max_size = float(data.get("max_size_usd", 0))
        buy_dex = data.get("buy_dex", "?")
        sell_dex = data.get("sell_dex", "?")
        buy_addr = data.get("buy_pair", "")
        sell_addr = data.get("sell_pair", "")
        spread_bps = spread * 100
        gross_profit_100 = 100 * spread / 100
        net_profit_100 = gross_profit_100 - (100 * EST_SLIPPAGE_PCT / 100) - SOLANA_GAS
        if net_profit_100 < MIN_ARB_NET_PROFIT:
            self.state[key] = True
            return
        trades_for_10 = max(1, int(10 / net_profit_100)) if net_profit_100 > 0 else 999
        if net_profit_100 >= 10:
            rating = "🟢 HIGH VALUE"
        elif net_profit_100 >= 5:
            rating = "🟡 GOOD"
        else:
            rating = "⚪ SMALL"
        est_profit_max = max_size * (spread - EST_SLIPPAGE_PCT) / 100 - SOLANA_GAS
        self.send_telegram(
            f"⚡ <b>Arb — {token}</b> [{rating}]{_dex_link(buy_addr)}\n"
            f"Spread: <b>{_fmt_pct(spread)}</b> ({spread_bps:.0f} bps)\n"
            f"Buy:  {buy_dex} @ ${buy_price:.6f}\n"
            f"Sell: {sell_dex} @ ${sell_price:.6f}\n"
            f"Net/$100: <b>{_fmt_usd(net_profit_100)}</b> | To $10: {trades_for_10} trades\n"
            f"Max: {_fmt_usd(max_size)} → {_fmt_usd(est_profit_max)} net profit"
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
        rate = float(data.get("funding_rate", 0))
        apr = float(data.get("annualized_apr", 0))
        signal = data.get("signal", "?")
        direction = data.get("direction", "?")
        next_ts = data.get("next_funding_time", 0)
        bps = rate * 10000
        daily_rate = rate * 3 * 100
        emoji = "🔥" if signal == "EXTREME" else "📈"
        dir_hint = "Shorts pay → long bias" if direction == "SHORT_PAYS" else "Longs pay → short bias"
        earn_100_8h = abs(rate) * 100
        earn_100_day = earn_100_8h * 3
        earn_100_month = earn_100_day * 30
        if earn_100_month < MIN_PROFIT_100:
            self.state[key] = True
            return
        self.send_telegram(
            f"{emoji} <b>Funding Spike — {symbol}</b> [{signal}]{_binance_link(symbol)}\n"
            f"Rate: {rate:.6f} ({bps:+.1f} bps) | APR: <b>{_fmt_pct(apr, 1)}</b>\n"
            f"Direction: {direction} ({dir_hint})\n"
            f"Income ($100): {_fmt_usd(earn_100_8h)}/8h | {_fmt_usd(earn_100_day)}/day\n"
            f"Next funding: {_fmt_ts(next_ts)}"
        )
        self.state[key] = True

    def _handle_narrative(self, data, topic):
        if not self.config.alert_on_narrative:
            return
        token = data.get("token", "?")
        addr = data.get("address", "")
        category = data.get("category", "?")
        key = f"narr:{category}:{token}"
        if self.state.get(key):
            return
        keyword = data.get("keyword", "")
        vol = float(data.get("volume_24h", 0))
        spike = float(data.get("volume_spike", 0))
        liq = float(data.get("liquidity", 0))
        price = data.get("price", 0)
        p5m = float(data.get("price_change_5m", 0))
        p1h = float(data.get("price_change_1h", 0))
        p24h = float(data.get("price_change_24h", 0))
        vol_liq = (vol / liq) if liq > 0 else 0
        momentum = "Accelerating" if abs(p5m) > abs(p1h / 12) else "Stable"
        trend = "Bullish" if p5m > 0 and p1h > 0 else "Bearish" if p5m < 0 and p1h < 0 else "Mixed"
        # Estimated profit context if trend continues
        est_profit_pct = max(p1h * 0.5, 0) if p1h > 0 else 0
        if spike >= 5 and p1h > 5 and trend == "Bullish":
            rating = "🟢 HIGH CONVICTION"
        elif spike >= 3 and p1h > 2:
            rating = "🟡 MODERATE"
        else:
            rating = "⚪ EARLY SIGNAL"
        self.send_telegram(
            f"📡 <b>Narrative — {token}</b> [{category}]{_token_link(addr)}\n"
            f"Spike: <b>{spike:.1f}x</b> [{rating}] | Keyword: {keyword}\n"
            f"Liq: {_fmt_usd(liq)} | Vol 24h: {_fmt_usd(vol)} ({vol_liq:.1f}x)\n"
            f"Change: 1h {_sign(p1h)}% | 5m {_sign(p5m)}% | Trend: {trend} ({momentum})\n"
            f"💰 <b>$100 → {_fmt_usd(est_profit_pct)}</b> (extrapolated 1h trend)"
        )
        self.state[key] = True

    def _handle_swarm(self, data, topic):
        if not self.config.alert_on_swarm:
            return
        if "/deploy/" in topic:
            token = data.get("token", "?")
            status = data.get("status", "?")
            pair = data.get("pair", "")
            dex = data.get("dex", "?")
            capital = float(data.get("capital", 0))
            entry = float(data.get("entry_price", 0))
            score = data.get("score", 0)
            is_live = status == "ACTIVE"
            tokens_bought = (capital / entry) if entry > 0 else 0
            win_prob = min(90, max(30, score * 8))
            est_gain = capital * 0.15
            est_loss = capital * 0.20
            ev = (win_prob / 100 * est_gain) - ((100 - win_prob) / 100 * est_loss)
            self.send_telegram(
                f"{'🤖' if is_live else '📋'} <b>Swarm {'Deploy' if is_live else 'Recommendation'} — {token}</b>\n"
                f"Pair: {pair} on {dex}\n"
                f"Score: <b>{score}/10</b> {_bar(score)}\n"
                f"Capital: {_fmt_usd(capital)} @ ${entry:.6f} ({tokens_bought:.2f} tokens)\n"
                f"Win prob: {win_prob}% | EV per trade: <b>{_fmt_usd(ev)}</b>\n"
                f"💰 Target +15% ({_fmt_usd(est_gain)}) | Stop -20% ({_fmt_usd(est_loss)})\n"
                f"Status: <b>{status}</b>"
            )
        elif "/status" in topic:
            active = int(data.get("active_bots", 0))
            total = int(data.get("total_bots", 0))
            total_pnl = float(data.get("total_pnl", 0))
            deployed = float(data.get("total_capital_deployed", 0))
            available = float(data.get("available_capital", 0))
            by_status = data.get("by_status", {})
            killed = by_status.get("KILLED", 0)
            active_list = data.get("active", [])

            key_killed = "swarm_killed"
            prev_killed = self.state.get(key_killed, 0)
            new_kills = killed - prev_killed

            if new_kills > 0 or (active > 0 and total_pnl != self.state.get("swarm_prev_pnl", total_pnl)):
                roi = (total_pnl / deployed * 100) if deployed > 0 else 0
                pnl_emoji = "🟢" if total_pnl > 0 else "🔴" if total_pnl < 0 else "⚪"
                top_bots = sorted(active_list, key=lambda b: b.get("pnl", 0), reverse=True)[:3]
                bot_lines = "\n".join(
                    f"  {_sign(b.get('pnl', 0))} {b.get('token', '?')} ({b.get('age_hours', 0):.0f}h)"
                    for b in top_bots
                ) if top_bots else ""
                self.send_telegram(
                    f"{pnl_emoji} <b>Swarm Fleet Status</b>\n"
                    f"Active: {active}/{total} bots | Total ROI: <b>{roi:+.2f}%</b>\n"
                    f"PnL: <b>{_fmt_usd(total_pnl)}</b> | Capital: {_fmt_usd(deployed)}\n"
                    + (f"New Kills: {new_kills}\n" if new_kills > 0 else "")
                    + (f"<b>Top Performers:</b>\n{bot_lines}" if bot_lines else "")
                )

            self.state[key_killed] = killed
            self.state["swarm_prev_pnl"] = total_pnl

    def _handle_clmm(self, data, topic):
        if not self.config.alert_on_clmm:
            return
        if not data.get("should_rebalance"):
            return
        target = topic.split("/")[-1]
        price = float(data.get("price", 0))
        lower = float(data.get("range_lower", 0))
        upper = float(data.get("range_upper", 0))
        range_pct = float(data.get("range_pct", 0))
        util = float(data.get("utilization_pct", 0))
        regime = data.get("regime", "?")
        session = data.get("session", "?")
        natr = float(data.get("natr", 0))
        range_width = upper - lower
        mid = (upper + lower) / 2 if (upper + lower) > 0 else 0
        off_center = ((price - mid) / (range_width / 2) * 100) if range_width > 0 else 0
        edge = "upper" if price > mid else "lower"
        dist_to_edge = min(abs(price - lower), abs(price - upper))
        est_daily_fees = float(data.get("volume_24h", 0)) * 0.003 / max(float(data.get("liquidity", 1)), 1)
        est_fee_100_day = est_daily_fees * 100
        self.send_telegram(
            f"🔄 <b>CLMM Rebalance — {target}</b>\n"
            f"Price: <b>${price:.4f}</b> ({off_center:+.0f}% off-center, near {edge} edge)\n"
            f"New range: ${lower:.4f} – ${upper:.4f} ({_fmt_pct(range_pct)} width)\n"
            f"Util: {_fmt_pct(util)} | NATR: {natr * 100:.2f}% | {regime}/{session}\n"
            f"Est. fees: <b>{_fmt_usd(est_fee_100_day)}/day</b> per $100 LP"
        )

    def _handle_migration(self, data, topic):
        if not self.config.alert_on_migration:
            return
        token = data.get("token", "?")
        if "/new_pool/" in topic:
            key = f"new_pool:{data.get('pair', topic)}"
            if self.state.get(key):
                return
            pair = data.get("pair", "?")
            dex = data.get("dex", "?")
            liq = float(data.get("liquidity", 0))
            vol = float(data.get("volume_24h", 0))
            price = data.get("price", 0)
            age_min = float(data.get("age_minutes", 0))
            vol_liq = (vol / liq) if liq > 0 else 0
            addr = data.get("address", "")
            addr_short = f"{addr[:6]}...{addr[-4:]}" if len(addr) > 10 else addr
            if vol_liq > 3:
                pool_heat = "🟢 HOT activity"
            elif vol_liq > 1:
                pool_heat = "🟡 Normal activity"
            else:
                pool_heat = "⚪ Low activity"
            pair_addr = data.get("pair_address", "")
            self.send_telegram(
                f"🏊 <b>New Pool — {token}</b> [{pool_heat}]{_dex_link(pair_addr or addr)}\n"
                f"{pair} on <b>{dex}</b> | Age: {age_min:.0f}min\n"
                f"Liq: {_fmt_usd(liq)} | Vol: {_fmt_usd(vol)} ({vol_liq:.1f}x)\n"
                f"Price: ${price} | <code>{addr_short}</code>\n"
                f"💰 Early entry — est. 20-50% moves if traction builds"
            )
            self.state[key] = True
        elif "/event/" in topic:
            status = data.get("status", "")
            key = f"event:{token}:{status}"
            if self.state.get(key) == status:
                return
            event_type = data.get("event_type", "?")
            hours = float(data.get("hours", 0))
            desc = data.get("description", "")
            source = data.get("source", "")
            pair = data.get("pair", "")
            is_upcoming = status == "ACTIVE"
            timing = f"⏳ In {_fmt_hours(hours)}" if is_upcoming else f"✅ {_fmt_hours(hours)} ago"
            self.send_telegram(
                f"📅 <b>{event_type} — {token}</b>\n"
                + (f"Pair: {pair}\n" if pair else "")
                + f"{timing}\n"
                + (f"<i>{desc}</i>\n" if desc else "")
                + (f"Source: {source}" if source else "")
            )
            self.state[key] = status

    def _handle_watchlist(self, data, topic):
        if not self.config.alert_on_watchlist:
            return
        sym = data.get("symbol", data.get("token", "?"))
        parts = topic.split("/")
        entry_type = parts[-2] if len(parts) >= 2 else "?"
        type_labels = {"arb": "Arb Tokens", "rewards": "LP Pools", "funding": "Funding Symbols"}
        type_label = type_labels.get(entry_type, entry_type)

        if "/added/" in topic:
            source = data.get("source", "?")
            addr = data.get("address", "")
            liq = _fmt_usd(float(data.get("liquidity", 0)))
            vol = _fmt_usd(float(data.get("volume_24h", 0)))
            source_labels = {
                "alpha": "Alpha signal", "narrative": "Narrative spike",
                "dex_boost": "DexScreener boost", "dex_profile": "DexScreener trending",
            }
            source_label = source_labels.get(source, source)
            next_step = {
                "arb": "Watch arb-service for spread alerts",
                "rewards": "Watch rewards-service for APR updates",
                "funding": "Watch funding-scanner for rate alerts",
            }.get(entry_type, "Monitor signals")
            meta = [f"Pair: {data['pair']}" if data.get("pair") else "", f"DEX: {data['dex']}" if data.get("dex") else "", f"Liq: {liq}", f"Vol: {vol}"]
            meta_str = " | ".join(m for m in meta if m)
            self.send_telegram(
                f"➕ <b>Watchlist: {sym} Added</b> ({type_label}){_token_link(addr)}\n"
                f"Via: {source_label} | {meta_str}\n"
                f"<i>⚡ {next_step}</i>"
            )
        elif "/removed/" in topic:
            stale_cycles = data.get("consecutive_stale_cycles", 0)
            self.send_telegram(
                f"➖ <b>Watchlist: {sym} Removed</b> ({type_label})\n"
                f"Stale for {stale_cycles} cycles — volume & liquidity dried up"
            )

    def _handle_rewards(self, data, topic):
        if not self.config.alert_on_rewards:
            return
        if "/summary" in topic:
            top = data.get("top_pools", [])
            top = [p for p in top if 100 * float(p.get("effective_apr", 0)) / 100 / 365 * 30 >= MIN_PROFIT_100]
            if not top:
                return
            key = f"rewards_top:{top[0].get('pair', '')}"
            if self.state.get(key):
                return
            lines = [f"🏆 <b>Top LP Rewards</b> ({len(top)} pools)"]
            for i, p in enumerate(top[:5], 1):
                eff = float(p.get("effective_apr", 0))
                risk = p.get("risk_score", "?")
                liq = float(p.get("liquidity", 0))
                addr = p.get("address", "")
                earn_100_day = 100 * eff / 100 / 365
                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
                lines.append(
                    f"{medal} <b>{p.get('pair', '?')}</b> ({p.get('dex', '?')}){_token_link(addr)}\n"
                    f"   {_fmt_pct(eff)} APR | Risk: {risk}/10 | {_fmt_usd(liq)} liq\n"
                    f"   Income ($100): <b>{_fmt_usd(earn_100_day)}/day</b>"
                )
            self.send_telegram("\n\n".join(lines))
            self.state[key] = True
        else:
            token = data.get("token", "?")
            key = f"rewards_pool:{token}"
            prev_apr = self.state.get(key, 0)
            eff_apr = float(data.get("effective_apr", 0))
            if abs(eff_apr - prev_apr) < 5:
                self.state[key] = eff_apr
                return
            fee_apr = float(data.get("fee_apr", 0))
            reward_apr = float(data.get("reward_apr", 0))
            risk_adj = float(data.get("risk_adjusted_apr", 0))
            risk = data.get("risk_score", "?")
            liq = float(data.get("liquidity", 0))
            vol = float(data.get("volume_24h", 0))
            pair = data.get("pair", "?")
            dex = data.get("dex", "?")
            reward_token = data.get("reward_token", "?")
            addr = data.get("address", "")
            apr_dir = "📈" if eff_apr > prev_apr else "📉"
            earn_100_day = 100 * eff_apr / 100 / 365
            earn_100_month = earn_100_day * 30
            if earn_100_month < MIN_PROFIT_100:
                self.state[key] = eff_apr
                return
            change_str = f"+{eff_apr - prev_apr:.1f}%" if (eff_apr - prev_apr) > 0 else f"{eff_apr - prev_apr:.1f}%"
            self.send_telegram(
                f"{apr_dir} <b>LP Reward — {pair}</b> ({dex}){_token_link(addr)}\n"
                f"APR: <b>{_fmt_pct(eff_apr)}</b> ({change_str}) | Risk: {risk}/10\n"
                f"Fees: {_fmt_pct(fee_apr)} + Rewards: {_fmt_pct(reward_apr)} ({reward_token})\n"
                f"Income ($100): <b>{_fmt_usd(earn_100_day)}/day</b> | {_fmt_usd(earn_100_month)}/mo\n"
                f"Liq: {_fmt_usd(liq)} | Vol: {_fmt_usd(vol)}"
            )
            self.state[key] = eff_apr

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
            elif "/watchlist/" in topic:
                self._handle_watchlist(data, topic)
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
        self.send_telegram(
            "🤖 <b>Edge Services Online</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "📡 Monitoring: Regime | Session | Funding\n"
            "⚡ Scanning:   Arb | Alpha | Narrative | Swarm\n"
            "🛡️ Managing:   Hedge | Inventory | PnL\n"
            "🎯 Optimizing: CLMM | Rewards | Lab | Migration\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"All signals routing to Telegram. Min arb: {_fmt_usd(MIN_ARB_NET_PROFIT)} 💰"
        )

        while self.running:
            time.sleep(1)

        self.shutdown_mqtt()


if __name__ == "__main__":
    AlertService().run()
