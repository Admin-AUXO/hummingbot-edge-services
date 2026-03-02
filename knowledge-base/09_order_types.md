# 📋 Order Types in DEX Trading with Hummingbot

> How orders work on decentralized exchanges and what Hummingbot supports

---

## AMM vs CLOB DEX Order Model

Unlike centralized exchanges with traditional order books, most DEXs use **AMM pools** where trades are executed as **swaps** against liquidity reserves. This fundamentally changes how "orders" work.

| Feature             | DEX (AMM)               | DEX (CLOB)              |
| ------------------- | ----------------------- | ----------------------- |
| **Matching**        | Swap against pool       | Buyer ↔ Seller on-chain |
| **Order types**     | Swap (market-like)      | Limit, Market           |
| **Price discovery** | Pool ratio (`x*y=k`)    | On-chain order book     |
| **Execution**       | 1 block confirmation    | 1 block confirmation    |
| **Settlement**      | On-chain, non-custodial | On-chain, non-custodial |
| **Examples**        | Uniswap, Raydium        | dYdX, Hyperliquid       |

---

## Order Types on AMM DEXs

### 1. Swap Order (Market-like)

The fundamental DEX trade. You swap one token for another at the current pool price.

- **How it works**: Send Token A to the pool, receive Token B based on the AMM formula
- **Price guarantee**: None — you get whatever the pool ratio gives you
- **Slippage**: You set a max slippage tolerance (e.g., 0.5%)
- **Gas cost**: One blockchain transaction per swap
- **Hummingbot support**: ✅ All Gateway connectors (Router, AMM, CLMM)

```
Example: Swap 1 ETH → USDT on Uniswap V3 (Arbitrum)
- Pool price: 1 ETH = $2,000
- Slippage tolerance: 0.5%
- You receive: ~$1,990-2,000 USDT (after fees + slippage)
- Gas cost: ~$0.05 on Arbitrum
```

### 2. Aggregated Swap (Best-Route)

Routed through a DEX aggregator that splits the trade across multiple pools for the best price.

- **How it works**: Aggregator finds optimal route across multiple DEX pools
- **Advantage**: Better price and lower slippage than a single pool
- **Hummingbot support**: ✅ Via Router connectors (Jupiter, 1inch)

```
Example: Swap 10 SOL → USDC via Jupiter
- Jupiter checks: Raydium, Orca, Meteora, Phoenix
- Routes: 60% via Raydium, 40% via Orca
- Result: Better price than any single DEX
```

### 3. Liquidity Provision Order (Add/Remove LP)

Not a trade per se, but an order to deposit or withdraw tokens from a liquidity pool.

- **Add liquidity**: Deposit token pair into pool, receive LP tokens
- **Remove liquidity**: Burn LP tokens, receive underlying tokens
- **Hummingbot support**: ✅ Via AMM and CLMM connectors

### 4. Concentrated Liquidity Position (CLMM)

Place liquidity within a specific price range on V3-style DEXs.

- **How it works**: Choose lower and upper price bounds; earn fees only when price is in range
- **More capital efficient**: Up to 4000x compared to V2 full-range positions
- **Hummingbot support**: ✅ Via CLMM connectors (Uniswap V3, Raydium Concentrated, Meteora, Orca)

---

## Order Types on CLOB DEXs

Some DEXs operate like traditional order books (on-chain or hybrid):

### 5. Limit Order

Place an order at a specific price. Executes only when the market reaches that price.

- **Maker order**: Adds liquidity to the book (often lower fees)
- **Sits on-chain**: Until filled or cancelled
- **Hummingbot support**: ✅ On CLOB DEXs (dYdX, Hyperliquid, Polkadex)

### 6. Market Order

Execute immediately at the best available price in the on-chain order book.

- **Taker order**: Removes liquidity (higher fees)
- **Guaranteed execution**: But not guaranteed price
- **Hummingbot support**: ✅ On CLOB DEXs

---

## Hummingbot Executor Order Types

Hummingbot's V2 framework uses **Executors** to manage complex order logic on DEXs. These combine basic swap/limit orders into sophisticated trading patterns:

### 7. Position Executor (Triple Barrier)

Manages a single position with automatic exit conditions.

| Parameter         | What It Does                                  |
| ----------------- | --------------------------------------------- |
| **Entry order**   | Opens position (swap on DEX or limit on CLOB) |
| **Leverage**      | Defines multiplier on Perp DEXs (e.g. 20x)    |
| **Stop loss**     | Auto-closes if price drops X% below entry     |
| **Take profit**   | Auto-closes if price rises X% above entry     |
| **Time limit**    | Auto-closes after N seconds regardless of P&L |
| **Trailing stop** | Moving stop that locks in profits             |

```yaml
# Position Executor config
stop_loss: 0.03 # Close at -3%
take_profit: 0.02 # Close at +2%
time_limit: 3600 # Close after 1 hour
trailing_stop:
  activation_price: 0.01 # Activate after +1%
  trailing_delta: 0.005 # Trail by 0.5%
```

**How it works on DEX**: Entry and exit are both swaps. The executor monitors the price off-chain and submits a swap transaction when a barrier is hit.

### 8. Arbitrage Executor

Executes simultaneous trades on two venues to capture price differences.

| Parameter             | What It Does                        |
| --------------------- | ----------------------------------- |
| **Buy order**         | Swap/limit on cheaper venue         |
| **Sell order**        | Swap/limit on more expensive venue  |
| **Min profitability** | Only triggers if profit > threshold |
| **Slippage buffers**  | Per-venue slippage tolerance        |

```
Arbitrage flow:
1. Monitor ETH price on Uniswap (DEX 1) and SushiSwap (DEX 2)
2. Detect: DEX 1 price = $1,995, DEX 2 price = $2,005
3. Spread = 0.5% > min_profitability (0.3%)
4. Execute: Buy on DEX 1 (swap), Sell on DEX 2 (swap)
5. Profit: ~$10 minus gas and fees
```

### 9. DCA Executor (Dollar-Cost Averaging)

Splits a large order into multiple smaller swaps over time or price levels.

| Parameter            | What It Does                      |
| -------------------- | --------------------------------- |
| **Total amount**     | Full position size                |
| **Number of levels** | How many sub-orders to split into |
| **Price intervals**  | Distance between each sub-order   |
| **Time intervals**   | Time gap between each execution   |

```
DCA flow (buying 1 ETH):
- Level 1: Buy 0.25 ETH at market ($2,000)
- Level 2: Buy 0.25 ETH at $1,980 (-1%)
- Level 3: Buy 0.25 ETH at $1,960 (-2%)
- Level 4: Buy 0.25 ETH at $1,940 (-3%)
- Average entry: ~$1,970 (if all levels fill)
```

### 10. Grid Executor

Places a grid of buy and sell orders at fixed price intervals.

| Parameter       | What It Does           |
| --------------- | ---------------------- |
| **Price range** | Upper and lower bounds |
| **Grid levels** | Number of order levels |
| **Order size**  | Amount per grid level  |

```
Grid layout (ETH at $2,000):
  SELL $2,060 ─── 0.05 ETH
  SELL $2,040 ─── 0.05 ETH
  SELL $2,020 ─── 0.05 ETH
  ─── Current price: $2,000 ───
  BUY  $1,980 ─── 0.05 ETH
  BUY  $1,960 ─── 0.05 ETH
  BUY  $1,940 ─── 0.05 ETH
```

### 11. XEMM Executor (Cross-Exchange)

Places maker orders on one exchange, hedges fills on another.

| Parameter        | What It Does                                  |
| ---------------- | --------------------------------------------- |
| **Maker orders** | Limit orders on less liquid venue (DEX 1)     |
| **Taker hedge**  | Immediate market/swap on liquid venue (DEX 2) |
| **Maker levels** | Multiple price levels with different sizes    |

```
XEMM flow:
1. Place SELL at $2,010 on Uniswap (maker, DEX 1)
2. Someone buys from your pool position
3. Immediately BUY at $2,005 on SushiSwap (taker, DEX 2)
4. Net profit: $5 minus fees and gas
```

---

## DEX Order Execution Details

### How Hummingbot Executes on DEXs

```
Strategy Decision
    ↓
Controller (V2)
    ↓
Executor (Position/Arb/DCA/Grid/XEMM)
    ↓
Gateway REST API
    ↓
Blockchain Transaction (swap, addLiquidity, etc.)
    ↓
DEX Smart Contract Execution
    ↓
On-chain Settlement
```

### Transaction Lifecycle

| Step               | What Happens                  | Time            |
| ------------------ | ----------------------------- | --------------- |
| 1. Signal          | Controller decides to trade   | Instant         |
| 2. Order creation  | Executor creates order params | Instant         |
| 3. Gateway call    | REST API → Gateway            | ~100ms          |
| 4. TX submission   | Gateway signs & broadcasts TX | ~200ms          |
| 5. Block inclusion | TX included in next block     | Chain-dependent |
| 6. Confirmation    | TX confirmed on-chain         | Chain-dependent |

> Chain-specific confirmation times: see [03_chains_and_dexs](03_chains_and_dexs.md#chain-rankings-for-bot-trading). Gas costs: see [12_costs_and_setup](12_costs_and_setup.md#3-blockchain-gas--050-to-150mo-biggest-variable).

---

## Important DEX Order Limitations

### AMM Constraints vs Traditional Books

| Feature               | AMM DEX                    | CLOB DEX       |
| --------------------- | -------------------------- | -------------- |
| Native limit orders   | ❌ (simulated by bot)      | ✅             |
| Native stop loss      | ❌ (simulated by bot)      | Some           |
| Partial fills         | ❌ (all-or-nothing swap)   | ✅             |
| Order modification    | ❌ (must cancel + re-swap) | ✅             |
| Hidden/iceberg orders | ❌                         | ❌             |
| Margin/leverage       | ❌ (spot only)             | ✅ (perp DEXs) |

### How Hummingbot Simulates Advanced Orders on AMM DEXs

- **"Limit orders"**: Bot monitors price off-chain, submits swap when target price is hit
- **"Stop loss"**: Bot watches price, submits sell-swap if price drops below threshold
- **"Take profit"**: Bot watches price, submits sell-swap if price exceeds target
- **"Order refresh"**: Bot cancels nothing (no orders on-chain), just submits new swaps as needed

> ⚠️ **Key difference**: On AMM DEXs, there are no resting orders on-chain. Hummingbot simulates order book behavior by monitoring prices off-chain and executing swaps at the right moment.
