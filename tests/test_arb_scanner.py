from types import SimpleNamespace
from unittest.mock import patch

from arb_scanner import group_pairs_by_dex, find_arb_opportunities

CFG = SimpleNamespace(
    min_arb_pct=0.5,
    min_liquidity=5000.0,
    min_dex_count=2,
)


def _pair(dex="raydium", price=100.0, liquidity=50000, volume=10000, pair_addr="0xpair"):
    return {
        "dexId": dex,
        "priceUsd": price,
        "liquidity": {"usd": liquidity},
        "volume": {"h24": volume},
        "pairAddress": pair_addr,
    }


class TestGroupPairsByDex:
    def test_basic_grouping(self):
        pairs = [_pair("raydium", 100, 50000), _pair("orca", 101, 30000)]
        result = group_pairs_by_dex(pairs, 5000)
        assert "raydium" in result
        assert "orca" in result
        assert result["raydium"]["price"] == 100
        assert result["orca"]["price"] == 101

    def test_keeps_best_liquidity(self):
        pairs = [
            _pair("raydium", 100, 50000, pair_addr="0x1"),
            _pair("raydium", 101, 80000, pair_addr="0x2"),
        ]
        result = group_pairs_by_dex(pairs, 5000)
        assert result["raydium"]["liquidity"] == 80000
        assert result["raydium"]["pair_address"] == "0x2"

    def test_filters_low_liquidity(self):
        pairs = [_pair("raydium", 100, 100)]
        result = group_pairs_by_dex(pairs, 5000)
        assert len(result) == 0

    def test_filters_zero_price(self):
        pairs = [_pair("raydium", 0, 50000)]
        result = group_pairs_by_dex(pairs, 5000)
        assert len(result) == 0

    def test_empty(self):
        assert group_pairs_by_dex([], 5000) == {}


class TestFindArbOpportunities:
    @patch("arb_scanner.time.time", return_value=1000000)
    def test_finds_opportunity(self, _):
        pairs = [_pair("raydium", 100.0, 50000), _pair("orca", 101.0, 40000)]
        opps = find_arb_opportunities("SOL", pairs, CFG)
        assert len(opps) == 1
        assert opps[0]["token"] == "SOL"
        assert opps[0]["buy_dex"] == "raydium"
        assert opps[0]["sell_dex"] == "orca"
        assert opps[0]["spread_pct"] > 0.5

    def test_below_min_spread(self):
        pairs = [_pair("raydium", 100.0, 50000), _pair("orca", 100.1, 40000)]
        opps = find_arb_opportunities("SOL", pairs, CFG)
        assert len(opps) == 0

    def test_insufficient_dexes(self):
        pairs = [_pair("raydium", 100.0, 50000)]
        opps = find_arb_opportunities("SOL", pairs, CFG)
        assert len(opps) == 0

    @patch("arb_scanner.time.time", return_value=1000000)
    def test_max_size(self, _):
        pairs = [_pair("raydium", 100.0, 50000), _pair("orca", 102.0, 20000)]
        opps = find_arb_opportunities("SOL", pairs, CFG)
        assert opps[0]["max_size_usd"] == 20000 * 0.02

    @patch("arb_scanner.time.time", return_value=1000000)
    def test_three_dexes(self, _):
        pairs = [
            _pair("raydium", 100.0, 50000),
            _pair("orca", 102.0, 40000),
            _pair("meteora", 103.0, 30000),
        ]
        opps = find_arb_opportunities("SOL", pairs, CFG)
        assert len(opps) == 3
        assert opps[0]["spread_pct"] > opps[1]["spread_pct"]

    def test_empty_pairs(self):
        assert find_arb_opportunities("SOL", [], CFG) == []
