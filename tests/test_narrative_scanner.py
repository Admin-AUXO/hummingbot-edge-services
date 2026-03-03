from types import SimpleNamespace
from unittest.mock import patch

from narrative_scanner import score_narrative_token, filter_spiking_tokens

CFG = SimpleNamespace(
    min_volume_24h=50000.0,
    min_volume_spike=2.0,
    min_price_change_1h=1.0,
    min_liquidity=20000.0,
)


def _pair(volume_24h=100000, liquidity=50000, price=1.5,
          pc_5m=2.0, pc_1h=5.0, pc_24h=15.0):
    return {
        "volume": {"h24": volume_24h},
        "liquidity": {"usd": liquidity},
        "priceUsd": price,
        "priceChange": {"m5": pc_5m, "h1": pc_1h, "h24": pc_24h},
        "baseToken": {"symbol": "TEST", "address": "0xtest"},
        "pairAddress": "0xpair",
        "dexId": "raydium",
    }


class TestScoreNarrativeToken:
    @patch("narrative_scanner.time.time", return_value=1000000)
    def test_basic(self, _):
        result = score_narrative_token(_pair(), 50000, CFG)
        assert result is not None
        assert result["token"] == "TEST"
        assert result["volume_24h"] == 100000
        assert result["volume_spike"] == 2.0
        assert result["price_change_5m"] == 2.0

    def test_low_volume_returns_none(self):
        assert score_narrative_token(_pair(volume_24h=1000), 500, CFG) is None

    def test_low_liquidity_returns_none(self):
        assert score_narrative_token(_pair(liquidity=100), 50000, CFG) is None

    @patch("narrative_scanner.time.time", return_value=1000000)
    def test_zero_prev_volume(self, _):
        result = score_narrative_token(_pair(), 0, CFG)
        assert result is not None
        assert result["volume_spike"] == 0

    @patch("narrative_scanner.time.time", return_value=1000000)
    def test_spike_calculation(self, _):
        result = score_narrative_token(_pair(volume_24h=300000), 100000, CFG)
        assert result["volume_spike"] == 3.0


class TestFilterSpikingTokens:
    def test_filters_above_threshold(self):
        tokens = [
            {"volume_spike": 3.0, "token": "A", "price_change_5m": 1.0, "price_change_1h": 3.0},
            {"volume_spike": 1.5, "token": "B", "price_change_5m": 1.0, "price_change_1h": 3.0},
            {"volume_spike": 2.5, "token": "C", "price_change_5m": 1.0, "price_change_1h": 3.0},
        ]
        result = filter_spiking_tokens(tokens, CFG)
        assert len(result) == 2
        assert all(t["volume_spike"] >= 2.0 for t in result)

    def test_empty(self):
        assert filter_spiking_tokens([], CFG) == []

    def test_none_pass(self):
        tokens = [
            {"volume_spike": 0.5, "price_change_5m": 1.0, "price_change_1h": 3.0},
            {"volume_spike": 1.0, "price_change_5m": 1.0, "price_change_1h": 3.0},
        ]
        assert filter_spiking_tokens(tokens, CFG) == []

    def test_exact_threshold(self):
        tokens = [{"volume_spike": 2.0, "price_change_5m": 1.0, "price_change_1h": 3.0}]
        assert len(filter_spiking_tokens(tokens, CFG)) == 1
