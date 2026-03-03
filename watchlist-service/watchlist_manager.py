import json
import logging
import os
import time
from typing import Dict, List, Set, Tuple

logger = logging.getLogger("watchlist")


def load_state(path: str) -> Dict:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load state from {path}, returning empty: {e}")
        return {"arb_tokens": [], "rewards_pools": [], "funding_symbols": []}


def save_state(state: Dict, path: str):
    tmp_path = f"{path}.tmp"
    try:
        with open(tmp_path, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp_path, path)
    except Exception as e:
        logger.error(f"Failed to save state to {path}: {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _wrap_entry(entry: Dict, source: str = "static") -> Dict:
    now = time.time()
    defaults = {
        "added_at": now,
        "source": source,
        "last_active_at": now,
        "consecutive_stale_cycles": 0
    }
    for k, v in defaults.items():
        if k not in entry:
            entry[k] = v
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


def should_add_arb(signal, existing_set, state, config):
    address = signal.get("address", "")
    if not address or address in existing_set:
        return False, "duplicate or missing address"
    if len(state["arb_tokens"]) >= config.max_arb_tokens:
        return False, "cap reached"
    if signal.get("liquidity", 0) < config.min_liquidity_arb:
        return False, "low liquidity"
    if signal.get("volume_24h", 0) < config.min_volume_24h:
        return False, "low volume"
    return True, "eligible"


def should_add_rewards(signal, existing_set, state, config):
    address = signal.get("address", "")
    if not address or address in existing_set:
        return False, "duplicate or missing address"
    if len(state["rewards_pools"]) >= config.max_rewards_pools:
        return False, "cap reached"
    if signal.get("liquidity", 0) < config.min_liquidity_rewards:
        return False, "low liquidity"
    if signal.get("volume_24h", 0) < config.min_volume_24h:
        return False, "low volume"
    return True, "eligible"


def should_add_funding(signal, existing_set, state, config):
    token = signal.get("token", "")
    symbol = f"{token}USDT"
    if not symbol or symbol in existing_set:
        return False, "duplicate or missing symbol"
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


def _valid_symbol(s: str) -> bool:
    if not s or not (1 <= len(s) <= 10) or s == "?":
        return False
    return all(c.isalnum() or c in "_-" for c in s)


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
