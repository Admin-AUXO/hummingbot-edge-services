# 🤖 Hummingbot Edge Services

> A fleet of 20 Python microservices that give your Hummingbot trading bot a real edge — regime detection, delta-neutral hedging, cross-DEX arbitrage, funding rate harvesting, narrative scanning, and more.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## What This Is

Hummingbot is a powerful open-source trading bot, but running it out of the box is like driving a race car without a pit crew. These edge services are the pit crew — they monitor markets, detect regimes, find arbitrage, track token unlocks, and send you Telegram alerts so you can trade smarter, not harder.

**Every service communicates via MQTT** (EMQX broker), forming a reactive signal mesh. The alert service aggregates everything into Telegram notifications with profitability filtering.

---

## Architecture

```
External APIs (free, no keys)              Infrastructure (Docker)
├── Binance (candles, funding rates)       ├── EMQX           :1883  (MQTT broker)
├── DexScreener (Solana pairs, trending)   ├── PostgreSQL      :5432  (trade history)
                                           ├── Hummingbot API  :8000  (REST orchestration)
Edge Services (Python → MQTT)              └── Gateway         :15888 (DEX routing)
├── Tier 1: Independent scanners
│   ├── regime-service         Market regime classifier (BULL/BEAR/SIDEWAYS/SPIKE)
│   ├── session-service        Time-zone session detector (ASIA/EU/US/NIGHT)
│   ├── funding-service        Single-pair funding rate monitor
│   ├── correlation-service    SOL vs ETH/BTC correlation & z-score
│   ├── alpha-service          AI token discovery & scoring
│   ├── arb-service            Cross-DEX arbitrage scanner (40+ tokens, auto-discovery)
│   ├── funding-scanner        Multi-pair funding scanner (ALL Binance perps)
│   ├── narrative-service      Narrative/social momentum tracker
│   └── rewards-service        LP reward APR ranker (Raydium/Orca/Meteora)
├── Tier 2: Needs Hummingbot API
│   ├── inventory-service      Inventory skew & kill switch
│   ├── hedge-service          Delta-neutral hedging (spot + perp)
│   └── pnl-service            P&L tracking & Sharpe ratio
├── Tier 3: Consumes MQTT signals
│   ├── alert-service          Telegram alerts for all services
│   ├── lab-service            Experiment framework (hypothesis → test → measure)
│   ├── swarm-service          Multi-bot fleet manager
│   ├── clmm-service           Concentrated liquidity range optimizer
│   └── watchlist-service      Auto token list management
└── Tier 4: On-demand
    ├── unlock-service         Token unlock calendar (auto-cleanup)
    ├── backtest-service       Strategy backtesting
    └── migration-service      Airdrop & new pool monitor (auto-cleanup)
```

---

## Key Features

### 🔍 Auto-Discovery

- **Arb scanner** auto-discovers trending Solana tokens from DexScreener every 30 min
- **Funding scanner** auto-discovers extreme rates across ALL 500+ Binance perpetuals
- **Watchlist service** feeds discoveries back into tracking lists automatically

### 💰 Profitability-First

- Arb scanner only reports opportunities netting **$5+ per $100 trade** (after slippage + gas)
- Net profit scoring system ranks by `spread × liquidity × volume`
- Funding scanner separates watchlist (30% APR threshold) from auto-discovered (50% APR)

### 🧹 Auto-Cleanup

- Arb signals expire after 10 min (re-appear if still valid)
- Token unlocks auto-removed from JSON after 48h post-unlock
- Migration events auto-cleaned when expired
- Narrative alerts clear at 5K entries

### 📱 Telegram Alerts

- One service aggregates all 20 services into filtered, actionable alerts
- Profitability checks prevent noise (min net profit thresholds)
- Per-signal toggles: enable/disable regime, arb, funding, alpha, etc.

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
cd regime-service && python regime_classifier.py
cd arb-service && python arb_service.py
# ... see GETTING_STARTED.md for all services
```

See [GETTING_STARTED.md](GETTING_STARTED.md) for the full setup guide.

---

## Services Overview

| Service             | What It Does                                            | Data Source              | Poll      |
| ------------------- | ------------------------------------------------------- | ------------------------ | --------- |
| **regime**          | Classifies market as BULL/BEAR/SIDEWAYS/SPIKE           | Binance 4H candles       | 5 min     |
| **session**         | Detects trading session (ASIA/EU/US/NIGHT)              | UTC clock                | 1 min     |
| **funding**         | Monitors SOL perp funding rate                          | Binance Futures          | 5 min     |
| **correlation**     | SOL vs ETH/BTC z-score divergence                       | Binance 5M candles       | 5 min     |
| **alpha**           | Discovers & scores trending Solana tokens               | DexScreener              | 15 min    |
| **arb**             | Cross-DEX spread scanner (40+ tokens)                   | DexScreener              | 30s       |
| **funding-scanner** | All Binance perp funding rates                          | Binance Futures          | 5 min     |
| **narrative**       | Tracks narrative momentum (AI, meme, DePIN)             | DexScreener              | 30 min    |
| **rewards**         | Ranks LP pools by risk-adjusted APR                     | DexScreener              | 1 hr      |
| **inventory**       | Monitors spot balance & skew                            | Hummingbot API           | 1 min     |
| **hedge**           | Delta-neutral hedging (Raydium spot + Hyperliquid perp) | Hummingbot API           | 30s       |
| **pnl**             | Tracks P&L, win rate, Sharpe ratio                      | Hummingbot API           | 5 min     |
| **alert**           | Aggregates all signals → Telegram                       | MQTT                     | Real-time |
| **lab**             | Experiment lifecycle manager                            | MQTT                     | 5 min     |
| **swarm**           | Multi-bot fleet manager                                 | MQTT                     | 5 min     |
| **clmm**            | Dynamic CLMM range optimization                         | MQTT + Binance           | 2 min     |
| **watchlist**       | Auto-manages token lists for arb/rewards/funding        | MQTT + DexScreener       | 5 min     |
| **unlock**          | Token vesting unlock calendar                           | Local JSON               | 1 hr      |
| **backtest**        | V2 strategy backtesting                                 | Hummingbot API           | On-demand |
| **migration**       | Airdrop/migration events + new pool detection           | Local JSON + DexScreener | 5 min     |

---

## Data Files

Services that use JSON data files auto-reload them each poll cycle. Edit on disk and changes take effect immediately.

| File                                   | Service           | Entries                         |      Auto-Discovery       |
| -------------------------------------- | ----------------- | ------------------------------- | :-----------------------: |
| `arb-service/tokens.json`              | Arb Scanner       | 40 Solana tokens                | ✅ + DexScreener trending |
| `funding-scanner-service/symbols.json` | Funding Scanner   | 35 Binance perps                |   ✅ All Binance perps    |
| `narrative-service/narratives.json`    | Narrative Scanner | 10 categories                   |          Static           |
| `rewards-service/pools.json`           | Rewards Tracker   | 12 pools (Raydium/Orca/Meteora) |     Watchlist service     |
| `unlock-service/unlocks.json`          | Unlock Calendar   | 10 upcoming unlocks             |       Auto-cleanup        |
| `migration-service/events.json`        | Migration Monitor | Operator-maintained             |       Auto-cleanup        |

---

## Configuration

All services use [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) with environment variable prefixes.

```bash
# Override any setting via environment variable
export ARB_MIN_ARB_PCT=3.0           # Lower arb threshold
export FSCAN_AUTO_DISCOVER_ALL=false # Disable funding auto-discovery
export ALERT_TELEGRAM_BOT_TOKEN=... # Your Telegram bot token
```

See [GETTING_STARTED.md](GETTING_STARTED.md) for all prefixes and variables.

---

## MQTT Topics

```
hbot/regime/{pair}                    → BULL / BEAR / SIDEWAYS / SPIKE
hbot/session/{pair}                   → ASIA / EU / US / NIGHT
hbot/funding/{pair}                   → Funding rate + bias
hbot/correlation/{pair}               → CONVERGING / DIVERGING / NEUTRAL
hbot/alpha/signal/{token}             → Scored tokens (score >= 7)
hbot/alpha/new_listing/{token}        → New pairs <48h, liq >$50K
hbot/arb/{token}                      → Cross-DEX price discrepancies
hbot/funding_scan/{symbol}            → Extreme funding rates + summary
hbot/narrative/{category}/{token}     → Narrative volume spikes
hbot/rewards/{token}                  → Per-pool APR rankings
hbot/inventory/{pair}                 → Skew, kill switch
hbot/hedge/{pair}                     → Delta, hedge actions
hbot/analytics/{pair}                 → PnL, win rate, Sharpe
hbot/unlock/pre/{pair}                → Pre-unlock spread adjustments
hbot/unlock/post/{pair}               → Post-unlock mean reversion
hbot/swarm/deploy/{token}             → Bot deployment recommendations
hbot/clmm/{pair}                      → Range + rebalance signals
hbot/migration/event/{token}          → Scheduled events
hbot/migration/new_pool/{token}       → Brand-new pools (<60min)
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
├── backtest-service/        Strategy backtesting
├── clmm-service/            CLMM range optimizer
├── correlation-service/     SOL vs ETH/BTC correlation
├── funding-service/         Single-pair funding
├── funding-scanner-service/ Multi-pair funding scanner
├── hedge-service/           Delta-neutral hedging
├── inventory-service/       Inventory management
├── lab-service/             Experiment framework
├── migration-service/       Airdrop & pool monitor
├── narrative-service/       Narrative momentum
├── pnl-service/             P&L tracking
├── regime-service/          Market regime classifier
├── rewards-service/         LP reward tracker
├── session-service/         Trading session detector
├── swarm-service/           Bot fleet manager
├── unlock-service/          Token unlock calendar
├── watchlist-service/       Auto token management
├── deploy/                  Docker deployment files
├── knowledge-base/          Comprehensive trading guides
├── tests/                   Test suite
└── hummingbot-api/          API + EMQX + PostgreSQL compose
```

---

## License

MIT
