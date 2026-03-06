import time

from shared.utils import normalize_chain_id


def group_pairs_by_dex(pairs, config):
    by_dex = {}
    now_ms = time.time() * 1000
    min_liquidity = config.min_liquidity
    min_volume = config.min_volume_24h
    max_pool_age_ms = (config.max_pool_age_hours * 3600000) if config.max_pool_age_hours > 0 else 0
    for pair in pairs:
        liq_data = pair.get("liquidity", {})
        liq = float(liq_data.get("usd", 0))
        if liq < min_liquidity: continue

        vol_data = pair.get("volume", {})
        vol = float(vol_data.get("h24", 0))
        if vol < min_volume: continue

        dex = pair.get("dexId", "unknown")
        price = float(pair.get("priceUsd", 0))
        if price <= 0: continue

        if max_pool_age_ms > 0:
            created = pair.get("pairCreatedAt", 0)
            if created and (now_ms - created) < max_pool_age_ms:
                continue

        txn_data = pair.get("txns", {})
        h24_data = txn_data.get("h24", {})
        sells, buys = int(h24_data.get("sells", 0)), int(h24_data.get("buys", 0))
        if sells == 0 and buys > 5: continue

        price_change = pair.get("priceChange", {})
        entry = {
            "dex": dex,
            "price": price,
            "liquidity": liq,
            "pair_address": pair.get("pairAddress", ""),
            "volume_24h": vol,
            "price_change_5m": float(price_change.get("m5", 0) or 0),
            "price_change_1h": float(price_change.get("h1", 0) or 0),
            "txns_24h": buys + sells,
        }

        if dex not in by_dex or liq > by_dex[dex]["liquidity"]:
            by_dex[dex] = entry

    return by_dex

def estimate_dynamic_slippage_pct(config, chain_id, buy, sell, trade_size_usd):
    base_slippage = config.est_slippage_for(chain_id)
    min_liq = max(1.0, min(float(buy.get("liquidity", 0) or 0), float(sell.get("liquidity", 0) or 0)))
    liquidity_impact = (trade_size_usd / min_liq) * config.slippage_liquidity_impact_factor

    buy_vol = abs(float(buy.get("price_change_5m", 0) or 0)) + abs(float(buy.get("price_change_1h", 0) or 0))
    sell_vol = abs(float(sell.get("price_change_5m", 0) or 0)) + abs(float(sell.get("price_change_1h", 0) or 0))
    volatility_impact = ((buy_vol + sell_vol) / 2.0) * config.slippage_volatility_impact_factor

    txns = max(1.0, float(buy.get("txns_24h", 0) or 0) + float(sell.get("txns_24h", 0) or 0))
    flow_impact = min(0.5, 20.0 / txns)

    return max(base_slippage, base_slippage + liquidity_impact + volatility_impact + flow_impact)


def find_arb_opportunities(token_symbol: str, pairs: list, config, chain_id: str = None) -> list:
    if len(pairs) < 2:
        return []

    chain_id = normalize_chain_id(chain_id or (pairs[0].get("chainId") if pairs else "solana"))
    by_dex = group_pairs_by_dex(pairs, config)
    if len(by_dex) < config.min_dex_count:
        return []

    dex_list = list(by_dex.values())
    dex_count = len(dex_list)
    opportunities = []
    
    now = time.time()
    gas = float(config.gas_cost_for(chain_id))
    max_trade_ratio = config.max_trade_pct_of_liq
    min_arb = config.min_arb_for(chain_id)
    max_spread = config.max_spread_pct
    min_net_100 = config.min_net_profit_100

    append_opp = opportunities.append
    for i in range(dex_count - 1):
        a = dex_list[i]
        ap, al = a["price"], a["liquidity"]
        
        for j in range(i + 1, dex_count):
            b = dex_list[j]
            bp, bl = b["price"], b["liquidity"]

            spread_pct = abs(ap - bp) / ((ap + bp) / 2) * 100
            if not (min_arb <= spread_pct <= max_spread):
                continue
            
            if ap < bp:
                buy, sell = a, b
                buy_p, sell_p = ap, bp
                min_liq = al if al < bl else bl
            else:
                buy, sell = b, a
                buy_p, sell_p = bp, ap
                min_liq = bl if bl < al else al

            max_trade = min_liq * max_trade_ratio
            dynamic_slippage = estimate_dynamic_slippage_pct(config, chain_id, buy, sell, max_trade)
            net_spread = spread_pct - dynamic_slippage
            net_profit_100 = (100 * net_spread / 100) - gas
            if net_profit_100 < min_net_100:
                continue

            net_profit_max = (max_trade * net_spread / 100) - gas
            if net_profit_max <= 0:
                continue

            spread_score = min(net_spread * 10, 40)
            profit_score = min(net_profit_max * 5, 30)
            liquidity_score = min(min_liq / 10000, 20)
            volume_score = min(buy.get("volume_24h", 0) / 50000, 10)
            score = round(spread_score + profit_score + liquidity_score + volume_score, 1)
            if score <= 0:
                continue

            opp = {
                "token": token_symbol,
                "buy_dex": buy["dex"],
                "buy_price": buy_p,
                "buy_pair": buy["pair_address"],
                "buy_liquidity": buy["liquidity"],
                "buy_volume": buy["volume_24h"],
                "sell_dex": sell["dex"],
                "sell_price": sell_p,
                "sell_pair": sell["pair_address"],
                "sell_liquidity": sell["liquidity"],
                "sell_volume": sell["volume_24h"],
                "chainId": chain_id,
                "spread_pct": round(spread_pct, 2),
                "net_spread_pct": round(net_spread, 2),
                "est_slippage_pct": round(dynamic_slippage, 4),
                "gas_cost_usd": round(gas, 4),
                "max_size_usd": round(max_trade, 2),
                "net_profit_max": round(net_profit_max, 2),
                "net_profit_100": round(net_profit_100, 2),
                "timestamp": now,
                "score": score,
            }
            append_opp(opp)

    return sorted(opportunities, key=lambda x: x["score"], reverse=True)
