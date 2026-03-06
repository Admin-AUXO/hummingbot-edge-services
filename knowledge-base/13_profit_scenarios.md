# ⏳ Profit Scenarios & Time to Profit ($100 Capital)

> The realistic milestones, challenges, and timelines for trading with a $100 starter budget on DEXs.

---

## 1. The $100 Reality Check: Learning > Earning

Starting with $100 on decentralized exchanges is the **best way to learn bot trading**. At this scale, your goal is to prove you can maintain a **positive yield curve over 30 days**. Once validated, you scale to $1,000+.

### The Profitability Hurdle: Gas & Fees

Small trade sizes ($10-$20) are sensitive to gas.

| Variable                | Solana Reality | L2 (Base/Arb) Reality |
| ----------------------- | -------------- | --------------------- |
| **Order Size**          | $20            | $20                   |
| **Gross Profit (0.5%)** | $0.10          | $0.10                 |
| **Gas Fee**             | $0.005         | $0.05                 |
| **Net Profit**          | **$0.045**     | **-$0.005 (LOSS)**    |

**Conclusion:** For $100 capital, you **must** use Solana or target much wider spreads (5%+) on L2s.

---

## 2. Hyper-Velocity Scenarios (The Path to 2x)

### Scenario A: Pure Market Making (SOL/USDC)

- **Strategy**: "The Grinder"
- **Time to Double**: **8 - 12 months**
- **Verdict**: Too slow for users wanting rapid growth. Use this only for safety.

### Scenario B: DEX-DEX Arbitrage (Solana)

- **Strategy**: "The Arb Hunter"
- **Time to Double**: **3 - 6 months**
- **Edge service**: `arb-service` scans DexScreener every 60s, catches 0.5%+ price gaps across Raydium/Orca/Meteora — see [15_edge_systems](15_edge_systems.md#system-8-cross-dex-arbitrage-scanner--implemented)
- **Verdict**: Solid, but passive. Limited by market discrepancies.

### Scenario C: Directional Momentum (V2 Sniper)

- **Strategy**: "The Momentum Sniper"
- **Time to Double**: **2 - 14 Days**
- **Edge service**: `alpha-service` scores tokens on 6-criteria rubric, `regime-service` confirms trend direction — see [15_edge_systems](15_edge_systems.md#system-5-ai-alpha-pipeline--implemented-phase-1)
- **Risk**: High. Requires hitting 4-5 successful 20% trades.

### Scenario D: Liquidity Sniping (The "Flash Sniper")

- **Strategy**: Extreme momentum on pool launch.
- **Time to Double**: **4 - 24 Hours**
- **Edge workflow**: `alpha-service` scores new listings; pool-launch detection is manual/external script driven — see [15_edge_systems](15_edge_systems.md#system-13-airdrop--migration-monitor--archived)
- **Risk**: Extreme. Most pools are rugs. Requires splitting $100 into 10-20 "snipes."

### Scenario E: Leveraged Perps (Hyperliquid)

- **Strategy**: 20x Leverage Micro-Scalping.
- **Time to Double**: **24 - 48 Hours**
- **Edge service**: `funding-scanner-service` scans all Binance Futures rates, finds HIGH/EXTREME opportunities — see [15_edge_systems](15_edge_systems.md#system-9-multi-pair-funding-scanner--implemented)
- **Risk**: High. Requires high precision and zero gas fees.

### Scenario F: Narrative Momentum Trading

- **Strategy**: Ride narrative waves (AI, meme, RWA, DePIN) on spiking tokens.
- **Time to Double**: **2 - 7 Days**
- **Edge service**: `narrative-service` tracks volume per narrative keyword, alerts on 2x+ spikes — see [15_edge_systems](15_edge_systems.md#system-10-narrativesocial-scanner--implemented)
- **Risk**: Medium-high. Narratives can reverse fast, but volume spikes are real signals.

### Scenario G: Funding Rate Harvesting (Delta-Neutral)

- **Strategy**: Spot long + perp short on high-funding-rate pairs. Earn funding payments, zero directional risk.
- **Time to Double**: **2 - 6 months** (30-100%+ annualized APR during spikes)
- **Edge service**: `funding-scanner-service` ranks all pairs by annualized APR, `hedge-service` maintains delta-neutral position
- **Risk**: Low. Market-neutral, but requires capital on both spot and perp.

### Scenario H: LP Reward Farming

- **Strategy**: Provide liquidity to incentivized pools with high reward APR.
- **Time to Double**: **3 - 6 months** (at 50%+ effective APR after risk adjustment)
- **Edge service**: `rewards-service` ranks pools by risk-adjusted APR, `clmm-service` optimizes concentrated liquidity ranges — see [15_edge_systems](15_edge_systems.md#system-14-lp-reward-tracker--implemented)
- **Risk**: Medium. Impermanent loss in trending markets, reward token may depreciate.

---

## 3. Best Ways to Double Capital (Calculated Risks)

Starting with $100, these are the **only** ways to double capital in under 30 days:

### The "Multi-Target Basket" (Bot Farm)

Instead of one bot on SOL/USDC, run **10 separate bot instances** each with $10. Manage lifecycle manually (deploy, TTL expiry, loss kills) using alerts + checklists — see [15_edge_systems](15_edge_systems.md#system-11-multi-pair-bot-swarm--archived).

- **Target**: Trending micro-caps on Solana.
- **Exit**: 100% gain (2x) or -20% Stop Loss.
- **Logic**: You only need **one** 10x winner to double your entire $100.

### High-Leverage Scalping (Perp DEX)

Deposit $100 into Hyperliquid.

- **Leverage**: 20x ($2,000 buying power).
- **Trade**: Target 1% price moves in highly liquid markets (ETH/SOL).
- **Math**: 5 successful 1% trades at 20x = 100% gain = Double.
- **Duration**: **1 - 2 Days**.

### "Pump.fun" Graduate Sniping

Monitor tokens graduating to PumpSwap (pump.fun's native DEX, since March 2025) with a custom Hummingbot script. Detection is manual/external-script based in the current stack — see [15_edge_systems](15_edge_systems.md#system-13-airdrop--migration-monitor--archived).

- **Entry**: First block of PumpSwap listing (~$69K market cap graduation threshold).
- **Exit**: 50% gain trailing stop.
- **Duration**: **< 1 Hour**.

---

### Funding Rate Harvesting (Passive Income)

Use `funding-scanner-service` to find pairs with annualized APR > 30%. Deploy delta-neutral positions (spot long + perp short) via `hedge-service`.

- **Capital**: $50 spot + $50 perp margin
- **Math at 0.1% funding rate**: $50 × 0.1% × 3/day = $0.15/day = **$4.50/mo** = ~108% annualized
- **Duration**: Hold as long as rate stays elevated. Scanner alerts when rates drop.
- **Risk**: Minimal — delta-neutral means you earn regardless of price direction.

### Narrative Sniping (Momentum + Edge Services)

Combine `narrative-service` (detects volume spikes) + `alpha-service` (scores tokens) + manual deployment rules:

- **Capital**: $100 split across 5-10 narrative tokens
- **Flow**: narrative-service alerts → alpha-service scores → operator deploys/rotates bots via checklist
- **Target**: 20-50% on 2-3 winners before narrative peaks
- **Duration**: **3 - 7 Days** per narrative cycle

---

## 4. Growth Summary

| Goal | Strategy | Edge Service | Chain | Time to 2x |
|---|---|---|---|---|
| **Instant** | Sniping | alpha + manual pool watcher | Solana | **< 24 Hours** |
| **Aggressive** | 20x Perps | funding-scanner | Hyperliquid | **1 - 2 Days** |
| **Fast** | Narrative Momentum | narrative + alpha | Solana | **2 - 7 Days** |
| **Medium** | Bot Basket | manual ops + alpha | Solana | **2 - 14 Days** |
| **Steady** | Cross-DEX Arb | arb-service | Solana | **3 - 6 Months** |
| **Passive** | Funding Harvesting | funding-scanner + hedge | Multi-chain | **2 - 6 Months** |
| **Yield** | LP Rewards | rewards + clmm | Solana | **3 - 6 Months** |
| **Safe** | PMM Grinder | regime + session | Solana | **8 - 12 Months** |

---

## 5. Survival Rules for High Velocity

> Full risk controls: see [06_risk_management](06_risk_management.md#hyper-velocity-risk-control-for--48h-doubling).

- **Never trade without a stop-loss.** One bad trade at 20x leverage = $0 balance.
- **Use Zero-Fee/Low-Fee chains.** For $100, every $0.10 gas fee is a 0.1% loss of the _entire_ account.
- **Verify Liquidity.** Do not snipe pools with < $20k liquidity. `alpha-service` enforces $50K minimum by default.
- **Use a weekly experiment log** to track hypotheses with explicit kill criteria.
- **Use manual bot basket rules** — kill bots exceeding 20% loss or 48h TTL.
- **Use regime-service** before any trade — wrong regime = guaranteed loss. Alerts on change via Telegram.
- **Use funding-scanner-service** for delta-neutral plays — only enter when annualized APR > 30%.
- **Use external unlock calendars** — avoid providing liquidity during major token unlocks (>2% supply).
