from unittest.mock import patch

from reward_calculator import (
    estimate_fee_apr, calc_effective_apr, calc_risk_adjusted_apr,
    build_pool_payload, rank_pools,
)


class TestEstimateFeeApr:
    def test_basic(self):
        apr = estimate_fee_apr(volume_24h=100000, liquidity=500000, fee_tier_pct=0.25)
        assert apr == 18.25

    def test_zero_liquidity(self):
        assert estimate_fee_apr(100000, 0, 0.25) == 0.0

    def test_negative_liquidity(self):
        assert estimate_fee_apr(100000, -1, 0.25) == 0.0

    def test_zero_volume(self):
        assert estimate_fee_apr(0, 500000, 0.25) == 0.0

    def test_high_fee_tier(self):
        apr = estimate_fee_apr(100000, 100000, 1.0)
        assert apr == 365.0


class TestCalcEffectiveApr:
    def test_basic(self):
        assert calc_effective_apr(18.25, 15.0) == 33.25

    def test_zero_reward(self):
        assert calc_effective_apr(18.25, 0) == 18.25

    def test_zero_fee(self):
        assert calc_effective_apr(0, 25.0) == 25.0


class TestCalcRiskAdjustedApr:
    def test_risk_2(self):
        result = calc_risk_adjusted_apr(33.25, 2)
        assert result == 27.71

    def test_risk_0(self):
        assert calc_risk_adjusted_apr(33.25, 0) == 33.25

    def test_negative_risk(self):
        assert calc_risk_adjusted_apr(33.25, -1) == 33.25

    def test_high_risk(self):
        result = calc_risk_adjusted_apr(100.0, 10)
        assert result == 50.0


class TestBuildPoolPayload:
    @patch("reward_calculator.time.time", return_value=1000000)
    def test_payload_fields(self, _):
        pool = {"token": "SOL", "pair": "SOL/USDC", "dex": "raydium",
                "reward_apr": 15.0, "reward_token": "RAY", "risk_score": 2}
        p = build_pool_payload(pool, 18.25, 33.25, 27.71, 100000, 500000)
        assert p["token"] == "SOL"
        assert p["fee_apr"] == 18.25
        assert p["effective_apr"] == 33.25
        assert p["risk_adjusted_apr"] == 27.71
        assert p["volume_24h"] == 100000
        assert p["liquidity"] == 500000
        assert p["reward_token"] == "RAY"
        assert p["timestamp"] == 1000000

    @patch("reward_calculator.time.time", return_value=1000000)
    def test_defaults(self, _):
        p = build_pool_payload({}, 0, 0, 0, 0, 0)
        assert p["token"] == "?"
        assert p["risk_score"] == 5


class TestRankPools:
    def test_ranking_order(self):
        pools = [
            {"risk_adjusted_apr": 10},
            {"risk_adjusted_apr": 50},
            {"risk_adjusted_apr": 30},
        ]
        ranked = rank_pools(pools)
        assert ranked[0]["risk_adjusted_apr"] == 50
        assert ranked[1]["risk_adjusted_apr"] == 30
        assert ranked[2]["risk_adjusted_apr"] == 10

    def test_empty(self):
        assert rank_pools([]) == []

    def test_single(self):
        pools = [{"risk_adjusted_apr": 25}]
        assert rank_pools(pools) == pools
