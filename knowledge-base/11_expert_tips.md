# 🧠 Expert Tips & Battle-Tested Bot Rules

> Real-world lessons from the Hummingbot community, experienced traders, and expert analysis
> Sources: Reddit, Discord, Hummingbot Academy, Botcamp, YouTube Live sessions, Medium articles

---

## The #1 Rule Everyone Agrees On

> **"There is no optimal configuration that prints money."** — Hummingbot Reddit community
>
> Every profitable setup depends on the current market conditions. What works today may lose money tomorrow. The bot is a tool — your edge comes from understanding _when_ and _how_ to deploy it.

---

## Market-Regime Awareness (Most Important Skill)

The single biggest factor in profitability is matching your settings to the current market regime. Most losses come from running a sideways-market config in a trending market.

### How to Detect the Regime

| Regime                    | Signs                                                                                         | Bot Response                                                   |
| ------------------------- | --------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| **Sideways / Ranging**    | Price bounces between support/resistance, low directional momentum, Bollinger Bands narrowing | ✅ Best for market making. Use standard PMM settings           |
| **Trending Up (Bull)**    | Higher highs, higher lows, price above 20-day MA, strong volume                               | ⚠️ Adjust inventory to accumulate base asset. Widen ask spread |
| **Trending Down (Bear)**  | Lower highs, lower lows, price below 20-day MA                                                | ⚠️ Adjust inventory to sell base asset. Widen bid spread       |
| **High Volatility Spike** | Sudden 5%+ moves, Bollinger Bands expanding rapidly, news-driven                              | 🛑 Widen spreads significantly or pause the bot                |
| **Low Volatility / Dead** | Flat price, tiny candles, minimal volume                                                      | ⚠️ Spreads too thin to profit. Switch pairs or pause           |

### Settings Adjustments by Regime

```yaml
# SIDEWAYS MARKET (Default / Best case)
buy_spreads: "0.003,0.006,0.01"
sell_spreads: "0.003,0.006,0.01"
inventory_target_base_pct: 50              # Keep balanced
stop_loss: 0.02

# BULL MARKET (Accumulate base asset)
buy_spreads: "0.002,0.004,0.008"          # Tighter buys → buy more
sell_spreads: "0.005,0.01,0.015"          # Wider sells → sell less
inventory_target_base_pct: 65             # Favor holding base
stop_loss: 0.025

# BEAR MARKET (Shed base asset)
buy_spreads: "0.005,0.01,0.015"           # Wider buys → buy less
sell_spreads: "0.002,0.004,0.008"         # Tighter sells → sell more
inventory_target_base_pct: 35             # Favor holding quote
stop_loss: 0.015

# HIGH VOLATILITY (Protect capital)
buy_spreads: "0.008,0.015,0.025"          # Very wide
sell_spreads: "0.008,0.015,0.025"
stop_loss: 0.01                            # Tight stop
time_limit: 600                            # 10 min max exposure
```

---

## Spread Rules (Community Consensus)

### Rule 1: Match Spread to Volatility

> "Your spread should be at least 2× the token's typical 5-minute price movement." — Botcamp graduates

| Token Volatility       | Recommended Spread | Why                                 |
| ---------------------- | ------------------ | ----------------------------------- |
| Low (stables, BTC)     | 0.1–0.3%           | Thin margins but frequent fills     |
| Moderate (ETH, SOL)    | 0.3–0.8%           | Good balance of fills and profit    |
| High (mid-caps, memes) | 0.8–2.0%           | Need wide spreads to survive swings |

### Rule 2: Dynamic Spreads > Static Spreads

Expert traders use indicators to auto-adjust spreads rather than fixed values:

| Indicator                 | How to Use                                                         | Hummingbot Controller |
| ------------------------- | ------------------------------------------------------------------ | --------------------- |
| **NATR** (Normalized ATR) | Spread = NATR × multiplier. Widens in volatility, tightens in calm | `pmm_dynamic`         |
| **Bollinger Bands**       | Shift mid-price toward mean; widen spread when bands expand        | `dman_v3`             |
| **Bollinger Band Width**  | If BBW > threshold → pause or widen. Signal of incoming volatility | Custom script         |
| **Volume Profile**        | Place orders at high-volume price nodes where fills are likely     | Custom script         |

### Rule 3: Account for ALL Costs

> Full profit math breakdown: see [06_risk_management](06_risk_management.md#real-profit-math).

Your spread must cover gas + DEX fee + slippage with profit remaining. If gas + fees consume > 70% of gross spread, switch to a cheaper chain or widen spreads.

### Rule 4: The Refresh Tolerance Trick

> "One of the most underrated settings." — Experienced users on Discord

`order_refresh_tolerance_pct` prevents cancelling and replacing orders when price has only moved a tiny bit. This:

- Saves on gas (fewer cancel transactions)
- Maintains your order queue priority
- Recommended: 0.1–0.3% (cancel only if price moved more than this)

---

## Inventory Management (Where Most Beginners Fail)

> Full inventory defenses table and YAML configs: see [06_risk_management](06_risk_management.md#inventory-management) and [05_configurations](05_configurations.md#inventory--regime-add-ons).
> The inventory-service monitors skew and kill-switch via MQTT — see `inventory-service/` in the codebase.

If the market trends in one direction, your bot accumulates a large position in a depreciating asset. This is the #1 way market making bots lose money.

Key defenses: inventory skew (auto-rebalance), ping pong mode (alternate buy/sell), price ceiling/floor (hard range limits), and filled order delay (prevent rapid accumulation).

---

## Arbitrage Rules (From Profitable Arb Runners)

### Rule 1: Speed Beats Everything

> "If your arb bot can't execute in under 2 seconds, someone else will take the opportunity." — Reddit arb trader

- Use Solana or Arbitrum for fastest DEX execution
- Co-locate your bot near the DEX RPC nodes if possible (e.g., AWS/GCP regions matching validator centers)
- Enable `concurrent_orders_submission: true` for simultaneous execution

### Rule 2: The Real Minimum Profitability

Most guides suggest `min_profitability: 0.003` (0.3%), but experienced arb traders say:

| Market              | Real Min Profitability | Why                              |
| ------------------- | ---------------------- | -------------------------------- |
| ETH/USDT (high liq) | 0.15-0.25%             | Very competitive, thin margins   |
| SOL/USDT (Solana)   | 0.2-0.3%               | Fast, but many competitors       |
| Mid-caps            | 0.3-0.8%               | Less competition, wider spreads  |
| New listings        | 1-3%                   | Highest spreads but highest risk |

### Rule 3: Slippage Kills Arb Profits

- Deep DEX slippage buffer: 0.05-0.1% (e.g., Uniswap V3)
- Standard AMM pool slippage buffer: 0.1-0.3%
- **Expert tip**: If a pool has < $500K TVL, add 0.5%+ slippage buffer

### Rule 4: Keep Funds on Both Sides

> The `arb-service` automates cross-DEX price scanning by polling DexScreener every 60s and alerting on spread discrepancies — see [15_edge_systems](15_edge_systems.md#system-8-cross-dex-arbitrage-scanner--implemented).

You need capital pre-deposited on **both** DEXs. Moving funds between them takes time and the arb opportunity will be gone.

```
Capital split for cross-DEX arb:
  DEX 1 wallet: 50% of capital (for the sell side)
  DEX 2 wallet: 50% of capital (for the buy side)
  + Extra gas tokens on-chain
```

---

## Top 10 Mistakes to Avoid

| #   | Mistake                            | What Happens                                           | Fix                                                |
| --- | ---------------------------------- | ------------------------------------------------------ | -------------------------------------------------- |
| 1   | **No stop loss**                   | One bad trade wipes out weeks of gains                 | Always set 2-3% stop loss                          |
| 2   | **Running in a strong trend**      | Inventory accumulates heavily on losing side           | Check regime; pause or adjust skew                 |
| 3   | **Spreads too tight**              | Fees/gas eat all profit; frequent losing trades        | Ensure spread > 2× (gas + fees)                    |
| 4   | **Spreads too wide**               | Orders never fill; bot sits idle                       | Monitor fill rate; tighten if < 2 fills/hour       |
| 5   | **Ignoring gas costs**             | Think you're profitable, but gas nets you negative     | Track net P&L including all gas spent              |
| 6   | **Starting with too much capital** | Amplifies mistakes while still learning                | Start with $50-100, scale up only after profitable |
| 7   | **Not paper trading first**        | Learn expensive lessons with real money                | Paper trade 3-7 days minimum                       |
| 8   | **Set and forget**                 | Market regime changes; bot keeps running losing config | Check bot at least 2× daily                        |
| 9   | **Too many pairs**                 | Capital spread thin, hard to monitor, mediocre results | Focus on 2-3 pairs maximum                         |
| 10  | **No daily P&L tracking**          | Can't tell if strategy is actually working             | Log P&L daily; review weekly                       |

---

## 📈 Data-Driven Trend Spotting for 10-50% Margins

Achieving double-digit daily returns on a $100 budget requires identifying **breakout velocity** before the rest of the market. This isn't gambling; it's filtering for high-probability momentum.

### 1. The Volume-to-Liquidity Ratio (The "Explosion" Filter)

> "If a token has $50k in liquidity but does $500k in volume in 1 hour, a massive move is incoming."

| Metric                     | Bullish Signal | Why                               |
| -------------------------- | -------------- | --------------------------------- |
| **Volume/MCAP**            | > 0.5          | High turnover relative to size    |
| **1H Volume / 24H Volume** | > 20%          | Momentum is accelerating _now_    |
| **Buy/Sell Ratio (1H)**    | > 1.5          | Genuine accumulation taking place |

### 2. Spotting the "Bollinger Squeeze" (V2 Entry)

Use the Hummingbot V2 framework to monitor the **Bollinger Band Width (BBW)**:

- **The Squeeze**: When BBW reaches a 48-hour low, volatility is coiled like a spring.
- **The Breakout**: Enter when price closes outside the band AND the 1-minute volume is 2x the average.
- **Profit Target**: High-volatility DEX tokens often move 10-20% in the first 15 minutes of a squeeze breakout.

### 3. Programmatic Alpha: Scanning for New Pools (Sniping)

If you are running the "Swarm" (Sniping V2), Hummingbot cannot find new tokens on its own. You must build an external script (Python/Node.js) to monitor the blockchain and send an MQTT signal to Hummingbot.

**How to find new tokens on Solana:**

1. **Connect via WebSocket** to a Solana RPC node (e.g., Helius).
2. **Listen to the SPL Token Program**: Use the `logsSubscribe` method and listen to events from the SPL Token Program address (`TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA`).
3. **Parse Logs**: When you see an instruction for `InitializeMint` followed by `CreateAccount`, a new token has been minted.
4. **Trigger Bot**: Grab the mint address, calculate the DEX pair, and send an MQTT payload to your Hummingbot instance.
5. **Note**: Since March 2025, pump.fun tokens graduate to **PumpSwap** (not Raydium) at ~$69K market cap after 800M tokens sold. Monitor PumpSwap factory for these migrations.

**How to find new tokens on Base (Aerodrome):**

1. **Connect via WebSocket** to an Ethereum/Base RPC.
2. **Listen to the Factory Registry**: Monitor the Aerodrome Factory contract (`0x5C3F18F0...1039E37C0`).
3. **Parse Events**: Listen specifically for the `PoolCreated` event.
4. **Trigger Bot**: The event log will output the new Token A, Token B, and the Pool Address. Send this to Hummingbot.

### 4. Narrative-Based Filtering

DEX markets move in waves (AI tokens, Meme coins, L2 infrastructure). The `narrative-service` automates this by scanning DexScreener per narrative keyword, tracking volume across cycles, and alerting on 2x+ volume spikes — see [15_edge_systems](15_edge_systems.md#system-10-narrativesocial-scanner--implemented).

- Identify the **current leading narrative** on Twitter/Discord (or via narrative-service alerts).
- Set up Hummingbot on the top 2-3 tokens in that narrative on Solana.
- Use wide spreads (2-5%) and let the narrative's inherent volatility provide the fills.

---

## 🔥 Hyper-Velocity Rules (Doubling $100 in < 48 Hours)

To hit the 48-hour doubling window, you must stop "Market Making" and start "Momentum Sniping."

### 1. The 20x Leverage Math (Perp DEX)

At 20x leverage, a **1% price move** doubles your position margin. The `funding-scanner-service` scans all Binance Futures funding rates to find the best opportunities — see [15_edge_systems](15_edge_systems.md#system-9-multi-pair-funding-scanner--implemented).

- Use **Hyperliquid** (zero gas fees) for this.
- Target: 5 successful 1% "scalps."
- Risk: A 5% move against you liquidates the $100.

### 2. The "Swarm" Method (10x10)

Split your $100 into 10 separate bot accounts ($10 each).

- Deploy each bot to a different **Trending New Token** on Solana.
- Exit Target: 50% profit.
- Stop Loss: 15%.
- Logic: If only 4 out of 10 bots win, you still double your total capital.

### 3. Sniper Block Logic & Jito MEV

If you are sniffing new pools on Solana:

- **Block 0 is for whales.** You cannot win unless you use **Jito MEV Bundles**.
- **Jito Tips vs. Priority Fees**: Standard priority fees go to the base Solana scheduler. To win a block-0 snipe, you must pay a "Jito Tip" directly to the validator out-of-protocol. This requires custom setups using Jito's Block Engine.
- **The "Block 5-10" Setup**: If you cannot afford massive Jito Tips, aim for Blocks 5-10. This is the sweet spot for $100 bots where the "initial dump" of MEV insiders has finished and the true retail trend begins.

### 4. CEX/DEX Arbitrage on Base

Base and Aerodrome have massive liquidity flows directly tied to Coinbase (via cbBTC and stablecoin flows). The latency between Coinbase Advanced API and Base network on-chain pricing creates tight but frequent CEX/DEX latency arbitrage loops. Use this for lower-risk scalping outside of memecoin swarms.

---

## Advanced Techniques (From Botcamp & Pro Traders)

### Technique 1: Volatility-Adaptive Spreads

Instead of fixed spreads, calculate them from NATR:

```
spread = base_spread + (NATR × multiplier)

Example:
  base_spread = 0.2%
  NATR (14-period) = 0.8%
  multiplier = 1.5
  → spread = 0.2% + (0.8% × 1.5) = 1.4%
```

In Hummingbot, use the `pmm_dynamic` controller which does this automatically.

### Technique 2: Bollinger Band Mid-Price Shifting

Shift your mid-price toward the Bollinger Band mean to increase fill probability:

```
If price is near upper band → shift mid-price down (more sells fill)
If price is near lower band → shift mid-price up (more buys fill)
```

Use the `dman_v3` controller in Hummingbot V2.

### Technique 3: Multi-Timeframe Regime Filter

```
Before placing orders, check:
  1. 4-hour chart: Is there a clear trend? (20 MA direction)
  2. 1-hour chart: Is volatility spiking? (Bollinger Band Width)
  3. 5-minute chart: Is the current range suitable?

Only trade if all three timeframes agree with your strategy assumptions.
```

### Technique 4: Asymmetric Spread Entry

Instead of symmetric spreads, bias toward the side where fills are more likely:

```yaml
# If you expect slight upward drift:
buy_spreads: "0.003,0.006" # Close buys: high probability fills
sell_spreads: "0.005,0.01" # Far sells: hold inventory longer for bigger gain
```

### Technique 5: Time-of-Day Optimization

> Full time-zone config switching schedule and implementation: see [15_edge_systems](15_edge_systems.md#time-zone-config-switching).
> The session-service automates this via MQTT — see `session-service/` in the codebase.

Tighten spreads during active hours (more fills), widen during quiet hours (wider margins).

---

## Checklist Before Going Live

```
Before pressing 'start' on a real-money strategy:

□ Paper traded for at least 3 days?
□ Understand the current market regime (trending/sideways)?
□ Spread covers gas + fees + slippage with profit remaining?
□ Stop loss is set?
□ Inventory skew is enabled?
□ Capital per trade < 2% of total capital?
□ Wallet has enough gas tokens for 100+ transactions?
□ Know how to emergency-stop the bot?
□ Set calendar reminder to check bot in 2 hours?
□ Tracking P&L in a spreadsheet or dashboard?
```
