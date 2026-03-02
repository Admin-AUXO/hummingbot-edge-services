import math
from bisect import bisect_right
from collections import defaultdict


def calc_win_rate(executors):
    if not executors:
        return 0.0
    wins = sum(1 for e in executors if e.get("net_pnl_quote", 0) > 0)
    return wins / len(executors)


def calc_sharpe(pnl_list, periods_per_year=365 * 24 * 12):
    if len(pnl_list) < 2:
        return 0.0
    mean = sum(pnl_list) / len(pnl_list)
    variance = sum((p - mean) ** 2 for p in pnl_list) / (len(pnl_list) - 1)
    std = math.sqrt(variance)
    if std == 0:
        return 0.0
    return (mean / std) * math.sqrt(periods_per_year)


def calc_profit_factor(executors):
    gains = sum(e["net_pnl_quote"] for e in executors if e.get("net_pnl_quote", 0) > 0)
    losses = abs(sum(e["net_pnl_quote"] for e in executors if e.get("net_pnl_quote", 0) < 0))
    if losses == 0:
        return float("inf") if gains > 0 else 0.0
    return gains / losses


def calc_max_drawdown(cumulative_pnl):
    if not cumulative_pnl:
        return 0.0
    peak = cumulative_pnl[0]
    max_dd = 0.0
    for val in cumulative_pnl:
        if val > peak:
            peak = val
        dd = peak - val
        if dd > max_dd:
            max_dd = dd
    return max_dd


def _find_signal_state(timestamp, signal_log):
    if not signal_log:
        return None
    timestamps = [s["timestamp"] for s in signal_log]
    idx = bisect_right(timestamps, timestamp) - 1
    if idx < 0:
        return None
    return signal_log[idx]


def _combo_key(state):
    if state is None:
        return "UNKNOWN"
    parts = []
    for field in ("regime", "correlation", "inventory", "session", "funding"):
        val = state.get(field)
        if val is not None:
            parts.append(str(val))
    return "+".join(parts) if parts else "UNKNOWN"


def _compute_group_metrics(executors):
    pnl_list = [e.get("net_pnl_quote", 0) for e in executors]
    return {
        "count": len(executors),
        "pnl": round(sum(pnl_list), 4),
        "win_rate": round(calc_win_rate(executors), 4),
    }


def group_by_signal(executors, signal_log):
    by_regime = defaultdict(list)
    by_session = defaultdict(list)
    by_combo = defaultdict(list)

    for ex in executors:
        ts = ex.get("timestamp", 0)
        state = _find_signal_state(ts, signal_log)
        combo = _combo_key(state)
        by_combo[combo].append(ex)

        if state:
            regime = state.get("regime", "UNKNOWN")
            session = state.get("session", "UNKNOWN")
        else:
            regime = "UNKNOWN"
            session = "UNKNOWN"

        by_regime[regime].append(ex)
        by_session[session].append(ex)

    regime_metrics = {k: _compute_group_metrics(v) for k, v in by_regime.items()}
    session_metrics = {k: _compute_group_metrics(v) for k, v in by_session.items()}
    combo_metrics = {k: _compute_group_metrics(v) for k, v in by_combo.items()}

    best_combo = max(combo_metrics, key=lambda k: combo_metrics[k]["pnl"]) if combo_metrics else "NONE"
    worst_combo = min(combo_metrics, key=lambda k: combo_metrics[k]["pnl"]) if combo_metrics else "NONE"

    return {
        "by_regime": regime_metrics,
        "by_session": session_metrics,
        "best_combo": best_combo,
        "worst_combo": worst_combo,
    }
