import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import median


def write_result_files(run_folder, config, overall, strategy_summary, token_winners, raw_trades, diagnostics, full_payload):
    folder = Path(run_folder)
    write_json(folder / "config.json", config)
    write_json(folder / "overall_performance.json", overall)
    write_json(folder / "strategy_summary.json", [{k: v for k, v in r.items() if k != "raw_trades"} for r in strategy_summary])
    write_json(folder / "token_winners.json", token_winners)
    write_json(folder / "raw_trades.json", raw_trades)
    write_json(folder / "diagnostics.json", diagnostics)
    stripped = [{k: v for k, v in r.items() if k != "raw_trades"} for r in full_payload.get("results", [])]
    write_json(folder / "strategy_results.json", stripped)


def clean_old_results(results_dir):
    base = Path(results_dir)
    if not base.exists():
        return
    for item in base.iterdir():
        if item.is_dir():
            for child in sorted(item.rglob("*"), reverse=True):
                if child.is_file():
                    child.unlink(missing_ok=True)
                else:
                    child.rmdir()
            item.rmdir()
        elif item.is_file():
            item.unlink(missing_ok=True)


def clean_legacy_result_files(backtest_dir):
    base = Path(backtest_dir)
    for name in ["results.json", "results_real.json", "results_5m_parquet.json",
                  "results_5m_realistic_100.json", "results_portfolio_optimized.json"]:
        path = base / name
        if path.exists():
            path.unlink(missing_ok=True)


def make_run_folder(results_dir):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = Path(results_dir) / f"run_{stamp}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def write_json(path, payload):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def build_overall_performance(mode, results):
    ranked = sorted(results, key=lambda r: (r["total_return"], r["sharpe"], -r["max_drawdown"]), reverse=True)
    best = ranked[0] if ranked else None
    return {
        "mode": mode,
        "strategies_tested": len(results),
        "total_trades": sum(int(r.get("trades", 0)) for r in results),
        "best_strategy_variant": None if best is None else best.get("strategy_variant"),
        "best_total_return": None if best is None else best.get("total_return"),
        "best_sharpe": None if best is None else best.get("sharpe"),
        "best_max_drawdown": None if best is None else best.get("max_drawdown"),
    }


def build_raw_trades_export(results):
    flat = []
    for row in results:
        token = row.get("token", "PORTFOLIO")
        variant = row.get("strategy_variant", "UNKNOWN")
        for trade in row.get("raw_trades", []):
            flat.append({"token": token, "strategy_variant": variant, **trade})
    return flat


def build_diagnostics(config, strategy_rows, raw_trades):
    initial_capital = float(config.get("initial_capital", 0.0) or 0.0)
    strategy_diagnostics = []
    failure_counts = {
        "overtrading_cost_drag": 0,
        "low_hit_rate": 0,
        "rotation_dominant_losses": 0,
        "capital_halt": 0,
    }

    for row in strategy_rows:
        trades = int(row.get("trades", 0) or 0)
        win_rate = float(row.get("win_rate", 0.0) or 0.0)
        total_return = float(row.get("total_return", 0.0) or 0.0)
        ending_equity = float(row.get("ending_equity", initial_capital) or initial_capital)
        fees_paid = float(row.get("fees_paid", 0.0) or 0.0)
        gas_paid = float(row.get("gas_paid", 0.0) or 0.0)
        avg_trades_per_day = float(row.get("avg_trades_per_day", 0.0) or 0.0)
        exit_reasons = row.get("exit_reasons", {}) or {}
        net_pnl = ending_equity - initial_capital
        total_cost = fees_paid + gas_paid
        cost_to_abs_pnl = None if abs(net_pnl) < 1e-9 else total_cost / abs(net_pnl)
        rotation_share = float(exit_reasons.get("rotation_exit", 0)) / max(1, trades)
        halted = bool(row.get("halted_due_to_capital", False))

        flags = []
        if avg_trades_per_day > 40 and total_return < 0 and total_cost > abs(net_pnl):
            flags.append("overtrading_cost_drag")
            failure_counts["overtrading_cost_drag"] += 1
        if trades >= 20 and win_rate < 0.35:
            flags.append("low_hit_rate")
            failure_counts["low_hit_rate"] += 1
        if rotation_share > 0.4 and total_return < 0:
            flags.append("rotation_dominant_losses")
            failure_counts["rotation_dominant_losses"] += 1
        if halted:
            flags.append("capital_halt")
            failure_counts["capital_halt"] += 1

        strategy_diagnostics.append({
            "strategy_variant": row.get("strategy_variant", ""),
            "strategy": row.get("strategy", ""),
            "trades": trades,
            "win_rate": win_rate,
            "total_return": total_return,
            "net_pnl": net_pnl,
            "fees_paid": fees_paid,
            "gas_paid": gas_paid,
            "total_cost": total_cost,
            "cost_to_abs_pnl": cost_to_abs_pnl,
            "avg_trades_per_day": avg_trades_per_day,
            "rotation_exit_share": rotation_share,
            "halted_due_to_capital": halted,
            "flags": flags,
        })

    reason_agg = {}
    token_agg = {}
    for trade in raw_trades:
        reason = str(trade.get("reason", "unknown") or "unknown")
        token = str(trade.get("token", "UNKNOWN") or "UNKNOWN")
        pnl = float(trade.get("pnl", 0.0) or 0.0)
        won = 1 if pnl > 0 else 0

        reason_agg.setdefault(reason, {"count": 0, "wins": 0, "pnl": 0.0})
        reason_agg[reason]["count"] += 1
        reason_agg[reason]["wins"] += won
        reason_agg[reason]["pnl"] += pnl

        token_agg.setdefault(token, {"count": 0, "pnl": 0.0})
        token_agg[token]["count"] += 1
        token_agg[token]["pnl"] += pnl

    reason_breakdown = []
    for reason, item in reason_agg.items():
        count = int(item["count"])
        pnl_sum = float(item["pnl"])
        reason_breakdown.append({
            "reason": reason,
            "count": count,
            "win_rate": 0.0 if count == 0 else float(item["wins"]) / count,
            "pnl_sum": pnl_sum,
            "avg_pnl": 0.0 if count == 0 else pnl_sum / count,
        })
    reason_breakdown.sort(key=lambda r: r["count"], reverse=True)

    token_breakdown = []
    for token, item in token_agg.items():
        count = int(item["count"])
        pnl_sum = float(item["pnl"])
        token_breakdown.append({
            "token": token,
            "count": count,
            "pnl_sum": pnl_sum,
            "avg_pnl": 0.0 if count == 0 else pnl_sum / count,
        })
    token_breakdown.sort(key=lambda r: r["pnl_sum"])

    findings = []
    if failure_counts["overtrading_cost_drag"] > 0:
        findings.append("Overtrading cost drag detected in one or more strategy variants.")
    if failure_counts["low_hit_rate"] > 0:
        findings.append("Low hit rate is a dominant issue for several directional variants.")
    if failure_counts["rotation_dominant_losses"] > 0:
        findings.append("Rotation exits dominate losses for some variants; selection threshold likely too loose.")
    if failure_counts["capital_halt"] > 0:
        findings.append("At least one variant halted due to capital exhaustion.")
    if not findings:
        findings.append("No major failure flags triggered under current diagnostics thresholds.")

    strategy_diagnostics.sort(key=lambda r: r["total_return"])
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy_diagnostics": strategy_diagnostics,
        "reason_breakdown": reason_breakdown,
        "token_breakdown": token_breakdown,
        "failure_counts": failure_counts,
        "aggregate_findings": findings,
    }


def write_dashboard(run_folder, payload, overall, raw_trades, diagnostics):
    ranked = payload.get("strategy_summary") or payload.get("results", [])
    initial_capital = float(payload.get("config", {}).get("initial_capital", 100.0))
    strategy_rows = []
    for row in ranked:
        ending_eq = float(row.get("ending_equity", initial_capital) or initial_capital)
        net_pnl = ending_eq - initial_capital
        fees = round(float(row.get("fees_paid", 0.0)), 6)
        gas = round(float(row.get("gas_paid", 0.0)), 6)
        strategy_rows.append({
            "strategy_variant": row.get("strategy_variant", ""),
            "strategy": row.get("strategy", ""),
            "total_return_pct": round(float(row.get("total_return", 0.0)) * 100.0, 4),
            "sharpe": round(float(row.get("sharpe", 0.0)), 4),
            "max_drawdown_pct": round(float(row.get("max_drawdown", 0.0)) * 100.0, 4),
            "profit_factor": round(float(row.get("profit_factor", 0.0) or 0.0), 4),
            "win_rate_pct": round(float(row.get("win_rate", 0.0)) * 100.0, 2),
            "fees_paid": fees,
            "gas_paid": gas,
            "total_cost": round(fees + gas, 6),
            "net_pnl": round(net_pnl, 6),
            "avg_trades_per_day": round(float(row.get("avg_trades_per_day", 0.0)), 4),
            "trades": int(row.get("trades", 0)),
            "token_count": int(row.get("token_count", 0)) if row.get("token_count") is not None else 0,
            "expectancy": round(float(row.get("expectancy_per_trade", 0.0) or 0.0), 6),
            "pnl_per_day": round(float(row.get("pnl_per_day", 0.0) or 0.0), 6),
            "avg_trade_duration_min": round(float(row.get("avg_trade_duration_minutes", 0.0) or 0.0), 2),
            "ending_equity": round(ending_eq, 6),
            "exit_reasons": row.get("exit_reasons", {}),
        })

    token_pnl = ranked[0].get("token_trade_pnl", {}) or {} if ranked else {}
    token_labels = list(token_pnl.keys())
    token_values = [round(float(token_pnl[k]), 6) for k in token_labels]

    normalized = []
    for t in raw_trades:
        normalized.append({
            "token": t.get("token", ""),
            "strategy_variant": t.get("strategy_variant", ""),
            "entry_timestamp": t.get("entry_timestamp", ""),
            "exit_timestamp": t.get("exit_timestamp", ""),
            "pnl": round(float(t.get("pnl", 0.0)), 6),
            "return_pct": round(float(t.get("return", 0.0)) * 100.0, 4),
            "reason": t.get("reason", ""),
        })

    config = payload.get("config", {})

    template_path = Path(__file__).with_name("dashboard_template.html")
    if not template_path.exists():
        return
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    replacements = {
        "__OVERALL_JSON__": json.dumps(overall),
        "__CONFIG_JSON__": json.dumps(config),
        "__STRATEGY_ROWS_JSON__": json.dumps(strategy_rows),
        "__TOKEN_LABELS_JSON__": json.dumps(token_labels),
        "__TOKEN_VALUES_JSON__": json.dumps(token_values),
        "__RAW_TRADES_JSON__": json.dumps(normalized),
        "__DIAGNOSTICS_JSON__": json.dumps(diagnostics),
    }
    html = template
    for key, value in replacements.items():
        html = html.replace(key, value)

    with open(Path(run_folder) / "dashboard.html", "w", encoding="utf-8") as f:
        f.write(html)


def _format_pct(value):
    return f"{value * 100:.2f}%"


def _safe_avg(rows, key):
    vals = [float(r.get(key, 0.0) or 0.0) for r in rows]
    return sum(vals) / len(vals) if vals else 0.0


def build_summary(results):
    by_strategy = {}
    by_token = {}
    for row in results:
        by_strategy.setdefault(row["strategy_variant"], []).append(row)
        by_token.setdefault(row["token"], []).append(row)

    strategy_summary = []
    for key, rows in by_strategy.items():
        strategy_summary.append({
            "strategy_variant": key,
            "strategy": rows[0].get("strategy", ""),
            "tokens": len(rows),
            "avg_total_return": _safe_avg(rows, "total_return"),
            "median_total_return": median(r["total_return"] for r in rows),
            "avg_sharpe": _safe_avg(rows, "sharpe"),
            "avg_max_drawdown": _safe_avg(rows, "max_drawdown"),
            "avg_win_rate": _safe_avg(rows, "win_rate"),
            "avg_profit_factor": _safe_avg(rows, "profit_factor"),
            "avg_cagr": _safe_avg(rows, "cagr"),
            "total_trades": sum(int(r.get("trades", 0)) for r in rows),
            "avg_trades_per_day": _safe_avg(rows, "avg_trades_per_day"),
            "avg_expectancy_per_trade": _safe_avg(rows, "expectancy_per_trade"),
            "avg_pnl_per_day": _safe_avg(rows, "pnl_per_day"),
            "avg_fees_paid": sum(float(r.get("fees_paid", 0.0) or 0.0) for r in rows) / len(rows),
            "avg_gas_paid": sum(float(r.get("gas_paid", 0.0) or 0.0) for r in rows) / len(rows),
            "avg_ending_equity": _safe_avg(rows, "ending_equity"),
        })
    strategy_summary.sort(key=lambda r: (r["avg_total_return"], r["avg_sharpe"], -r["avg_max_drawdown"]), reverse=True)

    token_winners = {}
    for key, rows in by_token.items():
        winner = sorted(rows, key=lambda r: (r["total_return"], r["sharpe"], -r["max_drawdown"]), reverse=True)[0]
        token_winners[key] = {
            "strategy_variant": winner["strategy_variant"],
            "total_return": winner["total_return"],
            "sharpe": winner["sharpe"],
            "max_drawdown": winner["max_drawdown"],
            "trades": winner["trades"],
        }

    return strategy_summary, token_winners


def print_console_report(strategy_summary, token_winners):
    print("\n=== Strategy Ranking Across Tokens ===")
    for idx, row in enumerate(strategy_summary, start=1):
        costs = row['avg_fees_paid'] + row['avg_gas_paid']
        print(
            f"{idx:>2}. {row['strategy_variant']:<38} "
            f"avg_ret={_format_pct(row['avg_total_return']):>10} "
            f"avg_sharpe={row['avg_sharpe']:.3f} "
            f"avg_dd={_format_pct(row['avg_max_drawdown']):>9} "
            f"win={_format_pct(row['avg_win_rate']):>7} "
            f"avg_costs={costs:.2f} "
            f"tokens={row['tokens']:>3} trades={row['total_trades']:>4}"
        )

    print("\n=== Best Strategy Per Token ===")
    for token, winner in sorted(token_winners.items()):
        print(
            f"{token:<15} {winner['strategy_variant']:<38} "
            f"ret={_format_pct(winner['total_return']):>10} "
            f"sharpe={winner['sharpe']:.3f} dd={_format_pct(winner['max_drawdown']):>9} trades={winner['trades']:>3}"
        )


def print_portfolio_report(results):
    ranked = sorted(results, key=lambda r: (r["total_return"], r["sharpe"], -r["max_drawdown"]), reverse=True)
    print("\n=== Portfolio Strategy Ranking ===")
    for idx, row in enumerate(ranked, start=1):
        print(
            f"{idx:>2}. {row['strategy_variant']:<38} "
            f"ret={_format_pct(row['total_return']):>10} "
            f"sharpe={row['sharpe']:.3f} "
            f"dd={_format_pct(row['max_drawdown']):>9} "
            f"trades={row['trades']:>4}"
        )

    if ranked:
        best = ranked[0]
        token_pnl = best.get("token_trade_pnl", {})
        top_tokens = sorted(token_pnl.items(), key=lambda x: x[1], reverse=True)[:8]
        print("\n=== Best Strategy Token PnL Contribution ===")
        for token, pnl in top_tokens:
            print(f"{token:<15} pnl={pnl:>10.4f}")
