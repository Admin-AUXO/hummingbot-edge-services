# Getting Started

Setup guide for the full stack: Docker infrastructure, edge services, alerts, and live trading.

## Prerequisites

| Requirement                 | Purpose                   |
| --------------------------- | ------------------------- |
| Docker Desktop (Compose v2) | Infrastructure containers |
| Python 3.10+                | Edge services             |
| Git                         | Version control           |

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

## 2. Start Infrastructure

```powershell
cd A:\Trading\hummingbot-api
docker compose up -d
```

| Container             | Service     | Port                    |
| --------------------- | ----------- | ----------------------- |
| `hummingbot-broker`   | EMQX (MQTT) | 1883, 18083 (dashboard) |
| `hummingbot-postgres` | PostgreSQL  | 5432                    |
| `hummingbot-api`      | FastAPI     | 8000                    |

> If you're running DEX-lean only, you can skip PostgreSQL/API and start only `deploy` services without `api-extended`.

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

| Service   | Prefix     | Key Variables                                                       | External API                   |
| --------- | ---------- | ------------------------------------------------------------------- | ------------------------------ |
| session   | `SESSION_` | `TARGET_PAIR` (sol_usdc), `POLL_INTERVAL_SECONDS` (60)             | None (UTC clock)               |
| alpha     | `ALPHA_`   | `MIN_SCORE` (7), `MIN_LIQUIDITY` (50000), `POLL_INTERVAL_SECONDS` (900), `MAX_WORKERS` | DexScreener                    |
| arb       | `ARB_`     | `MIN_ARB_PCT` (5.3), `MIN_LIQUIDITY` (10000), `TOKENS_FILE` (./tokens.json), `DEX_BATCH_SIZE`, `MAX_WORKERS` | DexScreener (+ auto-discovery) |
| narrative | `NARR_`    | `MIN_VOLUME_SPIKE` (2.0), `MIN_VOLUME_24H` (50000), `NARRATIVES_FILE`, `MAX_WORKERS` | DexScreener                    |
| rewards   | `REWARDS_` | `MIN_EFFECTIVE_APR` (20), `POOLS_FILE` (./pools.json), `MAX_RISK_SCORE` (8) | DexScreener                    |

### Tier 2 — Optional (`api-extended` profile, needs Hummingbot API)

| Service   | Prefix   | Key Variables                                                |
| --------- | -------- | ------------------------------------------------------------ |
| inventory | `INV_`   | `TARGET_PAIR`, `API_BASE_URL` (http://localhost:8000)        |
| hedge     | `HEDGE_` | `TARGET_PAIR`, `DELTA_THRESHOLD` (0.5), `API_BASE_URL`       |
| pnl       | `PNL_`   | `TARGET_PAIR`, `API_BASE_URL`, `POLL_INTERVAL_SECONDS` (300) |

### Tier 3 — Consumes MQTT signals

| Service   | Prefix   | Key Variables                                                                                              |
| --------- | -------- | ---------------------------------------------------------------------------------------------------------- |
| alert     | `ALERT_` | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, per-signal toggles                                               |
| clmm      | `CLMM_`  | `TARGET_PAIR` (sol_usdc), `PRICE_SYMBOL` (SOLUSDT), `BASE_RANGE_PCT` (2.0), `REBALANCE_THRESHOLD_PCT` (70) |
| watchlist | `WL_`    | `EVAL_INTERVAL_SECONDS` (300), `MAX_ARB_TOKENS` (40), `MAX_REWARDS_POOLS` (20), `MAX_FUNDING_SYMBOLS` (20) |

### Performance tuning (optional)

Use these env vars to tune runtime throughput:

```powershell
$env:ALPHA_MAX_WORKERS="6"
$env:ALPHA_SIGNAL_TTL_SECONDS="7200"

$env:ARB_MAX_WORKERS="10"
$env:ARB_DEX_BATCH_SIZE="30"
$env:ARB_DISCOVERY_INTERVAL_SECONDS="1800"
$env:ARB_SEEN_ARB_TTL_SECONDS="600"

$env:NARR_MAX_WORKERS="5"
$env:NARR_ALERTED_TOKENS_LIMIT="5000"

$env:CLMM_PRICE_SYMBOL="SOLUSDT"
```

---

## 5. Start Edge Services

Run each in its own terminal, following tier order:

```powershell
# Tier 1 — Independent scanners
cd A:\Trading\session-service;              python session_service.py
cd A:\Trading\alpha-service;                python alpha_service.py
cd A:\Trading\arb-service;                  python arb_service.py
cd A:\Trading\narrative-service;            python narrative_service.py
cd A:\Trading\rewards-service;              python rewards_service.py

# Tier 2 — Needs Hummingbot API
cd A:\Trading\inventory-service;            python inventory_service.py
cd A:\Trading\hedge-service;                python hedge_service.py
cd A:\Trading\pnl-service;                  python pnl_service.py

# Tier 3 — Consumes MQTT signals from other services
cd A:\Trading\alert-service;                python alert_service.py
cd A:\Trading\clmm-service;                 python clmm_service.py
cd A:\Trading\watchlist-service;            python watchlist_service.py
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

**Alerts cover:** session state, inventory/kill switch, alpha signals, new listings, PnL reports, hedge actions, arb opportunities, narrative spikes, CLMM rebalances, reward rankings, watchlist add/remove events.

---

## 7. Verify

1. **EMQX dashboard** → http://localhost:18083 → Monitoring → check topics like `hbot/session/sol_usdc`
2. **Service logs** → look for `Connected to MQTT` and periodic signal publications
3. **Alpha test** → run `alpha_service.py`, wait ~15s, confirm `Fetched X Solana pairs`
4. **Alert test** → if Telegram configured, startup message: _"Alert Service Started"_

---

## MQTT Topic Map

| Topic                                    | Signals                                      |
| ---------------------------------------- | -------------------------------------------- |
| `hbot/session/{pair}`                    | ASIA / EU / US / NIGHT + spread_mult         |
| `hbot/inventory/{pair}`                  | Skew, kill switch, drawdown                  |
| `hbot/hedge/{pair}`                      | Delta, hedge ratio, order actions            |
| `hbot/analytics/{pair}`                  | PnL, win rate, Sharpe                        |
| `hbot/alpha/signal/{token}`              | Scored tokens (score >= 7)                   |
| `hbot/alpha/new_listing/{token}`         | New pairs <48h, liq >$50K                    |
| `hbot/arb/{token}`                       | Cross-DEX price discrepancies                |
| `hbot/narrative/{category}/{token}`      | Narrative volume spikes                      |
| `hbot/clmm/{pair}`                       | Optimal range + rebalance signals            |
| `hbot/rewards/{token}`                   | Per-pool APR + risk-adjusted ranking         |
| `hbot/rewards/summary`                   | Top 5 pools by risk-adjusted APR             |
| `hbot/watchlist/added/{type}/{symbol}`   | Token auto-added to arb/rewards list         |
| `hbot/watchlist/removed/{type}/{symbol}` | Stale token auto-removed from list           |
| `hbot/watchlist/status`                  | Watchlist counts (arb, rewards, funding)     |

Alert service subscribes to `hbot/#` and forwards to Telegram.

---

## Architecture

```
External APIs (free, no keys)          Infrastructure (Docker)
├── DexScreener (Solana pairs)         ├── EMQX         :1883  (MQTT broker)
                                       ├── PostgreSQL    :5432  (optional api-extended)
                                       ├── Hummingbot API:8000  (optional api-extended)
Edge Services (Python → MQTT)          └── Gateway       :15888 (DEX routing)
├── Tier 1: session, alpha,
│   arb, narrative, rewards            Trading (Docker)
├── Tier 2: inventory, hedge, pnl      ├── Hummingbot CLI (executes trades)
│   (optional api-extended)            └── Gateway (on-chain transactions)
└── Tier 3: alert, clmm, watchlist
```

---

## Default Credentials

| Service           | Username | Password                |
| ----------------- | -------- | ----------------------- |
| MQTT Broker       | admin    | password                |
| Hummingbot API    | admin    | admin                   |
| PostgreSQL        | hbot     | hummingbot-api          |
| EMQX Dashboard    | admin    | public                  |
| Gateway           | —        | admin (passphrase)      |
| Hummingbot Config | —        | admin (CONFIG_PASSWORD) |

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
