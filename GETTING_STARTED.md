# Getting Started

Setup guide for the full stack: Docker infrastructure, edge services, alerts, and live trading.

## Prerequisites

| Requirement | Purpose |
|---|---|
| Docker Desktop (Compose v2) | Infrastructure containers |
| Python 3.10+ | Edge services |
| Git | Version control |

**Optional (live trading):**
- Solana wallet (Phantom) with SOL + USDC
- Hyperliquid account (delta-neutral hedging)
- Telegram bot via @BotFather (alerts)

---

## 1. Install Python Dependencies

```powershell
cd A:\Trading
pip install -r requirements.txt
```

> **Python 3.14 note:** `pandas-ta` requires `numba` which doesn't support 3.14 yet. Install separately: `pip install pandas-ta --no-deps`

---

## 2. Start Infrastructure

```powershell
cd A:\Trading\hummingbot-api
docker compose up -d
```

| Container | Service | Port |
|---|---|---|
| `hummingbot-broker` | EMQX (MQTT) | 1883, 18083 (dashboard) |
| `hummingbot-postgres` | PostgreSQL | 5432 |
| `hummingbot-api` | FastAPI | 8000 |

**Verify:**
- API docs: http://localhost:8000/docs
- EMQX dashboard: http://localhost:18083 (admin / public)

---

## 3. Start Hummingbot + Gateway

> Skip if you only want edge services without live trading.

```powershell
cd A:\Trading\hummingbot
$env:COMPOSE_PROFILES="gateway"; docker compose up -d
docker attach hummingbot
```

Inside the CLI: `gateway connect` → `create` → `start`

Detach without stopping: `Ctrl+P` then `Ctrl+Q`

---

## 4. Configure Edge Services

All services inherit shared MQTT defaults that match the broker from Step 2:

```
MQTT_HOST=localhost  MQTT_PORT=1883  MQTT_USERNAME=admin  MQTT_PASSWORD=password
```

Override any setting via environment variables using each service's prefix:

### Tier 1 — Independent (MQTT + public APIs only)

| Service | Prefix | Key Variables | External API |
|---|---|---|---|
| session | `SESSION_` | `TARGET_PAIR` (sol_usdc), `POLL_INTERVAL_SECONDS` (60) | None (UTC clock) |
| regime | `REGIME_` | `SYMBOL` (SOLUSDT), `POLL_INTERVAL_SECONDS` (300) | Binance |
| funding | `FUNDING_` | `SYMBOL` (SOLUSDT), `POLL_INTERVAL_SECONDS` (300) | Binance Futures |
| correlation | `CORR_` | `TARGET_PAIR`, `REFERENCE_PAIRS` (ETHUSDT,BTCUSDT) | Binance |
| alpha | `ALPHA_` | `MIN_SCORE` (7), `MIN_LIQUIDITY` (50000), `POLL_INTERVAL_SECONDS` (900) | DexScreener |
| arb | `ARB_` | `MIN_ARB_PCT` (0.5), `MIN_LIQUIDITY` (5000), `TOKENS_FILE` (./tokens.json) | DexScreener |
| funding-scanner | `FSCAN_` | `HIGH_RATE_THRESHOLD` (0.0003), `SYMBOLS_FILE` (./symbols.json), `MIN_ANNUALIZED_APR` (30) | Binance Futures |
| narrative | `NARR_` | `MIN_VOLUME_SPIKE` (2.0), `MIN_VOLUME_24H` (50000), `NARRATIVES_FILE` | DexScreener |
| rewards | `REWARDS_` | `MIN_EFFECTIVE_APR` (20), `POOLS_FILE` (./pools.json), `MAX_RISK_SCORE` (8) | DexScreener |

### Tier 2 — Needs Hummingbot API

| Service | Prefix | Key Variables |
|---|---|---|
| inventory | `INV_` | `TARGET_PAIR`, `API_BASE_URL` (http://localhost:8000) |
| hedge | `HEDGE_` | `TARGET_PAIR`, `DELTA_THRESHOLD` (0.5), `API_BASE_URL` |
| pnl | `PNL_` | `TARGET_PAIR`, `API_BASE_URL`, `POLL_INTERVAL_SECONDS` (300) |

### Tier 3 — Consumes MQTT signals

| Service | Prefix | Key Variables |
|---|---|---|
| lab | `LAB_` | `DATA_FILE` (./experiments.json), `EVAL_INTERVAL_SECONDS` (300) |
| alert | `ALERT_` | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, per-signal toggles |
| swarm | `SWARM_` | `MAX_ACTIVE_BOTS` (50), `CAPITAL_PER_BOT` (10), `AUTO_DEPLOY` (false) |
| clmm | `CLMM_` | `TARGET_PAIR` (sol_usdc), `BASE_RANGE_PCT` (2.0), `REBALANCE_THRESHOLD_PCT` (70) |
| watchlist | `WL_` | `EVAL_INTERVAL_SECONDS` (300), `MAX_ARB_TOKENS` (40), `MAX_REWARDS_POOLS` (20), `MAX_FUNDING_SYMBOLS` (20) |

### Tier 4 — Manual / on-demand

| Service | Prefix | Key Variables |
|---|---|---|
| unlock | `UNLOCK_` | `DATA_FILE` (./unlocks.json), `PRE_UNLOCK_HOURS` (24), `POST_UNLOCK_HOURS` (48) |
| backtest | `BT_` | `API_BASE_URL` (http://localhost:8000) |
| migration | `MIG_` | `EVENTS_FILE` (./events.json), `NEW_POOL_MAX_AGE_MINUTES` (60) |

---

## 5. Start Edge Services

Run each in its own terminal, following tier order:

```powershell
# Tier 1 — Independent scanners
cd A:\Trading\session-service;              python session_service.py
cd A:\Trading\regime-service;               python regime_classifier.py
cd A:\Trading\funding-service;              python funding_service.py
cd A:\Trading\correlation-service;          python correlation_service.py
cd A:\Trading\alpha-service;                python alpha_service.py
cd A:\Trading\arb-service;                  python arb_service.py
cd A:\Trading\funding-scanner-service;      python funding_scanner_service.py
cd A:\Trading\narrative-service;            python narrative_service.py
cd A:\Trading\rewards-service;              python rewards_service.py

# Tier 2 — Needs Hummingbot API
cd A:\Trading\inventory-service;            python inventory_service.py
cd A:\Trading\hedge-service;                python hedge_service.py
cd A:\Trading\pnl-service;                  python pnl_service.py

# Tier 3 — Consumes MQTT signals from other services
cd A:\Trading\lab-service;                  python lab_service.py
cd A:\Trading\alert-service;                python alert_service.py
cd A:\Trading\swarm-service;                python swarm_service.py
cd A:\Trading\clmm-service;                 python clmm_service.py
cd A:\Trading\watchlist-service;            python watchlist_service.py

# Tier 4 — Manual / on-demand
cd A:\Trading\unlock-service;               python unlock_service.py
cd A:\Trading\backtest-service;             python backtest_service.py
cd A:\Trading\migration-service;            python migration_service.py
```

---

## 6. Telegram Alerts

1. Message **@BotFather** → `/newbot` → copy the bot token
2. Start a chat with your bot, send any message
3. Get your chat ID:
   ```powershell
   Invoke-RestMethod "https://api.telegram.org/bot<TOKEN>/getUpdates"
   ```
   Find `"chat":{"id": <NUMBER>}`
4. Set env vars and start:
   ```powershell
   $env:ALERT_TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."
   $env:ALERT_TELEGRAM_CHAT_ID="987654321"
   cd A:\Trading\alert-service; python alert_service.py
   ```

**Alerts cover:** regime changes, correlation shifts, funding rates, inventory/kill switch, alpha signals, new listings, unlock events, PnL reports, backtest results, hedge actions, lab experiments, arb opportunities, funding scan rankings, narrative spikes, swarm deployments, CLMM rebalances, migration events, new pools, reward rankings, watchlist add/remove events.

---

## 7. Token Unlock Calendar

Edit `unlock-service/unlocks.json` with entries from [TokenUnlocks.app](https://tokenunlocks.app) or CryptoRank:

```json
[
  {
    "token": "JTO",
    "pair": "JTO_USDC",
    "unlock_time": "2026-03-07T12:00:00Z",
    "unlock_pct": 5.2,
    "unlock_amount": "24M JTO",
    "source": "tokenunlocks.app",
    "notes": "Investor vesting cliff"
  }
]
```

| Status | Window | Action |
|---|---|---|
| PRE_UNLOCK | 0–24h before | Widen buy spread (1.5x), tighten sell (0.8x) |
| POST_UNLOCK | 0–48h after | Mean reversion — tighten buy (0.8x) |
| UPCOMING | >24h before | No action |
| INSIGNIFICANT | <2% supply | Ignored |

---

## 8. Verify

1. **EMQX dashboard** → http://localhost:18083 → Monitoring → check topics like `hbot/regime/sol_usdc`
2. **Service logs** → look for `Connected to MQTT` and periodic signal publications
3. **Alpha test** → run `alpha_service.py`, wait ~15s, confirm `Fetched X Solana pairs`
4. **Alert test** → if Telegram configured, startup message: *"Alert Service Started"*

---

## MQTT Topic Map

| Topic | Signals |
|---|---|
| `hbot/regime/{pair}` | BULL / BEAR / SIDEWAYS / SPIKE |
| `hbot/correlation/{pair}` | CONVERGING / DIVERGING / NEUTRAL |
| `hbot/funding/{pair}` | HIGH_POSITIVE / NEUTRAL / HIGH_NEGATIVE |
| `hbot/session/{pair}` | ASIA / EU / US / NIGHT + spread_mult |
| `hbot/inventory/{pair}` | Skew, kill switch, drawdown |
| `hbot/hedge/{pair}` | Delta, hedge ratio, order actions |
| `hbot/analytics/{pair}` | PnL, win rate, Sharpe |
| `hbot/backtest/{pair}` | Sweep results, top configs |
| `hbot/lab/{pair}` | Experiment status, kills, promotions |
| `hbot/alpha/signal/{token}` | Scored tokens (score >= 7) |
| `hbot/alpha/new_listing/{token}` | New pairs <48h, liq >$50K |
| `hbot/unlock/pre/{pair}` | Pre-unlock spread adjustments |
| `hbot/unlock/post/{pair}` | Post-unlock mean reversion |
| `hbot/arb/{token}` | Cross-DEX price discrepancies |
| `hbot/funding_scan/{symbol}` | High/extreme funding rates + ranked summary |
| `hbot/narrative/{category}/{token}` | Narrative volume spikes |
| `hbot/swarm/deploy/{token}` | Bot deployment recommendations |
| `hbot/swarm/status` | Swarm fleet dashboard |
| `hbot/clmm/{pair}` | Optimal range + rebalance signals |
| `hbot/migration/event/{token}` | Scheduled airdrop/migration events |
| `hbot/migration/new_pool/{token}` | Brand-new pool detections (<60min) |
| `hbot/rewards/{token}` | Per-pool APR + risk-adjusted ranking |
| `hbot/rewards/summary` | Top 5 pools by risk-adjusted APR |
| `hbot/watchlist/added/{type}/{symbol}` | Token auto-added to arb/rewards/funding list |
| `hbot/watchlist/removed/{type}/{symbol}` | Stale token auto-removed from list |
| `hbot/watchlist/status` | Watchlist counts (arb, rewards, funding) |

Alert service subscribes to `hbot/#` and forwards to Telegram.

---

## Architecture

```
External APIs (free, no keys)          Infrastructure (Docker)
├── Binance (candles, funding)         ├── EMQX         :1883  (MQTT broker)
├── DexScreener (Solana pairs)         ├── PostgreSQL    :5432  (bot history)
                                       ├── Hummingbot API:8000  (REST orchestration)
Edge Services (Python → MQTT)          └── Gateway       :15888 (DEX routing)
├── Tier 1: regime, session,
│   funding, correlation, alpha,       Trading (Docker)
│   arb, funding-scanner,              ├── Hummingbot CLI (executes trades)
│   narrative, rewards                 └── Gateway (on-chain transactions)
├── Tier 2: inventory, hedge, pnl
├── Tier 3: lab, alert, swarm, clmm, watchlist
└── Tier 4: unlock, backtest, migration
```

---

## Default Credentials

| Service | Username | Password |
|---|---|---|
| MQTT Broker | admin | password |
| Hummingbot API | admin | admin |
| PostgreSQL | hbot | hummingbot-api |
| EMQX Dashboard | admin | public |
| Gateway | — | admin (passphrase) |
| Hummingbot Config | — | admin (CONFIG_PASSWORD) |

> Change all defaults before running with real funds.

---

## Shutdown

```powershell
# Edge services: Ctrl+C in each terminal

# Hummingbot + Gateway
cd A:\Trading\hummingbot
docker compose --profile gateway down

# API + Broker + DB
cd A:\Trading\hummingbot-api
docker compose down

# Full reset (removes volumes)
docker compose down -v
```
