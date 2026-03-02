from itertools import product


def generate_param_grid(config):
    combos = product(
        config.spread_values,
        config.stop_loss_values,
        config.take_profit_values,
        config.time_limit_values,
    )
    grid = []
    for spread, sl, tp, tl in combos:
        grid.append({
            "buy_spreads": f"{spread},{spread * 2}",
            "sell_spreads": f"{spread},{spread * 2}",
            "stop_loss": sl,
            "take_profit": tp,
            "time_limit": tl,
        })
    return grid


def build_backtest_config(base_config, overrides):
    config = base_config.copy()
    config.update(overrides)
    return config


def rank_results(results, min_executors=10):
    filtered = [r for r in results if r["metrics"].get("total_executors", 0) >= min_executors]
    return sorted(filtered, key=lambda r: r["metrics"].get("sharpe_ratio", 0), reverse=True)


def format_report(ranked, top_n):
    top = ranked[:top_n]
    return {
        "top_configs": [
            {
                "rank": i + 1,
                "params": entry["params"],
                "sharpe_ratio": entry["metrics"].get("sharpe_ratio", 0),
                "net_pnl": entry["metrics"].get("net_pnl", 0),
                "accuracy": entry["metrics"].get("accuracy", 0),
                "max_drawdown_pct": entry["metrics"].get("max_drawdown_pct", 0),
                "profit_factor": entry["metrics"].get("profit_factor", 0),
                "total_executors": entry["metrics"].get("total_executors", 0),
            }
            for i, entry in enumerate(top)
        ]
    }
