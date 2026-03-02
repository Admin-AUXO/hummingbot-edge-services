# 💸 Monthly Operating Costs & Best Setup

> What it costs to run 1 Hummingbot trading bot + edge services per month (excluding trading capital)

---

## Cost Categories

### 1. Software — $0/mo

| Item            | Cost     | License                  |
| --------------- | -------- | ------------------------ |
| Hummingbot      | **Free** | Open-source, Apache 2.0  |
| Gateway         | **Free** | Included with Hummingbot |
| EMQX Broker     | **Free** | Open-source MQTT         |
| Docker          | **Free** | Free for personal use    |
| Edge Services   | **Free** | Custom Python, open-source deps |
| Python + deps   | **Free** | paho-mqtt, requests, pydantic, numpy, pandas |

> Optional: Hummingbot Botcamp (training/certification) = $2,000-3,000 one-time. Not required.

---

### 2. Infrastructure — $0 to $25/mo

| Option                                 | Monthly                | Uptime         | Latency   | Best For                  |
| -------------------------------------- | ---------------------- | -------------- | --------- | ------------------------- |
| **Your own PC**                        | $0 (+$3-5 electricity) | Depends on you | Higher    | Learning, paper trading   |
| **Budget VPS** (Hetzner, Contabo)      | $5-10                  | 99.9%          | Good      | 1-2 bots, serious trading |
| **Standard VPS** (DigitalOcean, Vultr) | $20-25                 | 99.95%         | Very good | Reliable 24/7 operation   |
| **Cloud** (AWS, GCP)                   | $20-50                 | 99.99%         | Lowest    | Arb bots needing speed    |

**Minimum specs:**

| Setup | vCPU | RAM | SSD | Notes |
|---|---|---|---|---|
| 1 bot only | 2 | 4 GB | 25 GB | Hummingbot + Gateway + EMQX + PostgreSQL |
| 1 bot + core edge services (8) | 2 | 4 GB | 25 GB | Edge services add ~200 MB RAM total |
| 1 bot + full edge stack (20) | 4 | 8 GB | 40 GB | All scanners + orchestration services |
| Swarm (10 bots + full stack) | 4 | 8 GB | 40 GB | Docker Compose scales horizontally |

---

### 3. Blockchain Gas — $0.50 to $150+/mo (Biggest Variable)

Assuming ~50 swap transactions/day (moderate PMM or arb activity):

| Chain           | Cost/TX | Daily (50 TX) | **Monthly**    | Verdict            |
| --------------- | ------- | ------------- | -------------- | ------------------ |
| **Solana**      | $0.0003 | $0.015        | **$0.50**      | 🟢 Basically free  |
| **Base**        | $0.03   | $1.50         | **$45**        | 🟢 Very affordable |
| **Arbitrum**    | $0.05   | $2.50         | **$75**        | 🟡 Moderate        |
| **BNB Chain**   | $0.07   | $3.50         | **$105**       | 🟡 Moderate        |
| **Polygon**     | $0.03   | $1.50         | **$45**        | 🟢 Very affordable |
| **Optimism**    | $0.05   | $2.50         | **$75**        | 🟡 Moderate        |
| **Avalanche**   | $0.15   | $7.50         | **$225**       | 🔴 Expensive       |
| **Ethereum L1** | $0.30-5 | $15-250       | **$450-7,500** | 🔴 Only for whales |
| **Hyperliquid** | $0      | $0            | **$0**         | 🟢 **Zero Gas**    |

> ⚠️ On AMM DEXs, gas is only charged for actual on-chain swaps. Hummingbot monitors prices off-chain for free. So "50 TX/day" = 50 actual swaps, not 50 price checks.

---

### 4. Exchange Trading Fees (Per Trade)

| Exchange                    | Fee                 | On $20 Trade | On $100 Trade |
| --------------------------- | ------------------- | ------------ | ------------- |
| **Uniswap V3** (0.3% pool)  | 0.30%               | $0.06        | $0.30         |
| **Uniswap V3** (0.05% pool) | 0.05%               | $0.01        | $0.05         |
| **Uniswap V3** (0.01% pool) | 0.01%               | $0.002       | $0.01         |
| **Raydium**                 | 0.25%               | $0.05        | $0.25         |
| **Jupiter** (aggregator)    | 0% + underlying DEX | varies       | varies        |
| **PancakeSwap V3**          | 0.01-1%             | $0.002-0.20  | $0.01-1.00    |

**Monthly fee estimate** at $100/day trading volume:

- DEX only (Uniswap 0.3%): ~$9/mo in fees
- Cross-DEX arb: ~$6/mo in fees (mix of rates)
- Solana DEX (Raydium): ~$7.50/mo in fees

---

### 5. External API Usage (Edge Services) — $0/mo

All edge services use free public APIs with no authentication required:

| API | Used By | Rate Limit | Cost |
|---|---|---|---|
| **DexScreener** | alpha, arb, narrative, migration, rewards | ~300 req/min | **Free** |
| **Binance Spot** | regime, correlation, clmm | 1200 req/min | **Free** |
| **Binance Futures** | funding, funding-scanner | 1200 req/min | **Free** |
| **Telegram Bot API** | alert | 30 msg/sec | **Free** |

> Edge services poll at conservative intervals (60s–3600s), well within free rate limits. Running all 20 services simultaneously uses ~500 API calls/hour total across all providers.

**API call budget per service:**

| Service | Interval | Calls/Hour | Target API |
|---|---|---|---|
| regime | 5 min | 12 | Binance |
| session | 1 min | 60 | None (clock) |
| funding | 5 min | 12 | Binance Futures |
| correlation | 5 min | 12 | Binance |
| alpha | 15 min | 4 | DexScreener |
| arb | 1 min | 60 × N tokens | DexScreener |
| funding-scanner | 5 min | 12 | Binance Futures |
| narrative | 30 min | 2 × N keywords | DexScreener |
| rewards | 1 hr | 1 × N pools | DexScreener |
| clmm | 2 min | 30 | Binance |
| migration | 5 min | 12 | DexScreener |
| unlock | 1 hr | 0 | None (local JSON) |

> **DexScreener is the bottleneck.** If you run arb-service with 10 tokens at 60s interval = 600 calls/hour to DexScreener. Stay under ~1000 calls/hour total to avoid soft rate limits.

---

### 6. RPC Node (Optional but Recommended)

Public RPCs are free but rate-limited, which can cause failed transactions during high activity.

| Provider             | Free Tier                | Paid               | Best For             |
| -------------------- | ------------------------ | ------------------ | -------------------- |
| **Default (public)** | Unlimited (rate-limited) | —                  | Learning, low volume |
| **Alchemy**          | 3M compute/mo free       | $49/mo (Growth)    | EVM chains           |
| **Helius**           | 500K credits/day free    | $49/mo (Developer) | Solana               |
| **QuickNode**        | Limited free tier        | $49/mo             | Multi-chain          |
| **Infura**           | 100K requests/day free   | $50/mo             | Ethereum-focused     |

> For 1 bot with moderate activity, the **free tiers are usually sufficient**. Upgrade only if you see rate-limit errors. Edge services do NOT use RPC nodes — they call REST APIs directly.

---

### 7. One-Time Costs (First Month Only)

| Item                         | Cost          | Notes                                        |
| ---------------------------- | ------------- | -------------------------------------------- |
| Token approvals (EVM)        | $0.50-5 total | ~$0.05 each on L2s, need 1 per token per DEX |
| Initial gas tokens in wallet | $5-20         | ETH (for L2s), SOL, or BNB for gas           |
| Domain/SSL (if remote)       | $0-12/yr      | Only if exposing API publicly                |

---

## Total Monthly Cost by Scenario

### 🟢 Scenario A: Learning / Paper Trading

> Run on your own PC, Solana, free everything. No edge services yet.

| Category         | Cost               |
| ---------------- | ------------------ |
| Software         | $0                 |
| Server (your PC) | $0                 |
| Gas              | $0 (paper trading) |
| Edge services    | $0 (not running)   |
| RPC              | $0 (public)        |
| Trading fees     | $0 (paper trading) |
| **Total**        | **$0/mo**          |

### 🟢 Scenario B: First Real Money + Core Signals (Solana, local)

> Your PC, Solana chain, small capital, 4 core edge services for awareness

| Category                        | Cost            |
| ------------------------------- | --------------- |
| Software                        | $0              |
| Server (your PC)                | ~$3 electricity |
| Gas (Solana, 50 TX/day)         | $0.50           |
| Edge services (regime, session, funding, alert) | $0 |
| External APIs                   | $0 (free)       |
| RPC                             | $0 (public)     |
| Trading fees (~$200/day volume) | ~$15            |
| **Total**                       | **~$19/mo**     |

Edge services running: `regime-service` (regime alerts), `session-service` (time-zone spreads), `funding-service` (funding rate), `alert-service` (Telegram notifications).

### 🟡 Scenario C: Serious Trader + Full Edge Stack (Solana, VPS)

> Budget VPS, Solana chain, all core + scanner services

| Category                        | Cost           |
| ------------------------------- | -------------- |
| Software                        | $0             |
| Server (Hetzner VPS, 4GB)       | $5             |
| Gas (Solana, 50 TX/day)         | $0.50          |
| Edge services (8 core + 5 scanners) | $0         |
| External APIs                   | $0 (free)      |
| RPC                             | $0 (free tier) |
| Trading fees (~$500/day volume) | ~$35           |
| **Total**                       | **~$41/mo**    |

Edge services running: core 8 (regime, session, funding, correlation, inventory, hedge, pnl, alert) + scanners (alpha, arb, funding-scanner, narrative, rewards).

### 🟡 Scenario D: Full Stack + Orchestration (Multi-chain, VPS)

> Standard VPS, Solana + Arbitrum + Hyperliquid, all 20 services

| Category                        | Cost           |
| ------------------------------- | -------------- |
| Software                        | $0             |
| Server (Hetzner VPS, 8GB)       | $10            |
| Gas (Solana + Arbitrum)          | $40            |
| Edge services (all 20)          | $0             |
| External APIs                   | $0 (free)      |
| RPC                             | $0 (free tier) |
| Trading fees (~$500/day volume) | ~$45           |
| **Total**                       | **~$95/mo**    |

Full stack: core 8 + scanners 7 (alpha, arb, funding-scanner, narrative, rewards, unlock, migration) + orchestration 3 (lab, swarm, clmm) + backtest on-demand.

### 🔴 Scenario E: The "Swarm" (10 Bots + Full Stack on VPS)

> Dedicated VPS, Solana, 10 bot instances managed by swarm-service

| Category                       | Cost             |
| ------------------------------ | ---------------- |
| Software                       | $0               |
| Server (DigitalOcean, 4 Core)  | $24              |
| Gas (Solana, 50 TX × 10 bots) | $5               |
| **Jito MEV Tips** (Sniping)    | **$20-50**       |
| Edge services (all 20)         | $0               |
| External APIs                  | $0 (free)        |
| RPC (Helius Paid Tier)         | $49 (Required)   |
| Trading fees (~$500/day total) | ~$35             |
| **Total**                      | **~$133-163/mo** |

Swarm-service manages bot lifecycle (deploy, TTL expiry, loss kills). Alpha-service and narrative-service feed signals. Migration-service detects new pools for sniping.

---

## ⭐ Recommended Best Setup

Based on your situation (learning phase, running locally on Windows, 1 bot):

### Phase 1: Start Here (Week 1-2) — **$0/mo**

```
Chain:     None (paper trading)
Server:    Your PC (local Docker)
Strategy:  PMM Simple on paper trade mode
Services:  None yet
Goal:      Learn the interface, test configs
Cost:      $0
```

### Phase 2: First Real Trades (Week 3-4) — **~$5/mo**

```
Chain:     Solana ← cheapest gas, fastest execution
DEX:       Jupiter (aggregator) or Raydium
Server:    Your PC (local Docker)
Pair:      SOL/USDC on Raydium
Capital:   $100-300
Strategy:  PMM Simple, conservative config (0.5% spread)
Services:  regime-service, session-service, alert-service (3 services, awareness only)
Gas:       ~$0.50/mo
Fees:      ~$5/mo at low volume
```

**Why start with 3 edge services:**

- Regime alerts prevent running sideways config in trending market (the #1 killer)
- Session timing tells you when spreads should be wider/tighter
- Alert-service sends Telegram notifications — no need to watch the terminal
- Zero extra cost (public APIs, no RPC needed)

**Why Solana first:**

- Gas is essentially free ($0.0003/TX)
- Sub-second execution (400ms blocks)
- Good liquidity on Raydium/Jupiter
- You can make mistakes cheaply

### Phase 3: Scale Up + Core Edge Stack (Month 2+) — **~$20-50/mo**

```
Chain:     Solana (primary) + Arbitrum (secondary)
DEX:       Jupiter + Uniswap V3
Server:    Hetzner VPS ($5/mo) for 24/7 uptime
Pair:      SOL/USDC + ETH/USDT
Capital:   $100-300
Strategy:  PMM Simple (Solana) + Cross-DEX Arb
Services:  Core 8: regime, session, funding, correlation, inventory, hedge, pnl, alert
           Scanners: alpha-service (token scoring), funding-scanner (multi-pair rates)
RPC:       Free tier (upgrade if hitting limits)
```

**Why add core edge services:**

- Inventory + hedge services automate delta-neutral positioning
- Funding-scanner finds best funding rate opportunities across all Binance pairs
- Alpha-service scores new tokens and sends Telegram alerts
- Correlation-service warns when pair relationships break down
- All free — no API keys, no subscriptions

### Phase 4: Full Edge Stack + Orchestration (Month 3+) — **~$50-100/mo**

```
Chain:     Solana + Arbitrum + Hyperliquid (hedge)
Server:    VPS with 24/7 uptime ($5-24/mo, 8GB RAM recommended)
Strategy:  2-3 controllers + full edge services
           - PMM on SOL/USDC (Solana) + hedge-service (delta-neutral)
           - AMM Arb ETH/USDT (Arbitrum ↔ SushiSwap)
           - lab-service managing experiment tiers
Services:  Core 8: regime, session, funding, correlation, inventory, hedge, pnl, alert
           Scanners 7: alpha, arb, funding-scanner, narrative, rewards, unlock, migration
           Orchestration 3: lab, swarm, clmm
           On-demand: backtest
Capital:   $300-1000
RPC:       Paid if needed ($49/mo)
```

**Why full stack matters:**

- Arb-service catches cross-DEX price gaps in real-time (60s scans)
- Narrative-service detects which crypto themes are gaining momentum
- Swarm-service automates multi-bot deployment from alpha signals
- CLMM-service optimizes concentrated liquidity ranges using regime + session data
- Rewards-service ranks LP pools by risk-adjusted APR
- Migration-service catches new pools and token events within minutes
- Everything publishes to MQTT — alert-service forwards all to Telegram

---

## Cost Optimization Tips

| Tip                                                                        | Savings                           |
| -------------------------------------------------------------------------- | --------------------------------- |
| **Start on Solana** — gas is 100-1000× cheaper than EVM chains             | $50-100/mo                        |
| **Use 0.05% or 0.01% fee pools** on Uniswap V3 for major pairs             | 60-97% less per trade             |
| **Enable `order_refresh_tolerance_pct`** — fewer unnecessary cancellations | Saves gas on every skipped cancel |
| **Increase `filled_order_delay`** — slower but fewer TXs                   | 30-50% gas reduction              |
| **Use Hetzner VPS** instead of AWS/DigitalOcean                            | Save $15-40/mo                    |
| **Free RPC tiers** are enough for 1 bot                                    | Save $49/mo                       |
| **Use native DEX tokens for fee discounts** where available                | Varies                            |
| **Batch token approvals** on a low-gas day                                 | One-time savings                  |
| **Edge services use zero-cost APIs** — no subscriptions needed             | $0 (vs $50-200/mo for data feeds) |
| **Tune scanner intervals** — arb at 60s, narrative at 30min, rewards at 1h | Fewer API calls, same alpha       |
| **Run only services you need** — core 8 first, add scanners as you grow   | Lower RAM, simpler monitoring     |

---

## The Bottom Line

```
Absolute minimum to run 1 real bot + edge services for 1 month:

  Software:        $0
  Edge services:   $0  (20 Python services, free APIs)
  Server (local):  $0
  Gas (Solana):    $0.50
  External APIs:   $0  (DexScreener, Binance, Telegram — all free)
  Initial wallet:  $5 SOL for gas
  ────────────────────────
  Total:           ~$5 to get started (first month, one-time gas deposit)
  Monthly ongoing: ~$1

Compare to alternatives:
  - 3Commas: $49-79/mo (and it's Centralized-only, no edge services)
  - Pionex: Free but limited, Centralized-only, no customization
  - Custom bot (AWS Lambda + code): $20-100/mo + data feed subscriptions
  - Institutional data feeds (Nansen, Santiment): $100-500/mo

Hummingbot + edge services on Solana is the cheapest full-stack
trading setup available. 20 services, zero API costs, zero subscriptions.
```
