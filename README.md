# 🤖 Hummingbot Edge Services

> A fleet of Python microservices that give your Hummingbot trading bot a real edge — session awareness, token scoring, cross-DEX arbitrage, narrative scanning, rewards ranking, and Telegram alerting.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## What This Is

Hummingbot is a powerful open-source trading bot, but running it out of the box is like driving a race car without a pit crew. These edge services are the pit crew — they monitor markets, score opportunities, find arbitrage, and send you Telegram alerts so you can trade smarter, not harder.

**Every service communicates via MQTT** (EMQX broker), forming a reactive signal mesh. The alert service aggregates everything into Telegram notifications with profitability filtering.

---

## Architecture

```
External APIs (free, no keys)              Infrastructure (Docker)
├── DexScreener (Solana pairs, trending)   ├── EMQX           :1883  (MQTT broker)
                                           ├── PostgreSQL      :5432  (optional api-extended profile)
                                           ├── Hummingbot API  :8000  (optional api-extended profile)
Edge Services (Python → MQTT)              └── Gateway         :15888 (DEX routing)
├── Tier 1: Independent scanners
│   ├── session-service        Time-zone session detector (ASIA/EU/US/NIGHT)
│   ├── alpha-service          AI token discovery & scoring
│   ├── arb-service            Cross-DEX arbitrage scanner (40+ tokens, auto-discovery)
│   ├── narrative-service      Narrative/social momentum tracker
│   └── rewards-service        LP reward APR ranker (Raydium/Orca/Meteora)
├── Tier 2: Optional (api-extended profile)
│   ├── inventory-service      Inventory skew & kill switch
│   ├── hedge-service          Delta-neutral hedging (spot + perp)
│   └── pnl-service            P&L tracking & Sharpe ratio
├── Tier 3: Consumes MQTT signals
│   ├── alert-service          Telegram alerts for all services
│   ├── clmm-service           Concentrated liquidity range optimizer
│   └── watchlist-service      Auto token list management
```

---

## Key Features

### 🔍 Auto-Discovery

- **Arb scanner** auto-discovers trending Solana tokens from DexScreener every 30 min
- **Watchlist service** feeds discoveries back into tracking lists automatically

### 💰 Profitability-First

- Arb scanner only reports opportunities netting **$5+ per $100 trade** (after slippage + gas)
- Net profit scoring system ranks by `spread × liquidity × volume`

### 🛡️ Scam & Risk Protection

- **Honeypot Detection**: Arb, Alpha, and Narrative scanners auto-reject tokens with 0 sells (to prevent buying into non-sellable contracts).
- **Wash Trading Filters**: Token scorers heavily penalize pools with extreme volume-to-MCAP ratios to prevent manipulation.
- **LP APR Normalization**: Rewards service dampens 24h volume peaks and caps max fee APRs to 300% to prevent unrealistic yield extrapolations.
- **Bad Data Filtering**: Arb scanner enforces maximum price deviation ratios between DEXes to ignore stale or scam pools.

### 🧹 Auto-Cleanup

- Arb signals expire after 10 min (re-appear if still valid)
- Narrative alerts clear at 5K entries

### 📱 Telegram Alerts

- One service aggregates all active services into filtered, actionable alerts
- Profitability checks prevent noise (min net profit thresholds)
- Per-signal toggles: enable/disable session, arb, alpha, narrative, rewards, etc.

---

## Quick Start

### Option 1: Docker (Recommended for VPS)

```bash
git clone https://github.com/Admin-AUXO/hummingbot-edge-services.git
cd hummingbot-edge-services/deploy
cp .env.example .env   # Edit with your credentials
docker compose up -d
```

See [deploy/README.md](deploy/README.md) for Hostinger VPS instructions.

### Option 2: Local Development

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start infrastructure
cd hummingbot-api && docker compose up -d

# 3. Start edge services (each in its own terminal)
cd session-service && python session_service.py
cd alpha-service && python alpha_service.py
cd arb-service && python arb_service.py
# ... see GETTING_STARTED.md for all services

# Optional: enable API-integrated profile services
cd deploy && docker compose --profile api-extended up -d
```

See [GETTING_STARTED.md](GETTING_STARTED.md) for the full setup guide.

---

## Services Overview

| Service             | What It Does                                            | Data Source              | Poll      |
| ------------------- | ------------------------------------------------------- | ------------------------ | --------- |
| **session**         | Detects trading session (ASIA/EU/US/NIGHT)              | UTC clock                | 1 min     |
| **alpha**           | Discovers & scores trending Solana tokens               | DexScreener              | 15 min    |
| **arb**             | Cross-DEX spread scanner (40+ tokens)                   | DexScreener              | 30s       |
| **narrative**       | Tracks narrative momentum (AI, meme, DePIN)             | DexScreener              | 30 min    |
| **rewards**         | Ranks LP pools by risk-adjusted APR                     | DexScreener              | 1 hr      |
| **inventory**       | Monitors spot balance & skew (optional `api-extended`)  | Hummingbot API           | 1 min     |
| **hedge**           | Delta-neutral hedging (optional `api-extended`)         | Hummingbot API           | 30s       |
| **pnl**             | Tracks P&L metrics (optional `api-extended`)            | Hummingbot API           | 5 min     |
| **alert**           | Aggregates all signals → Telegram                       | MQTT                     | Real-time |
| **clmm**            | Dynamic CLMM range optimization                         | MQTT + Binance           | 2 min     |
| **watchlist**       | Auto-manages token lists for arb/rewards                | MQTT + DexScreener       | 5 min     |

---

## Data Files

Services that use JSON data files auto-reload them each poll cycle. Edit on disk and changes take effect immediately.

| File                                   | Service           | Entries                         |      Auto-Discovery       |
| -------------------------------------- | ----------------- | ------------------------------- | :-----------------------: |
| `arb-service/tokens.json`              | Arb Scanner       | 40 Solana tokens                | ✅ + DexScreener trending |
| `watchlist-service/funding_symbols.json` | Watchlist cache | Local optional funding symbol cache |          Static           |
| `narrative-service/narratives.json`    | Narrative Scanner | 10 categories                   |          Static           |
| `rewards-service/pools.json`           | Rewards Tracker   | 12 pools (Raydium/Orca/Meteora) |     Watchlist service     |

---

## Configuration

All services use [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) with environment variable prefixes.

```bash
# Override any setting via environment variable
export ARB_MIN_ARB_PCT=3.0           # Lower arb threshold
export ALERT_TELEGRAM_BOT_TOKEN=... # Your Telegram bot token
```

### Performance tuning (algorithmic speedups)

```bash
# Alpha
export ALPHA_MAX_WORKERS=6
export ALPHA_SIGNAL_TTL_SECONDS=7200
export ALPHA_LISTING_TTL_SECONDS=14400

# Arb
export ARB_MAX_WORKERS=10
export ARB_DEX_BATCH_SIZE=30
export ARB_DISCOVERY_INTERVAL_SECONDS=1800
export ARB_SEEN_ARB_TTL_SECONDS=600

# Narrative
export NARR_MAX_WORKERS=5
export NARR_ALERTED_TOKENS_LIMIT=5000
export NARR_PREV_VOLUMES_LIMIT=10000

# CLMM
export CLMM_PRICE_SYMBOL=SOLUSDT
```

The stack now uses connection pooling + retries for external API calls and supports runtime tuning of worker counts, batch sizes, and cache TTLs.

See [GETTING_STARTED.md](GETTING_STARTED.md) for all prefixes and variables.

---

## MQTT Topics

```
hbot/session/{pair}                   → ASIA / EU / US / NIGHT
hbot/alpha/signal/{token}             → Scored tokens (score >= 7)
hbot/alpha/new_listing/{token}        → New pairs <48h, liq >$50K
hbot/arb/{token}                      → Cross-DEX price discrepancies
hbot/narrative/{category}/{token}     → Narrative volume spikes
hbot/rewards/{token}                  → Per-pool APR rankings
hbot/inventory/{pair}                 → Skew, kill switch
hbot/hedge/{pair}                     → Delta, hedge actions
hbot/analytics/{pair}                 → PnL, win rate, Sharpe
hbot/clmm/{pair}                      → Range + rebalance signals
hbot/watchlist/added/{type}/{symbol}  → Token auto-added
hbot/watchlist/removed/{type}/{symbol}→ Stale token removed
```

---

## Default Credentials

| Service        | Username | Password       |
| -------------- | -------- | -------------- |
| MQTT Broker    | admin    | password       |
| Hummingbot API | admin    | admin          |
| PostgreSQL     | hbot     | hummingbot-api |
| EMQX Dashboard | admin    | public         |

> ⚠️ **Change all defaults before trading with real funds.**

---

## Knowledge Base

The `knowledge-base/` directory contains 16 comprehensive guides covering:

- Hummingbot features, strategies, and V2 framework
- Chain/DEX selection, trading pairs, and configurations
- Risk management, order types, and expert tips
- Profit scenarios, costs, and the edge systems architecture

---

## Project Structure

```
├── shared/                  Base config + MQTT service classes
├── alert-service/           Telegram alert aggregator
├── alpha-service/           AI token discovery
├── arb-service/             Cross-DEX arbitrage
├── clmm-service/            CLMM range optimizer
├── hedge-service/           Delta-neutral hedging
├── inventory-service/       Inventory management
├── narrative-service/       Narrative momentum
├── pnl-service/             P&L tracking
├── rewards-service/         LP reward tracker
├── session-service/         Trading session detector
├── watchlist-service/       Auto token management
├── deploy/                  Docker deployment files
├── knowledge-base/          Comprehensive trading guides
└── hummingbot-api/          API + EMQX + PostgreSQL compose
```

---

## License

MIT
