import pandas as pd
import pandas_ta as ta


def calc_natr(df, period=14):
    return ta.natr(df["high"], df["low"], df["close"], length=period)


def calc_bb_width(df, period=20, std=2.0):
    bb = ta.bbands(df["close"], length=period, std=std)
    upper = bb[f"BBU_{period}_{std}"]
    lower = bb[f"BBL_{period}_{std}"]
    mid = bb[f"BBM_{period}_{std}"]
    return (upper - lower) / mid


def calc_sma(df, period=20):
    return ta.sma(df["close"], length=period)


def _higher_highs(df, lookback):
    highs = df["high"].iloc[-lookback:]
    return all(highs.iloc[i] > highs.iloc[i - 1] for i in range(1, len(highs)))


def _lower_lows(df, lookback):
    lows = df["low"].iloc[-lookback:]
    return all(lows.iloc[i] < lows.iloc[i - 1] for i in range(1, len(lows)))


def classify_regime(df, config):
    natr = calc_natr(df, config.natr_period)
    bb_width = calc_bb_width(df, config.bb_period, config.bb_std)
    sma = calc_sma(df, config.ma_period)

    latest_natr = natr.iloc[-1] / 100
    latest_bb_width = bb_width.iloc[-1]
    latest_close = df["close"].iloc[-1]
    latest_sma = sma.iloc[-1]

    if latest_natr > config.spike_natr_threshold or latest_bb_width > config.spike_bb_width_threshold:
        regime = "SPIKE"
    elif latest_close > latest_sma * config.bull_ma_threshold and _higher_highs(df, config.higher_highs_lookback):
        regime = "BULL"
    elif latest_close < latest_sma * config.bear_ma_threshold and _lower_lows(df, config.higher_highs_lookback):
        regime = "BEAR"
    else:
        regime = "SIDEWAYS"

    return regime, latest_natr, latest_bb_width
