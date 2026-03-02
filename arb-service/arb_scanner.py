import time


def group_pairs_by_dex(pairs, min_liquidity):
    by_dex = {}
    for pair in pairs:
        liq = float(pair.get("liquidity", {}).get("usd", 0))
        if liq < min_liquidity:
            continue
        dex = pair.get("dexId", "unknown")
        price = float(pair.get("priceUsd", 0))
        if price <= 0:
            continue
        if dex not in by_dex or liq > by_dex[dex]["liquidity"]:
            by_dex[dex] = {
                "dex": dex,
                "price": price,
                "liquidity": liq,
                "pair_address": pair.get("pairAddress", ""),
                "volume_24h": float(pair.get("volume", {}).get("h24", 0)),
            }
    return by_dex


def find_arb_opportunities(token_symbol, pairs, config):
    by_dex = group_pairs_by_dex(pairs, config.min_liquidity)
    if len(by_dex) < config.min_dex_count:
        return []

    dex_list = list(by_dex.values())
    opportunities = []

    for i in range(len(dex_list)):
        for j in range(i + 1, len(dex_list)):
            a, b = dex_list[i], dex_list[j]
            mid = (a["price"] + b["price"]) / 2
            spread_pct = abs(a["price"] - b["price"]) / mid * 100

            if spread_pct >= config.min_arb_pct:
                buy_side = a if a["price"] < b["price"] else b
                sell_side = b if a["price"] < b["price"] else a
                opportunities.append({
                    "token": token_symbol,
                    "buy_dex": buy_side["dex"],
                    "buy_price": buy_side["price"],
                    "buy_pair": buy_side["pair_address"],
                    "sell_dex": sell_side["dex"],
                    "sell_price": sell_side["price"],
                    "sell_pair": sell_side["pair_address"],
                    "spread_pct": round(spread_pct, 3),
                    "max_size_usd": min(buy_side["liquidity"], sell_side["liquidity"]) * 0.02,
                    "timestamp": time.time(),
                })

    return sorted(opportunities, key=lambda x: x["spread_pct"], reverse=True)
