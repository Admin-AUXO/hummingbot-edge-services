import time


def group_pairs_by_dex(pairs, config):
    """Group token pairs by DEX, keeping only the most liquid pool per DEX."""
    by_dex = {}
    for pair in pairs:
        liq = float(pair.get("liquidity", {}).get("usd", 0))
        if liq < config.min_liquidity:
            continue

        vol = float(pair.get("volume", {}).get("h24", 0))
        if vol < config.min_volume_24h:
            continue

        dex = pair.get("dexId", "unknown")
        price = float(pair.get("priceUsd", 0))
        if price <= 0:
            continue

        # Filter very new pools (optional)
        if config.max_pool_age_hours > 0:
            created = pair.get("pairCreatedAt", 0)
            if created:
                age_hours = (time.time() * 1000 - created) / 3600000
                if age_hours < 1:  # Skip pools under 1 hour old (possible rug)
                    continue

        # Price change data for momentum context
        price_change = pair.get("priceChange", {})
        p5m = float(price_change.get("m5", 0) or 0)
        p1h = float(price_change.get("h1", 0) or 0)

        entry = {
            "dex": dex,
            "price": price,
            "liquidity": liq,
            "pair_address": pair.get("pairAddress", ""),
            "volume_24h": vol,
            "price_change_5m": p5m,
            "price_change_1h": p1h,
            "txns_24h": sum(
                int(pair.get("txns", {}).get(period, {}).get("buys", 0))
                + int(pair.get("txns", {}).get(period, {}).get("sells", 0))
                for period in ["h24"]
            ),
        }

        # Keep most liquid pool per DEX
        if dex not in by_dex or liq > by_dex[dex]["liquidity"]:
            by_dex[dex] = entry

    return by_dex


def score_opportunity(opp, config):
    """Score an arb opportunity for ranking. Higher = better."""
    spread = opp["spread_pct"]
    buy_liq = opp["buy_liquidity"]
    sell_liq = opp["sell_liquidity"]
    min_liq = min(buy_liq, sell_liq)

    # Net profit after gas + slippage
    net_spread = spread - config.est_slippage_pct
    if net_spread <= 0:
        return 0

    # Max realistic trade size (2% of smaller pool)
    max_trade = min_liq * config.max_trade_pct_of_liq
    net_profit = max_trade * net_spread / 100 - config.gas_cost_usd

    if net_profit <= 0:
        return 0

    # Score components (weighted)
    spread_score = min(net_spread * 10, 40)         # up to 40 pts for spread
    profit_score = min(net_profit * 5, 30)           # up to 30 pts for $ profit
    liquidity_score = min(min_liq / 10000, 20)       # up to 20 pts for deep pools
    volume_score = min(opp.get("buy_volume", 0) / 50000, 10)  # up to 10 pts

    return round(spread_score + profit_score + liquidity_score + volume_score, 1)


def find_arb_opportunities(token_symbol, pairs, config):
    by_dex = group_pairs_by_dex(pairs, config)
    if len(by_dex) < config.min_dex_count:
        return []

    dex_list = list(by_dex.values())
    opportunities = []

    for i in range(len(dex_list)):
        for j in range(i + 1, len(dex_list)):
            a, b = dex_list[i], dex_list[j]
            mid = (a["price"] + b["price"]) / 2
            spread_pct = abs(a["price"] - b["price"]) / mid * 100

            if spread_pct < config.min_arb_pct:
                continue

            buy_side = a if a["price"] < b["price"] else b
            sell_side = b if a["price"] < b["price"] else a

            # Calculate net profitability
            net_spread = spread_pct - config.est_slippage_pct
            max_trade = min(buy_side["liquidity"], sell_side["liquidity"]) * config.max_trade_pct_of_liq
            net_profit_max = max_trade * net_spread / 100 - config.gas_cost_usd
            net_profit_100 = 100 * net_spread / 100 - config.gas_cost_usd
            trades_for_10 = max(1, int(10 / net_profit_100)) if net_profit_100 > 0 else 999

            opp = {
                "token": token_symbol,
                "buy_dex": buy_side["dex"],
                "buy_price": buy_side["price"],
                "buy_pair": buy_side["pair_address"],
                "buy_liquidity": buy_side["liquidity"],
                "buy_volume": buy_side["volume_24h"],
                "sell_dex": sell_side["dex"],
                "sell_price": sell_side["price"],
                "sell_pair": sell_side["pair_address"],
                "sell_liquidity": sell_side["liquidity"],
                "sell_volume": sell_side["volume_24h"],
                "spread_pct": round(spread_pct, 3),
                "net_spread_pct": round(net_spread, 3),
                "max_size_usd": round(max_trade, 2),
                "net_profit_max": round(net_profit_max, 2),
                "net_profit_100": round(net_profit_100, 2),
                "trades_for_10": trades_for_10,
                "timestamp": time.time(),
            }

            opp["score"] = score_opportunity(opp, config)

            # Only include if actually profitable after costs
            if opp["score"] > 0 and net_profit_100 > 0:
                opportunities.append(opp)

    return sorted(opportunities, key=lambda x: x["score"], reverse=True)
