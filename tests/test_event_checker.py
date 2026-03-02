import time
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from event_checker import (
    parse_event_time, classify_event, detect_new_pools, build_event_payload,
    UPCOMING, ACTIVE, POST_EVENT, EXPIRED,
)

CFG = SimpleNamespace(
    pre_event_hours=24,
    post_event_hours=48,
    new_pool_max_age_minutes=60,
    new_pool_min_liquidity=5000.0,
    new_pool_min_volume=1000.0,
)


def _iso(offset_hours):
    ts = time.time() + offset_hours * 3600
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


class TestParseEventTime:
    def test_valid(self):
        ts = parse_event_time({"event_time": "2026-06-01T00:00:00Z"})
        assert ts > 0

    def test_invalid(self):
        assert parse_event_time({"event_time": "nope"}) == 0.0

    def test_missing(self):
        assert parse_event_time({}) == 0.0


class TestClassifyEvent:
    def test_upcoming(self):
        event = {"event_time": _iso(48)}
        status, hours = classify_event(event, CFG)
        assert status == UPCOMING
        assert hours > 24

    def test_active(self):
        event = {"event_time": _iso(10)}
        status, hours = classify_event(event, CFG)
        assert status == ACTIVE
        assert 9 < hours < 11

    def test_post_event(self):
        event = {"event_time": _iso(-10)}
        status, hours = classify_event(event, CFG)
        assert status == POST_EVENT
        assert 9 < hours < 11

    def test_expired(self):
        event = {"event_time": _iso(-72)}
        status, _ = classify_event(event, CFG)
        assert status == EXPIRED

    def test_bad_time(self):
        event = {"event_time": "bad"}
        status, _ = classify_event(event, CFG)
        assert status == EXPIRED


def _pair(age_minutes=30, liquidity=10000, volume=5000, token="TEST"):
    now_ms = time.time() * 1000
    return {
        "pairCreatedAt": now_ms - age_minutes * 60 * 1000,
        "liquidity": {"usd": liquidity},
        "volume": {"h24": volume},
        "baseToken": {"symbol": token, "address": "0xtest"},
        "pairAddress": "0xpair",
        "dexId": "raydium",
        "priceUsd": 1.5,
    }


class TestDetectNewPools:
    def test_finds_new_pool(self):
        pairs = [_pair(age_minutes=10)]
        result = detect_new_pools(pairs, CFG)
        assert len(result) == 1
        assert result[0]["token"] == "TEST"
        assert result[0]["age_minutes"] < 15

    def test_filters_old_pool(self):
        pairs = [_pair(age_minutes=120)]
        assert detect_new_pools(pairs, CFG) == []

    def test_filters_low_liquidity(self):
        pairs = [_pair(liquidity=100)]
        assert detect_new_pools(pairs, CFG) == []

    def test_filters_low_volume(self):
        pairs = [_pair(volume=100)]
        assert detect_new_pools(pairs, CFG) == []

    def test_no_created_at(self):
        pairs = [{"liquidity": {"usd": 10000}, "volume": {"h24": 5000}}]
        assert detect_new_pools(pairs, CFG) == []

    def test_sorted_by_age(self):
        pairs = [_pair(age_minutes=50), _pair(age_minutes=5, token="NEW")]
        result = detect_new_pools(pairs, CFG)
        assert result[0]["token"] == "NEW"

    def test_empty(self):
        assert detect_new_pools([], CFG) == []


class TestBuildEventPayload:
    @patch("event_checker.time.time", return_value=1000000)
    def test_payload(self, _):
        event = {"token": "JTO", "pair": "JTO_USDC", "event_type": "airdrop",
                 "description": "Phase 2 airdrop", "source": "official"}
        p = build_event_payload(event, ACTIVE, 12.5)
        assert p["token"] == "JTO"
        assert p["status"] == "ACTIVE"
        assert p["hours"] == 12.5
        assert p["event_type"] == "airdrop"
        assert p["timestamp"] == 1000000
