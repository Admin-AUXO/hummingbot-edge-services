import time


def score_narrative_token(pair_data, prev_volume, config):
    volume_24h = float(pair_data.get("volume", {}).get("h24", 0))
    liquidity = float(pair_data.get("liquidity", {}).get("usd", 0))

    if volume_24h < config.min_volume_24h:
        return None
    if liquidity < config.min_liquidity:
        return None

    volume_spike = volume_24h / prev_volume if prev_volume > 0 else 0
    price_change_5m = float(pair_data.get("priceChange", {}).get("m5", 0))
    price_change_1h = float(pair_data.get("priceChange", {}).get("h1", 0))
    price_change_24h = float(pair_data.get("priceChange", {}).get("h24", 0))

    return {
        "token": pair_data.get("baseToken", {}).get("symbol", "?"),
        "address": pair_data.get("baseToken", {}).get("address", ""),
        "pair": pair_data.get("pairAddress", ""),
        "dex": pair_data.get("dexId", ""),
        "price": float(pair_data.get("priceUsd", 0)),
        "volume_24h": volume_24h,
        "volume_spike": round(volume_spike, 2),
        "liquidity": liquidity,
        "price_change_5m": price_change_5m,
        "price_change_1h": price_change_1h,
        "price_change_24h": price_change_24h,
        "timestamp": time.time(),
    }


def filter_spiking_tokens(scored_tokens, config):
    min_p1h = getattr(config, "min_price_change_1h", 1.0)
    return [
        t for t in scored_tokens
        if t["volume_spike"] >= config.min_volume_spike
        and t["price_change_5m"] > 0       # Must be moving UP right now
        and t["price_change_1h"] >= min_p1h  # Sustained upward momentum
    ]
