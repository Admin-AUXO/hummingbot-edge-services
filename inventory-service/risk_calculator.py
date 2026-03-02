def calc_inventory_skew(base_value, quote_value, target_base_pct):
    total = base_value + quote_value
    if total <= 0:
        return 0.0
    actual_base_pct = base_value / total
    normalizer = max(target_base_pct, 1 - target_base_pct)
    return (actual_base_pct - target_base_pct) / normalizer


def calc_skew_bias(skew, max_skew, max_bias, sensitivity):
    abs_skew = abs(skew)
    if abs_skew <= max_skew:
        return 0.0
    excess = abs_skew - max_skew
    max_excess = 1.0 - max_skew
    if max_excess <= 0:
        return 0.0
    ratio = min(excess / max_excess, 1.0)
    magnitude = ratio ** sensitivity * max_bias
    return magnitude if skew > 0 else -magnitude


def classify_inventory(skew, max_skew):
    if skew > max_skew:
        return "LONG_HEAVY"
    elif skew < -max_skew:
        return "SHORT_HEAVY"
    return "BALANCED"


def calc_drawdown(current_value, peak_value):
    if peak_value <= 0:
        return 0.0
    return (peak_value - current_value) / peak_value


def should_kill(drawdown, max_drawdown):
    return drawdown >= max_drawdown
