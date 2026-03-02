# 🛡️ Risk Management

> Position sizing, stop losses, drawdown limits, and survival rules
> See also: [11_expert_tips](11_expert_tips.md) for battle-tested rules from the community

---

## The Golden Rules

1. **Never risk more than 2% of total capital on a single trade**
2. **Always set a stop loss** — no exceptions
3. **Start with paper trading** before real money
4. **Keep 20% of capital in reserve** for opportunities
5. **Set a maximum drawdown** — stop the bot at 10% account loss
6. **Diversify** across 2-3 strategies and 2-3 pairs minimum
7. **Monitor daily** — bots are not truly "set and forget"
8. **Factor in gas costs** — they eat thin margins fast

---

## Position Sizing

### By Account Size

| Account Size   | Max Per Trade | Max Open Positions | Max Daily Loss | Max Drawdown |
| -------------- | ------------- | ------------------ | -------------- | ------------ |
| $100 (Starter) | 10% ($10)     | 2                  | 5% ($5)        | 15% ($15)    |
| $500           | 5% ($25)      | 3                  | 3% ($15)       | 10% ($50)    |
| $1,000         | 3% ($30)      | 4                  | 2% ($20)       | 8% ($80)     |
| $5,000+        | 2% ($100+)    | 5                  | 1.5% ($75+)    | 6% ($300+)   |

### Capital Allocation Across Strategies

| Profile      | Strategy 1 | Strategy 2     | Strategy 3     | Reserve |
| ------------ | ---------- | -------------- | -------------- | ------- |
| Conservative | PMM 40%    | Stable Arb 30% | —              | 30%     |
| Balanced     | PMM 30%    | AMM Arb 25%    | Stable Arb 25% | 20%     |
| Aggressive   | XEMM 25%   | AMM Arb 25%    | CLMM 25%       | 25%     |

---

## Inventory Management

The #1 way market making bots lose money is **inventory accumulation** in trending markets. Use these defenses:

| Defense                 | What It Does                                                      | When to Use                            |
| ----------------------- | ----------------------------------------------------------------- | -------------------------------------- |
| **Inventory Skew**      | Auto-adjusts order sizes to maintain target base/quote ratio      | Always (default: 50/50)                |
| **Ping Pong**           | After buy fills, only place sell (and vice versa)                 | Sideways markets                       |
| **Price Ceiling/Floor** | Hard limits — stop buying above ceiling, stop selling below floor | When you have clear support/resistance |
| **Filled Order Delay**  | Wait N seconds after fill before new orders                       | High volatility (30-120s)              |
| **Regime-Based Skew**   | Shift target to 65% base (bull) or 35% base (bear)                | When you have a directional view       |
| **Delta-Neutral Hedge** | Offset spot inventory with perp short on Hyperliquid             | Always (eliminates directional risk)   |

> Full YAML configs: see [05_configurations](05_configurations.md#inventory--regime-add-ons)
> Automated monitoring: `inventory-service/` publishes skew + kill-switch to MQTT
> Delta-neutral hedging: `hedge-service/` maintains offsetting Hyperliquid short — see [15_edge_systems](15_edge_systems.md#system-2-delta-neutral-market-making--implemented)

---

## Real Profit Math

Many beginners assume spread = profit. It's not. Always calculate net:

```
Net Profit = Gross Spread - Gas Cost - DEX Fees - Slippage

Example: SOL/USDC PMM on Solana (Raydium), 0.5% spread, $20 per order
  Gross:    $20 × 0.5% = $0.10
  Gas:      -$0.005 (Solana)
  DEX fee:  -$0.05 (Raydium 0.25%)
  Slippage: -$0.01
  ─────────────────────
  Net:      $0.035 per completed cycle

→ Gas fees should be funded separately as infrastructure costs rather than deducted from your $100 core trading capital.
→ Not every cycle completes (orders may not fill)
→ Trending markets can cause inventory losses that dwarf spread profit
```

> 💡 If gas + fees consume > 70% of your gross spread, switch to a cheaper chain or widen spreads.

---

## Stop Loss & Take Profit Settings

### By Strategy Type

| Strategy           | Stop Loss     | Take Profit     | Time Limit  | Trailing Stop                 |
| ------------------ | ------------- | --------------- | ----------- | ----------------------------- |
| PMM Conservative   | 3%            | 2%              | 1 hour      | 0.5% trail after 1% profit    |
| PMM Moderate       | 2%            | 1.5%            | 30 min      | 0.3% trail after 0.8%         |
| PMM Aggressive     | 1.5%          | 1%              | 15 min      | 0.2% trail after 0.5%         |
| AMM Arbitrage      | 1%            | N/A (per-trade) | N/A         | N/A                           |
| XEMM               | 2%            | 1%              | 1 hour      | 0.5% trail                    |
| Stablecoin Arb     | 0.5%          | N/A (per-trade) | N/A         | N/A                           |
| CLMM LP            | 5% IL trigger | Rebalance       | 24 hours    | Rebalance at range edge       |
| **Directional V2** | **5%**        | **10-50%**      | **4 hours** | **3% trail after 15% profit** |

### Stop Loss YAML Template

```yaml
# Include these in any strategy config
stop_loss: 0.03 # 3% max loss per position
take_profit: 0.02 # 2% profit target
time_limit: 3600 # Close after 1 hour max
trailing_stop:
  activation_price: 0.01 # Activate after 1% profit
  trailing_delta: 0.005 # Trail by 0.5%
```

---

## Risk Scenarios & Responses

### Scenario 1: Flash Crash (Price drops 10%+ in minutes)

- **What happens**: PMM buy orders fill rapidly, accumulating inventory
- **Protection**: Stop loss triggers, time limit closes positions
- **Prevention**: Use `inventory_skew_enabled: true`, set `price_floor`

### Scenario 2: Gas Spike (Ethereum L1 gas 500+ gwei)

- **What happens**: Arbitrage becomes unprofitable, transactions may fail
- **Protection**: `min_profitability` threshold filters unprofitable trades
- **Prevention**: Trade on L2s (Arbitrum, Base) or Solana

### Scenario 3: DEX Liquidity Drain

- **What happens**: Large withdrawal from LP pool increases slippage
- **Protection**: `slippage_buffer` prevents execution at bad prices
- **Prevention**: Trade on high-TVL pools only ($1M+ TVL)

### Scenario 4: API/Connection Failure

- **What happens**: Bot can't place/cancel orders, positions may be left open
- **Protection**: Time limits auto-close stale positions
- **Prevention**: Monitor uptime, set alerts, use `docker restart` policies

### Scenario 5: Sandwich Attack (MEV)

- **What happens**: MEV bot front-runs your DEX swap, increasing cost
- **Protection**: Use DEX aggregators (Jupiter) with MEV protection
- **Prevention**: Set low slippage tolerance (0.5%), use private mempools if available

---

## 🚀 Hyper-Velocity Risk Control (For < 48H Doubling)

When attempting to double $100 in under 48 hours using Leveraged Perps or Liquidity Sniping, your risk of a `-100% drawdown` (liquidation) becomes exponentially higher. You must use specialized risk structures.

### 1. Leveraged Perps (Hyperliquid at 20x)

- **The Math**: At 20x leverage, a 5% move against you equals total liquidation of the $100.
- **Stop Loss Rule**: Your Stop-Loss MUST be executed by the exchange (dYdX/Hyperliquid), not your bot. Set a hard exchange-side limit stop at **2% maximum adverse excursion** (which equals a 40% account loss).
- **Zero Averaging Down**: Do not use DCA or "Inventory Skew" on a losing 20x leveraged position. You will be wiped out instantly if the trend continues.

### 2. Liquidity Sniping & "The Swarm" (Spot DEX)

- **The Math**: 90% of newly launched pools are scams, rug pulls, or slow bleeds.
- **The Swarm Guard**: If using the "Swarm Method" (10 bots with $10 each), treat each $10 deployment as disposable. Set a `-20%` stop-loss ($2 loss per bad snipe).
- **Time-Based Execution**: If a sniped tokens fails to double (100% gain) in the first 15 minutes of launch, exit immediately at market price. New pools that stall early generally die.

---

## 🦅 High-Alpha Risk Control (For 10-50% Targets)

Targeting 10-50% daily margins on a small $100 budget requires a **"Sniper" mindset** rather than a "Market Maker" mindset.

### 1. The 1:3 Risk/Reward Ratio

For every trade where you set a **5% Stop Loss**, your **Take Profit** must be at least **15%**.

- If you win only 30% of your trades, you will still be significantly profitable.
- Never enter a high-alpha trade if the technical data doesn't support at least a 10% move (use Bollinger Width as a volatility proxy).

### 2. Time-Based Stops (Avoid the "Slow Bleed")

- Trend following on DEXs is about immediate momentum.
- If the trade hasn't moved 3% in your favor within 30 minutes, **close it**. Stagnation in a high-volatility token often precedes a massive dump.

### 3. Maximum Drawdown for $100 Accounts

When chasing 10-50% daily, your risk of drawdown is amplified.

- **Hard Daily Stop**: If you lose $10 (10% of your $100) in a single day, **immediately exit all positions**.
- Market context has clearly shifted, and your data model is no longer accurate for current conditions.

### 4. Zero Lag Execution

- Use the **Hummingbot V2 Framework** executors (PositionExecutor / DCAExecutor).
- These run logic on every candle tick—far faster than manual trading—ensuring your 5% stop is hit the second the price crosses it.

---

## Daily Monitoring Checklist

Most of this is automated by the edge services via MQTT + Telegram alerts. See [15_edge_systems](15_edge_systems.md) for full architecture.

```
□ Check bot status (running, no errors)
□ Review P&L for last 24 hours              ← pnl-service + alert-service
□ Check inventory balance (not too skewed?)  ← inventory-service (auto kill-switch)
□ Check hedge ratio (delta-neutral?)         ← hedge-service
□ Verify gas costs haven't spiked
□ Review any stopped/failed trades
□ Check exchange connectivity
□ Assess market regime                       ← regime-service (auto alerts on change)
□ Review lab experiments                     ← lab-service (auto-kills, promotion alerts)
□ Check funding rate opportunities           ← funding-scanner-service (multi-pair scan)
□ Review alpha signals & new listings        ← alpha-service + swarm-service
□ Check CLMM range utilization              ← clmm-service (auto rebalance alerts)
□ Review token unlock calendar              ← unlock-service (pre/post spread adjustments)
```

### Hummingbot Commands for Monitoring

```bash
status              # Current bot status and active orders
balance             # Connected exchange balances
history             # Trade history and P&L
open_orders         # View all active orders
pnl                 # Profit and loss summary
```

---

## When to Stop the Bot

**Immediately stop** if any of these occur:

- Account drawdown exceeds your max limit (e.g., 10%)
- Gas costs consistently eat more than 30% of profits
- Strategy hasn't been profitable for 3+ consecutive days
- Major market event (black swan, exchange hack, regulatory news)
- You don't understand why the bot is making certain trades
- Connection issues causing repeated failed transactions
- Market regime has clearly shifted (e.g., sideways → strong trend) and you haven't adjusted
- Inventory skew has reached extreme levels (>80% one asset)

### Emergency Stop Commands

```bash
# Inside Hummingbot CLI
stop                    # Stop active strategy
exit                    # Exit Hummingbot

# From Docker (outside)
docker stop hummingbot
docker stop gateway
```
