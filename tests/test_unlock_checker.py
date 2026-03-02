import time
from types import SimpleNamespace
from unittest.mock import patch

from unlock_checker import (
    parse_unlock_time, classify_unlock, build_pre_unlock_payload,
    build_post_unlock_payload, _base_unlock_payload,
    PRE_UNLOCK, POST_UNLOCK, UPCOMING, EXPIRED, INSIGNIFICANT,
)

CFG = SimpleNamespace(
    min_unlock_pct=2.0,
    pre_unlock_hours=24,
    post_unlock_hours=48,
    pre_unlock_buy_spread_mult=1.5,
    pre_unlock_sell_spread_mult=0.8,
    post_unlock_buy_spread_mult=0.8,
    post_unlock_sell_spread_mult=1.0,
)


class TestParseUnlockTime:
    def test_valid_utc(self):
        ts = parse_unlock_time({"unlock_time": "2026-03-07T12:00:00Z"})
        assert ts > 0

    def test_valid_offset(self):
        ts = parse_unlock_time({"unlock_time": "2026-03-07T12:00:00+00:00"})
        assert ts > 0

    def test_invalid(self):
        assert parse_unlock_time({"unlock_time": "not-a-date"}) == 0.0

    def test_missing(self):
        assert parse_unlock_time({}) == 0.0


class TestClassifyUnlock:
    def test_insignificant(self):
        status, hours = classify_unlock({"unlock_pct": 1.0}, CFG)
        assert status == INSIGNIFICANT
        assert hours == 0

    def test_pre_unlock(self):
        future_time = time.time() + 10 * 3600
        from datetime import datetime, timezone
        iso = datetime.fromtimestamp(future_time, tz=timezone.utc).isoformat()
        unlock = {"unlock_pct": 5.0, "unlock_time": iso}
        status, hours = classify_unlock(unlock, CFG)
        assert status == PRE_UNLOCK
        assert 9 < hours < 11

    def test_post_unlock(self):
        past_time = time.time() - 10 * 3600
        from datetime import datetime, timezone
        iso = datetime.fromtimestamp(past_time, tz=timezone.utc).isoformat()
        unlock = {"unlock_pct": 5.0, "unlock_time": iso}
        status, hours = classify_unlock(unlock, CFG)
        assert status == POST_UNLOCK
        assert 9 < hours < 11

    def test_upcoming(self):
        future_time = time.time() + 48 * 3600
        from datetime import datetime, timezone
        iso = datetime.fromtimestamp(future_time, tz=timezone.utc).isoformat()
        unlock = {"unlock_pct": 5.0, "unlock_time": iso}
        status, hours = classify_unlock(unlock, CFG)
        assert status == UPCOMING

    def test_expired(self):
        past_time = time.time() - 72 * 3600
        from datetime import datetime, timezone
        iso = datetime.fromtimestamp(past_time, tz=timezone.utc).isoformat()
        unlock = {"unlock_pct": 5.0, "unlock_time": iso}
        status, hours = classify_unlock(unlock, CFG)
        assert status == EXPIRED

    def test_bad_time_expired(self):
        unlock = {"unlock_pct": 5.0, "unlock_time": "garbage"}
        status, _ = classify_unlock(unlock, CFG)
        assert status == EXPIRED


class TestPayloads:
    @patch("unlock_checker.time.time", return_value=1000000)
    def test_base_payload(self, _):
        unlock = {"token": "JTO", "pair": "JTO_USDC", "unlock_pct": 5.2,
                  "unlock_amount": "24M JTO", "source": "tokenunlocks.app"}
        p = _base_unlock_payload(unlock)
        assert p["token"] == "JTO"
        assert p["unlock_pct"] == 5.2
        assert p["timestamp"] == 1000000

    @patch("unlock_checker.time.time", return_value=1000000)
    def test_pre_unlock_payload(self, _):
        unlock = {"token": "JTO", "pair": "JTO_USDC", "unlock_pct": 5.2}
        p = build_pre_unlock_payload(unlock, 12.5, CFG)
        assert p["status"] == PRE_UNLOCK
        assert p["hours_until_unlock"] == 12.5
        assert p["buy_spread_mult"] == 1.5
        assert p["sell_spread_mult"] == 0.8

    @patch("unlock_checker.time.time", return_value=1000000)
    def test_post_unlock_payload(self, _):
        unlock = {"token": "JTO", "pair": "JTO_USDC", "unlock_pct": 5.2}
        p = build_post_unlock_payload(unlock, 6.0, CFG)
        assert p["status"] == POST_UNLOCK
        assert p["hours_since_unlock"] == 6.0
        assert p["buy_spread_mult"] == 0.8
        assert p["sell_spread_mult"] == 1.0
