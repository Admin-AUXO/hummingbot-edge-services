from types import SimpleNamespace
from unittest.mock import patch

from range_calculator import (
    calc_optimal_range, calc_range_utilization, should_rebalance, build_range_payload,
)

CFG = SimpleNamespace(
    regime_multipliers={"SIDEWAYS": 0.5, "BULL": 1.0, "BEAR": 1.0, "SPIKE": 2.5},
    session_multipliers={"US": 0.8, "EU": 0.9, "ASIA": 1.1, "NIGHT": 1.5},
    natr_tight_threshold=0.015,
    natr_wide_threshold=0.035,
)


class TestCalcOptimalRange:
    def test_sideways_us_normal_vol(self):
        lower, upper, eff = calc_optimal_range(100.0, 2.0, "SIDEWAYS", "US", 0.02, CFG)
        assert eff == 0.8
        assert lower < 100.0 < upper
        assert abs(lower - 99.2) < 0.01
        assert abs(upper - 100.8) < 0.01

    def test_spike_night_wide_vol(self):
        lower, upper, eff = calc_optimal_range(100.0, 2.0, "SPIKE", "NIGHT", 0.04, CFG)
        expected = 2.0 * 2.5 * 1.5 * 1.5
        assert eff == 11.25
        assert lower < 89 and upper > 111

    def test_tight_natr(self):
        _, _, eff = calc_optimal_range(100.0, 2.0, "BULL", "EU", 0.01, CFG)
        expected = 2.0 * 1.0 * 0.9 * 0.7
        assert eff == round(expected, 3)

    def test_range_clamped_min(self):
        _, _, eff = calc_optimal_range(100.0, 0.1, "SIDEWAYS", "US", 0.01, CFG)
        assert eff >= 0.5

    def test_range_clamped_max(self):
        _, _, eff = calc_optimal_range(100.0, 10.0, "SPIKE", "NIGHT", 0.05, CFG)
        assert eff <= 15.0

    def test_unknown_regime_session(self):
        lower, upper, eff = calc_optimal_range(100.0, 2.0, "UNKNOWN", "MARS", 0.02, CFG)
        assert eff == 2.0

    def test_zero_natr(self):
        _, _, eff = calc_optimal_range(100.0, 2.0, "BULL", "US", 0, CFG)
        assert eff == 2.0 * 1.0 * 0.8 * 1.0


class TestCalcRangeUtilization:
    def test_centered(self):
        util = calc_range_utilization(100.0, 99.0, 101.0)
        assert util == 100.0

    def test_at_edge(self):
        util = calc_range_utilization(99.0, 99.0, 101.0)
        assert util == 0.0

    def test_outside_range(self):
        assert calc_range_utilization(98.0, 99.0, 101.0) == 0.0
        assert calc_range_utilization(102.0, 99.0, 101.0) == 0.0

    def test_25_percent_from_edge(self):
        util = calc_range_utilization(99.5, 99.0, 101.0)
        assert util == 50.0

    def test_invalid_range(self):
        assert calc_range_utilization(100.0, 101.0, 99.0) == 0.0
        assert calc_range_utilization(100.0, 100.0, 100.0) == 0.0


class TestShouldRebalance:
    def test_below_threshold(self):
        assert should_rebalance(30.0, 70.0) is True

    def test_above_threshold(self):
        assert should_rebalance(85.0, 70.0) is False

    def test_at_threshold(self):
        assert should_rebalance(70.0, 70.0) is False


class TestBuildRangePayload:
    @patch("range_calculator.time.time", return_value=1000000)
    def test_payload(self, _):
        p = build_range_payload(100.0, 99.0, 101.0, 2.0, 95.0, "SIDEWAYS", "US", 0.02, False)
        assert p["price"] == 100.0
        assert p["range_lower"] == 99.0
        assert p["range_upper"] == 101.0
        assert p["range_pct"] == 2.0
        assert p["utilization_pct"] == 95.0
        assert p["should_rebalance"] is False
        assert p["regime"] == "SIDEWAYS"
        assert p["natr"] == 0.02
        assert p["timestamp"] == 1000000
