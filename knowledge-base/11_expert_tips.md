# 🧠 Expert Operating Rules

> Last reviewed: March 6, 2026
> Focus: durable rules that stay useful across releases.

---

## 1. Match Strategy to Market Stage

### Use this sequence

| Market stage | Best tool |
| --- | --- |
| Fresh listing / violent discovery | Directional controllers |
| Two-way flow starts | `pmm_dynamic` |
| Cross-listing appears | Arbitrage / XEMM |
| Pool matures | LP automation |

This is the main reason many bots lose money: they start passive market making too early.

## 2. New Tokens Need Filters Before Strategy

Before trading a new token, require:

- minimum liquidity
- minimum 1H or 24H volume
- no obvious holder concentration or honeypot risk
- enough depth for your intended order size

## 3. Do Not Stay Solana-Only

Use Solana for speed, but diversify workflow across:

- **Base** for the best non-Solana new-token setup
- **BNB Chain** for retail-flow token rotations
- **Arbitrum** for more mature liquidity and later-stage cross-venue trading

## 4. Use Platform-Specific Strategy Defaults

| Platform | Best default |
| --- | --- |
| Solana / Jupiter / Raydium | Directional first, PMM later |
| Base / Uniswap | Directional first, then PMM Dynamic |
| BNB / PancakeSwap | Directional first, then selective PMM |
| Arbitrum / Uniswap | PMM Dynamic, XEMM, arb |
| Hyperliquid | Hedge and perp execution |

## 5. Prefer Dynamic Over Static When Volatility Is Real

If the token can move several percent in minutes, `pmm_dynamic` is usually safer than `pmm_simple`.

Why:

- spread adapts to volatility
- less brittle in regime shifts
- better fit for tokens graduating out of pure chaos

## 6. Use LP Late, Not Early

`lp_rebalancer` is useful after a pool becomes stable enough that fee capture is not overwhelmed by repricing risk.

Avoid LP when:

- the token is very new
- liquidity is thin
- most movement is still one-way discovery

## 7. Use Hedge Venues for Risk Control, Not Token Discovery

Hyperliquid and dYdX are excellent for:

- hedge legs
- directional perps
- funding trades

They are not your primary new-token discovery venues.

## 8. Verify Connectors From Current Docs, Not Old Posts

Older guides often use stale controller names and connector IDs.

Current safe defaults:

- Solana: `jupiter`, `raydium`, `orca`, `meteora`
- EVM: `uniswap`, `pancakeswap`
- Perps: `hyperliquid`, `hyperliquid_perpetual`

## 9. Use API When Operations Get Bigger

Once you need:

- multiple bots
- deployment automation
- external scanners
- alert routing

move from client-only operations toward **Hummingbot API**.

## 10. Keep One Rule for All New Tokens

If you cannot explain why a token should still be tradeable after the first spike, do not switch it from directional mode into PMM or LP mode.

---

Next reads:

- [02_strategies.md](02_strategies.md)
- [03_chains_and_dexs.md](03_chains_and_dexs.md)
- [15_edge_systems.md](15_edge_systems.md)
