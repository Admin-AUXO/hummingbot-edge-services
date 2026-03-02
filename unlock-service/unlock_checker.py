import json
import logging
import time
from datetime import datetime

logger = logging.getLogger("unlock")

PRE_UNLOCK = "PRE_UNLOCK"
POST_UNLOCK = "POST_UNLOCK"
UPCOMING = "UPCOMING"
EXPIRED = "EXPIRED"
INSIGNIFICANT = "INSIGNIFICANT"


def load_unlocks(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load unlocks from {path}: {e}")
        return []


def parse_unlock_time(unlock):
    ts = unlock.get("unlock_time", "")
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.timestamp()
    except Exception:
        return 0.0


def classify_unlock(unlock, config):
    unlock_pct = float(unlock.get("unlock_pct", 0))
    if unlock_pct < config.min_unlock_pct:
        return INSIGNIFICANT, 0

    unlock_ts = parse_unlock_time(unlock)
    if unlock_ts == 0:
        return EXPIRED, 0

    now = time.time()
    hours_until = (unlock_ts - now) / 3600

    if hours_until > config.pre_unlock_hours:
        return UPCOMING, round(hours_until, 1)
    elif 0 < hours_until <= config.pre_unlock_hours:
        return PRE_UNLOCK, round(hours_until, 1)
    elif -config.post_unlock_hours <= hours_until <= 0:
        return POST_UNLOCK, round(abs(hours_until), 1)
    else:
        return EXPIRED, 0


def _base_unlock_payload(unlock):
    return {
        "token": unlock.get("token", "?"),
        "pair": unlock.get("pair", ""),
        "unlock_pct": float(unlock.get("unlock_pct", 0)),
        "unlock_amount": unlock.get("unlock_amount", ""),
        "source": unlock.get("source", ""),
        "timestamp": time.time(),
    }


def build_pre_unlock_payload(unlock, hours, config):
    payload = _base_unlock_payload(unlock)
    payload["status"] = PRE_UNLOCK
    payload["hours_until_unlock"] = hours
    payload["buy_spread_mult"] = config.pre_unlock_buy_spread_mult
    payload["sell_spread_mult"] = config.pre_unlock_sell_spread_mult
    return payload


def build_post_unlock_payload(unlock, hours, config):
    payload = _base_unlock_payload(unlock)
    payload["status"] = POST_UNLOCK
    payload["hours_since_unlock"] = hours
    payload["buy_spread_mult"] = config.post_unlock_buy_spread_mult
    payload["sell_spread_mult"] = config.post_unlock_sell_spread_mult
    return payload
