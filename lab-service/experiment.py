import json
import logging
import time

logger = logging.getLogger(__name__)


def generate_experiment_id(experiments):
    existing = [int(e["id"].split("-")[1]) for e in experiments if e.get("id", "").startswith("LAB-")]
    next_num = max(existing, default=0) + 1
    return f"LAB-{next_num:03d}"


def create_experiment(cmd_data, config):
    return {
        "id": None,
        "hypothesis": cmd_data.get("hypothesis", ""),
        "pair": cmd_data.get("pair", "sol_usdc"),
        "tier": cmd_data.get("tier", "EXPLORATION"),
        "status": "PENDING",
        "capital": cmd_data.get("capital", 0.0),
        "config_ref": cmd_data.get("config_ref", ""),
        "created_at": time.time(),
        "started_at": None,
        "ended_at": None,
        "trial_hours": cmd_data.get("trial_hours", config.default_trial_hours),
        "kill_criteria": {
            "max_loss": cmd_data.get("kill_criteria", {}).get("max_loss", config.default_kill_loss),
            "max_drawdown": cmd_data.get("kill_criteria", {}).get("max_drawdown", config.default_kill_drawdown),
        },
        "success_criteria": {
            "daily_pnl": cmd_data.get("success_criteria", {}).get("daily_pnl", config.default_success_daily_pnl),
            "min_win_rate": cmd_data.get("success_criteria", {}).get("min_win_rate", config.default_min_win_rate),
            "consecutive_profitable_days": cmd_data.get("success_criteria", {}).get("consecutive_profitable_days", 3),
        },
        "metrics": {
            "total_pnl": 0.0,
            "win_rate": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "daily_pnl": 0.0,
            "profitable_days": 0,
        },
        "post_mortem": None,
    }


def update_metrics(experiment, analytics_data):
    m = experiment["metrics"]
    m["total_pnl"] = analytics_data.get("total_pnl", m["total_pnl"])
    m["win_rate"] = analytics_data.get("win_rate", m["win_rate"])
    m["sharpe_ratio"] = analytics_data.get("sharpe_ratio", m["sharpe_ratio"])
    m["max_drawdown"] = analytics_data.get("max_drawdown", m["max_drawdown"])
    m["daily_pnl"] = analytics_data.get("daily_pnl", m["daily_pnl"])
    if analytics_data.get("daily_pnl", 0) > 0:
        m["profitable_days"] = m.get("profitable_days", 0) + 1
    else:
        m["profitable_days"] = 0
    if experiment["status"] == "PENDING":
        experiment["status"] = "RUNNING"
        experiment["started_at"] = time.time()


def evaluate_kill(experiment):
    m = experiment["metrics"]
    kc = experiment["kill_criteria"]

    if m["total_pnl"] < -kc["max_loss"]:
        return True, f"Max loss exceeded: {m['total_pnl']:.2f} < -{kc['max_loss']}"

    if m["max_drawdown"] > kc["max_drawdown"]:
        return True, f"Max drawdown exceeded: {m['max_drawdown']:.4f} > {kc['max_drawdown']}"

    if experiment["started_at"]:
        elapsed_hours = (time.time() - experiment["started_at"]) / 3600
        if elapsed_hours >= experiment["trial_hours"] and m["total_pnl"] <= 0:
            return True, f"Trial expired unprofitable after {elapsed_hours:.1f}h"

    return False, ""


def evaluate_promotion(experiment):
    m = experiment["metrics"]
    sc = experiment["success_criteria"]

    if m["daily_pnl"] < sc["daily_pnl"]:
        return False, "Daily PnL below threshold"

    if m["win_rate"] < sc["min_win_rate"]:
        return False, "Win rate below threshold"

    if m.get("profitable_days", 0) < sc.get("consecutive_profitable_days", 3):
        return False, "Not enough consecutive profitable days"

    return True, f"All criteria met: PnL={m['daily_pnl']:.2f}, WR={m['win_rate']:.1%}, Days={m['profitable_days']}"


def load_experiments(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Failed to load experiments from {path}: {e}")
        return []


def save_experiments(experiments, path):
    with open(path, "w") as f:
        json.dump(experiments, f, indent=2)


def build_lab_status(experiments):
    by_tier = {}
    by_status = {"RUNNING": 0, "PENDING": 0, "PROMOTED": 0, "KILLED": 0}
    active = []

    for exp in experiments:
        tier = exp.get("tier", "EXPLORATION")
        status = exp.get("status", "PENDING")

        if tier not in by_tier:
            by_tier[tier] = {"count": 0, "total_capital": 0.0, "total_pnl": 0.0}
        if status in ("RUNNING", "PENDING"):
            by_tier[tier]["count"] += 1
            by_tier[tier]["total_capital"] += exp.get("capital", 0)
            by_tier[tier]["total_pnl"] += exp["metrics"].get("total_pnl", 0)

        if status in by_status:
            by_status[status] += 1

        if status == "RUNNING":
            days = 0
            if exp.get("started_at"):
                days = int((time.time() - exp["started_at"]) / 86400)
            active.append({
                "id": exp["id"],
                "pair": exp.get("pair"),
                "tier": tier,
                "pnl": exp["metrics"].get("total_pnl", 0),
                "days": days,
            })

    return {
        "total_experiments": len(experiments),
        "by_tier": by_tier,
        "by_status": by_status,
        "active_experiments": active,
        "timestamp": time.time(),
    }
