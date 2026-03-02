import json
import logging
import time

logger = logging.getLogger("watchlist")


def load_state(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {"arb_tokens": [], "rewards_pools": [], "funding_symbols": []}


def save_state(state, path):
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


def _wrap_entry(entry, source="static"):
    entry["added_at"] = entry.get("added_at", time.time())
    entry["source"] = entry.get("source", source)
    entry["last_active_at"] = entry.get("last_active_at", time.time())
    entry["consecutive_stale_cycles"] = entry.get("consecutive_stale_cycles", 0)
    return entry


def seed_state(arb_path, pools_path, symbols_path):
    state = {"arb_tokens": [], "rewards_pools": [], "funding_symbols": []}

    try:
        with open(arb_path, "r") as f:
            for entry in json.load(f):
                state["arb_tokens"].append(_wrap_entry(dict(entry), "static"))
    except Exception:
        pass

    try:
        with open(pools_path, "r") as f:
            for entry in json.load(f):
                state["rewards_pools"].append(_wrap_entry(dict(entry), "static"))
    except Exception:
        pass

    try:
        with open(symbols_path, "r") as f:
            for sym in json.load(f):
                state["funding_symbols"].append(_wrap_entry({"symbol": sym}, "static"))
    except Exception:
        pass

    return state


def should_add_arb(signal, state, config):
    address = signal.get("address", "")
    existing = {e["address"] for e in state["arb_tokens"]}
    if address in existing:
        return False, "duplicate address"
    if len(state["arb_tokens"]) >= config.max_arb_tokens:
        return False, "cap reached"
    if signal.get("liquidity", 0) < config.min_liquidity_arb:
        return False, "low liquidity"
    if signal.get("volume_24h", 0) < config.min_volume_24h:
        return False, "low volume"
    return True, "eligible"


def should_add_rewards(signal, state, config):
    address = signal.get("address", "")
    existing = {e["address"] for e in state["rewards_pools"]}
    if address in existing:
        return False, "duplicate address"
    if len(state["rewards_pools"]) >= config.max_rewards_pools:
        return False, "cap reached"
    if signal.get("liquidity", 0) < config.min_liquidity_rewards:
        return False, "low liquidity"
    if signal.get("volume_24h", 0) < config.min_volume_24h:
        return False, "low volume"
    return True, "eligible"


def should_add_funding(signal, state, config):
    token = signal.get("token", "")
    symbol = f"{token}USDT"
    existing = {e["symbol"] for e in state["funding_symbols"]}
    if symbol in existing:
        return False, "duplicate symbol"
    if len(state["funding_symbols"]) >= config.max_funding_symbols:
        return False, "cap reached"
    return True, "eligible"


def build_arb_entry(signal, source):
    return _wrap_entry({
        "symbol": signal.get("token", signal.get("symbol", "?")),
        "address": signal.get("address", ""),
    }, source)


def build_rewards_entry(signal, source):
    return _wrap_entry({
        "token": signal.get("token", "?"),
        "pair": signal.get("pair", ""),
        "dex": signal.get("dex", ""),
        "address": signal.get("address", ""),
        "reward_token": signal.get("reward_token", ""),
        "reward_apr": signal.get("reward_apr", 0),
        "fee_tier": signal.get("fee_tier", 0),
        "risk_score": signal.get("risk_score", 5),
    }, source)


def build_funding_entry(symbol, source):
    return _wrap_entry({"symbol": symbol}, source)


def check_staleness(entry, market_data, config):
    if entry.get("source") == "static":
        return False
    vol = market_data.get("volume_24h", 0)
    liq = market_data.get("liquidity", 0)
    if vol < config.stale_volume_threshold and liq < config.stale_liquidity_threshold:
        entry["consecutive_stale_cycles"] = entry.get("consecutive_stale_cycles", 0) + 1
    else:
        entry["consecutive_stale_cycles"] = 0
        entry["last_active_at"] = time.time()
    return entry["consecutive_stale_cycles"] >= config.stale_cycles_threshold


def prune_stale(entries, stale_ids):
    kept = [e for e in entries if id(e) not in stale_ids]
    removed = [e for e in entries if id(e) in stale_ids]
    return kept, removed


def to_arb_json(entries):
    return [{"symbol": e["symbol"], "address": e["address"]} for e in entries]


def to_rewards_json(entries):
    fields = ["token", "pair", "dex", "address", "reward_token", "reward_apr", "fee_tier", "risk_score"]
    return [{k: e.get(k) for k in fields} for e in entries]


def to_funding_json(entries):
    return [e["symbol"] for e in entries]


def _valid_symbol(s):
    if not s or len(s) > 10 or s == "?":
        return False
    return s.isalnum() or all(c.isalnum() or c in ("_", "-") for c in s)


def parse_boost_signals(data):
    signals = []
    for item in data if isinstance(data, list) else []:
        chain = item.get("chainId", "")
        if chain != "solana":
            continue
        addr = item.get("tokenAddress", "")
        desc = item.get("description", "")
        symbol = item.get("symbol", desc.split()[0] if desc else "?")
        if addr and _valid_symbol(symbol):
            signals.append({"token": symbol, "address": addr, "source": "dex_boost"})
    return signals


def parse_profile_signals(data):
    signals = []
    for item in data if isinstance(data, list) else []:
        chain = item.get("chainId", "")
        if chain != "solana":
            continue
        addr = item.get("tokenAddress", "")
        symbol = item.get("symbol", item.get("name", "?"))
        if addr and _valid_symbol(symbol):
            signals.append({"token": symbol, "address": addr, "source": "dex_profile"})
    return signals
