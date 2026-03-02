# 💱 Best Trading Pairs

> Pair selection for market making, arbitrage, and LP strategies

---

## Pair Selection Criteria

| Factor                       | Why It Matters                                        |
| ---------------------------- | ----------------------------------------------------- |
| **Volume**                   | Higher volume = more fills, more opportunities        |
| **Spread**                   | Wider spread = more profit per trade, but fewer fills |
| **Liquidity**                | Deeper pools = less slippage on execution             |
| **Volatility**               | Moderate = best for MM; High = best for arb           |
| **Cross-venue availability** | Must be on multiple DEXs for arbitrage                |
| **Gas cost ratio**           | Gas must be < 30% of expected profit per trade        |

### Recommended Spread by Pair Volatility

> From community experience — your spread should be ≥ 2× the token's typical 5-min price movement

| Pair Category            | Typical 5-min Move | Min Spread | Recommended Spread |
| ------------------------ | ------------------ | ---------- | ------------------ |
| Stablecoins (USDT/USDC)  | < 0.01%            | 0.05%      | 0.05-0.1%          |
| Major (ETH, BTC, SOL)    | 0.05-0.2%          | 0.2%       | 0.3-0.8%           |
| Mid-cap (LINK, ARB, UNI) | 0.1-0.4%           | 0.4%       | 0.5-1.5%           |
| Small-cap / Meme         | 0.5%+              | 1.0%       | 1.5-3.0%           |

> See [11_expert_tips](11_expert_tips.md#spread-rules-community-consensus) for dynamic spread formulas

---

## High-Volume Majors (Best for Market Making)

| Pair         | Daily Volume | Primary DEX           | Secondary DEX | Strategy       |
| ------------ | ------------ | --------------------- | ------------- | -------------- |
| **ETH/USDT** | $10B+        | Uniswap V3 (Arbitrum) | SushiSwap     | PMM, XEMM, Arb |
| **ETH/USDC** | $5B+         | Uniswap V3 (Base)     | Aerodrome     | PMM, Arb       |
| **SOL/USDT** | $3B+         | Raydium, Jupiter      | Orca          | PMM, Arb       |
| **SOL/USDC** | $1B+         | Orca                  | Raydium       | PMM            |
| **BNB/USDT** | $1B+         | PancakeSwap V3        | BiSwap        | PMM, XEMM      |
| **BTC/USDT** | $15B+        | Uniswap V3 (wBTC)     | SushiSwap     | Arb            |

---

## Stablecoin Pairs (Lowest Risk)

| Pair          | Spread Range | Where          | Strategy        | Notes                       |
| ------------- | ------------ | -------------- | --------------- | --------------------------- |
| **USDT/USDC** | 0.01-0.1%    | Curve, Uniswap | Arb             | Most liquid stable pair     |
| **USDC/DAI**  | 0.02-0.15%   | Curve, Maker   | Arb             | DAI soft-peg can diverge    |
| **USDT/DAI**  | 0.05-0.3%    | Uniswap, Curve | Arb             | Wider spreads = more profit |
| **USDC/USDT** | 0.01-0.05%   | Cross-chain    | Cross-chain arb | Arb between Arbitrum↔Base   |

---

## Mid-Cap Pairs (Higher Spreads = More Profit)

| Pair           | Typical Spread | Volume | Risk        | Why Trade It                     |
| -------------- | -------------- | ------ | ----------- | -------------------------------- |
| **LINK/USDT**  | 0.2-0.5%       | High   | Medium      | Oracle leader, consistent volume |
| **ARB/USDT**   | 0.3-0.8%       | Medium | Medium      | L2 native token, growing         |
| **UNI/USDT**   | 0.2-0.5%       | Medium | Medium      | DeFi blue chip                   |
| **AAVE/USDT**  | 0.3-0.8%       | Medium | Medium      | Lending protocol leader          |
| **AVAX/USDT**  | 0.3-0.7%       | Medium | Medium      | Avalanche native                 |
| **POL/USDT**   | 0.2-0.5%       | Medium | Medium      | Polygon ecosystem (formerly MATIC)|
| **OP/USDT**    | 0.3-0.8%       | Medium | Medium      | Optimism native                  |
| **INJ/USDT**   | 0.4-1.0%       | Medium | Medium-High | Cosmos DeFi, wider spreads       |

---

## Arbitrage Opportunity Matrix

### DEX-DEX Arbitrage Pairs

| DEX 1              | DEX 2             | Pair     | Typical Arb Spread | Gas Cost | Notes                   |
| ------------------ | ----------------- | -------- | ------------------ | -------- | ----------------------- |
| Raydium (Solana)   | Orca (Solana)     | SOL/USDC | 0.1-0.3%           | ~$0.005  | Same-chain, ultra-fast  |
| Uniswap (Arbitrum) | SushiSwap (Arb)   | ETH/USDT | 0.05-0.2%          | ~$0.05   | Same-chain              |
| Uniswap (Arbitrum) | Uniswap (Base)    | ETH/USDC | 0.05-0.15%         | Variable | Cross-L2, bridge needed |
| Uniswap (Ethereum) | PancakeSwap (BSC) | ETH/USDT | 0.1-0.3%           | Variable | Cross-chain             |
| PancakeSwap (BSC)  | BiSwap (BSC)      | BNB/USDT | 0.1-0.3%           | ~$0.07   | Same-chain              |

---

## High-Alpha & Trending Pairs (For 10-50% Profit Targets)

To achieve 10-50% daily targets, you must move beyond established majors into **high-velocity narrative tokens**. These tokens move 10%+ daily, allowing a bot to capture massive swings using trend-following or wide-spread market making.

| Pair Category       | Examples (Solana/L2) | Bullish Trigger          | Typical Daily Move | Risk        |
| ------------------- | -------------------- | ------------------------ | ------------------ | ----------- |
| **New Narrative**   | AI (GOAT, VIRTUAL)   | Social volume spike      | 15-40%             | Very High   |
| **Ecosystem Beta**  | JUP, PYTH, KMNO      | Protocol news / airdrops | 5-15%              | Medium-High |
| **Blue-chip Memes** | PEPE, BONK, WIF      | ETH/SOL price strength   | 10-30%             | High        |
| **DEX Launchpad**   | New Raydium listings | 24H Vol > Liquidity      | 50%+               | Extreme     |
| **Liquidity Snipe** | "Block 0" Launches   | `PoolCreated` Event      | 100-1000%          | Critical    |
| **Leveraged Perps** | ETH-PERP / SOL-PERP  | Hyperliquid (Zero Gas)   | 20x Amplification  | High        |

### How to Safely Trade These on $100

1. **Never HODL**: These are for 30-minute to 4-hour bot sessions only.
2. **Strict Filtering**: For Spot/Sniping, only trade tokens with **Liquidity > $50k** and **Contract Verified** to avoid "honeypot" scams.
3. **Use WIDE Spreads (Spot)**: Set spreads to 2.5% to 5.0%. The volatility is so high that these will still fill, providing massive profit buffers.
4. **Micro-Scalp Leverage (Perps)**: On Hyperliquid, target 1% actual price moves with 20x leverage to achieve 20% account growth per trade. Ensure stop-losses are incredibly tight.

---

## Pair Selection by Strategy

### For PMM (Market Making)

**Best**: High volume + moderate spread + range-bound

1. ETH/USDT on Arbitrum (safest)
2. SOL/USDT on Raydium (cheapest gas)
3. BNB/USDT on PancakeSwap (BNB ecosystem)

### For AMM Arbitrage

**Best**: High volatility + cross-venue presence + low gas chain

1. SOL/USDT: Raydium ↔ Orca (fastest arb cycle)
2. ETH/USDT: Uniswap (Arbitrum) ↔ SushiSwap (Arbitrum)
3. BNB/USDT: PancakeSwap ↔ BiSwap

### For XEMM

**Best**: Significant liquidity gap between venues

1. ETH/USDT: DEX maker (smaller DEX) → DEX taker (Uniswap)
2. SOL/USDT: DEX maker (Meteora) → DEX taker (Raydium)

### For CLMM LP

**Best**: Highest fee-generating pairs

1. ETH/USDC on Uniswap V3 (Arbitrum) — ~30% APR
2. SOL/USDC on Raydium Concentrated — ~40% APR
3. ETH/USDT on Uniswap V3 (Base) — ~25% APR

### For Stablecoin Arbitrage

**Best**: Maximum safety, thin but consistent margins

1. USDT/USDC across Curve pools
2. USDC cross-chain (Arbitrum ↔ Base)
3. DAI/USDC on Uniswap
