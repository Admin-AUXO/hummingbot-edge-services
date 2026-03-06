# ⏳ Profitability Reality Check

> Last reviewed: March 6, 2026
> Purpose: realistic expectations by strategy class, without “double fast” framing.

---

## 1. What Actually Drives Results

Results depend far more on:

- market selection
- venue selection
- fee drag
- slippage
- regime matching
- risk discipline

than on the bot alone.

## 2. Expected Behavior by Strategy Type

| Strategy type | Return profile | Stability | Best use |
| --- | --- | --- | --- |
| **PMM / PMM Dynamic** | Lower upside, steadier | Higher | Mature liquid pairs |
| **Directional new-token trading** | Higher upside, unstable | Lower | Fresh listings and narrative flow |
| **Arbitrage / XEMM** | Medium upside, execution-dependent | Medium | Multi-venue tokens |
| **LP automation** | Fee-driven, slower | Medium | Mature active pools |
| **Perp hedge / funding** | Utility and carry more than discovery | Medium | Risk reduction and yield overlays |

## 3. Small Account Reality

For small accounts:

- Solana, Base, and BNB are usually more practical than Ethereum mainnet
- PMM on very small size works only when fees stay small relative to spread
- new-token directional trading can outperform, but variance is much higher

## 4. Best Practical Mix by Objective

### If you want steadier compounding

- Base / Arbitrum majors with `pmm_dynamic`
- Hyperliquid hedge if needed

### If you want higher upside

- directional controllers on Solana, Base, and BNB new-token shortlists
- move only selected winners into later PMM or arb workflows

### If you want platform diversification

- Solana for first-wave discovery
- Base for best non-Solana new-token exposure
- BNB Chain for retail token rotation
- Arbitrum for mature-liquidity follow-through

## 5. The Main Profitability Error

The most common mistake is using a mature-market strategy on an immature token.

Examples:

- PMM on a token that just launched
- LP on a pool with unstable price discovery
- arb before there are actually two reliable venues

## 6. Sober Strategy Ranking

| Goal | Best first strategy |
| --- | --- |
| **Mature pair compounding** | `pmm_dynamic` |
| **Fresh new-token participation** | `macd_bb_v1` or `bollinger_v2` |
| **Multi-venue edge** | `xemm_multiple_levels` or arbitrage |
| **CLMM fee capture** | `lp_rebalancer` |

---

Next reads:

- [02_strategies.md](02_strategies.md)
- [08_playbooks.md](08_playbooks.md)
- [11_expert_tips.md](11_expert_tips.md)
