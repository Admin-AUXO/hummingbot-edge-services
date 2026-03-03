import time


def score_narrative_token(pair_data, prev_volume, config):
    bt = pair_data.get("baseToken", {})
    vol_data = pair_data.get("volume", {})
    vol_24h = float(vol_data.get("h24", 0))
    liq = float(pair_data.get("liquidity", {}).get("usd", 0))

    if vol_24h < config.min_volume_24h or liq < config.min_liquidity:
        return None

    txns = pair_data.get("txns", {}).get("h24", {})
    if int(txns.get("sells", 0)) == 0 and int(txns.get("buys", 0)) > 5:
        return None

    pc = pair_data.get("priceChange", {})
    spike = vol_24h / prev_volume if prev_volume > 0 else 0
    
    return {
        "token": bt.get("symbol", "?"),
        "address": bt.get("address", ""),
        "pair": pair_data.get("pairAddress", ""),
        "dex": pair_data.get("dexId", ""),
        "price": float(pair_data.get("priceUsd", 0)),
        "volume_24h": vol_24h,
        "volume_spike": round(spike, 2),
        "liquidity": liq,
        "price_change_5m": float(pc.get("m5", 0) or 0),
        "price_change_1h": float(pc.get("h1", 0) or 0),
        "price_change_24h": float(pc.get("h24", 0) or 0),
        "timestamp": time.time(),
    }


def filter_spiking_tokens(scored_tokens, config):
    m_spike = config.min_volume_spike
    m_p1h = getattr(config, "min_price_change_1h", 1.0)
    return [
        t for t in scored_tokens
        if t["volume_spike"] >= m_spike
        and t["price_change_5m"] > 0
        and t["price_change_1h"] >= m_p1h
    ]
