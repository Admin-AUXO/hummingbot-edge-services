import time
from types import SimpleNamespace
from unittest.mock import patch

from scorer import score_token, is_new_listing, _base_payload, build_signal_payload, build_new_listing_payload

CFG = SimpleNamespace(
    vol_mcap_threshold=0.5,
    h1_vol_ratio_threshold=0.20,
    buy_sell_ratio_threshold=1.5,
    min_liquidity=50000.0,
    new_listing_max_age_hours=48,
)


def _pair(volume_24h=100000, volume_1h=25000, mcap=200000, buys=200, sells=100,
          liquidity=60000, socials=True, created_ms=None, price=1.5):
    p = {
        "volume": {"h24": volume_24h, "h1": volume_1h},
        "marketCap": mcap,
        "txns": {"h24": {"buys": buys, "sells": sells}},
        "liquidity": {"usd": liquidity},
        "priceUsd": price,
        "baseToken": {"symbol": "TEST", "address": "0xabc"},
        "pairAddress": "0xpair",
        "dexId": "raydium",
    }
    if socials:
        p["info"] = {"socials": ["twitter"], "websites": ["https://test.com"]}
    if created_ms is not None:
        p["pairCreatedAt"] = created_ms
    return p


class TestScoreToken:
    def test_max_score(self):
        pair = _pair(volume_24h=200000, volume_1h=50000, mcap=200000,
                     buys=300, sells=100, liquidity=60000, socials=True)
        score, bd = score_token(pair, CFG)
        assert score == 9  # no priceChange data in test pair = flat momentum (+0)

    def test_zero_score(self):
        pair = _pair(volume_24h=100, volume_1h=1, mcap=1000000,
                     buys=10, sells=100, liquidity=100, socials=False)
        score, bd = score_token(pair, CFG)
        assert score == 0

    def test_vol_mcap_criterion(self):
        pair_high = _pair(volume_24h=600000, mcap=1000000)
        pair_low = _pair(volume_24h=100, mcap=1000000)
        s1, _ = score_token(pair_high, CFG)
        s2, _ = score_token(pair_low, CFG)
        assert s1 > s2

    def test_h1_ratio_criterion(self):
        pair = _pair(volume_24h=100000, volume_1h=30000)
        score, bd = score_token(pair, CFG)
        assert "h1_vol_ratio" in bd
        assert "30.00%" in bd["h1_vol_ratio"]

    def test_buy_sell_zero_sells(self):
        pair = _pair(buys=100, sells=0)
        score, bd = score_token(pair, CFG)
        assert "0.00" in bd["buy_sell_ratio"]

    def test_zero_mcap_no_crash(self):
        pair = _pair(mcap=0)
        pair["fdv"] = 0
        score, bd = score_token(pair, CFG)
        assert "vol_mcap" in bd

    def test_breakdown_keys(self):
        _, bd = score_token(_pair(), CFG)
        expected = {"vol_mcap", "h1_vol_ratio", "buy_sell_ratio", "liquidity", "socials", "momentum", "est_profit_pct"}
        assert set(bd.keys()) == expected


class TestIsNewListing:
    def test_new_listing_true(self):
        now_ms = time.time() * 1000
        pair = _pair(created_ms=now_ms - 3600 * 1000, liquidity=60000)
        assert is_new_listing(pair, CFG) is True

    def test_old_listing_false(self):
        now_ms = time.time() * 1000
        pair = _pair(created_ms=now_ms - 72 * 3600 * 1000, liquidity=60000)
        assert is_new_listing(pair, CFG) is False

    def test_low_liquidity_false(self):
        now_ms = time.time() * 1000
        pair = _pair(created_ms=now_ms - 3600 * 1000, liquidity=1000)
        assert is_new_listing(pair, CFG) is False

    def test_no_created_at(self):
        pair = _pair()
        assert is_new_listing(pair, CFG) is False


class TestPayloads:
    @patch("scorer.time.time", return_value=1000000)
    def test_base_payload(self, _):
        pair = _pair(price=2.5, volume_24h=50000, liquidity=80000)
        p = _base_payload(pair)
        assert p["token"] == "TEST"
        assert p["price"] == 2.5
        assert p["timestamp"] == 1000000

    @patch("scorer.time.time", return_value=1000000)
    def test_signal_payload(self, _):
        pair = _pair(mcap=500000)
        p = build_signal_payload(pair, 8, {"vol_mcap": "high"})
        assert p["score"] == 8
        assert p["mcap"] == 500000
        assert p["breakdown"] == {"vol_mcap": "high"}

    @patch("scorer.time.time", return_value=1000000)
    def test_new_listing_payload(self, _):
        now_ms = 1000000 * 1000
        pair = _pair(created_ms=now_ms - 3600 * 1000)
        p = build_new_listing_payload(pair)
        assert p["age_hours"] == 1.0
        assert p["token"] == "TEST"
