# 🚀 Playbooks: Local, Multi-Chain, Multi-Bot

> Last reviewed: March 6, 2026
> Focus: practical deployment paths without the hype loops.

---

## 1. Beginner Playbook

### Goal

Learn current Hummingbot V2 without locking yourself into one chain.

### Week 1

- generate one `pmm_simple` config for a liquid pair
- generate one `macd_bb_v1` config for a high-volatility pair
- paper trade or dry run first

### Recommended starter markets

| Goal | Pair idea | Chain / venue |
| --- | --- | --- |
| Liquid learning market | WETH-USDC | Base / Uniswap |
| Cheap liquid learning market | SOL-USDC | Solana / Raydium |
| Non-Solana retail flow | WBNB-USDT or major BNB pair | BNB / PancakeSwap |

## 2. Intermediate Playbook

### Goal

Run a small diversified book.

### Suggested mix

| Bucket | Controller | Market type |
| --- | --- | --- |
| Core liquid MM | `pmm_dynamic` | Base or Arbitrum major |
| Fast directional | `macd_bb_v1` | Solana new-token shortlist |
| Non-Solana directional | `bollinger_v2` or `macd_bb_v1` | Base or BNB new-token shortlist |
| Hedge leg | Hyperliquid perp | Neutralize directional inventory |

## 3. Advanced Playbook

### Goal

Separate execution by market maturity.

### Framework

| Stage | What you do |
| --- | --- |
| **Discovery** | scan Solana, Base, and BNB token flow |
| **Entry** | use directional controllers, small size |
| **Stabilization** | switch to `pmm_dynamic` only after two-way flow appears |
| **Cross-venue expansion** | add `xemm_multiple_levels` or arb when token cross-lists |
| **Yield stage** | consider `lp_rebalancer` only after the pool matures |

## 4. New-Token Playbook

### Best chain order

1. Solana
2. Base
3. BNB Chain
4. Arbitrum

### Default rules

- start with directional controllers
- require liquidity floor
- require real volume, not just printed price changes
- widen stops only if liquidity justifies it
- move to PMM only after price discovery slows

## 5. Multi-Bot Playbook

Use Hummingbot API when you need:

- multiple bots
- remote orchestration
- service-driven signal deployment

Use Client only when you want:

- local learning
- one or two manually supervised bots

## 6. Platform Diversification Playbook

### Strong default split

| Allocation focus | Suggested platforms |
| --- | --- |
| Early token flow | Solana + Base |
| Retail rotation | BNB Chain |
| Mature EVM liquidity | Arbitrum |
| Hedge / perps | Hyperliquid |

---

Next reads:

- [03_chains_and_dexs.md](03_chains_and_dexs.md)
- [02_strategies.md](02_strategies.md)
- [13_profit_scenarios.md](13_profit_scenarios.md)
