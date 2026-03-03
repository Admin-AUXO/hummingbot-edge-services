import time


def score_token(pair_data, config):
    score = 0
    breakdown = {}

    volume_24h = float(pair_data.get("volume", {}).get("h24", 0))
    mcap = float(pair_data.get("marketCap", 0) or pair_data.get("fdv", 0) or 1)
    vol_mcap = volume_24h / mcap if mcap > 0 else 0

    if vol_mcap > config.vol_mcap_threshold:
        score += 3
        breakdown["vol_mcap"] = f"{vol_mcap:.2f} > {config.vol_mcap_threshold}"
    else:
        breakdown["vol_mcap"] = f"{vol_mcap:.2f} (below)"

    volume_1h = float(pair_data.get("volume", {}).get("h1", 0))
    h1_ratio = volume_1h / volume_24h if volume_24h > 0 else 0

    if h1_ratio > config.h1_vol_ratio_threshold:
        score += 2
        breakdown["h1_vol_ratio"] = f"{h1_ratio:.2%} > {config.h1_vol_ratio_threshold:.0%}"
    else:
        breakdown["h1_vol_ratio"] = f"{h1_ratio:.2%} (below)"

    buys = int(pair_data.get("txns", {}).get("h24", {}).get("buys", 0))
    sells = int(pair_data.get("txns", {}).get("h24", {}).get("sells", 0))
    buy_sell_ratio = buys / sells if sells > 0 else 0

    if buy_sell_ratio > config.buy_sell_ratio_threshold:
        score += 2
        breakdown["buy_sell_ratio"] = f"{buy_sell_ratio:.2f} > {config.buy_sell_ratio_threshold}"
    else:
        breakdown["buy_sell_ratio"] = f"{buy_sell_ratio:.2f} (below)"

    liquidity = float(pair_data.get("liquidity", {}).get("usd", 0))

    if liquidity > config.min_liquidity:
        score += 1
        breakdown["liquidity"] = f"${liquidity:,.0f} > ${config.min_liquidity:,.0f}"
    else:
        breakdown["liquidity"] = f"${liquidity:,.0f} (below)"

    info = pair_data.get("info", {})
    has_socials = bool(info.get("socials")) or bool(info.get("websites"))

    if has_socials:
        score += 1
        breakdown["socials"] = "verified"
    else:
        breakdown["socials"] = "none"

    # Price momentum scoring
    price_5m = float(pair_data.get("priceChange", {}).get("m5", 0))
    price_1h = float(pair_data.get("priceChange", {}).get("h1", 0))
    price_24h = float(pair_data.get("priceChange", {}).get("h24", 0))

    if price_5m > 2 and price_1h > 5:
        score += 2
        breakdown["momentum"] = f"5m:{price_5m:+.1f}% 1h:{price_1h:+.1f}% (STRONG)"
    elif price_5m > 0.5 and price_1h > 2:
        score += 1
        breakdown["momentum"] = f"5m:{price_5m:+.1f}% 1h:{price_1h:+.1f}% (moderate)"
    elif price_5m < -2 or price_1h < -5:
        score -= 1
        breakdown["momentum"] = f"5m:{price_5m:+.1f}% 1h:{price_1h:+.1f}% (DUMPING)"
    else:
        breakdown["momentum"] = f"5m:{price_5m:+.1f}% 1h:{price_1h:+.1f}% (flat)"

    # Estimated profit potential on $100 (conservative: 50% of 1h trend continuation)
    est_profit_pct = round(max(price_1h * 0.5, 0), 2) if price_1h > 0 else 0
    breakdown["est_profit_pct"] = est_profit_pct

    return score, breakdown


def is_new_listing(pair_data, config):
    created_at = pair_data.get("pairCreatedAt")
    if not created_at:
        return False
    age_hours = (time.time() * 1000 - created_at) / (1000 * 3600)
    if age_hours > config.new_listing_max_age_hours:
        return False
    liquidity = float(pair_data.get("liquidity", {}).get("usd", 0))
    return liquidity >= config.min_liquidity


def _base_payload(pair_data):
    return {
        "token": pair_data.get("baseToken", {}).get("symbol", "?"),
        "address": pair_data.get("baseToken", {}).get("address", ""),
        "pair": pair_data.get("pairAddress", ""),
        "dex": pair_data.get("dexId", ""),
        "price": float(pair_data.get("priceUsd", 0)),
        "volume_24h": float(pair_data.get("volume", {}).get("h24", 0)),
        "liquidity": float(pair_data.get("liquidity", {}).get("usd", 0)),
        "timestamp": time.time(),
    }


def build_signal_payload(pair_data, score, breakdown):
    payload = _base_payload(pair_data)
    payload["mcap"] = float(pair_data.get("marketCap", 0) or pair_data.get("fdv", 0) or 0)
    payload["score"] = score
    payload["breakdown"] = breakdown
    payload["est_profit_pct"] = breakdown.get("est_profit_pct", 0)
    payload["price_change_5m"] = float(pair_data.get("priceChange", {}).get("m5", 0))
    payload["price_change_1h"] = float(pair_data.get("priceChange", {}).get("h1", 0))
    payload["price_change_24h"] = float(pair_data.get("priceChange", {}).get("h24", 0))
    return payload


def build_new_listing_payload(pair_data):
    created_at = pair_data.get("pairCreatedAt", 0)
    age_hours = (time.time() * 1000 - created_at) / (1000 * 3600) if created_at else 0
    payload = _base_payload(pair_data)
    payload["age_hours"] = round(age_hours, 1)
    return payload
