import json
import logging
import os
import time
from typing import Dict, List

from shared.utils import chain_address_key, normalize_chain_id

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
        "consecutive_stale_cycles": 0,
        "chainId": normalize_chain_id(entry.get("chainId") or entry.get("chain_id") or entry.get("chain") or "solana"),
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
    chain_id = normalize_chain_id(signal.get("chainId"))
    key = chain_address_key(chain_id, address)
    if not address or key in existing_set:
        return False, "duplicate or missing address"
    if len(state["arb_tokens"]) >= config.max_arb_tokens:
        return False, "cap reached"
    if signal.get("liquidity", 0) < config.min_liquidity_arb:
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
        "chainId": normalize_chain_id(signal.get("chainId")),
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
    output = []
    for entry in entries:
        chain_id = normalize_chain_id(entry.get("chainId"))
        item = {"symbol": entry["symbol"], "address": entry["address"], "chainId": chain_id}
        output.append(item)
    return output


def to_rewards_json(entries):
    fields = ["token", "pair", "dex", "address", "chainId", "reward_token", "reward_apr", "fee_tier", "risk_score"]
    output = []
    for entry in entries:
        row = {k: entry.get(k) for k in fields}
        row["chainId"] = normalize_chain_id(row.get("chainId"))
        output.append(row)
    return output


def to_funding_json(entries):
    return [e["symbol"] for e in entries]


def _valid_symbol(s: str) -> bool:
    if not s or not (1 <= len(s) <= 10) or s == "?":
        return False
    return all(c.isalnum() or c in "_-" for c in s)


def parse_boost_signals(data, supported_chains=None):
    supported = {normalize_chain_id(chain) for chain in (supported_chains or ["solana"])}
    signals = []
    for item in data if isinstance(data, list) else []:
        chain = normalize_chain_id(item.get("chainId", ""))
        if chain not in supported:
            continue
        addr = item.get("tokenAddress", "")
        desc = item.get("description", "")
        symbol = item.get("symbol", desc.split()[0] if desc else "?")
        if addr and _valid_symbol(symbol):
            signals.append({"token": symbol, "address": addr, "chainId": chain, "source": "dex_boost"})
    return signals


def parse_profile_signals(data, supported_chains=None):
    supported = {normalize_chain_id(chain) for chain in (supported_chains or ["solana"])}
    signals = []
    for item in data if isinstance(data, list) else []:
        chain = normalize_chain_id(item.get("chainId", ""))
        if chain not in supported:
            continue
        addr = item.get("tokenAddress", "")
        symbol = item.get("symbol", item.get("name", "?"))
        if addr and _valid_symbol(symbol):
            signals.append({"token": symbol, "address": addr, "chainId": chain, "source": "dex_profile"})
    return signals
