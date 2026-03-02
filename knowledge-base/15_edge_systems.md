# Custom Edge Systems

> What you build ON TOP of Hummingbot — not configs, but systems that give you an actual edge
> None of this is in the docs. These are architectural patterns that separate profitable traders from the rest.

---

## The Core Problem

95% of Hummingbot users do the same thing:
1. Pick PMM or Arb
2. Choose ETH/USDT or SOL/USDC
3. Set 0.5% spreads
4. Run the bot
5. Check once a day
6. Lose money when the market regime changes
7. Quit

The bot itself is not the edge. Everyone has the same bot. The edge comes from the SYSTEMS you build around it.

---

## System 1: Automated Regime Switching

**Problem it solves**: The #1 killer of bot traders — running a sideways config in a trending market.

**How it works**: A Python script classifies the current market regime every 5-15 minutes and auto-swaps Hummingbot configs via MQTT or file replacement.

### Architecture

```
[Regime Classifier Script] ──MQTT──> [Hummingbot]
       │
       ├── Fetches 1H/4H candle data (via CoinGecko or Binance free API)
       ├── Calculates: NATR, BB Width, Price vs 20MA, Volume ratio
       ├── Classifies: BULL / BEAR / SIDEWAYS / SPIKE
       └── Sends config swap command if regime changed
```

### Classification Logic

```python
def classify_regime(candles_4h):
    natr = calc_natr(candles_4h, period=14)
    bb_width = calc_bb_width(candles_4h, period=20)
    price = candles_4h[-1]['close']
    ma20 = calc_sma(candles_4h, 20)
    vol_ratio = candles_4h[-1]['volume'] / avg_volume(candles_4h, 20)

    if natr > 0.03 or bb_width > 0.06:
        return "SPIKE"
    if price > ma20 * 1.01 and is_higher_highs(candles_4h):
        return "BULL"
    if price < ma20 * 0.99 and is_lower_lows(candles_4h):
        return "BEAR"
    return "SIDEWAYS"
```

### Config Mapping

| Regime | Config Action |
|---|---|
| SIDEWAYS | Standard symmetric PMM (default) |
| BULL | Tighter buys, wider sells, 65% base target |
| BEAR | Wider buys, tighter sells, 35% base target |
| SPIKE | Kill PMM, switch to arb-only OR pause entirely |

### Implementation

- Hummingbot MQTT: Enable EMQX broker, publish config updates to bot topic
- Alternative: Script writes new YAML config → restarts bot via Docker API
- Run as a systemd service or cron job every 5-15 min
- Log every regime change with timestamp for post-analysis

**Why nobody does this**: It requires building custom middleware. Most traders treat the bot as a black box.

**Why it works**: It eliminates the single biggest source of losses — regime mismatch — without requiring any human attention.

---

## System 2: Delta-Neutral Market Making — IMPLEMENTED

> **Implementation**: `hedge-service/` — polls inventory-service spot balance + Hyperliquid perp position, calculates net delta, places hedge orders when threshold exceeded, publishes status to `hbot/hedge/sol_usdc`.

**Problem it solves**: PMM accumulates inventory in trending markets. Even with skew enabled, you still have directional exposure.

**The institutional solution**: Run PMM on spot + hold a proportional hedge on a perp DEX. Net exposure = zero. You earn pure spread profit.

### Architecture

```
[hedge-service] ──polls every 30s──>
    │
    ├── Fetches spot SOL balance via hummingbot-api /portfolio/state (Raydium)
    ├── Fetches perp short size via hummingbot-api /trading/positions (Hyperliquid)
    ├── Calculates net delta (spot - short)
    ├── If |delta| > threshold (0.5 SOL) → places hedge order via /trading/orders
    └── Publishes status to MQTT: hbot/hedge/sol_usdc
```

### Key Parameters (hedge-service/config.py)

| Parameter | Default | Purpose |
|---|---|---|
| `delta_threshold` | 0.5 SOL | Minimum delta before hedging |
| `max_hedge_order_size` | 10.0 | Max single order size |
| `hedge_leverage` | 5x | Hyperliquid margin leverage |
| `max_position_size` | 50.0 | Safety cap on total short |
| `cooldown_seconds` | 10 | Prevents rapid-fire orders |

### Capital Split

```
$100 total:
  $70 → Raydium PMM (split into SOL + USDC)
  $30 → Hyperliquid margin (at 5x leverage = $150 hedging capacity)
```

### The Math

```
PMM spread capture: ~$0.50/day (conservative on $70 capital)
Hedge cost (funding): ~$0.05/day (typical funding rate)
Gas (Solana PMM): ~$0.01/day
Net: ~$0.44/day, REGARDLESS of market direction
```

**The key insight**: Unhedged PMM is profitable only in sideways markets (~40% of the time). Delta-neutral PMM is profitable in ALL regimes.

### When Funding Rates Work FOR You

When market is euphoric, perp funding rates go highly positive (longs pay shorts). Your hedge is a short — so you get PAID to hedge. The funding-service monitors this and adjusts spread bias accordingly.

---

## System 3: The Lab Framework — IMPLEMENTED

> **Implementation**: `lab-service/` — MQTT-driven experiment manager. Subscribes to `hbot/analytics/#` for PnL data and `hbot/lab/cmd/#` for commands. Auto-evaluates kill criteria, recommends promotions, persists to `experiments.json`.

**Problem it solves**: Most traders never find their edge because they never systematically search for it.

**The approach**: Treat trading like science. Hypothesis → Test → Measure → Iterate.

### Portfolio Tiers

```
PRODUCTION (70% of capital)
  └── Proven strategies with 30+ days of positive data

TESTING (20% of capital)
  └── New strategies, 72-hour trial period

EXPLORATION (10% of capital)
  └── Wild experiments, disposable capital
```

### MQTT Commands

| Command | Topic | Payload |
|---|---|---|
| Create | `hbot/lab/cmd/create` | `{hypothesis, pair, tier, capital, config_ref, trial_hours, kill_criteria, success_criteria}` |
| Kill | `hbot/lab/cmd/kill` | `{id, reason}` |
| Promote | `hbot/lab/cmd/promote` | `{id}` |

### Auto-Evaluation (every 5 min)

**Kill criteria** (auto-enforced):
- Total PnL exceeds max loss (default: -$5)
- Max drawdown exceeded (default: 10%)
- Trial expired unprofitable (default: 72 hours)

**Promotion criteria** (logged as recommendation, operator must send promote command):
- Daily PnL above threshold (default: $0.30)
- Win rate above minimum (default: 40%)
- Consecutive profitable days met (default: 3)

### Weekly Rotation Protocol

1. **Sunday evening**: Review lab status on `hbot/lab/{pair}`
2. **Promote**: Send promote command for winning experiments
3. **Kill**: Auto-killed by service, or manual kill with reason
4. **Mutate**: Take best Production configs, adjust 1 parameter, deploy to Testing
5. **Explore**: Launch 1-2 new Exploration experiments

---

## System 4: Backtesting Pipeline

**Problem it solves**: Deploying configs without testing them is gambling, not trading.

### Pipeline

```
1. COLLECT DATA
   └── Historical candle data from CoinGecko/Binance free API
   └── Store in CSV or SQLite
   └── Target: 30-90 days of 1-min candles per pair

2. PARAMETER SWEEP
   └── Use Hummingbot V2 backtester
   └── Test spread combinations: 0.2%, 0.3%, 0.5%, 0.8%, 1.0%, 1.5%
   └── Test refresh times: 15s, 30s, 60s, 120s
   └── Test stop-loss: 1%, 2%, 3%, 5%
   └── That's 6×4×4 = 96 combinations per pair

3. RANK RESULTS
   └── Sort by Sharpe ratio (return / risk), NOT just total return
   └── Filter: only configs with > 100 trades (statistical significance)
   └── Top 3 configs per pair → Testing tier in Lab Framework

4. REGIME-SEGMENT ANALYSIS
   └── Split historical data by regime (bull/bear/sideways)
   └── Find best configs PER REGIME
   └── Feed these into the Regime Switching system (System 1)
```

### The V2 Backtester

Hummingbot V2 has a built-in backtesting engine (40%+ faster since v2.5 improvements):

```python
# In a Hummingbot V2 script, you can backtest controllers:
from hummingbot.strategy_v2.backtesting import BacktestingEngine

engine = BacktestingEngine()
results = engine.run(
    controller_config="pmm_simple_config.yml",
    start_time="2025-12-01",
    end_time="2026-01-31"
)
print(results.sharpe_ratio, results.total_pnl, results.max_drawdown)
```

### Why Most Users Skip This

- "Boring" compared to live trading
- Requires collecting data
- Requires writing scripts to automate sweeps
- Results might show your favorite strategy doesn't actually work

The last point is exactly why you SHOULD do it.

---

## System 5: AI Alpha Pipeline — IMPLEMENTED (Phase 1)

> **Implementation**: `alpha-service/` — polls DexScreener API every 15min, scores Solana pairs on 6-criteria rubric, publishes signals to `hbot/alpha/signal/{TOKEN}` and new listing alerts to `hbot/alpha/new_listing/{TOKEN}`. Alert-service forwards to Telegram.

**Problem it solves**: Human traders check DexScreener once a day. The market moves in minutes.

**Leverages your existing tools**: You have Claude Code + MCP servers (serper for web search, playwright for browser automation, memory for persistence).

### Architecture

```
[alpha-service] ──polls every 15min──>
    │
    ├── GET DexScreener search API (free, no key)
    ├── Filter: chainId == "solana"
    │
    └── [scorer.py — 6-criteria rubric]
          ├── Volume/MCAP ratio > 0.5? (+3 points)
          ├── 1H volume > 20% of 24H volume? (+2 points, momentum accelerating)
          ├── Buy/sell ratio > 1.5? (+2 points, genuine accumulation)
          ├── Has socials/websites (verified proxy)? (+1 point)
          ├── Liquidity > $50K? (+1 point, minimum threshold)
          ├── Social mentions rising? (+0 placeholder for Phase 1)
          └── Score >= 7? → Publish signal via MQTT
                │
                ├── hbot/alpha/signal/{TOKEN} (scored tokens)
                └── hbot/alpha/new_listing/{TOKEN} (pairs < 48h old, liq > $50K)
```

### Implementation Phases

**Phase 1** (simple): Cron script that checks DexScreener API for volume spikes, sends alerts to your phone. You manually decide whether to deploy a bot.

**Phase 2** (semi-auto): Script scores tokens and suggests configs. You approve with one click.

**Phase 3** (full auto): Script deploys bots automatically on high-conviction signals. Full "Swarm" approach — $10 per token, 10 concurrent bots.

### Data Sources (Free)

| Source | What | How to Access |
|---|---|---|
| DexScreener | Trending pairs, volume, liquidity | Free API or Playwright scrape |
| Birdeye | Solana token analytics | Free API |
| CoinGecko | Price data, trending | Free API |
| Solana RPC | New pool events | WebSocket (free tier) |
| Twitter/X | Social sentiment | Serper search API |

---

## System 6: Timing & Niche Edges — IMPLEMENTED

### Time-Zone Config Switching

Crypto markets have predictable activity cycles. Exploit them:

```
Schedule (UTC):
  00:00-04:00 → "Night" config  (wide spreads 1.5%, few competitors)
  04:00-08:00 → "Asia" config   (moderate spreads 0.8%, Asian volume)
  08:00-14:00 → "EU" config     (tight spreads 0.5%, EU + Asia overlap)
  14:00-20:00 → "US" config     (tight spreads 0.5%, highest volume)
  20:00-00:00 → "Evening" config (moderate spreads 0.8%, declining volume)
```

Implementation: Simple cron job that swaps YAML configs on schedule. Takes 30 minutes to set up.

### New Token Market Making (First 48 Hours) — IMPLEMENTED

> **Implementation**: Covered by `alpha-service/` — `is_new_listing()` in `scorer.py` detects pairs created < 48h ago with liquidity > $50K. Publishes to `hbot/alpha/new_listing/{TOKEN}` for Telegram alerts via alert-service. Phase 1: scan + alert only, no auto deployment.

When a token first lists on a DEX, spreads are 5-20% because no bots are providing liquidity yet.

```
Window:  First 24-48 hours after listing
Spread:  3-8% (still tighter than the native spread, so you earn fills)
Capital: $5-10 per token (tiny, disposable)
Filter:  Only tokens passing the 60-second screen (14_skills.md)
Exit:    After 48H or if liquidity drops below $20K
```

You're essentially being paid to provide a service (liquidity) that nobody else is providing yet. The risk is the token dies — which is why you use tiny capital and strict screening.

### Funding Rate Harvesting

When perp funding rates spike (>0.05% per 8H), shorts get paid:

```
Signal:  Hyperliquid SOL-USD funding rate > 0.05% per 8H
Action:
  1. Buy $50 of SOL on Raydium (spot)
  2. Short $50 of SOL-USD on Hyperliquid (1x leverage, fully funded)
  3. Net exposure: ZERO (spot + short cancel out)
  4. Income: funding rate payments every 8 hours

Math at 0.1% funding rate:
  $50 × 0.1% × 3 payments/day = $0.15/day = $4.50/month on $50
  Annualized: ~108% APR, delta-neutral

Exit when funding rate drops below 0.02% (no longer worth it)
```

Monitor funding rates at: coinglass.com or Hyperliquid's own dashboard.

### Token Unlock Calendar — IMPLEMENTED

> **Implementation**: `unlock-service/` — reads operator-maintained `unlocks.json`, classifies each entry as PRE_UNLOCK / POST_UNLOCK / UPCOMING / EXPIRED / INSIGNIFICANT. Publishes spread multiplier recommendations to `hbot/unlock/pre/{pair}` and `hbot/unlock/post/{pair}`. Alert-service forwards to Telegram with hours-until/since and spread adjustments.

Large token unlocks create predictable sell pressure:

```
Tools: TokenUnlocks.app, CryptoRank unlocks calendar
Signal: Major unlock (>2% of supply) within 48 hours

Pre-unlock (24H before):
  - Widen buy spreads (expect selling pressure) — buy_spread_mult: 1.5x
  - Tighten sell spreads (help sell inventory faster) — sell_spread_mult: 0.8x
  - Consider directional short on perp DEX

Post-unlock (if price dropped):
  - Mean reversion opportunity
  - Tighten buy spreads to accumulate at discounted price — buy_spread_mult: 0.8x
  - Set trailing take-profit at 2-5%
```

---

## System 7: Self-Improving Data Flywheel

Every trade generates data. Most traders ignore it. Build a system that LEARNS from it.

### The Flywheel

```
TRADE → COLLECT DATA → ANALYZE → ADJUST → TRADE (improved)
  ↑                                           │
  └───────────────────────────────────────────┘
```

### What to Collect

Hummingbot saves trades to CSV/PostgreSQL. For each trade, record:
- Timestamp, pair, side, price, amount
- Market regime at time of trade (from your classifier)
- Spread at time of fill
- Time between order placement and fill
- Slippage (expected vs actual)
- Outcome (profit/loss amount)

### Weekly Analysis Script

```python
# Pseudo-code for weekly analysis
trades = load_from_postgres(last_7_days)

# Which regime produced best results?
by_regime = trades.groupby('regime').agg({'pnl': ['sum', 'mean', 'count']})

# Which spread settings had best risk-adjusted returns?
by_spread = trades.groupby('spread_pct').agg({'pnl': 'sum', 'pnl_std': 'std'})
by_spread['sharpe'] = by_spread['pnl_sum'] / by_spread['pnl_std']

# Which time of day is most profitable?
by_hour = trades.groupby(trades['timestamp'].dt.hour).agg({'pnl': 'sum'})

# Which pairs are actually making money?
by_pair = trades.groupby('pair').agg({'pnl': 'sum', 'fill_count': 'count'})

# Output: recommended adjustments for next week
```

### The Compounding Effect

- Week 1: Random guessing, 50% of configs lose money
- Week 4: Killed losers, doubled down on winners
- Week 8: Configs refined by 2 months of data. Sharpe ratio improving
- Week 12: Your Production tier is genuinely optimized for current market

This is what quantitative hedge funds do. They don't guess — they measure, iterate, and let data drive decisions. You can do the same thing at micro-scale.

---

## System 8: Cross-DEX Arbitrage Scanner — IMPLEMENTED

> **Implementation**: `arb-service/` — polls DexScreener `/tokens/{address}` every 60s for a watchlist of Solana tokens, groups pairs by DEX, finds price discrepancies. Publishes to `hbot/arb/{TOKEN}`.

**Problem it solves**: Same token trades at different prices across Raydium, Orca, Meteora, etc. By the time you manually check, the gap is gone.

### How It Works

```
[arb-service] ──polls every 60s──>
    │
    ├── Reads tokens.json (operator-maintained watchlist with addresses)
    ├── GET DexScreener /tokens/{address} for each token
    ├── Groups Solana pairs by DEX (keeps best-liquidity pair per DEX)
    ├── Compares all DEX pairs pairwise: spread_pct = |price_a - price_b| / min(a, b) * 100
    ├── Filters: spread > min_arb_pct (0.5%), both pools > min_liquidity ($5K)
    └── Publishes: hbot/arb/{TOKEN} with buy_dex, sell_dex, spread_pct, max_size_usd
```

### Key Parameters (arb-service/config.py)

| Parameter | Default | Purpose |
|---|---|---|
| `poll_interval_seconds` | 60 | Scan frequency |
| `min_arb_pct` | 0.5% | Minimum spread to alert |
| `min_liquidity` | $5,000 | Both pools must meet this |
| `min_dex_count` | 2 | Need 2+ DEXs listing the token |

---

## System 9: Multi-Pair Funding Scanner — IMPLEMENTED

> **Implementation**: `funding-scanner-service/` — fetches ALL Binance Futures funding rates in a single API call, filters a configurable watchlist, classifies HIGH/EXTREME, publishes per-symbol + ranked summary to `hbot/funding_scan/{SYMBOL}`.

**Problem it solves**: `funding-service` monitors a single pair. This scans the entire futures market to find the best funding rate harvesting opportunities across all watched symbols.

### How It Works

```
[funding-scanner-service] ──polls every 5min──>
    │
    ├── GET Binance /fapi/v1/premiumIndex (returns ALL symbols in one call)
    ├── Filters to watch_symbols list (SOLUSDT, WIFUSDT, JUPUSDT, etc.)
    ├── Classifies: HIGH (> 0.03%), EXTREME (> 0.1%)
    ├── Calculates annualized APR: rate × 3 × 365 × 100
    ├── Filters: annualized_apr >= min_annualized_apr (30%)
    └── Publishes: hbot/funding_scan/{SYMBOL} + hbot/funding_scan/summary (ranked)
```

---

## System 10: Narrative/Social Scanner — IMPLEMENTED

> **Implementation**: `narrative-service/` — searches DexScreener by narrative keywords (AI, RWA, MEME, etc.) every 30min, tracks volume across cycles, detects 2x+ volume spikes. Publishes to `hbot/narrative/{CATEGORY}/{TOKEN}`.

**Problem it solves**: Crypto moves in narrative waves (AI tokens, meme coins, RWA, DePIN). Retail traders notice narratives too late. This detects which narratives are gaining momentum before they peak.

### How It Works

```
[narrative-service] ──polls every 30min──>
    │
    ├── Reads narratives.json (categories with keywords + token mappings)
    ├── Searches DexScreener for each keyword, filters Solana pairs
    ├── Scores each token: volume, liquidity, price changes
    ├── Tracks prev_volume per token across cycles
    ├── Detects volume spikes: current_vol / prev_vol >= min_volume_spike (2x)
    └── Publishes: hbot/narrative/{CATEGORY}/{TOKEN} with score, spike_mult, volumes
```

### Seed Narratives (narratives.json)

AI, RWA, MEME, DEPIN, LST, GAMING — each with keyword→token mappings. Operator adds/removes narratives as market trends shift.

---

## System 11: Multi-Pair Bot Swarm — IMPLEMENTED

> **Implementation**: `swarm-service/` — subscribes to `hbot/alpha/#`, buffers signals, evaluates deployment eligibility, manages bot lifecycle RECOMMENDED→ACTIVE→EXPIRED/KILLED. Publishes to `hbot/swarm/deploy/{TOKEN}` and `hbot/swarm/status`.

**Problem it solves**: Alpha signals arrive faster than humans can deploy bots. The swarm manager evaluates signals and manages a fleet of small bots automatically.

### How It Works

```
[swarm-service] ──subscribes to hbot/alpha/#──>
    │
    ├── Buffers incoming alpha signals
    ├── Every 5min, evaluates pending signals:
    │   ├── Score >= min_alpha_score (7)?
    │   ├── Liquidity >= min_liquidity ($30K)?
    │   ├── Capital available? (total_swarm_capital / capital_per_bot)
    │   └── Not already deployed (dedup)?
    ├── Creates bot entries: RECOMMENDED status (auto_deploy=false by default)
    ├── Evaluates active bots: TTL expired (48h)? Loss exceeded (20%)?
    └── Publishes: deploy recommendations + swarm status dashboard
```

### Key Parameters

| Parameter | Default | Purpose |
|---|---|---|
| `max_active_bots` | 50 | Fleet size cap |
| `capital_per_bot` | $10 | Tiny, disposable capital per token |
| `total_swarm_capital` | $500 | Total swarm budget |
| `bot_ttl_hours` | 48 | Auto-expire bots after 48h |
| `kill_loss_pct` | 20% | Kill bot if loss exceeds this |
| `auto_deploy` | false | Phase 1: recommend only |

---

## System 12: CLMM Range Optimizer — IMPLEMENTED

> **Implementation**: `clmm-service/` — subscribes to regime and session signals, fetches live price from Binance, computes optimal concentrated liquidity range using regime/session/volatility multipliers. Publishes rebalance recommendations to `hbot/clmm/{pair}`.

**Problem it solves**: Concentrated liquidity (CLMM) positions go out of range constantly. Most LPs set static ranges and bleed impermanent loss. This dynamically adjusts range based on market conditions.

### How It Works

```
[clmm-service] ──subscribes to hbot/regime/# + hbot/session/#──>
    │
    ├── Receives regime (BULL/BEAR/SIDEWAYS/SPIKE) and session (US/EU/ASIA/NIGHT)
    ├── Fetches live price from Binance every 2min
    ├── Calculates optimal range:
    │   ├── base_range = price × base_range_pct (2%)
    │   ├── regime_mult: SIDEWAYS=0.5x (tight), SPIKE=2.5x (wide)
    │   ├── session_mult: US=0.8x (tight, high volume), NIGHT=1.5x (wide)
    │   └── lower/upper = price ± (base_range × regime_mult × session_mult)
    ├── Calculates range utilization (how centered price is)
    ├── If utilization < 70% → recommend rebalance
    └── Publishes: hbot/clmm/{pair} with range, utilization, rebalance flag
```

---

## System 13: Airdrop & Migration Monitor — IMPLEMENTED

> **Implementation**: `migration-service/` — dual function: monitors operator-maintained events.json for scheduled token events (airdrops, migrations, launches), AND scans DexScreener for brand-new Solana pools (<60min old). Publishes to `hbot/migration/event/{TOKEN}` and `hbot/migration/new_pool/{TOKEN}`.

**Problem it solves**: Token migrations, airdrops, and new pool launches create temporary inefficiencies. Most traders miss them entirely or notice hours late.

### How It Works

```
[migration-service] ──polls every 5min──>
    │
    ├── SCHEDULED EVENTS (events.json):
    │   ├── Reads operator-maintained event list (airdrop, migration, launch, listing)
    │   ├── Classifies: UPCOMING (>24h) / ACTIVE (within 24h) / POST_EVENT (0-48h after) / EXPIRED
    │   └── Publishes: hbot/migration/event/{TOKEN}
    │
    └── NEW POOL DETECTION:
        ├── Searches DexScreener for trending Solana tokens
        ├── Filters: pairCreatedAt < 60 minutes ago
        ├── Min thresholds: liquidity > $5K, volume > $1K
        └── Publishes: hbot/migration/new_pool/{TOKEN}
```

---

## System 14: LP Reward Tracker — IMPLEMENTED

> **Implementation**: `rewards-service/` — reads operator-maintained pools.json, fetches live volume/liquidity from DexScreener, calculates effective APR (fees + rewards), risk-adjusts by pool risk score, ranks and publishes to `hbot/rewards/{TOKEN}` and `hbot/rewards/summary`.

**Problem it solves**: LP reward programs change constantly. Manually checking Raydium, Meteora, Orca dashboards is slow. This ranks all tracked pools by risk-adjusted APR automatically.

### How It Works

```
[rewards-service] ──polls every 1h──>
    │
    ├── Reads pools.json (operator-maintained: token, pair, dex, reward_token, reward_apr, risk_score)
    ├── Fetches live volume/liquidity from DexScreener for each pool
    ├── Calculates:
    │   ├── fee_apr = (volume_24h × fee_tier / 100) / liquidity × 365 × 100
    │   ├── effective_apr = fee_apr + reward_apr
    │   └── risk_adjusted_apr = effective_apr / (1 + risk_score × 0.1)
    ├── Filters: effective_apr >= 20%, liquidity >= $10K, risk_score <= 8
    ├── Ranks by risk_adjusted_apr
    └── Publishes: hbot/rewards/{TOKEN} + hbot/rewards/summary (top 5)
```

---

## Implementation Status

| # | System | Status | Service |
|---|---|---|---|
| 1 | Regime Switching | IMPLEMENTED | `regime-service/` |
| 2 | Delta-Neutral MM | IMPLEMENTED | `hedge-service/` |
| 3 | Lab Framework | IMPLEMENTED | `lab-service/` |
| 4 | Backtesting Pipeline | IMPLEMENTED | `backtest-service/` |
| 5 | AI Alpha Pipeline | IMPLEMENTED (Phase 1) | `alpha-service/` |
| 6 | Timing & Niche Edges | IMPLEMENTED | `session-service/`, `funding-service/`, `alpha-service/`, `unlock-service/` |
| 7 | Data Flywheel | IMPLEMENTED | `pnl-service/` + `alert-service/` |
| 8 | Cross-DEX Arb Scanner | IMPLEMENTED | `arb-service/` |
| 9 | Multi-Pair Funding Scanner | IMPLEMENTED | `funding-scanner-service/` |
| 10 | Narrative/Social Scanner | IMPLEMENTED | `narrative-service/` |
| 11 | Multi-Pair Bot Swarm | IMPLEMENTED (Phase 1) | `swarm-service/` |
| 12 | CLMM Range Optimizer | IMPLEMENTED | `clmm-service/` |
| 13 | Airdrop & Migration Monitor | IMPLEMENTED | `migration-service/` |
| 14 | LP Reward Tracker | IMPLEMENTED | `rewards-service/` |

Supporting services: `inventory-service/`, `correlation-service/`, `alert-service/` (Telegram alerts for all 14 systems).

---

## The Meta-Lesson

The bot is a commodity. Everyone has it. The edge is in:

1. **WHAT** you trade (token selection, niche markets nobody else is in)
2. **WHEN** you trade (regime awareness, timing, event-driven)
3. **HOW** you manage risk (delta-neutral hedging, kill criteria, drawdown limits)
4. **HOW FAST** you adapt (data flywheel, automated regime switching, Lab rotation)

Build systems around these four dimensions. The bot is just the execution layer.
