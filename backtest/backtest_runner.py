import argparse
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from backtest.engines import run_backtest, run_market_making_backtest, run_portfolio_backtest
from backtest.loaders import load_token_candles
from backtest.metrics import make_result_row
from backtest.models import BacktestConfig, PortfolioConfig
from backtest.reporting import (
    build_diagnostics,
    build_overall_performance,
    build_raw_trades_export,
    build_summary,
    clean_legacy_result_files,
    clean_old_results,
    make_run_folder,
    print_console_report,
    print_portfolio_report,
    write_dashboard,
    write_json,
    write_result_files,
)
from backtest.strategies import ALL_STRATEGY_NAMES, MM_STRATEGIES, REGISTRY, build_variant_name, get_param_sets


def _chunks(items, size):
    chunk_size = max(1, int(size))
    for idx in range(0, len(items), chunk_size):
        yield items[idx : idx + chunk_size]


def _build_config(args):
    return BacktestConfig(
        initial_capital=args.initial_capital,
        position_size=args.position_size,
        cash_reserve_ratio=args.cash_reserve_ratio,
        min_trade_usd=args.min_trade_usd,
        risk_per_trade=args.risk_per_trade,
        dex_fee_bps=args.dex_fee_bps,
        slippage_bps=args.slippage_bps,
        gas_cost=args.gas_cost,
        stop_loss=args.stop_loss,
        take_profit=args.take_profit,
        time_limit_bars=args.time_limit_bars,
        trailing_activation=args.trailing_activation,
        trailing_delta=args.trailing_delta,
        cooldown_bars=args.cooldown_bars,
        min_hold_bars=args.min_hold_bars,
    )


def _build_portfolio_config(args):
    return PortfolioConfig(
        initial_capital=args.initial_capital,
        position_size=args.position_size,
        cash_reserve_ratio=args.cash_reserve_ratio,
        min_trade_usd=args.min_trade_usd,
        risk_per_trade=args.risk_per_trade,
        dex_fee_bps=args.dex_fee_bps,
        slippage_bps=args.slippage_bps,
        gas_cost=args.gas_cost,
        stop_loss=args.stop_loss,
        take_profit=args.take_profit,
        time_limit_bars=args.time_limit_bars,
        trailing_activation=args.trailing_activation,
        trailing_delta=args.trailing_delta,
        cooldown_bars=args.cooldown_bars,
        min_hold_bars=args.min_hold_bars,
        max_open_trades=args.max_open_trades,
        max_entries_per_bar=args.max_entries_per_bar,
        max_rotations_per_bar=args.max_rotations_per_bar,
        rotation_score_threshold=args.rotation_score_threshold,
        past_trade_weight=args.past_trade_weight,
        performance_decay=args.performance_decay,
        workers=args.workers,
        batch_size=args.batch_size,
    )


def _load_all_tokens(data_dir, selected_tokens, workers, batch_size):
    token_files = []
    for name in sorted(os.listdir(data_dir)):
        if not (name.lower().endswith(".csv") or name.lower().endswith(".parquet")):
            continue
        token = os.path.splitext(name)[0].upper()
        if selected_tokens and token not in selected_tokens:
            continue
        token_files.append((token, os.path.join(data_dir, name)))

    token_candles = {}
    worker_count = max(1, int(workers))
    for batch in _chunks(token_files, batch_size):
        with ThreadPoolExecutor(max_workers=min(worker_count, len(batch))) as executor:
            futures = [executor.submit(load_token_candles, path) for _, path in batch]
            for (token, _), fut in zip(batch, futures):
                candles = fut.result()
                if len(candles) >= 2:
                    token_candles[token] = candles
    return token_candles


def _num(value):
    return float(value) if isinstance(value, (int, float)) else 0.0


def _aggregate_mm_rows(per_token_rows, strategy_name, variant, initial_capital):
    n = len(per_token_rows)
    return {
        "strategy": strategy_name,
        "token": "PORTFOLIO",
        "strategy_variant": variant,
        "bars": int(sum(_num(r.get("bars", 0)) for r in per_token_rows) / n),
        "token_count": n,
        "trades": int(sum(_num(r.get("trades", 0)) for r in per_token_rows)),
        "win_rate": sum(_num(r.get("win_rate", 0.0)) for r in per_token_rows) / n,
        "profit_factor": sum(_num(r.get("profit_factor", 0.0)) for r in per_token_rows) / n,
        "total_return": sum(_num(r.get("total_return", 0.0)) for r in per_token_rows) / n,
        "cagr": sum(_num(r.get("cagr", 0.0)) for r in per_token_rows) / n,
        "max_drawdown": sum(_num(r.get("max_drawdown", 0.0)) for r in per_token_rows) / n,
        "sharpe": sum(_num(r.get("sharpe", 0.0)) for r in per_token_rows) / n,
        "ending_equity": sum(_num(r.get("ending_equity", 0.0)) for r in per_token_rows) / n,
        "avg_trade_return": sum(_num(r.get("avg_trade_return", 0.0)) for r in per_token_rows) / n,
        "avg_trade_pnl": sum(_num(r.get("avg_trade_pnl", 0.0)) for r in per_token_rows) / n,
        "fees_paid": sum(_num(r.get("fees_paid", 0.0)) for r in per_token_rows),
        "gas_paid": sum(_num(r.get("gas_paid", 0.0)) for r in per_token_rows),
        "exit_reasons": {"mm_cycle": sum(r.get("exit_reasons", {}).get("mm_cycle", 0) for r in per_token_rows)},
        "min_cash_balance": min(_num(r.get("min_cash_balance", initial_capital)) for r in per_token_rows),
        "ending_cash": sum(_num(r.get("ending_cash", 0.0)) for r in per_token_rows) / n,
        "skipped_entries_insufficient_cash": int(sum(_num(r.get("skipped_entries_insufficient_cash", 0)) for r in per_token_rows)),
        "token_trade_pnl": {r["token"]: _num(r.get("ending_equity", 0.0)) - initial_capital for r in per_token_rows},
        "token_trade_count": {r["token"]: int(_num(r.get("trades", 0))) for r in per_token_rows},
        "raw_trades": [t for r in per_token_rows for t in r.get("raw_trades", [])],
    }


def _run_portfolio_mode(token_candles, selected_strategies, cfg, pcfg, args):
    results = []
    ts_min = min(token_candles[t][0].timestamp for t in token_candles)
    ts_max = max(token_candles[t][-1].timestamp for t in token_candles)

    for strategy_name in selected_strategies:
        for params in get_param_sets(strategy_name):
            variant = build_variant_name(strategy_name, params)

            if strategy_name in MM_STRATEGIES:
                per_token_rows = []
                for token, candles in token_candles.items():
                    stats = run_market_making_backtest(candles, strategy_name, params, cfg)
                    if stats is None:
                        continue
                    row = make_result_row(
                        {"token": token, "strategy": strategy_name, "strategy_variant": variant},
                        stats, candles[0].timestamp, candles[-1].timestamp, cfg.initial_capital,
                    )
                    per_token_rows.append(row)
                if not per_token_rows:
                    continue
                agg = _aggregate_mm_rows(per_token_rows, strategy_name, variant, cfg.initial_capital)
                agg = make_result_row(
                    {"strategy": strategy_name, "strategy_variant": variant},
                    agg, ts_min, ts_max, cfg.initial_capital,
                )
                results.append(agg)
            else:
                stats = run_portfolio_backtest(token_candles, strategy_name, params, pcfg)
                if stats is None:
                    continue
                row = make_result_row(
                    {"strategy": strategy_name, "strategy_variant": variant},
                    stats, ts_min, ts_max, cfg.initial_capital,
                )
                results.append(row)
    return results


def _run_token_mode(token_candles, selected_strategies, cfg, workers, batch_size):
    tasks = []
    for token, candles in token_candles.items():
        for strategy_name in selected_strategies:
            for params in get_param_sets(strategy_name):
                tasks.append((token, candles, strategy_name, params))

    def _evaluate(task):
        token, candles, strategy_name, params = task
        if strategy_name in MM_STRATEGIES:
            stats = run_market_making_backtest(candles, strategy_name, params, cfg)
        else:
            stats = run_backtest(candles, strategy_name, params, cfg)
        if stats is None:
            return None
        variant = build_variant_name(strategy_name, params)
        return make_result_row(
            {"token": token, "strategy": strategy_name, "strategy_variant": variant},
            stats, candles[0].timestamp, candles[-1].timestamp, cfg.initial_capital,
        )

    results = []
    worker_count = max(1, int(workers))
    for batch in _chunks(tasks, batch_size):
        with ThreadPoolExecutor(max_workers=min(worker_count, len(batch))) as executor:
            futures = [executor.submit(_evaluate, t) for t in batch]
            for fut in as_completed(futures):
                row = fut.result()
                if row is not None:
                    results.append(row)
    return results


def _build_payload(args, selected_tokens, selected_strategies, results, strategy_summary, token_winners):
    return {
        "config": {
            "mode": args.mode,
            "data_dir": args.data_dir,
            "strategies": selected_strategies,
            "tokens": sorted(selected_tokens) if selected_tokens else "ALL",
            "initial_capital": args.initial_capital,
            "position_size": args.position_size,
            "cash_reserve_ratio": args.cash_reserve_ratio,
            "min_trade_usd": args.min_trade_usd,
            "risk_per_trade": args.risk_per_trade,
            "dex_fee_bps": args.dex_fee_bps,
            "slippage_bps": args.slippage_bps,
            "gas_cost": args.gas_cost,
            "stop_loss": args.stop_loss,
            "take_profit": args.take_profit,
            "time_limit_bars": args.time_limit_bars,
            "trailing_activation": args.trailing_activation,
            "trailing_delta": args.trailing_delta,
            "cooldown_bars": args.cooldown_bars,
            "min_hold_bars": args.min_hold_bars,
            "max_open_trades": args.max_open_trades,
            "max_entries_per_bar": args.max_entries_per_bar,
            "max_rotations_per_bar": args.max_rotations_per_bar,
            "rotation_score_threshold": args.rotation_score_threshold,
            "past_trade_weight": args.past_trade_weight,
            "performance_decay": args.performance_decay,
            "workers": args.workers,
            "batch_size": args.batch_size,
        },
        "results": results,
        "strategy_summary": strategy_summary,
        "token_winners": token_winners,
    }


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["token", "portfolio"], default="portfolio")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--strategies", default="supertrend_v1,macd_adx_v1,rsi_trend_v1,donchian_breakout_v1,trend_pullback_v1,mean_reversion_v1,pmm_dynamic")
    parser.add_argument("--tokens", default="")
    parser.add_argument("--initial-capital", type=float, default=100.0)
    parser.add_argument("--position-size", type=float, default=0.5)
    parser.add_argument("--cash-reserve-ratio", type=float, default=0.15)
    parser.add_argument("--min-trade-usd", type=float, default=2.0)
    parser.add_argument("--risk-per-trade", type=float, default=0.02)
    parser.add_argument("--dex-fee-bps", type=float, default=25.0)
    parser.add_argument("--slippage-bps", type=float, default=15.0)
    parser.add_argument("--gas-cost", type=float, default=0.05)
    parser.add_argument("--stop-loss", type=float, default=0.04)
    parser.add_argument("--take-profit", type=float, default=0.06)
    parser.add_argument("--time-limit-bars", type=int, default=576)
    parser.add_argument("--trailing-activation", type=float, default=0.03)
    parser.add_argument("--trailing-delta", type=float, default=0.02)
    parser.add_argument("--cooldown-bars", type=int, default=24)
    parser.add_argument("--min-hold-bars", type=int, default=48)
    parser.add_argument("--max-open-trades", type=int, default=5)
    parser.add_argument("--max-entries-per-bar", type=int, default=3)
    parser.add_argument("--max-rotations-per-bar", type=int, default=0)
    parser.add_argument("--rotation-score-threshold", type=float, default=0.05)
    parser.add_argument("--past-trade-weight", type=float, default=0.35)
    parser.add_argument("--performance-decay", type=float, default=0.2)
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) // 2))
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--results-dir", default="backtest/results")
    parser.add_argument("--clean-old-results", action="store_true", default=True)
    parser.add_argument("--output", default="")
    return parser.parse_args()


def main():
    args = parse_args()
    if not os.path.isdir(args.data_dir):
        raise ValueError(f"data-dir not found: {args.data_dir}")

    selected_tokens = {t.strip().upper() for t in args.tokens.split(",") if t.strip()}
    selected_strategies = [s.strip() for s in args.strategies.split(",") if s.strip()]

    for strategy in selected_strategies:
        if strategy not in REGISTRY and strategy not in MM_STRATEGIES:
            raise ValueError(f"Unknown strategy: {strategy}. Available: {', '.join(ALL_STRATEGY_NAMES)}")

    token_candles = _load_all_tokens(args.data_dir, selected_tokens, args.workers, args.batch_size)
    cfg = _build_config(args)

    if args.mode == "portfolio":
        if len(token_candles) < 2:
            raise ValueError("Portfolio mode requires at least 2 token datasets.")
        pcfg = _build_portfolio_config(args)
        results = _run_portfolio_mode(token_candles, selected_strategies, cfg, pcfg, args)
    else:
        results = _run_token_mode(token_candles, selected_strategies, cfg, args.workers, args.batch_size)

    if not results:
        raise ValueError("No backtest results generated. Check CSV files and selected tokens/strategies.")

    strategy_summary = []
    token_winners = {}
    if args.mode == "portfolio":
        print_portfolio_report(results)
        strategy_summary = sorted(results, key=lambda r: (r["total_return"], r["sharpe"], -r["max_drawdown"]), reverse=True)
    else:
        strategy_summary, token_winners = build_summary(results)
        print_console_report(strategy_summary, token_winners)

    payload = _build_payload(args, selected_tokens, selected_strategies, results, strategy_summary, token_winners)

    if args.clean_old_results:
        clean_old_results(args.results_dir)
        clean_legacy_result_files("backtest")

    run_folder = make_run_folder(args.results_dir)
    overall = build_overall_performance(args.mode, results)
    raw_trades = build_raw_trades_export(results)
    diagnostics = build_diagnostics(payload["config"], strategy_summary, raw_trades)

    write_result_files(run_folder, payload["config"], overall, strategy_summary, token_winners, raw_trades, diagnostics, payload)
    write_dashboard(run_folder, payload, overall, raw_trades, diagnostics)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(output_path, payload)

    print(f"\nSaved run artifacts to: {run_folder}")


if __name__ == "__main__":
    main()
