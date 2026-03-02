import json
import logging
import time

logger = logging.getLogger("swarm")


def load_state(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return []


def save_state(bots, path):
    with open(path, "w") as f:
        json.dump(bots, f, indent=2)


def should_deploy(signal, config, active_bots):
    if len(active_bots) >= config.max_active_bots:
        return False, "max bots reached"

    score = signal.get("score", 0)
    if score < config.min_alpha_score:
        return False, f"score {score} < {config.min_alpha_score}"

    liquidity = signal.get("liquidity", 0)
    if liquidity < config.min_liquidity:
        return False, f"liquidity ${liquidity:,.0f} < ${config.min_liquidity:,.0f}"

    total_deployed = sum(b.get("capital", 0) for b in active_bots)
    if total_deployed + config.capital_per_bot > config.total_swarm_capital:
        return False, "capital limit reached"

    existing_tokens = {b["token"] for b in active_bots}
    if signal.get("token", "") in existing_tokens:
        return False, "already deployed"

    return True, "eligible"


def create_bot_entry(signal, config):
    return {
        "token": signal.get("token", "?"),
        "pair": signal.get("pair", ""),
        "address": signal.get("address", ""),
        "dex": signal.get("dex", ""),
        "capital": config.capital_per_bot,
        "entry_price": signal.get("price", 0),
        "score": signal.get("score", 0),
        "deployed_at": time.time(),
        "status": "RECOMMENDED" if not config.auto_deploy else "ACTIVE",
        "pnl": 0.0,
    }


def evaluate_bots(bots, config):
    now = time.time()
    changes = []

    for bot in bots:
        if bot["status"] not in ("ACTIVE", "RECOMMENDED"):
            continue

        age_hours = (now - bot["deployed_at"]) / 3600

        if age_hours > config.bot_ttl_hours:
            bot["status"] = "EXPIRED"
            changes.append(f"EXPIRED: {bot['token']} after {age_hours:.1f}h")
            continue

        if bot.get("pnl", 0) < -(config.capital_per_bot * config.kill_loss_pct):
            bot["status"] = "KILLED"
            changes.append(f"KILLED: {bot['token']} pnl={bot['pnl']:.2f}")

    return changes


def build_swarm_status(bots, config):
    active = [b for b in bots if b["status"] in ("ACTIVE", "RECOMMENDED")]
    total_capital = sum(b["capital"] for b in active)
    total_pnl = sum(b.get("pnl", 0) for b in active)
    by_status = {}
    for b in bots:
        by_status[b["status"]] = by_status.get(b["status"], 0) + 1

    return {
        "total_bots": len(bots),
        "active_bots": len(active),
        "total_capital_deployed": round(total_capital, 2),
        "available_capital": round(config.total_swarm_capital - total_capital, 2),
        "total_pnl": round(total_pnl, 2),
        "by_status": by_status,
        "active": [
            {
                "token": b["token"],
                "status": b["status"],
                "capital": b["capital"],
                "pnl": b.get("pnl", 0),
                "age_hours": round((time.time() - b["deployed_at"]) / 3600, 1),
            }
            for b in active
        ],
        "auto_deploy": config.auto_deploy,
        "timestamp": time.time(),
    }
