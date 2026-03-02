import numpy as np


def calc_price_ratio(target_closes, ref_closes):
    return target_closes / ref_closes


def calc_rolling_z_score(ratio, lookback):
    window = ratio[-lookback:]
    mean = np.mean(window)
    std = np.std(window)
    if std == 0:
        return 0.0
    return float((window[-1] - mean) / std)


def calc_rolling_correlation(target_returns, ref_returns, lookback):
    t = target_returns[-lookback:]
    r = ref_returns[-lookback:]
    if len(t) < 2 or len(r) < 2:
        return 0.0
    corr_matrix = np.corrcoef(t, r)
    return float(corr_matrix[0, 1])


def classify_signal(avg_z, overbought, oversold):
    if avg_z >= overbought:
        return "OVERBOUGHT"
    elif avg_z <= oversold:
        return "OVERSOLD"
    return "NEUTRAL"


def calc_spread_bias(avg_z, overbought, oversold, max_bias):
    if avg_z >= overbought:
        return max_bias
    elif avg_z <= oversold:
        return -max_bias
    elif avg_z > 0:
        return float(np.clip(avg_z / overbought * max_bias, 0, max_bias))
    elif avg_z < 0:
        return float(np.clip(avg_z / abs(oversold) * max_bias, -max_bias, 0))
    return 0.0
