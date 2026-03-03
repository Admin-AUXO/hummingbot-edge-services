import time


def estimate_fee_apr(volume_24h, liquidity, fee_tier_pct):
    if liquidity <= 0:
        return 0.0
    # Dampen 24h volume peak to approximate a 7-day average (approx 0.5x of peak)
    smoothed_volume = volume_24h * 0.5
    daily_fees = smoothed_volume * (fee_tier_pct / 100)
    raw_fee_apr = (daily_fees / liquidity) * 365 * 100
    # Hard cap the fee APR to 300% to prevent unrealistic numbers
    return min(round(raw_fee_apr, 2), 300.0)


def calc_effective_apr(fee_apr, reward_apr):
    return round(fee_apr + reward_apr, 2)


def calc_risk_adjusted_apr(effective_apr, risk_score):
    if risk_score <= 0:
        return effective_apr
    return round(effective_apr / (1 + risk_score * 0.1), 2)


def build_pool_payload(pool_entry, fee_apr, effective_apr, risk_adjusted_apr, volume_24h, liquidity):
    return {
        "token": pool_entry.get("token", "?"),
        "pair": pool_entry.get("pair", ""),
        "dex": pool_entry.get("dex", ""),
        "fee_apr": fee_apr,
        "reward_apr": pool_entry.get("reward_apr", 0),
        "reward_token": pool_entry.get("reward_token", ""),
        "effective_apr": effective_apr,
        "risk_adjusted_apr": risk_adjusted_apr,
        "risk_score": pool_entry.get("risk_score", 5),
        "volume_24h": round(volume_24h, 2),
        "liquidity": round(liquidity, 2),
        "timestamp": time.time(),
    }


def rank_pools(pool_payloads):
    return sorted(pool_payloads, key=lambda x: x["risk_adjusted_apr"], reverse=True)
