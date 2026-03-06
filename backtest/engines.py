from concurrent.futures import ThreadPoolExecutor, as_completed

from backtest.indicators import rolling_mean_std
from backtest.metrics import compute_result_stats
from backtest.strategies import REGISTRY, compute_signals


def _chunks(items, size):
    chunk_size = max(1, int(size))
    for idx in range(0, len(items), chunk_size):
        yield items[idx : idx + chunk_size]


def run_market_making_backtest(candles, strategy_name, strategy_params, cfg):
    if len(candles) < 2:
        return None

    closes = [c.close for c in candles]
    means, stds = rolling_mean_std(closes, int(strategy_params.get("vol_window", 30)))
    cash = cfg.initial_capital
    equity_curve = [cash]
    period_returns = []
    trade_pnls = []
    trade_returns = []
    raw_trades = []
    total_fees_paid = 0.0
    total_gas_paid = 0.0
    skipped_cycles = 0
    halted_due_to_capital = False
    halt_index = None
    halt_timestamp = None

    for idx in range(1, len(candles)):
        prev_equity = cash
        candle = candles[idx]
        mean, std = means[idx], stds[idx]
        if mean is None or std is None or mean <= 0:
            equity_curve.append(cash)
            period_returns.append(0.0)
            continue

        tradeable = cfg.tradeable_cash(cash)
        allocation = tradeable * max(0.0, min(1.0, cfg.position_size))
        if cfg.risk_per_trade > 0:
            allocation = min(allocation, cash * max(0.0, cfg.risk_per_trade) * 10.0)

        if tradeable < cfg.min_required_cash() or allocation < cfg.min_trade_usd:
            halted_due_to_capital = True
            halt_index = idx
            halt_timestamp = candle.timestamp
            skipped_cycles += 1
            equity_curve.append(cash)
            period_returns.append(0.0)
            break

        vol_ratio = std / mean
        if strategy_name == "pmm_dynamic":
            base_spread = float(strategy_params.get("base_spread", 0.004))
            vol_mult = float(strategy_params.get("vol_mult", 2.0))
            min_spread = float(strategy_params.get("min_spread", 0.002))
            max_spread = float(strategy_params.get("max_spread", 0.02))
            spread = max(min_spread, min(max_spread, base_spread + (vol_mult * vol_ratio)))
            buy_level = candle.open * (1 - spread / 2)
            sell_level = candle.open * (1 + spread / 2)
            cycle_count = 1 if candle.low <= buy_level and candle.high >= sell_level else 0
        else:
            grid_step = float(strategy_params.get("grid_step", 0.008))
            max_cycles = int(strategy_params.get("max_cycles_per_bar", 2))
            min_profitable_spread = (cfg.fee_rate * 2.0) + (cfg.gas_cost * 2.0 / max(allocation, 1.0))
            grid_step = max(grid_step, min_profitable_spread * 1.5)
            range_pct = 0.0 if candle.open <= 0 else (candle.high - candle.low) / candle.open
            cycle_count = min(max_cycles, int(range_pct / max(grid_step, 1e-6)))
            spread = grid_step

        if cycle_count <= 0:
            skipped_cycles += 1
            equity_curve.append(cash)
            period_returns.append(0.0)
            continue

        gross_pnl = allocation * spread * cycle_count
        fees = (allocation * cfg.fee_rate * 2.0) * cycle_count
        gas = (cfg.gas_cost * 2.0) * cycle_count
        net_pnl = gross_pnl - fees - gas
        entry_cash = cash
        cash += net_pnl
        total_fees_paid += fees
        total_gas_paid += gas
        trade_pnls.append(net_pnl)
        trade_returns.append(0.0 if entry_cash == 0 else net_pnl / entry_cash)
        raw_trades.append({
            "entry_timestamp": candle.timestamp,
            "exit_timestamp": candle.timestamp,
            "entry_index": idx,
            "exit_index": idx,
            "entry_price": candle.open,
            "exit_price": candle.close,
            "pnl": net_pnl,
            "return": 0.0 if entry_cash == 0 else net_pnl / entry_cash,
            "reason": "mm_cycle",
            "cycles": cycle_count,
            "spread": spread,
        })
        equity_curve.append(cash)
        period_returns.append(0.0 if prev_equity <= 0 else (cash - prev_equity) / prev_equity)

    timestamps = [c.timestamp for c in candles]
    stats = compute_result_stats(cfg.initial_capital, cash, equity_curve, period_returns, trade_pnls, trade_returns, timestamps)
    stats.update({
        "strategy": strategy_name,
        "bars": len(candles),
        "fees_paid": total_fees_paid,
        "gas_paid": total_gas_paid,
        "exit_reasons": {"mm_cycle": len(raw_trades)},
        "min_cash_balance": min(equity_curve) if equity_curve else cash,
        "ending_cash": cash,
        "skipped_entries_insufficient_cash": skipped_cycles,
        "halted_due_to_capital": halted_due_to_capital,
        "halt_index": halt_index,
        "halt_timestamp": halt_timestamp,
        "raw_trades": raw_trades,
    })
    return stats


def run_backtest(candles, strategy_name, strategy_params, cfg):
    if len(candles) < 2:
        return None

    timestamps = [c.timestamp for c in candles]
    signals, _ = compute_signals(candles, strategy_name, strategy_params)
    if len(signals) != len(candles):
        raise ValueError(f"Strategy {strategy_name} returned invalid signal length")

    cash = cfg.initial_capital
    units = 0.0
    in_position = False
    position_dir = 0
    entry_equity = 0.0
    entry_price = 0.0
    entry_index = -1
    margin = 0.0
    trailing_stop_price = None
    peak_price = 0.0
    trough_price = float('inf')
    next_entry_index = 1
    force_edge = False

    equity_curve = [cfg.initial_capital]
    period_returns = []
    trade_returns = []
    trade_pnls = []
    raw_trades = []
    exit_reason_counts = {
        "stop_loss": 0, "take_profit": 0, "trailing_stop": 0,
        "time_limit": 0, "signal_exit": 0, "forced_close": 0,
    }
    total_fees_paid = 0.0
    total_gas_paid = 0.0
    skipped_entries = 0
    min_cash_balance = cash
    halted_due_to_capital = False
    halt_index = None
    halt_timestamp = None

    def current_equity(mark_price):
        if not in_position:
            return cash
        if position_dir == 1:
            return cash + units * mark_price
        return cash + margin + units * (entry_price - mark_price)

    def _close_position(exit_level, reason, candle_idx):
        nonlocal cash, units, in_position, position_dir, margin
        nonlocal trailing_stop_price, peak_price, trough_price
        nonlocal total_fees_paid, total_gas_paid, next_entry_index, force_edge

        if position_dir == 1:
            price_out = cfg.exit_price(exit_level)
            notional = units * price_out
            fee = notional * cfg.fee_rate
            cash += notional - fee - cfg.gas_cost
        else:
            price_out = cfg.entry_price(exit_level)
            notional = units * price_out
            fee = notional * cfg.fee_rate
            pnl_units = units * (entry_price - price_out)
            cash += margin + pnl_units - fee - cfg.gas_cost

        total_fees_paid += fee
        total_gas_paid += cfg.gas_cost
        direction_label = "long" if position_dir == 1 else "short"
        units = 0.0
        in_position = False
        exit_reason_counts[reason] += 1
        trade_pnl = cash - entry_equity
        trade_pnls.append(trade_pnl)
        trade_return = 0.0 if entry_equity == 0 else trade_pnl / entry_equity
        trade_returns.append(trade_return)
        raw_trades.append({
            "entry_timestamp": candles[entry_index].timestamp,
            "exit_timestamp": candles[candle_idx].timestamp,
            "entry_index": entry_index,
            "exit_index": candle_idx,
            "entry_price": entry_price,
            "exit_price": price_out,
            "direction": direction_label,
            "pnl": trade_pnl,
            "return": trade_return,
            "reason": reason,
        })
        position_dir = 0
        margin = 0.0
        trailing_stop_price = None
        peak_price = 0.0
        trough_price = float('inf')
        next_entry_index = candle_idx + max(0, cfg.cooldown_bars)
        force_edge = True

    for idx in range(1, len(candles)):
        prev_equity = current_equity(candles[idx - 1].close)
        candle = candles[idx]
        min_cash_balance = min(min_cash_balance, cash)

        if not in_position:
            tradeable = cfg.tradeable_cash(cash)
            if tradeable < cfg.min_required_cash():
                halted_due_to_capital = True
                halt_index = idx
                halt_timestamp = candle.timestamp
                equity_curve.append(cash)
                period_returns.append(0.0 if prev_equity <= 0 else (cash - prev_equity) / prev_equity)
                break

        if in_position:
            exit_reason = None
            exit_level = None

            if position_dir == 1:
                peak_price = max(peak_price, candle.high)
                if peak_price >= entry_price * (1 + cfg.trailing_activation):
                    candidate = peak_price * (1 - cfg.trailing_delta)
                    trailing_stop_price = candidate if trailing_stop_price is None else max(trailing_stop_price, candidate)

                stop_level = entry_price * (1 - cfg.stop_loss)
                take_level = entry_price * (1 + cfg.take_profit)

                if candle.low <= stop_level:
                    exit_reason, exit_level = "stop_loss", stop_level
                elif trailing_stop_price is not None and candle.low <= trailing_stop_price:
                    exit_reason, exit_level = "trailing_stop", trailing_stop_price
                elif candle.high >= take_level:
                    exit_reason, exit_level = "take_profit", take_level
                elif (idx - entry_index) >= cfg.time_limit_bars:
                    exit_reason, exit_level = "time_limit", candle.close
            else:
                trough_price = min(trough_price, candle.low)
                if trough_price <= entry_price * (1 - cfg.trailing_activation):
                    candidate = trough_price * (1 + cfg.trailing_delta)
                    trailing_stop_price = candidate if trailing_stop_price is None else min(trailing_stop_price, candidate)

                stop_level = entry_price * (1 + cfg.stop_loss)
                take_level = entry_price * (1 - cfg.take_profit)

                if candle.high >= stop_level:
                    exit_reason, exit_level = "stop_loss", stop_level
                elif trailing_stop_price is not None and candle.high >= trailing_stop_price:
                    exit_reason, exit_level = "trailing_stop", trailing_stop_price
                elif candle.low <= take_level:
                    exit_reason, exit_level = "take_profit", take_level
                elif (idx - entry_index) >= cfg.time_limit_bars:
                    exit_reason, exit_level = "time_limit", candle.close

            if exit_reason is not None:
                _close_position(exit_level, exit_reason, idx)

        if not in_position and idx >= next_entry_index:
            sig = signals[idx]
            prev_sig = signals[idx - 1] if idx >= 1 else 0
            enter_long = sig == 1 and (prev_sig != 1 or force_edge)
            enter_short = sig == -1 and (prev_sig != -1 or force_edge)

            if enter_long or enter_short:
                force_edge = False
                tradeable = cfg.tradeable_cash(cash)
                allocation = tradeable * max(0.0, min(1.0, cfg.position_size))
                if cfg.risk_per_trade > 0 and cfg.stop_loss > 0:
                    risk_cap = (cash * cfg.risk_per_trade) / cfg.stop_loss
                    allocation = min(allocation, risk_cap)

                if allocation > 0:
                    fee = allocation * cfg.fee_rate
                    total_cost = allocation + fee + cfg.gas_cost
                    if allocation >= cfg.min_trade_usd and total_cost < cash:
                        if enter_long:
                            exec_price = cfg.entry_price(candle.close)
                            units = allocation / exec_price
                            position_dir = 1
                            margin = 0.0
                            peak_price = candle.high
                            trough_price = float('inf')
                        else:
                            exec_price = cfg.exit_price(candle.close)
                            units = allocation / exec_price
                            position_dir = -1
                            margin = allocation
                            peak_price = 0.0
                            trough_price = candle.low

                        cash -= total_cost
                        in_position = True
                        entry_price = exec_price
                        entry_equity = current_equity(candle.close)
                        entry_index = idx
                        trailing_stop_price = None
                        total_fees_paid += fee
                        total_gas_paid += cfg.gas_cost
                    else:
                        skipped_entries += 1

        end_equity = current_equity(candle.close)
        equity_curve.append(end_equity)
        period_returns.append(0.0 if prev_equity <= 0 else (end_equity - prev_equity) / prev_equity)

    if in_position:
        _close_position(candles[-1].close, "forced_close", len(candles) - 1)
        equity_curve[-1] = cash

    stats = compute_result_stats(cfg.initial_capital, cash, equity_curve, period_returns, trade_pnls, trade_returns, timestamps)
    stats.update({
        "strategy": strategy_name,
        "bars": len(candles),
        "fees_paid": total_fees_paid,
        "gas_paid": total_gas_paid,
        "exit_reasons": exit_reason_counts,
        "min_cash_balance": min_cash_balance,
        "ending_cash": cash,
        "skipped_entries_insufficient_cash": skipped_entries,
        "halted_due_to_capital": halted_due_to_capital,
        "halt_index": halt_index,
        "halt_timestamp": halt_timestamp,
        "raw_trades": raw_trades,
    })
    return stats


def run_portfolio_backtest(token_candles, strategy_name, strategy_params, cfg):
    if not token_candles:
        return None

    tokens = sorted(token_candles.keys())
    min_len = min(len(token_candles[t]) for t in tokens)
    if min_len < 2:
        return None

    signals_by_token = {}
    scores_by_token = {}

    def _compute(token):
        candles_local = token_candles[token][:min_len]
        sig, score = compute_signals(candles_local, strategy_name, strategy_params)
        return token, sig[:min_len], score[:min_len]

    worker_count = max(1, int(cfg.workers))
    for token_batch in _chunks(tokens, cfg.batch_size):
        with ThreadPoolExecutor(max_workers=min(worker_count, len(token_batch))) as executor:
            futures = [executor.submit(_compute, t) for t in token_batch]
            for fut in as_completed(futures):
                token, sig, score = fut.result()
                signals_by_token[token] = sig
                scores_by_token[token] = score

    cash = cfg.initial_capital
    positions = {}
    token_next_entry = {t: 1 for t in tokens}
    token_force_edge = {t: False for t in tokens}
    token_trade_pnl = {t: 0.0 for t in tokens}
    token_trade_count = {t: 0 for t in tokens}
    token_perf_score = {t: 0.0 for t in tokens}

    equity_curve = [cfg.initial_capital]
    period_returns = []
    trade_returns = []
    trade_pnls = []
    raw_trades = []
    exit_reason_counts = {
        "stop_loss": 0, "take_profit": 0, "trailing_stop": 0,
        "time_limit": 0, "signal_exit": 0, "rotation_exit": 0, "forced_close": 0,
    }
    total_fees_paid = 0.0
    total_gas_paid = 0.0
    trades = 0
    skipped_entries = 0
    min_cash_balance = cash
    halted_due_to_capital = False
    halt_index = None
    halt_timestamp = None

    def current_equity(index):
        total = cash
        for t, pos in positions.items():
            mark = token_candles[t][index].close
            if pos["direction"] == 1:
                total += pos["units"] * mark
            else:
                total += pos["margin"] + pos["units"] * (pos["entry_price"] - mark)
        return total

    def close_position(token, index, exit_price_level, reason):
        nonlocal cash, total_fees_paid, total_gas_paid, trades
        pos = positions[token]

        if pos["direction"] == 1:
            price_out = cfg.exit_price(exit_price_level)
            notional = pos["units"] * price_out
            fee = notional * cfg.fee_rate
            cash += notional - fee - cfg.gas_cost
        else:
            price_out = cfg.entry_price(exit_price_level)
            notional = pos["units"] * price_out
            fee = notional * cfg.fee_rate
            pnl_units = pos["units"] * (pos["entry_price"] - price_out)
            cash += pos["margin"] + pnl_units - fee - cfg.gas_cost

        total_fees_paid += fee
        total_gas_paid += cfg.gas_cost
        trade_pnl = cash - pos["entry_equity"]
        trade_pnls.append(trade_pnl)
        trade_return = 0.0 if pos["entry_equity"] == 0 else trade_pnl / pos["entry_equity"]
        trade_returns.append(trade_return)
        raw_trades.append({
            "token": token,
            "entry_timestamp": token_candles[token][pos["entry_index"]].timestamp,
            "exit_timestamp": token_candles[token][index].timestamp,
            "entry_index": pos["entry_index"],
            "exit_index": index,
            "entry_price": pos["entry_price"],
            "exit_price": price_out,
            "direction": "long" if pos["direction"] == 1 else "short",
            "pnl": trade_pnl,
            "return": trade_return,
            "reason": reason,
        })
        token_trade_pnl[token] += trade_pnl
        token_trade_count[token] += 1
        alpha = max(0.01, min(1.0, cfg.performance_decay))
        token_perf_score[token] = (1.0 - alpha) * token_perf_score[token] + alpha * trade_return
        trades += 1
        exit_reason_counts[reason] += 1
        token_next_entry[token] = index + max(0, cfg.cooldown_bars)
        token_force_edge[token] = True
        del positions[token]

    for idx in range(1, min_len):
        prev_equity = current_equity(idx - 1)
        min_cash_balance = min(min_cash_balance, cash)

        if not positions:
            tradeable = cfg.tradeable_cash(cash)
            if tradeable < cfg.min_required_cash():
                halted_due_to_capital = True
                halt_index = idx
                halt_timestamp = token_candles[tokens[0]][idx].timestamp
                equity_curve.append(cash)
                period_returns.append(0.0 if prev_equity <= 0 else (cash - prev_equity) / prev_equity)
                break

        to_close = []
        for token, pos in positions.items():
            candle = token_candles[token][idx]
            score_now = scores_by_token[token][idx]
            if score_now > pos["peak_score"]:
                pos["peak_score"] = score_now

            if pos["direction"] == 1:
                pos["peak_price"] = max(pos["peak_price"], candle.high)
                if pos["peak_price"] >= pos["entry_price"] * (1 + cfg.trailing_activation):
                    candidate = pos["peak_price"] * (1 - cfg.trailing_delta)
                    if pos["trailing_stop_price"] is None:
                        pos["trailing_stop_price"] = candidate
                    else:
                        pos["trailing_stop_price"] = max(pos["trailing_stop_price"], candidate)

                stop_level = pos["entry_price"] * (1 - cfg.stop_loss)
                take_level = pos["entry_price"] * (1 + cfg.take_profit)

                if candle.low <= stop_level:
                    to_close.append((token, stop_level, "stop_loss"))
                elif pos["trailing_stop_price"] is not None and candle.low <= pos["trailing_stop_price"]:
                    to_close.append((token, pos["trailing_stop_price"], "trailing_stop"))
                elif candle.high >= take_level:
                    to_close.append((token, take_level, "take_profit"))
                elif (idx - pos["entry_index"]) >= cfg.time_limit_bars:
                    to_close.append((token, candle.close, "time_limit"))
            else:
                pos["trough_price"] = min(pos["trough_price"], candle.low)
                if pos["trough_price"] <= pos["entry_price"] * (1 - cfg.trailing_activation):
                    candidate = pos["trough_price"] * (1 + cfg.trailing_delta)
                    if pos["trailing_stop_price"] is None:
                        pos["trailing_stop_price"] = candidate
                    else:
                        pos["trailing_stop_price"] = min(pos["trailing_stop_price"], candidate)

                stop_level = pos["entry_price"] * (1 + cfg.stop_loss)
                take_level = pos["entry_price"] * (1 - cfg.take_profit)

                if candle.high >= stop_level:
                    to_close.append((token, stop_level, "stop_loss"))
                elif pos["trailing_stop_price"] is not None and candle.high >= pos["trailing_stop_price"]:
                    to_close.append((token, pos["trailing_stop_price"], "trailing_stop"))
                elif candle.low <= take_level:
                    to_close.append((token, take_level, "take_profit"))
                elif (idx - pos["entry_index"]) >= cfg.time_limit_bars:
                    to_close.append((token, candle.close, "time_limit"))

        for token, exit_level, reason in to_close:
            if token in positions:
                close_position(token, idx, exit_level, reason)

        candidates = []
        for token in tokens:
            if token in positions or idx < token_next_entry[token]:
                continue
            sig = signals_by_token[token][idx]
            prev_sig = signals_by_token[token][idx - 1] if idx >= 1 else 0
            forced = token_force_edge[token]
            enter_long = sig == 1 and (prev_sig != 1 or forced)
            enter_short = sig == -1 and (prev_sig != -1 or forced)
            if enter_long or enter_short:
                token_force_edge[token] = False
                base_score = scores_by_token[token][idx]
                weighted = base_score + (max(0.0, cfg.past_trade_weight) * token_perf_score[token])
                candidates.append((token, weighted, sig))
        candidates.sort(key=lambda x: x[1], reverse=True)

        rotations_done = 0
        while (
            len(positions) >= cfg.max_open_trades
            and candidates
            and cfg.max_rotations_per_bar > 0
            and rotations_done < cfg.max_rotations_per_bar
        ):
            weakest_token, _ = min(positions.items(), key=lambda x: scores_by_token[x[0]][idx])
            weakest_score = scores_by_token[weakest_token][idx] + (max(0.0, cfg.past_trade_weight) * token_perf_score[weakest_token])
            best_token, best_score, _ = candidates[0]
            if best_score <= weakest_score + cfg.rotation_score_threshold:
                break
            close_position(weakest_token, idx, token_candles[weakest_token][idx].close, "rotation_exit")
            candidates = [(t, s, d) for (t, s, d) in candidates if t != best_token]
            rotations_done += 1

        entries_done = 0
        for token, _score, direction in candidates:
            if entries_done >= cfg.max_entries_per_bar or len(positions) >= cfg.max_open_trades:
                break

            tradeable = cfg.tradeable_cash(cash)
            open_slots = max(1, cfg.max_open_trades - len(positions))
            allocation = (tradeable / open_slots) * max(0.0, min(1.0, cfg.position_size))
            if cfg.risk_per_trade > 0 and cfg.stop_loss > 0:
                allocation = min(allocation, (cash * cfg.risk_per_trade) / cfg.stop_loss)

            candle = token_candles[token][idx]
            fee = allocation * cfg.fee_rate
            total_cost = allocation + fee + cfg.gas_cost

            if allocation < cfg.min_trade_usd or total_cost >= cash:
                skipped_entries += 1
                continue

            if direction == 1:
                exec_price = cfg.entry_price(candle.close)
                pos_units = allocation / exec_price
                pos_margin = 0.0
                pos_peak = candle.high
                pos_trough = float('inf')
            else:
                exec_price = cfg.exit_price(candle.close)
                pos_units = allocation / exec_price
                pos_margin = allocation
                pos_peak = 0.0
                pos_trough = candle.low

            cash -= total_cost
            total_fees_paid += fee
            total_gas_paid += cfg.gas_cost

            positions[token] = {
                "units": pos_units,
                "entry_price": exec_price,
                "entry_index": idx,
                "entry_equity": current_equity(idx),
                "direction": direction,
                "margin": pos_margin,
                "peak_price": pos_peak,
                "trough_price": pos_trough,
                "trailing_stop_price": None,
                "peak_score": scores_by_token[token][idx],
            }
            entries_done += 1

        end_equity = current_equity(idx)
        equity_curve.append(end_equity)
        period_returns.append(0.0 if prev_equity <= 0 else (end_equity - prev_equity) / prev_equity)

    final_index = min_len - 1
    for token in list(positions.keys()):
        close_position(token, final_index, token_candles[token][final_index].close, "forced_close")

    if equity_curve:
        equity_curve[-1] = cash

    timestamps = [token_candles[tokens[0]][i].timestamp for i in range(min_len)]
    stats = compute_result_stats(cfg.initial_capital, cash, equity_curve, period_returns, trade_pnls, trade_returns, timestamps)
    stats.update({
        "strategy": strategy_name,
        "token": "PORTFOLIO",
        "bars": min_len,
        "token_count": len(tokens),
        "fees_paid": total_fees_paid,
        "gas_paid": total_gas_paid,
        "exit_reasons": exit_reason_counts,
        "min_cash_balance": min_cash_balance,
        "ending_cash": cash,
        "skipped_entries_insufficient_cash": skipped_entries,
        "token_trade_pnl": token_trade_pnl,
        "token_trade_count": token_trade_count,
        "halted_due_to_capital": halted_due_to_capital,
        "halt_index": halt_index,
        "halt_timestamp": halt_timestamp,
        "raw_trades": raw_trades,
    })
    return stats
