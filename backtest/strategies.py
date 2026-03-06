from backtest.indicators import ema, rolling_mean_std, rolling_max, rsi, atr, adx, donchian, volume_sma


def _extract(candles):
    closes = [c.close for c in candles]
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]
    volumes = [c.volume for c in candles]
    return closes, highs, lows, volumes


def supertrend_atr(candles, params):
    atr_window = int(params.get("atr_window", 10))
    multiplier = float(params.get("multiplier", 3.0))
    adx_window = int(params.get("adx_window", 14))
    adx_threshold = float(params.get("adx_threshold", 20.0))

    closes, highs, lows, volumes = _extract(candles)
    n = len(closes)
    atr_vals = atr(highs, lows, closes, atr_window)
    adx_vals = adx(highs, lows, closes, adx_window)

    upper_band = [0.0] * n
    lower_band = [0.0] * n
    direction = [1] * n
    signals = [0] * n
    scores = [0.0] * n

    for idx in range(n):
        av = atr_vals[idx]
        if av is None or av <= 0:
            continue
        mid = (highs[idx] + lows[idx]) / 2.0
        upper_band[idx] = mid + multiplier * av
        lower_band[idx] = mid - multiplier * av

        if idx > 0:
            if lower_band[idx] < lower_band[idx - 1] and closes[idx - 1] > lower_band[idx - 1]:
                lower_band[idx] = lower_band[idx - 1]
            if upper_band[idx] > upper_band[idx - 1] and closes[idx - 1] < upper_band[idx - 1]:
                upper_band[idx] = upper_band[idx - 1]
            prev_dir = direction[idx - 1]
            if prev_dir == 1:
                direction[idx] = -1 if closes[idx] < lower_band[idx] else 1
            else:
                direction[idx] = 1 if closes[idx] > upper_band[idx] else -1

        adx_v = adx_vals[idx]
        trend_strong = adx_v is not None and adx_v >= adx_threshold
        if trend_strong:
            signals[idx] = direction[idx]
        trend_score = (adx_v / 50.0) if adx_v is not None else 0.0
        scores[idx] = trend_score * direction[idx]
    return signals, scores


def macd_adx(candles, params):
    fast = int(params.get("fast", 12))
    slow = int(params.get("slow", 26))
    signal_span = int(params.get("signal", 9))
    adx_window = int(params.get("adx_window", 14))
    adx_threshold = float(params.get("adx_threshold", 20.0))

    closes, highs, lows, volumes = _extract(candles)
    n = len(closes)
    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    macd_line = [0.0] * n
    for idx in range(n):
        ef, es = ema_fast[idx], ema_slow[idx]
        macd_line[idx] = 0.0 if ef is None or es is None else (ef - es)
    macd_signal = ema(macd_line, signal_span)
    adx_vals = adx(highs, lows, closes, adx_window)

    signals = [0] * n
    scores = [0.0] * n
    for idx in range(n):
        s = macd_signal[idx]
        adx_v = adx_vals[idx]
        if s is None:
            continue
        histogram = macd_line[idx] - s
        trend_strong = adx_v is not None and adx_v >= adx_threshold
        if trend_strong:
            signals[idx] = 1 if histogram > 0 else -1
        adx_score = (adx_v / 50.0) if adx_v is not None else 0.0
        scores[idx] = (1 if histogram > 0 else -1) * adx_score
    return signals, scores


def rsi_trend(candles, params):
    rsi_window = int(params.get("rsi_window", 14))
    ema_window = int(params.get("ema_window", 50))
    rsi_long = float(params.get("rsi_long", 55.0))
    rsi_short = float(params.get("rsi_short", 45.0))
    adx_window = int(params.get("adx_window", 14))
    adx_threshold = float(params.get("adx_threshold", 18.0))

    closes, highs, lows, volumes = _extract(candles)
    n = len(closes)
    rsi_vals = rsi(closes, rsi_window)
    ema_trend = ema(closes, ema_window)
    adx_vals = adx(highs, lows, closes, adx_window)

    signals = [0] * n
    scores = [0.0] * n
    for idx in range(n):
        rv = rsi_vals[idx]
        ev = ema_trend[idx]
        adx_v = adx_vals[idx]
        if rv is None or ev is None:
            continue
        trend_strong = adx_v is not None and adx_v >= adx_threshold
        if not trend_strong:
            continue
        if rv >= rsi_long and closes[idx] > ev:
            signals[idx] = 1
        elif rv <= rsi_short and closes[idx] < ev:
            signals[idx] = -1
        momentum = (rv - 50.0) / 50.0
        scores[idx] = momentum * ((adx_v / 50.0) if adx_v is not None else 0.5)
    return signals, scores


def donchian_breakout(candles, params):
    breakout_window = int(params.get("breakout_window", 40))
    ema_window = int(params.get("ema_window", 50))
    adx_window = int(params.get("adx_window", 14))
    adx_threshold = float(params.get("adx_threshold", 22.0))
    vol_window = int(params.get("vol_window", 20))
    vol_mult = float(params.get("vol_mult", 1.2))

    closes, highs, lows, volumes = _extract(candles)
    n = len(closes)
    don_hi, don_lo = donchian(closes, breakout_window)
    ema_trend = ema(closes, ema_window)
    adx_vals = adx(highs, lows, closes, adx_window)
    vol_avg = volume_sma(volumes, vol_window)

    signals = [0] * n
    scores = [0.0] * n
    prev_signal = 0
    for idx in range(n):
        prev_hi = don_hi[idx - 1] if idx > 0 and don_hi[idx - 1] is not None else None
        prev_lo = don_lo[idx - 1] if idx > 0 and don_lo[idx - 1] is not None else None
        ev = ema_trend[idx]
        adx_v = adx_vals[idx]
        va = vol_avg[idx]
        if prev_hi is None or prev_lo is None or ev is None:
            signals[idx] = prev_signal
            continue

        trend_strong = adx_v is not None and adx_v >= adx_threshold
        vol_ok = va is not None and va > 0 and volumes[idx] >= va * vol_mult

        if closes[idx] > prev_hi and closes[idx] > ev and trend_strong and vol_ok:
            prev_signal = 1
        elif closes[idx] < prev_lo and closes[idx] < ev and trend_strong and vol_ok:
            prev_signal = -1
        elif prev_signal == 1 and closes[idx] < ev:
            prev_signal = 0
        elif prev_signal == -1 and closes[idx] > ev:
            prev_signal = 0

        signals[idx] = prev_signal
        adx_score = (adx_v / 50.0) if adx_v is not None else 0.0
        scores[idx] = prev_signal * adx_score
    return signals, scores


def trend_pullback(candles, params):
    fast = int(params.get("fast", 20))
    slow = int(params.get("slow", 80))
    atr_window = int(params.get("atr_window", 14))
    adx_window = int(params.get("adx_window", 14))
    adx_threshold = float(params.get("adx_threshold", 22.0))
    pullback_atr_mult = float(params.get("pullback_atr_mult", 1.5))

    closes, highs, lows, volumes = _extract(candles)
    n = len(closes)
    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    atr_vals = atr(highs, lows, closes, atr_window)
    adx_vals = adx(highs, lows, closes, adx_window)

    signals = [0] * n
    scores = [0.0] * n
    prev_signal = 0
    for idx in range(n):
        ef, es = ema_fast[idx], ema_slow[idx]
        av = atr_vals[idx]
        adx_v = adx_vals[idx]
        if ef is None or es is None or es == 0 or av is None or av <= 0:
            signals[idx] = prev_signal
            continue

        trend_strong = adx_v is not None and adx_v >= adx_threshold
        trend_up = ef > es
        trend_dn = ef < es

        if trend_up and trend_strong and closes[idx] <= ef - pullback_atr_mult * av:
            prev_signal = 1
        elif trend_dn and trend_strong and closes[idx] >= ef + pullback_atr_mult * av:
            prev_signal = -1
        elif prev_signal == 1 and closes[idx] >= ef:
            prev_signal = 0
        elif prev_signal == -1 and closes[idx] <= ef:
            prev_signal = 0

        signals[idx] = prev_signal
        trend_str = abs(ef - es) / es
        scores[idx] = prev_signal * trend_str * 50.0
    return signals, scores


def mean_reversion_bb(candles, params):
    window = int(params.get("window", 20))
    std_mult = float(params.get("std_mult", 2.0))
    rsi_window = int(params.get("rsi_window", 14))
    rsi_oversold = float(params.get("rsi_oversold", 30.0))
    rsi_overbought = float(params.get("rsi_overbought", 70.0))
    adx_window = int(params.get("adx_window", 14))
    adx_max = float(params.get("adx_max", 25.0))

    closes, highs, lows, volumes = _extract(candles)
    n = len(closes)
    means, stds = rolling_mean_std(closes, window)
    rsi_vals = rsi(closes, rsi_window)
    adx_vals = adx(highs, lows, closes, adx_window)

    signals = [0] * n
    scores = [0.0] * n
    prev_signal = 0
    for idx in range(n):
        mean, std, rv = means[idx], stds[idx], rsi_vals[idx]
        adx_v = adx_vals[idx]
        if mean is None or std is None or rv is None or std <= 0:
            signals[idx] = prev_signal
            continue
        upper = mean + std_mult * std
        lower = mean - std_mult * std
        ranging = adx_v is None or adx_v < adx_max

        if ranging and closes[idx] <= lower and rv <= rsi_oversold:
            prev_signal = 1
        elif ranging and closes[idx] >= upper and rv >= rsi_overbought:
            prev_signal = -1
        elif prev_signal == 1 and closes[idx] >= mean:
            prev_signal = 0
        elif prev_signal == -1 and closes[idx] <= mean:
            prev_signal = 0

        signals[idx] = prev_signal
        z = (closes[idx] - mean) / std
        scores[idx] = -z * 0.5 if prev_signal != 0 else 0.0
    return signals, scores


REGISTRY = {
    "supertrend_v1": supertrend_atr,
    "macd_adx_v1": macd_adx,
    "rsi_trend_v1": rsi_trend,
    "donchian_breakout_v1": donchian_breakout,
    "trend_pullback_v1": trend_pullback,
    "mean_reversion_v1": mean_reversion_bb,
}

MM_STRATEGIES = {"pmm_dynamic", "grid_strike"}

ALL_STRATEGY_NAMES = sorted(set(list(REGISTRY.keys()) + list(MM_STRATEGIES)))


def compute_signals(candles, strategy_name, params):
    fn = REGISTRY[strategy_name]
    return fn(candles, params)


PARAM_SETS = {
    "supertrend_v1": [
        {"atr_window": 100, "multiplier": 3.0, "adx_window": 100, "adx_threshold": 25.0},
        {"atr_window": 150, "multiplier": 3.5, "adx_window": 150, "adx_threshold": 28.0},
        {"atr_window": 200, "multiplier": 4.0, "adx_window": 200, "adx_threshold": 30.0},
    ],
    "macd_adx_v1": [
        {"fast": 100, "slow": 250, "signal": 50, "adx_window": 100, "adx_threshold": 25.0},
        {"fast": 150, "slow": 350, "signal": 75, "adx_window": 150, "adx_threshold": 28.0},
        {"fast": 50, "slow": 150, "signal": 30, "adx_window": 75, "adx_threshold": 22.0},
    ],
    "rsi_trend_v1": [
        {"rsi_window": 100, "ema_window": 500, "rsi_long": 58, "rsi_short": 42, "adx_window": 100, "adx_threshold": 25.0},
        {"rsi_window": 150, "ema_window": 600, "rsi_long": 60, "rsi_short": 40, "adx_window": 150, "adx_threshold": 28.0},
        {"rsi_window": 75, "ema_window": 400, "rsi_long": 55, "rsi_short": 45, "adx_window": 75, "adx_threshold": 22.0},
    ],
    "donchian_breakout_v1": [
        {"breakout_window": 300, "ema_window": 500, "adx_window": 100, "adx_threshold": 25.0, "vol_window": 200, "vol_mult": 1.2},
        {"breakout_window": 500, "ema_window": 600, "adx_window": 150, "adx_threshold": 28.0, "vol_window": 300, "vol_mult": 1.3},
        {"breakout_window": 200, "ema_window": 400, "adx_window": 75, "adx_threshold": 22.0, "vol_window": 150, "vol_mult": 1.0},
    ],
    "trend_pullback_v1": [
        {"fast": 150, "slow": 500, "atr_window": 100, "adx_window": 100, "adx_threshold": 25.0, "pullback_atr_mult": 1.5},
        {"fast": 200, "slow": 600, "atr_window": 150, "adx_window": 150, "adx_threshold": 28.0, "pullback_atr_mult": 2.0},
        {"fast": 100, "slow": 400, "atr_window": 75, "adx_window": 75, "adx_threshold": 22.0, "pullback_atr_mult": 1.2},
    ],
    "mean_reversion_v1": [
        {"window": 200, "std_mult": 2.2, "rsi_window": 100, "rsi_oversold": 28, "rsi_overbought": 72, "adx_window": 100, "adx_max": 22.0},
        {"window": 300, "std_mult": 2.5, "rsi_window": 150, "rsi_oversold": 25, "rsi_overbought": 75, "adx_window": 150, "adx_max": 20.0},
        {"window": 150, "std_mult": 2.0, "rsi_window": 75, "rsi_oversold": 30, "rsi_overbought": 70, "adx_window": 75, "adx_max": 25.0},
    ],
    "pmm_dynamic": [
        {"base_spread": 0.004, "vol_mult": 2.0, "min_spread": 0.002, "max_spread": 0.02, "vol_window": 30},
        {"base_spread": 0.006, "vol_mult": 1.8, "min_spread": 0.003, "max_spread": 0.03, "vol_window": 40},
        {"base_spread": 0.008, "vol_mult": 1.5, "min_spread": 0.004, "max_spread": 0.04, "vol_window": 50},
    ],
    "grid_strike": [
        {"grid_step": 0.008, "max_cycles_per_bar": 2, "vol_window": 30},
        {"grid_step": 0.012, "max_cycles_per_bar": 1, "vol_window": 40},
        {"grid_step": 0.006, "max_cycles_per_bar": 2, "vol_window": 20},
    ],
}


def get_param_sets(strategy_name):
    return PARAM_SETS.get(strategy_name, [{}])


def build_variant_name(strategy_name, params):
    if not params:
        return strategy_name
    return strategy_name + "(" + ",".join(f"{k}={v}" for k, v in params.items()) + ")"
