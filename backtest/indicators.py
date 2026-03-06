import math


def sma(values, window):
    out = [None] * len(values)
    if window <= 0 or len(values) < window:
        return out
    running = sum(values[:window])
    out[window - 1] = running / window
    for idx in range(window, len(values)):
        running += values[idx] - values[idx - window]
        out[idx] = running / window
    return out


def ema(values, span):
    out = [None] * len(values)
    if span <= 0 or not values:
        return out
    alpha = 2.0 / (span + 1.0)
    prev = values[0]
    out[0] = prev
    for idx in range(1, len(values)):
        prev = (values[idx] * alpha) + (prev * (1.0 - alpha))
        out[idx] = prev
    return out


def rolling_mean_std(values, window):
    means = [None] * len(values)
    stds = [None] * len(values)
    if window <= 1 or len(values) < window:
        return means, stds
    sum_x = sum(values[:window])
    sum_x2 = sum(v * v for v in values[:window])
    for idx in range(window - 1, len(values)):
        if idx >= window:
            add_v = values[idx]
            rem_v = values[idx - window]
            sum_x += add_v - rem_v
            sum_x2 += (add_v * add_v) - (rem_v * rem_v)
        mean = sum_x / window
        variance = (sum_x2 - (sum_x * sum_x) / window) / max(1, window - 1)
        variance = max(0.0, variance)
        means[idx] = mean
        stds[idx] = math.sqrt(variance)
    return means, stds


def rolling_max(values, window):
    out = [None] * len(values)
    if window <= 0 or len(values) < window:
        return out
    for idx in range(window - 1, len(values)):
        out[idx] = max(values[idx - window + 1 : idx + 1])
    return out


def rsi(values, window):
    out = [None] * len(values)
    if window <= 1 or len(values) <= window:
        return out
    gains = 0.0
    losses = 0.0
    for idx in range(1, window + 1):
        delta = values[idx] - values[idx - 1]
        if delta >= 0:
            gains += delta
        else:
            losses -= delta
    avg_gain = gains / window
    avg_loss = losses / window
    rs = (avg_gain / avg_loss) if avg_loss > 0 else float("inf")
    out[window] = 100.0 - (100.0 / (1.0 + rs))
    for idx in range(window + 1, len(values)):
        delta = values[idx] - values[idx - 1]
        gain = max(delta, 0.0)
        loss = max(-delta, 0.0)
        avg_gain = ((avg_gain * (window - 1)) + gain) / window
        avg_loss = ((avg_loss * (window - 1)) + loss) / window
        rs = (avg_gain / avg_loss) if avg_loss > 0 else float("inf")
        out[idx] = 100.0 - (100.0 / (1.0 + rs))
    return out


def true_range(highs, lows, closes):
    n = len(closes)
    tr = [0.0] * n
    if n == 0:
        return tr
    tr[0] = highs[0] - lows[0]
    for idx in range(1, n):
        hl = highs[idx] - lows[idx]
        hc = abs(highs[idx] - closes[idx - 1])
        lc = abs(lows[idx] - closes[idx - 1])
        tr[idx] = max(hl, hc, lc)
    return tr


def atr(highs, lows, closes, window):
    tr = true_range(highs, lows, closes)
    return ema(tr, window)


def adx(highs, lows, closes, window=14):
    n = len(closes)
    out = [None] * n
    if n < window + 1:
        return out
    plus_dm = [0.0] * n
    minus_dm = [0.0] * n
    for idx in range(1, n):
        up = highs[idx] - highs[idx - 1]
        down = lows[idx - 1] - lows[idx]
        plus_dm[idx] = up if up > down and up > 0 else 0.0
        minus_dm[idx] = down if down > up and down > 0 else 0.0
    atr_vals = atr(highs, lows, closes, window)
    smooth_plus = ema(plus_dm, window)
    smooth_minus = ema(minus_dm, window)
    dx = [None] * n
    for idx in range(n):
        sp, sm, av = smooth_plus[idx], smooth_minus[idx], atr_vals[idx]
        if sp is None or sm is None or av is None or av <= 0:
            continue
        plus_di = 100.0 * sp / av
        minus_di = 100.0 * sm / av
        denom = plus_di + minus_di
        dx[idx] = 100.0 * abs(plus_di - minus_di) / denom if denom > 0 else 0.0
    adx_vals = ema(dx, window)
    for idx in range(n):
        if adx_vals[idx] is not None:
            out[idx] = adx_vals[idx]
    return out


def donchian(values, window):
    n = len(values)
    highs = [None] * n
    lows = [None] * n
    if window <= 0 or n < window:
        return highs, lows
    for idx in range(window - 1, n):
        segment = values[idx - window + 1: idx + 1]
        highs[idx] = max(segment)
        lows[idx] = min(segment)
    return highs, lows


def volume_sma(volumes, window):
    return sma(volumes, window)
