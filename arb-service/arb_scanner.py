import time


def group_pairs_by_dex(pairs, config):
    by_dex = {}
    now_ms = time.time() * 1000
    for pair in pairs:
        # Optimization: Pull liquidity first as it's the primary filter
        liq_data = pair.get("liquidity", {})
        liq = float(liq_data.get("usd", 0))
        if liq < config.min_liquidity: continue

        vol_data = pair.get("volume", {})
        vol = float(vol_data.get("h24", 0))
        if vol < config.min_volume_24h: continue

        dex = pair.get("dexId", "unknown")
        price = float(pair.get("priceUsd", 0))
        if price <= 0: continue

        if config.max_pool_age_hours > 0:
            created = pair.get("pairCreatedAt", 0)
            if created and (now_ms - created) < 3600000:
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


def score_opportunity(opp, config):
    spread = opp["spread_pct"]
    buy_liq = opp["buy_liquidity"]
    sell_liq = opp["sell_liquidity"]
    min_liq = min(buy_liq, sell_liq)

    net_spread = spread - config.est_slippage_pct
    if net_spread <= 0:
        return 0

    max_trade = min_liq * config.max_trade_pct_of_liq
    net_profit = max_trade * net_spread / 100 - config.gas_cost_usd

    if net_profit <= 0:
        return 0

    spread_score = min(net_spread * 10, 40)
    profit_score = min(net_profit * 5, 30)
    liquidity_score = min(min_liq / 10000, 20)
    volume_score = min(opp.get("buy_volume", 0) / 50000, 10)

    return round(spread_score + profit_score + liquidity_score + volume_score, 1)


def find_arb_opportunities(token_symbol: str, pairs: list, config) -> list:
    by_dex = group_pairs_by_dex(pairs, config)
    if len(by_dex) < config.min_dex_count:
        return []

    dex_list = list(by_dex.values())
    opportunities = []
    
    now = time.time()
    slippage = config.est_slippage_pct
    gas = config.gas_cost_usd
    max_trade_ratio = config.max_trade_pct_of_liq
    min_arb = config.min_arb_pct
    max_spread = config.max_spread_pct
    min_net_100 = config.min_net_profit_100

    for i in range(len(dex_list)):
        a = dex_list[i]
        ap, al = a["price"], a["liquidity"]
        
        for j in range(i + 1, len(dex_list)):
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

            
            net_spread = spread_pct - slippage
            net_profit_100 = (100 * net_spread / 100) - gas
            if net_profit_100 < min_net_100:
                continue

            max_trade = min_liq * max_trade_ratio
            net_profit_max = (max_trade * net_spread / 100) - gas

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
                "spread_pct": round(spread_pct, 2),
                "net_spread_pct": round(net_spread, 2),
                "max_size_usd": round(max_trade, 2),
                "net_profit_max": round(net_profit_max, 2),
                "net_profit_100": round(net_profit_100, 2),
                "timestamp": now,
            }

            opp["score"] = score_opportunity(opp, config)
            if opp["score"] > 0:
                opportunities.append(opp)

    return sorted(opportunities, key=lambda x: x["score"], reverse=True)
