import math
from statistics import median


def calc_max_drawdown(equity_curve):
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for value in equity_curve:
        if value > peak:
            peak = value
        dd = 0.0 if peak <= 0 else (peak - value) / peak
        if dd > max_dd:
            max_dd = dd
    return max_dd


def calc_sharpe(period_returns, periods_per_year):
    if len(period_returns) < 2:
        return 0.0
    avg = sum(period_returns) / len(period_returns)
    variance = sum((x - avg) ** 2 for x in period_returns) / (len(period_returns) - 1)
    std = math.sqrt(variance)
    if std == 0:
        return 0.0
    return (avg / std) * math.sqrt(periods_per_year)


def estimate_periods_per_year(timestamps):
    if len(timestamps) < 3:
        return 365
    gaps = [timestamps[i] - timestamps[i - 1] for i in range(1, len(timestamps)) if timestamps[i] > timestamps[i - 1]]
    if not gaps:
        return 365
    typical_gap = median(gaps)
    if typical_gap <= 0:
        return 365
    return max(1, int((365 * 24 * 3600) / typical_gap))


def safe_float_for_json(value):
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def compute_result_stats(initial_capital, cash, equity_curve, period_returns, trade_pnls, trade_returns, timestamps):
    wins = sum(1 for tr in trade_pnls if tr > 0)
    losses = [tr for tr in trade_pnls if tr < 0]
    gains = [tr for tr in trade_pnls if tr > 0]
    loss_abs = abs(sum(losses))
    periods_per_year = estimate_periods_per_year(timestamps)
    total_return = (cash / initial_capital) - 1
    years = max((timestamps[-1] - timestamps[0]) / (365 * 24 * 3600), 1 / 365)
    cagr = (cash / initial_capital) ** (1 / years) - 1
    trade_count = len(trade_pnls)

    return {
        "trades": trade_count,
        "win_rate": 0.0 if trade_count == 0 else wins / trade_count,
        "profit_factor": float("inf") if loss_abs == 0 and gains else 0.0 if not gains else sum(gains) / loss_abs,
        "total_return": total_return,
        "cagr": cagr,
        "max_drawdown": calc_max_drawdown(equity_curve),
        "sharpe": calc_sharpe(period_returns, periods_per_year),
        "ending_equity": cash,
        "avg_trade_return": 0.0 if not trade_returns else sum(trade_returns) / len(trade_returns),
        "avg_trade_pnl": 0.0 if not trade_pnls else sum(trade_pnls) / len(trade_pnls),
    }


def enrich_trade_metrics(row, start_ts, end_ts, initial_capital):
    trades = row.get("raw_trades", [])
    duration_seconds = max(1.0, float(end_ts - start_ts))
    backtest_days = duration_seconds / 86400.0
    durations = [max(0.0, float(t.get("exit_timestamp", 0)) - float(t.get("entry_timestamp", 0))) for t in trades]
    row["backtest_days"] = backtest_days
    row["avg_trades_per_day"] = 0.0 if backtest_days <= 0 else len(trades) / backtest_days
    row["avg_trade_duration_minutes"] = 0.0 if not durations else (sum(durations) / len(durations)) / 60.0
    row["min_trade_duration_minutes"] = 0.0 if not durations else min(durations) / 60.0
    row["max_trade_duration_minutes"] = 0.0 if not durations else max(durations) / 60.0
    win_rate = float(row.get("win_rate", 0.0))
    avg_trade_pnl = float(row.get("avg_trade_pnl", 0.0))
    row["expectancy_per_trade"] = win_rate * avg_trade_pnl
    row["pnl_per_day"] = 0.0 if backtest_days <= 0 else (float(row.get("ending_equity", 0.0)) - float(initial_capital)) / backtest_days
    return row


def sanitize_row(row):
    for key, value in list(row.items()):
        row[key] = safe_float_for_json(value)
    return row


def make_result_row(base_fields, stats, start_ts, end_ts, initial_capital):
    row = {**base_fields, **stats}
    row = enrich_trade_metrics(row, start_ts, end_ts, initial_capital)
    return sanitize_row(row)
