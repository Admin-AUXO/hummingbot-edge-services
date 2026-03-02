import json
import os
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch

from watchlist_manager import (
    build_arb_entry,
    build_funding_entry,
    build_rewards_entry,
    check_staleness,
    load_state,
    parse_boost_signals,
    parse_profile_signals,
    prune_stale,
    save_state,
    seed_state,
    should_add_arb,
    should_add_funding,
    should_add_rewards,
    to_arb_json,
    to_funding_json,
    to_rewards_json,
)

CFG = SimpleNamespace(
    max_arb_tokens=40,
    max_rewards_pools=20,
    max_funding_symbols=20,
    min_liquidity_arb=50000,
    min_liquidity_rewards=100000,
    min_volume_24h=100000,
    stale_cycles_threshold=3,
    stale_volume_threshold=10000,
    stale_liquidity_threshold=5000,
)


def _state(arb=None, rewards=None, funding=None):
    return {
        "arb_tokens": arb or [],
        "rewards_pools": rewards or [],
        "funding_symbols": funding or [],
    }


def _signal(token="TEST", address="0xtest", liquidity=60000, volume_24h=150000, **kw):
    d = {"token": token, "address": address, "liquidity": liquidity, "volume_24h": volume_24h}
    d.update(kw)
    return d


class TestLoadSaveState:
    def test_load_missing_file(self):
        s = load_state("/nonexistent/path.json")
        assert s == {"arb_tokens": [], "rewards_pools": [], "funding_symbols": []}

    def test_round_trip(self):
        state = _state(arb=[{"symbol": "SOL", "address": "0x1"}])
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
        try:
            save_state(state, path)
            loaded = load_state(path)
            assert loaded["arb_tokens"][0]["symbol"] == "SOL"
        finally:
            os.unlink(path)


class TestSeedState:
    def test_seeds_from_files(self):
        with tempfile.TemporaryDirectory() as td:
            arb_path = os.path.join(td, "tokens.json")
            pools_path = os.path.join(td, "pools.json")
            symbols_path = os.path.join(td, "symbols.json")

            with open(arb_path, "w") as f:
                json.dump([{"symbol": "SOL", "address": "0x1"}], f)
            with open(pools_path, "w") as f:
                json.dump([{"token": "JUP", "pair": "JUP/USDC", "dex": "raydium", "address": "0x2"}], f)
            with open(symbols_path, "w") as f:
                json.dump(["SOLUSDT", "JUPUSDT"], f)

            state = seed_state(arb_path, pools_path, symbols_path)
            assert len(state["arb_tokens"]) == 1
            assert state["arb_tokens"][0]["source"] == "static"
            assert state["arb_tokens"][0]["consecutive_stale_cycles"] == 0
            assert len(state["rewards_pools"]) == 1
            assert len(state["funding_symbols"]) == 2
            assert state["funding_symbols"][0]["symbol"] == "SOLUSDT"

    def test_handles_missing_files(self):
        state = seed_state("/no/arb.json", "/no/pools.json", "/no/sym.json")
        assert state == _state()


class TestShouldAddArb:
    def test_eligible(self):
        ok, reason = should_add_arb(_signal(), _state(), CFG)
        assert ok is True

    def test_duplicate(self):
        state = _state(arb=[{"address": "0xtest"}])
        ok, reason = should_add_arb(_signal(), state, CFG)
        assert ok is False
        assert "duplicate" in reason

    def test_cap_reached(self):
        state = _state(arb=[{"address": f"0x{i}"} for i in range(40)])
        ok, reason = should_add_arb(_signal(), state, CFG)
        assert ok is False
        assert "cap" in reason

    def test_low_liquidity(self):
        ok, reason = should_add_arb(_signal(liquidity=1000), _state(), CFG)
        assert ok is False
        assert "liquidity" in reason

    def test_low_volume(self):
        ok, reason = should_add_arb(_signal(volume_24h=500), _state(), CFG)
        assert ok is False
        assert "volume" in reason


class TestShouldAddRewards:
    def test_eligible(self):
        ok, _ = should_add_rewards(_signal(liquidity=200000), _state(), CFG)
        assert ok is True

    def test_low_liquidity(self):
        ok, reason = should_add_rewards(_signal(liquidity=50000), _state(), CFG)
        assert ok is False
        assert "liquidity" in reason

    def test_duplicate(self):
        state = _state(rewards=[{"address": "0xtest"}])
        ok, _ = should_add_rewards(_signal(), state, CFG)
        assert ok is False


class TestShouldAddFunding:
    def test_eligible(self):
        ok, _ = should_add_funding(_signal(), _state(), CFG)
        assert ok is True

    def test_duplicate(self):
        state = _state(funding=[{"symbol": "TESTUSDT"}])
        ok, reason = should_add_funding(_signal(), state, CFG)
        assert ok is False
        assert "duplicate" in reason

    def test_cap_reached(self):
        state = _state(funding=[{"symbol": f"T{i}USDT"} for i in range(20)])
        ok, _ = should_add_funding(_signal(), state, CFG)
        assert ok is False


class TestEntryBuilders:
    @patch("watchlist_manager.time.time", return_value=1000000)
    def test_build_arb_entry(self, _):
        entry = build_arb_entry({"token": "SOL", "address": "0x1"}, "alpha")
        assert entry["symbol"] == "SOL"
        assert entry["address"] == "0x1"
        assert entry["source"] == "alpha"
        assert entry["added_at"] == 1000000
        assert entry["consecutive_stale_cycles"] == 0

    @patch("watchlist_manager.time.time", return_value=1000000)
    def test_build_rewards_entry(self, _):
        signal = {"token": "JUP", "pair": "JUP/USDC", "dex": "raydium", "address": "0x2",
                  "reward_token": "RAY", "reward_apr": 15.0, "fee_tier": 0.25, "risk_score": 3}
        entry = build_rewards_entry(signal, "narrative")
        assert entry["token"] == "JUP"
        assert entry["source"] == "narrative"
        assert entry["reward_apr"] == 15.0

    @patch("watchlist_manager.time.time", return_value=1000000)
    def test_build_funding_entry(self, _):
        entry = build_funding_entry("SOLUSDT", "alpha")
        assert entry["symbol"] == "SOLUSDT"
        assert entry["source"] == "alpha"


class TestStaleness:
    def test_static_never_stale(self):
        entry = {"source": "static", "consecutive_stale_cycles": 0}
        assert check_staleness(entry, {"volume_24h": 0, "liquidity": 0}, CFG) is False

    def test_healthy_resets_counter(self):
        entry = {"source": "alpha", "consecutive_stale_cycles": 2}
        result = check_staleness(entry, {"volume_24h": 200000, "liquidity": 100000}, CFG)
        assert result is False
        assert entry["consecutive_stale_cycles"] == 0

    def test_stale_increments(self):
        entry = {"source": "alpha", "consecutive_stale_cycles": 0}
        check_staleness(entry, {"volume_24h": 100, "liquidity": 100}, CFG)
        assert entry["consecutive_stale_cycles"] == 1

    def test_stale_after_threshold(self):
        entry = {"source": "alpha", "consecutive_stale_cycles": 2}
        result = check_staleness(entry, {"volume_24h": 100, "liquidity": 100}, CFG)
        assert result is True
        assert entry["consecutive_stale_cycles"] == 3

    def test_prune_stale(self):
        entries = [{"symbol": "A"}, {"symbol": "B"}, {"symbol": "C"}]
        stale_ids = {id(entries[1])}
        kept, removed = prune_stale(entries, stale_ids)
        assert len(kept) == 2
        assert len(removed) == 1
        assert removed[0]["symbol"] == "B"


class TestJsonSerializers:
    def test_to_arb_json(self):
        entries = [{"symbol": "SOL", "address": "0x1", "source": "static", "added_at": 123}]
        result = to_arb_json(entries)
        assert result == [{"symbol": "SOL", "address": "0x1"}]

    def test_to_rewards_json(self):
        entries = [{"token": "JUP", "pair": "JUP/USDC", "dex": "raydium", "address": "0x2",
                    "reward_token": "RAY", "reward_apr": 15.0, "fee_tier": 0.25, "risk_score": 3,
                    "source": "static", "added_at": 123}]
        result = to_rewards_json(entries)
        assert len(result) == 1
        assert "source" not in result[0]
        assert result[0]["token"] == "JUP"

    def test_to_funding_json(self):
        entries = [{"symbol": "SOLUSDT", "source": "alpha"}, {"symbol": "JUPUSDT", "source": "static"}]
        result = to_funding_json(entries)
        assert result == ["SOLUSDT", "JUPUSDT"]


class TestTrendingParsers:
    def test_parse_boost_signals_filters_solana(self):
        data = [
            {"chainId": "solana", "tokenAddress": "0x1", "symbol": "SOL"},
            {"chainId": "ethereum", "tokenAddress": "0x2", "symbol": "ETH"},
            {"chainId": "solana", "tokenAddress": "0x3", "description": "WIF token"},
        ]
        result = parse_boost_signals(data)
        assert len(result) == 2
        assert result[0]["token"] == "SOL"
        assert result[0]["source"] == "dex_boost"
        assert result[1]["address"] == "0x3"

    def test_parse_boost_signals_non_list(self):
        assert parse_boost_signals({}) == []
        assert parse_boost_signals(None) == []

    def test_parse_profile_signals(self):
        data = [
            {"chainId": "solana", "tokenAddress": "0x1", "symbol": "JUP"},
            {"chainId": "bsc", "tokenAddress": "0x2", "symbol": "BNB"},
        ]
        result = parse_profile_signals(data)
        assert len(result) == 1
        assert result[0]["source"] == "dex_profile"

    def test_parse_profile_skips_no_address(self):
        data = [{"chainId": "solana", "symbol": "NOADDR"}]
        assert parse_profile_signals(data) == []

    def test_parse_boost_rejects_bad_symbols(self):
        data = [
            {"chainId": "solana", "tokenAddress": "0x1", "symbol": "Oil's"},
            {"chainId": "solana", "tokenAddress": "0x2", "symbol": "Swarm-based token"},
            {"chainId": "solana", "tokenAddress": "0x3", "symbol": ""},
            {"chainId": "solana", "tokenAddress": "0x4", "symbol": "GOOD"},
            {"chainId": "solana", "tokenAddress": "0x5", "description": "it's a token"},
        ]
        result = parse_boost_signals(data)
        assert len(result) == 1
        assert result[0]["token"] == "GOOD"

    def test_parse_profile_rejects_bad_symbols(self):
        data = [
            {"chainId": "solana", "tokenAddress": "0x1", "symbol": "has space"},
            {"chainId": "solana", "tokenAddress": "0x2", "symbol": "VERYLONGSYMBOLNAME"},
            {"chainId": "solana", "tokenAddress": "0x3", "symbol": "OK-1"},
        ]
        result = parse_profile_signals(data)
        assert len(result) == 1
        assert result[0]["token"] == "OK-1"
