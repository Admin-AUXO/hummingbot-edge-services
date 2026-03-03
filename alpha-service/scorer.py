import time


def score_token(pair_data, config):
    score = 0
    breakdown = {}

    h24 = pair_data.get("volume", {}).get("h24", 0)
    volume_24h = float(h24) if h24 else 0
    mcap = float(pair_data.get("marketCap", 0) or pair_data.get("fdv", 0) or 1)
    vol_mcap = volume_24h / mcap if mcap > 0 else 0

    if vol_mcap > (config.vol_mcap_threshold * 10):
        score -= 5
        breakdown["vol_mcap"] = f"{vol_mcap:.2f} (WASH TRADING SPAM)"
    elif vol_mcap > config.vol_mcap_threshold:
        score += 3
        breakdown["vol_mcap"] = f"{vol_mcap:.2f} > {config.vol_mcap_threshold}"

    h1 = pair_data.get("volume", {}).get("h1", 0)
    volume_1h = float(h1) if h1 else 0
    h1_ratio = volume_1h / volume_24h if volume_24h > 0 else 0

    if h1_ratio > config.h1_vol_ratio_threshold:
        score += 2
        breakdown["h1_vol_ratio"] = f"{h1_ratio:.2%} > {config.h1_vol_ratio_threshold:.0%}"

    txns = pair_data.get("txns", {}).get("h24", {})
    buys, sells = int(txns.get("buys", 0)), int(txns.get("sells", 0))
    buy_sell_ratio = buys / sells if sells > 0 else 0

    if sells == 0 and buys > 10:
        score -= 100
        breakdown["buy_sell_ratio"] = "HONEYPOT (0 sells)"
    elif buy_sell_ratio > (config.buy_sell_ratio_threshold * 5):
        score -= 2
        breakdown["buy_sell_ratio"] = f"{buy_sell_ratio:.2f} (Suspiciously high)"
    elif buy_sell_ratio > config.buy_sell_ratio_threshold:
        score += 2
        breakdown["buy_sell_ratio"] = f"{buy_sell_ratio:.2f} > {config.buy_sell_ratio_threshold}"

    liq = float(pair_data.get("liquidity", {}).get("usd", 0))
    if liq > config.min_liquidity:
        score += 1
        breakdown["liquidity"] = f"${liq:,.0f} > ${config.min_liquidity:,.0f}"

    info = pair_data.get("info", {})
    if info.get("socials") or info.get("websites"):
        score += 1
        breakdown["socials"] = "verified"

    pc = pair_data.get("priceChange", {})
    p5m, p1h = float(pc.get("m5", 0) or 0), float(pc.get("h1", 0) or 0)

    if p5m > 2 and p1h > 5:
        score += 2
        breakdown["momentum"] = f"5m:{p5m:+.1f}% 1h:{p1h:+.1f}% (STRONG)"
    elif p5m > 0.5 and p1h > 2:
        score += 1
        breakdown["momentum"] = f"5m:{p5m:+.1f}% 1h:{p1h:+.1f}% (moderate)"
    elif p5m < -2 or p1h < -5:
        score -= 1
        breakdown["momentum"] = f"5m:{p5m:+.1f}% 1h:{p1h:+.1f}% (DUMPING)"

    breakdown["est_profit_pct"] = round(max(p1h * 0.5, 0), 2)
    return score, breakdown


def is_new_listing(pair_data, config):
    created_at = pair_data.get("pairCreatedAt")
    if not created_at: return False
    age_h = (time.time() * 1000 - created_at) / (1000 * 3600)
    return (age_h <= config.new_listing_max_age_hours) and (float(pair_data.get("liquidity", {}).get("usd", 0)) >= config.min_liquidity)


def _base_payload(pair_data):
    bt = pair_data.get("baseToken", {})
    return {
        "token": bt.get("symbol", "?"),
        "address": bt.get("address", ""),
        "pair": pair_data.get("pairAddress", ""),
        "dex": pair_data.get("dexId", ""),
        "price": float(pair_data.get("priceUsd", 0)),
        "volume_24h": float(pair_data.get("volume", {}).get("h24", 0)),
        "liquidity": float(pair_data.get("liquidity", {}).get("usd", 0)),
        "timestamp": time.time(),
    }


def build_signal_payload(pair_data, score, breakdown):
    payload = _base_payload(pair_data)
    pc = pair_data.get("priceChange", {})
    payload.update({
        "mcap": float(pair_data.get("marketCap", 0) or pair_data.get("fdv", 0) or 0),
        "score": score,
        "breakdown": breakdown,
        "est_profit_pct": breakdown.get("est_profit_pct", 0),
        "price_change_5m": float(pc.get("m5", 0) or 0),
        "price_change_1h": float(pc.get("h1", 0) or 0),
        "price_change_24h": float(pc.get("h24", 0) or 0),
    })
    return payload


def build_new_listing_payload(pair_data):
    created_at = pair_data.get("pairCreatedAt", 0)
    now = time.time()
    payload = _base_payload(pair_data)
    payload["age_hours"] = round((now * 1000 - created_at) / (1000 * 3600), 1) if created_at else 0
    return payload
