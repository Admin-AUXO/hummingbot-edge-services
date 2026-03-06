import time

from shared.utils import normalize_chain_id


def score_narrative_token(pair_data, prev_volume, config, token_override=None):
    chain_id = normalize_chain_id(pair_data.get("chainId"))
    token = token_override or pair_data.get("baseToken", {})
    vol_data = pair_data.get("volume", {})
    vol_24h = float(vol_data.get("h24", 0))
    liq = float(pair_data.get("liquidity", {}).get("usd", 0))

    if vol_24h < config.min_volume_for(chain_id) or liq < config.min_liquidity_for(chain_id):
        return None

    txns = pair_data.get("txns", {}).get("h24", {})
    if int(txns.get("sells", 0)) == 0 and int(txns.get("buys", 0)) > 5:
        return None

    pc = pair_data.get("priceChange", {})
    spike = vol_24h / prev_volume if prev_volume > 0 else 0
    
    return {
        "chainId": chain_id,
        "token": token.get("symbol", "?"),
        "address": token.get("address", ""),
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
    filtered = []
    for token in scored_tokens:
        chain_id = normalize_chain_id(token.get("chainId"))
        if token["volume_spike"] < config.min_spike_for(chain_id):
            continue
        if token["price_change_5m"] <= 0:
            continue
        if token["price_change_1h"] < config.min_price_change_1h_for(chain_id):
            continue
        filtered.append(token)
    return filtered
