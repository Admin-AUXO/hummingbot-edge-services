import time
from types import SimpleNamespace
from unittest.mock import patch

from swarm_manager import should_deploy, create_bot_entry, evaluate_bots, build_swarm_status

CFG = SimpleNamespace(
    max_active_bots=50,
    capital_per_bot=10.0,
    total_swarm_capital=500.0,
    min_alpha_score=7,
    min_liquidity=30000.0,
    bot_ttl_hours=48,
    kill_loss_pct=0.20,
    auto_deploy=False,
)


def _signal(token="TEST", score=8, liquidity=50000, price=1.5):
    return {"token": token, "score": score, "liquidity": liquidity,
            "price": price, "pair": "0xpair", "address": "0xaddr", "dex": "raydium"}


def _bot(token="TEST", status="ACTIVE", deployed_hours_ago=10, pnl=0.0, capital=10.0):
    return {
        "token": token, "status": status,
        "deployed_at": time.time() - deployed_hours_ago * 3600,
        "pnl": pnl, "capital": capital,
    }


class TestShouldDeploy:
    def test_eligible(self):
        ok, reason = should_deploy(_signal(), CFG, [])
        assert ok is True
        assert reason == "eligible"

    def test_max_bots_reached(self):
        bots = [_bot(token=f"T{i}") for i in range(50)]
        ok, reason = should_deploy(_signal(), CFG, bots)
        assert ok is False
        assert "max bots" in reason

    def test_low_score(self):
        ok, reason = should_deploy(_signal(score=3), CFG, [])
        assert ok is False
        assert "score" in reason

    def test_low_liquidity(self):
        ok, reason = should_deploy(_signal(liquidity=1000), CFG, [])
        assert ok is False
        assert "liquidity" in reason

    def test_capital_limit(self):
        bots = [_bot(token=f"T{i}", capital=10.0) for i in range(49)]
        ok, reason = should_deploy(_signal(), CFG, bots)
        assert ok is True
        bots2 = [_bot(token=f"T{i}", capital=10.0) for i in range(50)]
        ok2, reason2 = should_deploy(_signal(), CFG, bots2)
        assert ok2 is False

    def test_already_deployed(self):
        bots = [_bot(token="TEST")]
        ok, reason = should_deploy(_signal(token="TEST"), CFG, bots)
        assert ok is False
        assert "already deployed" in reason


class TestCreateBotEntry:
    @patch("swarm_manager.time.time", return_value=1000000)
    def test_recommended_by_default(self, _):
        entry = create_bot_entry(_signal(), CFG)
        assert entry["status"] == "RECOMMENDED"
        assert entry["capital"] == 10.0
        assert entry["token"] == "TEST"
        assert entry["deployed_at"] == 1000000
        assert entry["pnl"] == 0.0

    @patch("swarm_manager.time.time", return_value=1000000)
    def test_auto_deploy(self, _):
        cfg = SimpleNamespace(**vars(CFG))
        cfg.auto_deploy = True
        entry = create_bot_entry(_signal(), cfg)
        assert entry["status"] == "ACTIVE"


class TestEvaluateBots:
    def test_expires_old_bot(self):
        bots = [_bot(deployed_hours_ago=50)]
        changes = evaluate_bots(bots, CFG)
        assert len(changes) == 1
        assert "EXPIRED" in changes[0]
        assert bots[0]["status"] == "EXPIRED"

    def test_kills_losing_bot(self):
        bots = [_bot(pnl=-3.0)]
        changes = evaluate_bots(bots, CFG)
        assert len(changes) == 1
        assert "KILLED" in changes[0]
        assert bots[0]["status"] == "KILLED"

    def test_keeps_healthy_bot(self):
        bots = [_bot(deployed_hours_ago=10, pnl=1.0)]
        changes = evaluate_bots(bots, CFG)
        assert len(changes) == 0
        assert bots[0]["status"] == "ACTIVE"

    def test_skips_already_expired(self):
        bots = [_bot(status="EXPIRED", deployed_hours_ago=100)]
        changes = evaluate_bots(bots, CFG)
        assert len(changes) == 0

    def test_ttl_takes_priority(self):
        bots = [_bot(deployed_hours_ago=50, pnl=-5.0)]
        changes = evaluate_bots(bots, CFG)
        assert bots[0]["status"] == "EXPIRED"


class TestBuildSwarmStatus:
    @patch("swarm_manager.time.time", return_value=1000000)
    def test_basic(self, _):
        bots = [
            _bot(token="A", status="ACTIVE", pnl=2.0, capital=10),
            _bot(token="B", status="RECOMMENDED", pnl=0.0, capital=10),
            _bot(token="C", status="EXPIRED", pnl=-1.0, capital=10),
        ]
        s = build_swarm_status(bots, CFG)
        assert s["total_bots"] == 3
        assert s["active_bots"] == 2
        assert s["total_capital_deployed"] == 20.0
        assert s["available_capital"] == 480.0
        assert s["total_pnl"] == 2.0
        assert s["by_status"]["ACTIVE"] == 1
        assert s["by_status"]["RECOMMENDED"] == 1
        assert s["by_status"]["EXPIRED"] == 1
        assert s["auto_deploy"] is False
        assert len(s["active"]) == 2

    @patch("swarm_manager.time.time", return_value=1000000)
    def test_empty(self, _):
        s = build_swarm_status([], CFG)
        assert s["total_bots"] == 0
        assert s["active_bots"] == 0
        assert s["available_capital"] == 500.0
