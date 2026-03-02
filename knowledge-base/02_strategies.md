# 🎯 Trading Strategies Overview

> Ranking, comparison, and details for each Hummingbot strategy
> See [05_configurations](05_configurations.md) for ready-to-use YAML templates

---

## Strategy Comparison Matrix

| Strategy           | Difficulty   | Capital Needed | Expected Return      | Risk     | Best Market       |
| ------------------ | ------------ | -------------- | -------------------- | -------- | ----------------- |
| **PMM Simple**     | Beginner     | $100+          | 0.1-0.3%/cycle       | Medium   | Sideways/Range    |
| **Stablecoin Arb** | Beginner     | $100+          | 0.05-0.2%/trade      | Very Low | All               |
| **AMM Arbitrage**  | Intermediate | $100+          | 0.1-0.5%/trade       | Medium   | Volatile          |
| **XEMM V2**        | Intermediate | $100+          | 0.2-0.8%/fill        | Medium   | Liquid pairs      |
| **GridStrike V2**  | Intermediate | $100+          | Variable             | Medium   | Ranging           |
| **Directional V2** | Advanced     | $100+          | 10-50% (High Margin) | High     | Trending/Volatile |
| **Sniping V2**     | Advanced     | $100+          | 50-200% (Instant)    | Extreme  | New Listings      |
| **HLP Perp**       | Intermediate | $100+          | 20-100% (Leveraged)  | High     | All (Directional) |

---

## 1. Pure Market Making (PMM) ⭐⭐⭐

### What It Does

Places symmetric buy and sell limit orders around the current mid-price on a single exchange to capture the bid-ask spread.

### How It Works

1. Bot reads the current mid-price for a trading pair
2. Places buy orders at `mid_price × (1 - bid_spread)`
3. Places sell orders at `mid_price × (1 + ask_spread)`
4. When both sides fill, bot profits from the spread
5. Orders are refreshed every `order_refresh_time` seconds

### When to Use

- Market is range-bound / moving sideways
- Trading pair has moderate volatility (not too flat, not trending hard)
- You want passive income from spread capture

### When NOT to Use

- Strong trending markets (you'll accumulate the losing side)
- Extremely low volatility (spread too thin to cover fees)
- Very illiquid pairs (orders won't fill)

### Key Parameters

- `bid_spread` / `ask_spread`: Distance from mid-price (start with 0.5%)
- `order_amount`: Size per order (start small)
- `order_refresh_time`: How often to update orders (30-120s)
- `inventory_skew_enabled`: Prevent one-sided accumulation
- `filled_order_delay`: Wait N seconds after fill before new orders (prevents rapid accumulation)
- `order_refresh_tolerance_pct`: Don't cancel orders for tiny price moves (saves gas, keeps queue priority)

### Pro Tips

- **Use dynamic spreads** — the `pmm_dynamic` controller auto-adjusts spreads using NATR (volatility). Far more profitable than fixed spreads.
- **Match spread to regime** — in trending markets, widen spreads on the losing side and tighten on the winning side. See [11_expert_tips](11_expert_tips.md#market-regime-awareness-most-important-skill). Automated by `regime-service/`.
- **Go delta-neutral** — pair PMM with `hedge-service/` to offset spot inventory with a Hyperliquid short. Eliminates directional risk entirely. See [15_edge_systems](15_edge_systems.md#system-2-delta-neutral-market-making--implemented).
- **Real profit check**: `Spread - Gas - DEX Fee - Slippage = Actual Profit`. See [06_risk_management](06_risk_management.md#real-profit-math).

---

## 2. AMM Arbitrage ⭐⭐⭐

### What It Does

Exploits price discrepancies between two DEX AMM pools (e.g., Uniswap and SushiSwap, or across different chains).

### How It Works

1. Bot monitors price for the same pair on two venues simultaneously
2. When price difference exceeds `min_profitability` (after gas + fees), bot executes
3. Buys on the cheaper venue, sells on the more expensive venue
4. Profit = price difference - gas costs - exchange fees

### When to Use

- A token is listed on multiple DEXs
- Markets are volatile (creates more price divergence)
- Gas fees are low relative to trade size

### When NOT to Use

- Gas fees are high (Ethereum L1 during congestion)
- Trade size is too small to cover costs
- Token has very thin liquidity on one side

### Key Parameters

- `min_profitability`: Minimum spread to trigger (0.3% recommended)
- `market_1_slippage_buffer`: DEX 1 slippage allowance (0.2%)
- `market_2_slippage_buffer`: DEX 2 slippage allowance (0.2%)
- `order_amount`: Trade size per arbitrage cycle
- `concurrent_orders_submission`: Execute both legs simultaneously (faster but riskier)

### Pro Tips

- **Speed wins** — arb opportunities vanish in seconds. Use Solana or Arbitrum for fastest execution.
- **Real `min_profitability`** depends on competition: high-liquidity pairs (ETH/USDT) need 0.15-0.25%, mid-caps can sustain 0.3-0.8%.
- **Pre-fund both sides** — you need capital on both DEXs simultaneously. Moving funds mid-trade is too slow.
- If DEX pool TVL < $500K, add 0.5%+ to your slippage buffer.

---

## 3. Cross-Exchange Market Making (XEMM V2) ⭐⭐

### What It Does

Provides liquidity on a less liquid "maker" DEX and hedges fills on a more liquid "taker" DEX.

### How It Works

1. Bot places maker orders on the less liquid venue (e.g., smaller DEX)
2. When a maker order fills, bot immediately hedges on the taker venue (e.g., high-volume DEX)
3. Profit = maker spread - taker costs - gas fees
4. Risk is minimized because every fill is immediately hedged

### When to Use

- A pair has significantly different liquidity between two venues
- You want market making with reduced directional risk
- The maker venue has wider spreads (more profit per fill)

### Key Parameters

- `maker_connector` / `taker_connector`: Exchange pair
- `buy_maker_levels` / `sell_maker_levels`: Price levels and amounts
- `min_profitability`: Minimum net profit after hedge

### Pro Tips

- XEMM is **lower risk** than PMM because every fill is hedged, but latency between fill and hedge is your main risk.
- Use the DEX with the deepest liquidity as your taker (e.g., Uniswap v3 for most pairs).
- Monitor hedge fill rate — if taker hedges are failing, widen your maker spreads.

---

## 4. Concentrated Liquidity (CLMM) ⭐⭐

### What It Does

Actively manages Uniswap V3-style concentrated liquidity positions for maximum fee revenue.

### How It Works

1. Bot deposits liquidity within an optimal price range
2. Earns trading fees proportional to volume within that range
3. Automatically rebalances position when price moves outside range
4. More capital-efficient than traditional AMM LP positions

### When to Use

- High-volume pairs (ETH/USDT, SOL/USDC)
- You're comfortable with impermanent loss risk
- You want passive yield (20-50% APR potential)

> Supported CLMM DEXs: see [03_chains_and_dexs](03_chains_and_dexs.md#solana-connectors)

---

## 5. GridStrike V2 ⭐⭐

### What It Does

Places a grid of buy and sell orders at predefined price intervals, profiting from price oscillations within a range.

### How It Works

1. Defines a price range with upper and lower bounds
2. Places buy orders at evenly-spaced intervals below current price
3. Places sell orders at evenly-spaced intervals above current price
4. As price oscillates, orders fill and profit accumulates

### When to Use

- Clear support and resistance levels
- Ranging market with predictable oscillations
- Medium-term time horizon (days to weeks)

### When NOT to Use

- Strong breakout / trending markets (grid fills one side, price keeps moving)
- Very tight range (grid intervals too small to cover fees)

### Pro Tips

- Set the grid range based on the pair's recent support/resistance levels, not arbitrary numbers.
- Each grid level has its own SL/TP in GridStrike V2 — configure these rather than relying on an overall stop.

---

## 6. Stablecoin Arbitrage ⭐⭐⭐

### What It Does

Captures small price de-pegs between stablecoin pairs (USDT/USDC, USDC/DAI) across different venues or chains.

### How It Works

1. Monitors price of stablecoin pairs across DEXs and chains
2. When one stablecoin trades at a premium/discount, bot swaps
3. Very small spreads (0.01-0.1%) but extremely low risk
4. Requires larger capital for meaningful returns

### When to Use

- Risk-averse strategies
- Large capital ($100+) relative to gas to make thin margins worthwhile
- Want nearly market-neutral returns

> Best venues and pairs: see [04_trading_pairs](04_trading_pairs.md#stablecoin-pairs-lowest-risk)

---

## 7. Directional Momentum (Trend Following) V2 ⭐⭐⭐⭐

### What It Does

This strategy uses real-time technical analysis (MACD, Bollinger Bands, NATR) to capture explosive trending movements. Instead of catching sub-1% spreads, it enters positions strictly when a trend is explicitly confirmed, targeting massive 10% to 50% price movements typical in micro-caps or highly volatile assets.

### How It Works

1. Bot ingests 1-minute or 5-minute candle data (via the V2 framework)
2. Monitors indicators (e.g., MACD crossover combined with Bollinger Band width expansion)
3. When a bullish trend is mathematically confirmed, it triggers a long buy.
4. It trails the position, exiting only when the trend reversal is signaled or a strict stop-loss is hit.
5. Does not provide liquidity during sideways action, completely preserving capital for volatile breakouts.

### When to Use

- Aiming for large directional ROI (10-50%) on a small $100 budget.
- Trading highly volatile, narrative-driven DEX pairs (e.g., new Solana meme coins, pump.fun graduates).
- The overall market is experiencing high daily volume spikes.

### When NOT to Use

- Trading massive, low-volatility majors (e.g., WBTC, ETH). You will be chopped out by fake-outs.
- Sideways or dead markets.

### Key Parameters

- `macd_fast` / `macd_slow`: Tune these to the token's specific historical price action.
- `trailing_stop`: Critical to let winners run (up to 50%) while cutting losses instantly.
- `stop_loss`: Strict 2-5% stop. $100 budgets strictly cannot afford bag-holding.

### Pro Tips

- **Data is your Edge**: Do not blindly guess trends. Only deploy this when on-chain tools (DexScreener, Birdeye) show massive 24H volume spikes and the V2 charts confirm the breakout.
- **Micro-cap Focus**: PMM margins are squeezed by competition. But newly trending DEX pairs with low liquidity have massive price swings where a trend-following bot can safely capture 20%+ in a single hourly candle.

---

## 8. Liquidity Sniping (V2 Custom) ⭐⭐⭐⭐⭐

### What It Does

This strategy monitors blockchain logs for new liquidity pool creation events on Solana or Base and executes a buy order in the earliest possible block (often block 0-5). It aims to "front-run" the initial price discovery of newly launched tokens.

### How It Works

1. Bot scans DEX factory contracts (e.g., Raydium, PumpSwap, Aerodrome) for `PoolCreated` events.
2. Detects the new pool and constructs a buy transaction.
3. **Crucial (Solana)**: Submit the transaction as a **Jito MEV Bundle**. Include a "Jito Tip" (min 1,000 lamports, paid directly to the validator via Block Engine auction) rather than relying on standard base priority fees to guarantee block inclusion before retail manual buyers. 95%+ of Solana validators run Jito client.
4. Sells automatically after a 2x price increase (100% gain) or upon a rug-pull/sell-off signal.
5. Requires highly optimized RPC nodes (e.g., Helius) and sub-150ms execution latency.
6. **Note**: Since March 2025, pump.fun tokens graduate to **PumpSwap** (pump.fun's own DEX), not Raydium. Adjust sniper scripts accordingly.

### When to Use

- Aiming to double $100 in **under 24 hours**.
- Extremely high-risk tolerance.
- Trading on Solana or Base (lowest latency/fees).

### Risk Warning

- **90% of new pools fail or are "rug-pulls."** This strategy relies on hitting one 10x winner for every five losers.

---

## 9. Hyper-Leverage Perps (Hyperliquid/dYdX) ⭐⭐⭐⭐

### What It Does

Uses high leverage (10x-50x) on a Perpetual DEX to amplify small price movements into account-doubling returns.

### How It Works

1. $100 is deposited into Hyperliquid (no gas fees). HyperEVM launched Feb 2025 with Solidity smart contract support.
2. Bot uses 20x leverage ($2,000 buying power). Major pairs (BTC/ETH) support up to 50x.
3. Strategy: Trend following or Order Flow imbalance. Portfolio Margin available (Dec 2025) combining spot + perp accounts.
4. A small **5% price move** in your favor results in a **100% gain** (doubling the $100).
5. A 5% move against you liquidates the $100 entirely.

### Pro Tips

- **Zero Gas is Key**: Hyperliquid has zero gas fees for trading, making it the mathematically superior choice for high-frequency leveraged strategies on small accounts.
- **Micro-Scalping**: At 20x leverage, you can target 1% price moves for 20% account gains. 5-7 successful "scalps" in one day can double your $100.
