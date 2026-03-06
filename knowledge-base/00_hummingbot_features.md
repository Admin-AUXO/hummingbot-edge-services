# 🤖 Hummingbot Core Features

> Last reviewed: March 6, 2026
> Current official release line referenced here: Hummingbot / Gateway `v2.13.0`

---

## 1. Strategy V2 Is the Default

Hummingbot now centers on the **Strategy V2** stack:

- **Scripts**: simple Python entry points for prototyping or single-strategy bots
- **Controllers**: reusable production strategy modules loaded by `v2_with_controllers.py`
- **Executors**: self-managing trading workflows such as `position_executor`, `arbitrage_executor`, `grid_executor`, `dca_executor`, `twap_executor`, `xemm_executor`, and `lp_executor`

Official docs now recommend V2 for new work rather than legacy V1 templates.

## 2. Deployment Paths

Hummingbot is no longer just a local CLI workflow.

### Best deployment mode by use case

| Mode | Best for | Notes |
| --- | --- | --- |
| **Hummingbot Client** | Learning, local single-bot use, quick manual operation | Still the simplest starting point |
| **Hummingbot API** | Multi-bot deployment, cloud hosting, orchestration | Better fit for larger setups and service integrations |
| **Dashboard / Condor / MCP** | Operations, remote control, AI-assisted workflows | Built on top of API-driven flows |

## 3. DEX Connectivity via Gateway

Gateway is the TypeScript middleware layer for on-chain trading.

It standardizes three connector schemas:

- **Router**: best-route swap execution
- **AMM**: constant-product pools
- **CLMM**: concentrated-liquidity pools

### Active Gateway connector families

| Family | Chains | Schemas |
| --- | --- | --- |
| **Jupiter** | Solana | Router |
| **Raydium** | Solana | AMM, CLMM |
| **Orca** | Solana | CLMM |
| **Meteora** | Solana | CLMM |
| **Uniswap** | Ethereum / major EVM networks | Router, AMM, CLMM |
| **PancakeSwap** | BNB / EVM | Router, AMM, CLMM |

### Legacy / conditional families

These exist in the broader Hummingbot ecosystem, but support quality can vary by release and connector upgrade status:

- `curve`
- `balancer`
- `sushiswap`
- `quickswap`
- `traderjoe`

Treat them as **verify-first** connectors, not default recommendations.

## 4. CLOB DEX and Perp Support

For perps, hedging, or lower-latency orderbook execution, Hummingbot also supports non-Gateway connectors such as:

- **Hyperliquid**
- **dYdX v4**
- **Injective**

These are important for:

- delta-neutral hedging
- directional perp strategies
- funding-rate trades
- execution where AMM slippage is too expensive

## 5. Current V2 Building Blocks

### Controllers visible in this repo

#### Market making

- `pmm_simple`
- `pmm_dynamic`
- `dman_maker_v2`

#### Directional trading

- `bollinger_v1`
- `bollinger_v2`
- `macd_bb_v1`
- `supertrend_v1`
- `dman_v3`

#### Generic / multi-venue

- `xemm_multiple_levels`
- `arbitrage_controller`
- `grid_strike`
- `lp_rebalancer`
- `pmm_v1`

### Executors visible in this repo

- `position_executor`
- `arbitrage_executor`
- `grid_executor`
- `dca_executor`
- `twap_executor`
- `xemm_executor`
- `lp_executor`

## 6. What Changed Recently That Matters

Recent official release notes and docs matter more than older community examples.

Key items to account for now:

- `lp_executor` and `lp_rebalancer` are part of the current V2 story
- Hummingbot API is now a first-class deployment path
- Gateway connector coverage is cleaner, but not every popular DEX is officially maintained at the same level
- config examples copied from older guides often use stale controller or connector names

## 7. Practical Takeaways for This Repo

- Use **official connector families first**: Solana via Jupiter/Raydium/Orca/Meteora, EVM via Uniswap/PancakeSwap
- Use **API + services** when running multiple bots or external signal pipelines
- Use **perp venues** such as Hyperliquid for hedge legs, not for new-token discovery
- Prefer **generated fresh controller configs** over old copy-paste YAML

---

Next reads:

- [03_chains_and_dexs.md](03_chains_and_dexs.md)
- [07_v2_framework.md](07_v2_framework.md)
- [05_configurations.md](05_configurations.md)
