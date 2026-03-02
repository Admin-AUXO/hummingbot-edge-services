# ⛓️ Chains & DEXs Reference

> Comparing blockchains and decentralized exchanges for bot trading

---

## Chain Rankings for Bot Trading

### Tier 1: Best for Bots (Low fees + High volume + Fast)

| Chain         | Avg Gas/Trade | Block Time | Best DEXs                       | Why                                                                |
| ------------- | ------------- | ---------- | ------------------------------- | ------------------------------------------------------------------ |
| **Solana**    | < $0.01       | ~400ms     | Raydium, Jupiter, Orca, Meteora | Fastest execution. Essential for MEV/Sniping using Jito Tips.      |
| **Arbitrum**  | $0.01-0.10    | ~0.25s     | Uniswap V3, Camelot, GMX        | Best L2 for DeFi. Deep liquidity, mature ecosystem                 |
| **Base**      | $0.01-0.05    | ~2s        | Aerodrome, Uniswap V3           | Huge volume growth. Aerodrome serves as the premier liquidity hub. |
| **BNB Chain** | $0.03-0.10    | ~3s        | PancakeSwap V3, Venus           | Mature, huge user base, very low fees                              |

### Tier 2: Good but Trade-offs

| Chain         | Avg Gas/Trade | Block Time | Best DEXs             | Trade-off                                    |
| ------------- | ------------- | ---------- | --------------------- | -------------------------------------------- |
| **Optimism**  | $0.01-0.10    | ~2s        | Velodrome, Uniswap V3 | Good liquidity but less volume than Arbitrum |
| **Polygon**   | $0.01-0.05    | ~2s        | QuickSwap, Uniswap V3 | Cheap but lower DeFi depth                   |
| **Avalanche** | $0.05-0.30    | ~2s        | Trader Joe, Pangolin  | Fast finality, moderate fees                 |

### Tier 3: Specialized Use Cases

| Chain              | Gas           | Use Case                  | Notes                                                                          |
| ------------------ | ------------- | ------------------------- | ------------------------------------------------------------------------------ |
| **Ethereum L1**    | $1-50+        | Large trades only ($10K+) | Deepest liquidity but prohibitive gas for small trades                         |
| **Hyperliquid L1** | **$0**        | **Perpetual futures**     | **Essential for Leveraged Scalping. Up to 50x leverage.**                      |
| **dYdX v4**        | $0 (zero gas) | Perpetual futures         | Cosmos appchain, 0 gas, taker fees from 0.05%, up to 50x leverage              |
| **Injective**      | $0 (zero gas) | Spot & Perps              | Cosmos appchain, 0 gas, fully on-chain orderbook, negative maker fees for VIPs |
| **Monad**          | < $0.01       | Spot (emerging)           | EVM-compatible L1, 10K TPS, 1s blocks. Mainnet Nov 2025. Growing DEX ecosystem |
| **Berachain**      | < $0.01       | Spot & Perps              | Cosmos SDK L1 with Proof-of-Liquidity. EVM-compatible. Mainnet Feb 2025        |

### Chain Selection Flowchart

```
What are you trading?
├── Perpetuals/Derivatives
│   ├── Want zero gas? → Hyperliquid (50x) or dYdX v4 (50x)
│   ├── Want highest leverage? → GMX (100x on Arbitrum)
│   └── Want on-chain composability? → GMX (Arbitrum)
│
├── Spot tokens
│   ├── Trade size > $10,000?
│   │   ├── YES → Ethereum L1 (deepest liquidity) or Arbitrum
│   │   └── NO → Continue below
│   │
│   ├── Doing Block-0 Sniping?          → Solana or Base exclusively
│   ├── Need fastest execution (< 1s)?  → Solana
│   ├── Want absolute cheapest gas?     → Solana or Base
│   ├── Trading BNB ecosystem tokens?   → BNB Chain
│   ├── Want best L2 liquidity?         → Arbitrum
│   └── Want growing ecosystem + cheap? → Base
│
└── Stablecoins
    ├── Stablecoin swaps → Curve (Ethereum or Arbitrum)
    └── Cross-chain arb  → Arbitrum ↔ Base ↔ Solana
```

---

## DEX Deep Dives

### Uniswap (EVM chains)

- **Versions**: V2 (basic AMM), V3 (concentrated liquidity), V4 (hooks/custom logic — live Jan 2025, 12 chains)
- **V4 Hooks**: Plugin system for custom pool logic — dynamic fees, TWAMM, MEV rebates, auto-compounding. 2500+ hook-enabled pools
- **Chains**: Ethereum, Arbitrum, Base, Polygon, Optimism, BNB Chain
- **Volume**: Top EVM DEX, though Raydium now leads globally by volume
- **Bot suitability**: ⭐⭐⭐⭐⭐ Deep liquidity, wide pair coverage
- **Hummingbot connector**: `uniswap_<chain_name>`

### Raydium (Solana)

- **Type**: Hybrid AMM + order book integration
- **Pools**: Standard (V2-style) + Concentrated (V3-style CLMM)
- **Volume**: Topped Uniswap in Jan 2025, ~27% of all DEX volume
- **Bot suitability**: ⭐⭐⭐⭐⭐ Lightning fast, near-zero gas
- **Hummingbot connector**: `raydium_solana`

### Jupiter (Solana)

- **Type**: DEX aggregator (routes across multiple Solana DEXs)
- **Function**: Finds best price across Raydium, Orca, Meteora, etc.
- **Bot suitability**: ⭐⭐⭐⭐⭐ Best execution on Solana
- **Hummingbot connector**: `jupiter_solana` (Router type)

### PancakeSwap (BNB Chain + multi-chain)

- **Versions**: V2, V3 (concentrated), Smart Router
- **Chains**: BNB Chain (primary), Ethereum, Arbitrum
- **Volume**: At times surpassed Uniswap in daily volume
- **Bot suitability**: ⭐⭐⭐⭐ Ultra-low fees on BNB Chain
- **Hummingbot connector**: `pancakeswap_<chain_name>`

### Aerodrome / Aero (Base → multi-chain)

- **Type**: ve(3,3) DEX — leading DEX on Base (rebranding to Aero)
- **Volume**: $810M avg daily (Aug 2025), $177B+ total in 2025. 50%+ of Base DEX TVL
- **Expansion**: Ethereum mainnet planned Q2 2026
- **Bot suitability**: ⭐⭐⭐⭐ Massive liquidity, good spreads on Base

### Curve Finance (Multi-chain)

- **Type**: Stablecoin-optimized AMM
- **Specialty**: Minimal slippage for pegged-asset swaps
- **Bot suitability**: ⭐⭐⭐⭐ Perfect for stablecoin arbitrage
- **Hummingbot connector**: `curve_ethereum`

### GMX (Arbitrum + Avalanche + expanding)

- **Type**: Perpetual futures DEX
- **Leverage**: Up to 100x (V2.3+, varies by asset)
- **Model**: "Real yield" — fees distributed to stakers
- **Features**: Cross-collateral, cross-margin, gas abstraction (June 2025), 87+ listed tokens
- **Bot suitability**: ⭐⭐⭐⭐ Strong perp strategies, deep Arbitrum liquidity

### Orca (Solana)

- **Type**: CLMM (concentrated liquidity)
- **Specialty**: User-friendly Solana DEX
- **Bot suitability**: ⭐⭐⭐⭐ Near-instant, low fees
- **Hummingbot connector**: `orca_solana`

### Meteora (Solana)

- **Type**: DLMM (Dynamic Liquidity Market Maker)
- **Specialty**: Bin-based liquidity for zero-slippage within bins
- **Volume**: $39.9B in Jan 2025 (40x growth). 15%+ of Solana DEX volume. TVL $750M+
- **Upgrades**: Q1 2026 — on-chain limit orders, live PnL tracking, auto-compounding vaults
- **Bot suitability**: ⭐⭐⭐⭐ Advanced LP strategies
- **Hummingbot connector**: `meteora_solana`

---

## Hummingbot Gateway Connector Reference

### EVM Connectors

| DEX            | Connector Name        | Type | Chains                                      |
| -------------- | --------------------- | ---- | ------------------------------------------- |
| Uniswap V2     | `uniswap_<chain>`     | AMM  | Ethereum, Arbitrum, Base, Polygon, Optimism |
| Uniswap V3     | `uniswap_<chain>`     | CLMM | Same as above                               |
| PancakeSwap V2 | `pancakeswap_<chain>` | AMM  | BNB Chain, Ethereum                         |
| PancakeSwap V3 | `pancakeswap_<chain>` | CLMM | BNB Chain, Ethereum                         |
| Curve          | `curve_ethereum`      | AMM  | Ethereum, Arbitrum                          |
| SushiSwap      | `sushiswap_<chain>`   | AMM  | Multi-chain                                 |
| Balancer       | `balancer_<chain>`    | AMM  | Ethereum, Arbitrum                          |

### Solana Connectors

| DEX                  | Connector Name   | Type                |
| -------------------- | ---------------- | ------------------- |
| Jupiter              | `jupiter_solana` | Router (aggregator) |
| Raydium Standard     | `raydium_solana` | AMM                 |
| Raydium Concentrated | `raydium_solana` | CLMM                |
| Orca                 | `orca_solana`    | CLMM                |
| Meteora              | `meteora_solana` | CLMM (DLMM)         |

> **Connector types defined in [01_glossary](01_glossary.md#hummingbot-specific)**: Router (aggregator), AMM (V2 pools), CLMM (V3 concentrated)

---

## Gas Cost Impact on Profitability

> Full monthly gas cost breakdown by scenario: see [12_costs_and_setup](12_costs_and_setup.md#3-blockchain-gas--050-to-150mo-biggest-variable).

**Formula**: `Min Trade Size = Gas Cost / Target Spread %`

**Rule of thumb**: If gas costs eat > 30% of expected profit, switch to a cheaper chain. Solana is the only viable chain for $20 trade sizes at 0.5% spreads.
