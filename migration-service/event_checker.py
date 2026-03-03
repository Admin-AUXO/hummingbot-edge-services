import json
import logging
import time
from datetime import datetime

logger = logging.getLogger("migration")

UPCOMING = "UPCOMING"
ACTIVE = "ACTIVE"
POST_EVENT = "POST_EVENT"
EXPIRED = "EXPIRED"


def load_events(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load events from {path}: {e}")
        return []


def auto_cleanup_events(path, post_event_hours):
    """Remove expired event entries from the JSON file."""
    try:
        events = load_events(path)
        now = time.time()
        active = []
        removed = 0
        for e in events:
            event_ts = parse_event_time(e)
            if event_ts == 0:
                removed += 1
                continue
            hours_since = (now - event_ts) / 3600
            if hours_since > post_event_hours:
                removed += 1
                logger.info(f"Cleaned up expired event: {e.get('token', '?')} {e.get('event_type', '?')}")
            else:
                active.append(e)
        if removed > 0:
            with open(path, "w") as f:
                json.dump(active, f, indent=2)
            logger.info(f"Removed {removed} expired event entries")
        return active
    except Exception as e_err:
        logger.error(f"Auto-cleanup failed: {e_err}")
        return load_events(path)


def parse_event_time(event):
    ts = event.get("event_time", "")
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.timestamp()
    except Exception:
        return 0.0


def classify_event(event, config):
    event_ts = parse_event_time(event)
    if event_ts == 0:
        return EXPIRED, 0

    now = time.time()
    hours_until = (event_ts - now) / 3600

    if hours_until > config.pre_event_hours:
        return UPCOMING, round(hours_until, 1)
    elif 0 < hours_until <= config.pre_event_hours:
        return ACTIVE, round(hours_until, 1)
    elif -config.post_event_hours <= hours_until <= 0:
        return POST_EVENT, round(abs(hours_until), 1)
    else:
        return EXPIRED, 0


def detect_new_pools(pairs, config):
    now_ms = time.time() * 1000
    max_age_ms = config.new_pool_max_age_minutes * 60 * 1000
    new_pools = []

    for pair in pairs:
        created_at = pair.get("pairCreatedAt", 0)
        if not created_at:
            continue
        age_ms = now_ms - created_at
        if age_ms > max_age_ms:
            continue

        liquidity = float(pair.get("liquidity", {}).get("usd", 0))
        volume = float(pair.get("volume", {}).get("h24", 0))

        if liquidity < config.new_pool_min_liquidity:
            continue
        if volume < config.new_pool_min_volume:
            continue

        age_min = round(age_ms / 60000, 1)
        new_pools.append({
            "token": pair.get("baseToken", {}).get("symbol", "?"),
            "address": pair.get("baseToken", {}).get("address", ""),
            "pair": pair.get("pairAddress", ""),
            "dex": pair.get("dexId", ""),
            "price": float(pair.get("priceUsd", 0)),
            "liquidity": liquidity,
            "volume_24h": volume,
            "age_minutes": age_min,
            "timestamp": time.time(),
        })

    return sorted(new_pools, key=lambda x: x["age_minutes"])


def build_event_payload(event, status, hours):
    return {
        "token": event.get("token", "?"),
        "pair": event.get("pair", ""),
        "event_type": event.get("event_type", "unknown"),
        "status": status,
        "hours": hours,
        "description": event.get("description", ""),
        "source": event.get("source", ""),
        "timestamp": time.time(),
    }
