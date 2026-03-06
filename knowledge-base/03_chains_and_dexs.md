# ⛓️ Chains & DEXs Reference

> Last reviewed: March 6, 2026
> Focus: the best platforms you can use with Hummingbot now, not every interesting DEX in the market

---

## 1. Best Hummingbot-Usable Platforms Right Now

### Spot / AMM / Router venues

| Venue family | Chain | Official Hummingbot fit | Best for | Verdict |
| --- | --- | --- | --- | --- |
| **Jupiter** | Solana | Active Gateway connector | Best-route execution, directional entries, new-token access | **Top choice** |
| **Raydium** | Solana | Active Gateway connector | AMM + CLMM, PMM, early-token liquidity | **Top choice** |
| **Orca** | Solana | Active Gateway connector | CLMM and cleaner mature Solana pools | **Top choice** |
| **Meteora** | Solana | Active Gateway connector | CLMM / DLMM and LP automation | **Top choice** |
| **Uniswap** | Base / Arbitrum / Ethereum / other EVM | Active Gateway connector | Best all-around EVM venue family | **Top choice** |
| **PancakeSwap** | BNB Chain / EVM | Active Gateway connector | Low-fee retail flow and new-token rotation on BNB | **Top choice** |

### Perp / hedge venues

| Venue family | Chain | Hummingbot fit | Best for |
| --- | --- | --- | --- |
| **Hyperliquid** | Hyperliquid L1 | Active CLOB DEX connector | Hedge leg, perps, funding, directional leverage |
| **dYdX v4** | dYdX appchain | Active CLOB DEX connector | Perps and hedge workflows |
| **Injective** | Injective | Active CLOB DEX connector | On-chain orderbook strategies |

## 2. Best Platform by Objective

| Objective | Best platform | Why |
| --- | --- | --- |
| **Small-account spot trading** | Solana via Jupiter / Raydium | Lowest friction and cheapest execution |
| **Best non-Solana new-token venue** | Base via Uniswap | Strong token-launch activity plus manageable fees |
| **Best BNB ecosystem access** | PancakeSwap on BNB Chain | High retail flow and official Hummingbot support |
| **Best mature EVM spot venue** | Uniswap on Arbitrum | Strong depth for majors and later-stage tokens |
| **Best hedge venue** | Hyperliquid | Zero-gas trading model and strong perp liquidity |
| **Best CLMM experimentation** | Meteora / Raydium / Orca | Active Solana LP ecosystem plus current connector support |

## 3. Practical Chain Ranking

### Tier A — default choices

| Chain | Why it matters | Best Hummingbot venues |
| --- | --- | --- |
| **Solana** | Fastest reaction loop, cheapest fees, strongest early-token flow | Jupiter, Raydium, Orca, Meteora |
| **Base** | Best non-Solana chain for fresh token opportunities and low fees | Uniswap |
| **BNB Chain** | Good low-fee retail ecosystem and token rotation | PancakeSwap |
| **Arbitrum** | Stronger for mature tokens, hedged MM, and established liquidity | Uniswap |

### Tier B — selective use

| Chain | Use only when |
| --- | --- |
| **Ethereum mainnet** | Trade size is large enough that gas is not dominant |
| **Polygon / Optimism** | You already need their ecosystem exposure |
| **Avalanche** | You specifically need legacy connector coverage there |

## 4. DEX Families to Prioritize

### A. Solana stack

#### Jupiter

- best for **entry and exit execution quality**
- strong choice for **new-token directional strategies**
- good default when you want routing instead of managing pool choice yourself

#### Raydium

- best for **direct pool interaction**
- useful for **PMM**, **later-stage new-token MM**, and **cross-pool comparisons**

#### Orca and Meteora

- better for **CLMM / LP** use cases after a token matures
- not my first choice for the first minutes of a listing

### B. EVM stack

#### Uniswap

- best all-around EVM venue family
- strongest choice for **Base** and **Arbitrum** workflows in Hummingbot
- best non-Solana default for new-token trading where support quality matters

#### PancakeSwap

- best BNB Chain default
- useful for **retail-flow tokens**, lower-fee spot, and later PMM after spreads normalize

## 5. Venues Worth Watching but Not Default Hummingbot Recommendations

These can be good markets, but they should not be documented as default Hummingbot choices unless you verify connector support for your exact version:

- Aerodrome
- Camelot
- GMX
- Velodrome

Reason: they may be attractive markets, but they are not the cleanest official default connector path in current Hummingbot docs.

## 6. Best Platforms for New Tokens

### Use this ranking

| Rank | Chain / venue | Why |
| --- | --- | --- |
| **1** | Solana via Jupiter / Raydium | Deepest early-flow environment |
| **2** | Base via Uniswap | Best non-Solana new-token venue Hummingbot can cleanly use |
| **3** | BNB Chain via PancakeSwap | Strong retail launch flow with lower fees |
| **4** | Arbitrum via Uniswap | Better once token matures or cross-lists |

### What this means in practice

- If you want **speed and frequency**, keep Solana in the mix
- If you want **non-Solana diversification**, prioritize **Base** first, **BNB Chain** second
- If you want **more mature liquidity**, rotate into **Arbitrum**

## 7. Connector Guidance

Use the **official connector family names** from your installed version, not old blog-post naming schemes.

Examples of family names you should expect in current docs and repo references:

- `jupiter`
- `raydium`
- `orca`
- `meteora`
- `uniswap`
- `pancakeswap`
- `hyperliquid`
- `hyperliquid_perpetual`

Avoid assuming older chain-suffixed connector IDs unless your installed version actually generates them.

---

Next reads:

- [02_strategies.md](02_strategies.md)
- [05_configurations.md](05_configurations.md)
- [15_edge_systems.md](15_edge_systems.md)
