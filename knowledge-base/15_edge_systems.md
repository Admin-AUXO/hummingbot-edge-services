# Custom Edge Systems

> Last reviewed: March 6, 2026
> Scope: what this repo actually implements, what is still manual, and where to extend beyond Solana.

---

## 1. Use This File as a Repo Map

This repo contains useful edge services, but they are **not all equally mature** and **not all are multi-chain yet**.

The biggest current limitation is that several scanners are still **Solana-first** by default.

## 2. Implemented Services in This Repo

| Service | Role | Current bias |
| --- | --- | --- |
| `alpha-service/` | token scoring and new-listing alerts | Solana-first |
| `arb-service/` | cross-pool / cross-DEX scanning | Solana-first |
| `clmm-service/` | CLMM range optimization | Solana-heavy |
| `hedge-service/` | delta-neutral hedge coordination | spot + perp workflow |
| `inventory-service/` | inventory and risk monitoring | strategy-agnostic |
| `narrative-service/` | narrative keyword scanning | can be extended cross-chain |
| `pnl-service/` | performance aggregation | strategy-agnostic |
| `rewards-service/` | pool / rewards tracking | configurable |
| `session-service/` | session-aware timing | chain-agnostic |
| `watchlist-service/` | watchlist curation and stale-asset cleanup | currently Solana-biased DexScreener endpoints |
| `alert-service/` | Telegram / alert routing | chain-agnostic |

## 3. What Is Not an Active Service Here

Do not document these as active standalone services in this repo unless you add them:

- `regime-service`
- `funding-service`
- `correlation-service`
- `funding-scanner-service`
- `lab-service`

You can still use those ideas operationally, but they should be described as:

- manual workflows
- future extensions
- archived concepts

## 4. Current Best Repo Patterns

### A. Solana-first discovery stack

Current services such as `alpha-service/` and `arb-service/` default to Solana-oriented DexScreener queries.

This is useful because:

- Solana remains the fastest early-token environment
- data is easy to source from DexScreener

But it should not be mistaken for a full multi-chain architecture.

### B. Hedge overlay

`hedge-service/` is the cleanest example of a reusable non-discovery edge:

- run spot on AMM venues
- hedge exposure on a perp venue such as Hyperliquid
- use `inventory-service/` and `pnl-service/` to supervise the risk loop

### C. Session-aware automation

`session-service/` and `alert-service/` are useful across chains because they do not depend on one venue family.

## 5. Best Immediate Improvement: Multi-Chain Scanner Expansion

If you do not want to stay Solana-only, the highest-value upgrade is to expand the discovery services to support:

- **Base / Uniswap**
- **BNB Chain / PancakeSwap**
- **Arbitrum / Uniswap**

### Priority order

1. Base
2. BNB Chain
3. Arbitrum

Reason:

- Base is the best non-Solana new-token opportunity set for Hummingbot
- BNB adds a different retail-flow market
- Arbitrum is better for later-stage or more mature tokens

## 6. Concrete Repo Improvement Targets

### `alpha-service/`

Current config shows a Solana query bias.

Best next upgrades:

- add chain selector support
- maintain separate watchlists for Solana, Base, BNB, and Arbitrum
- score tokens per chain instead of using one default search term

### `arb-service/`

Best next upgrades:

- support Uniswap-based EVM token endpoints where possible
- split arb thresholds by chain
- use different gas assumptions for Solana, Base, BNB, and Arbitrum

### `watchlist-service/`

Best next upgrades:

- multi-chain token endpoint support
- chain-tagged watchlists
- separate stale thresholds by chain and liquidity regime

## 7. Suggested Architecture Going Forward

### Discovery layer

- Solana shortlist
- Base shortlist
- BNB shortlist
- Arbitrum shortlist

### Execution layer

- directional controllers for new tokens
- PMM Dynamic for stabilized tokens
- XEMM / arb for cross-listed tokens

### Risk layer

- inventory monitoring
- hedge coordination
- session-aware config adjustments
- alert routing
- PnL reporting

## 8. What to Remove From Older Mental Models

- assuming every edge service here is active and production-grade
- assuming the repo is already multi-chain discovery-ready
- assuming only Solana matters for new tokens

## 9. Best Operational View

Use this repo as:

- a strong **signal and risk framework**
- a **Solana-first baseline**
- a system that should now be expanded toward **Base first**, then **BNB**, then **Arbitrum**

---

Next reads:

- [03_chains_and_dexs.md](03_chains_and_dexs.md)
- [02_strategies.md](02_strategies.md)
- [05_configurations.md](05_configurations.md)
