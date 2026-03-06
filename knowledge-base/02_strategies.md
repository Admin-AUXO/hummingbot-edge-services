# 🎯 Strategy Selection Guide

> Last reviewed: March 6, 2026
> Focus: current Hummingbot V2 controllers plus practical new-token workflows

---

## 1. Best Current Strategy Families

| Strategy family | Best Hummingbot controller / executor | Best use | Avoid when |
| --- | --- | --- | --- |
| **Passive market making** | `pmm_simple`, `pmm_dynamic` | Liquid pairs with stable spreads | First hours of chaotic new-token discovery |
| **Cross-venue market making** | `xemm_multiple_levels` | One venue is wider, another is deeper | Hedge venue is illiquid or slow |
| **Cross-venue arbitrage** | `arbitrage_controller`, `arbitrage_executor` | Same asset on multiple venues with repeatable gaps | Token is only on one pool |
| **Grid trading** | `grid_strike` | Ranging markets with clear bounds | Violent breakout conditions |
| **Directional trading** | `macd_bb_v1`, `bollinger_v2`, `supertrend_v1`, `dman_v3` | Fast-moving tokens and narrative rotations | Dead volume or poor liquidity |
| **Concentrated liquidity** | `lp_rebalancer` + `lp_executor` | Mature pools with reliable fee flow | Brand-new pools with unstable price discovery |

## 2. Best Strategies for New Tokens

For **new tokens**, efficiency usually comes from **controlled directional trading**, not classic PMM.

### Recommended order of operations

1. **Directional entry first**
2. **Wide-spread PMM later** once liquidity stabilizes
3. **Arb or XEMM later** if the token reaches multiple venues
4. **LP / CLMM last** only after the market stops re-pricing every minute

### Efficiency ranking for new-token trading

| Phase | Best approach | Why |
| --- | --- | --- |
| **0-24h after listing** | Directional controllers + strict filters | Captures momentum without getting trapped as passive liquidity |
| **1-7 days** | Directional + selective wide-spread PMM | Volume is still high, but spreads begin to normalize |
| **After second venue listing** | Arbitrage / XEMM | Cross-venue dislocations appear |
| **After pool matures** | LP Rebalancer / PMM Dynamic | Better suited once price discovery slows down |

## 3. Best Chains and Venues for New Tokens

Do not focus on Solana alone.

### Best practical targets for Hummingbot

| Venue family | Chain | New-token fit | Best strategy type |
| --- | --- | --- | --- |
| **Jupiter / Raydium** | Solana | Excellent | Directional, later PMM / arb |
| **Uniswap** | Base | Very strong non-Solana choice | Directional first, later PMM |
| **PancakeSwap** | BNB Chain | Strong retail flow | Directional first, later PMM |
| **Uniswap** | Arbitrum | Better for stronger/more mature listings | Directional, XEMM, arb |
| **Uniswap** | Ethereum mainnet | Viable only for larger size due to gas | Large-cap or higher-conviction trades |

### Practical chain ranking for new-token workflows

1. **Solana** — fastest and deepest early-flow environment
2. **Base** — best non-Solana chain for Hummingbot-friendly new-token trading
3. **BNB Chain** — good retail token flow with low fees via PancakeSwap
4. **Arbitrum** — better once tokens have more depth and cross-listing
5. **Ethereum L1** — only if capital is large enough to absorb gas

## 4. Recommended Strategy by Token Maturity

### A. Fresh listing, single venue, thin history

Use:

- `macd_bb_v1`
- `bollinger_v2`
- `supertrend_v1`

Why:

- taker-style directional control is safer than sitting passively in front of toxic order flow
- better fit for breakout candles and narrative spikes

Rules:

- small size
- hard stop-loss
- minimum liquidity filter
- minimum 1H / 24H volume ratio filter

### B. Fresh listing, strong volume, spreads still wide

Use:

- `pmm_dynamic` only after the token shows repeatable two-way flow

Why:

- dynamic spreads adapt better than static PMM when volatility changes fast

Rules:

- wider-than-normal spreads
- shorter time limits
- inventory controls
- disable if price is one-directional for multiple sessions

### C. Token reaches second venue

Use:

- `arbitrage_controller`
- `xemm_multiple_levels`

Why:

- price discovery fragments across pools
- one venue often leads, another lags

Rules:

- pre-fund both sides
- verify true net edge after gas and slippage
- start with deep pools only

### D. Mature token with stable pool utilization

Use:

- `lp_rebalancer`

Why:

- LP works better once the market is no longer repricing by double digits every hour

Rules:

- use only on pools with real volume and stable active LPs
- avoid the first 24-72h unless liquidity is already institutional-grade

## 5. Default Strategy Recommendations by Goal

### If you want the safest default

- **Established pairs**: `pmm_dynamic`
- **New tokens**: `macd_bb_v1`

### If you want best new-token adaptability

- **Solana**: directional entry on Jupiter / Raydium
- **Base**: directional entry on Uniswap
- **BNB Chain**: directional entry on PancakeSwap

### If you want neutralized market making

- run `pmm_dynamic` on spot
- hedge exposure on Hyperliquid or dYdX

## 6. Strategy Mistakes to Avoid

- Running `pmm_simple` on a token that is less than a day old
- Using LP strategies before price discovery stabilizes
- Treating every new token as a sniper setup
- Ignoring Base and BNB just because Solana is noisier
- Using unsupported DEX venues in docs as if they were official Hummingbot connectors

---

Next reads:

- [03_chains_and_dexs.md](03_chains_and_dexs.md)
- [05_configurations.md](05_configurations.md)
- [11_expert_tips.md](11_expert_tips.md)
