import time


def calc_optimal_range(price, base_range_pct, regime, session, natr, config):
    regime_mult = config.regime_multipliers.get(regime, 1.0)
    session_mult = config.session_multipliers.get(session, 1.0)

    if natr > 0 and natr < config.natr_tight_threshold:
        vol_mult = 0.7
    elif natr > config.natr_wide_threshold:
        vol_mult = 1.5
    else:
        vol_mult = 1.0

    effective_range = base_range_pct * regime_mult * session_mult * vol_mult
    effective_range = max(0.5, min(effective_range, 15.0))

    lower = price * (1 - effective_range / 100)
    upper = price * (1 + effective_range / 100)

    return round(lower, 6), round(upper, 6), round(effective_range, 3)


def calc_range_utilization(price, lower, upper):
    if upper <= lower:
        return 0.0
    total_range = upper - lower
    if price <= lower or price >= upper:
        return 0.0
    dist_to_edge = min(price - lower, upper - price)
    return round(dist_to_edge / (total_range / 2) * 100, 1)


def should_rebalance(utilization, threshold):
    return utilization < threshold


def build_range_payload(price, lower, upper, effective_range, utilization, regime, session, natr, rebalance):
    return {
        "price": price,
        "range_lower": lower,
        "range_upper": upper,
        "range_pct": effective_range,
        "utilization_pct": utilization,
        "should_rebalance": rebalance,
        "regime": regime,
        "session": session,
        "natr": round(natr, 6),
        "timestamp": time.time(),
    }
