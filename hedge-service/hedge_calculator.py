def calc_net_delta(spot_balance, perp_short_size):
    return spot_balance - perp_short_size


def calc_hedge_action(delta, threshold):
    if abs(delta) <= threshold:
        return "HOLD", 0.0
    if delta > 0:
        return "INCREASE_SHORT", abs(delta)
    return "REDUCE_SHORT", abs(delta)


def clamp_order_size(desired, max_order, current_pos, max_pos, action):
    size = min(desired, max_order)
    if action == "INCREASE_SHORT":
        headroom = max_pos - current_pos
        size = min(size, max(headroom, 0.0))
    return round(size, 4)


def calc_hedge_ratio(spot, short):
    if spot <= 0:
        return 0.0
    return short / spot


def classify_hedge_status(ratio, tolerance=0.05):
    if ratio == 0.0:
        return "UNHEDGED"
    if abs(ratio - 1.0) <= tolerance:
        return "HEDGED"
    if ratio < 1.0:
        return "UNDERHEDGED"
    return "OVERHEDGED"
