# 🎯 DEX Trading Skills

> Practical skills for profitable decentralized exchange trading
> Companion to strategies and configs — this covers the human edge

---

## Skill 1: On-Chain Analysis (Reading the Blockchain)

The blockchain is a public ledger. Learning to read it gives you information advantages over traders who only watch price charts.

### What to Monitor

| Data Point | Tool | Why It Matters |
|---|---|---|
| **Whale wallets** | Arkham, Nansen, Debank | Large buys/sells signal direction before price moves |
| **Token holder distribution** | Solscan, Etherscan | Top 10 holders own 80%+ = rug risk |
| **Smart money flows** | Nansen Smart Money | Follow wallets with consistent alpha |
| **DEX volume spikes** | DexScreener, Birdeye | Sudden volume = breakout or dump incoming |
| **New pool creation** | DEX factory event logs | First-mover advantage on new listings |
| **Bridge flows** | DefiLlama bridges | Capital moving to a chain = upcoming activity |

### Key Skill: Wallet Tracking

1. Find profitable wallets via Arkham Intelligence or Nansen
2. Set up alerts for their transactions
3. When they accumulate a token, research why
4. Mirror positions with smaller size and tighter stops
5. Never blindly copy — validate the thesis independently

---

## Skill 2: Token Screening & Due Diligence

Before trading any token, run this filter to avoid scams and dead coins.

### The 60-Second Token Screen

```
1. LIQUIDITY CHECK
   □ Pool TVL > $50K? (below = too thin for bots)
   □ Liquidity locked or burned? (check via Solscan/Etherscan)
   □ LP token holders diversified? (1 holder = rug risk)

2. CONTRACT CHECK
   □ Contract verified on explorer?
   □ No mint function or owner-only pause? (honeypot indicators)
   □ Renounced ownership? (safer but not guaranteed)

3. VOLUME CHECK
   □ 24H volume > $100K?
   □ Buy/sell ratio roughly balanced? (one-sided = manipulation)
   □ Volume/MCAP ratio > 0.1? (active trading)

4. SOCIAL CHECK
   □ Active community (Twitter, Telegram)?
   □ Developer activity (GitHub commits)?
   □ Any audit reports?
```

### Red Flags (Exit Immediately)

- Top wallet holds > 50% of supply
- Contract has `blacklist` or `setMaxTxAmount` functions
- No social presence or website
- Trading only enabled for buys (honeypot)
- Massive unlock event within 7 days

### Token Screening Tools

| Tool | Chain | Free Tier | Best For |
|---|---|---|---|
| **DexScreener** | Multi-chain | Yes | Real-time pair charts, volume, liquidity |
| **Birdeye** | Solana | Yes | Solana token analytics, wallet tracking |
| **DEXTools** | Multi-chain | Yes | Pair explorer, hot pairs, audit scores |
| **GeckoTerminal** | Multi-chain | Yes | Pool analytics, trending tokens |
| **RugCheck** | Solana | Yes | Automated rug-pull detection |
| **TokenSniffer** | EVM | Yes | Contract audit scoring |
| **BubbleMaps** | Multi-chain | Yes | Visual token holder distribution |

---

## Skill 3: Gas Optimization

Gas is your largest variable cost. Mastering gas timing can 2-3x your net profit.

### EVM Gas Strategies

- **Time your trades**: Gas is cheapest during Asian overnight hours (0:00-4:00 UTC)
- **Use L2s**: Arbitrum/Base gas is 10-100x cheaper than Ethereum L1
- **Batch approvals**: Approve all tokens you plan to trade in a single low-gas window
- **Refresh tolerance**: Set `order_refresh_tolerance_pct: 0.002` to skip unnecessary cancels
- **Filled order delay**: Higher delay = fewer TXs = less gas

### Solana Gas Strategies

- **Priority fees**: Default 0.000005 SOL base. Add priority fee only when network is congested
- **Jito tips**: For time-sensitive trades (sniping), pay Jito tips for block priority. Min 1,000 lamports
- **Compute units**: Request only the compute units you need — lower CU = lower priority fee

### Gas Monitoring Tools

| Tool | What It Shows |
|---|---|
| **l2fees.info** | Real-time L2 gas comparison |
| **Arbiscan gas tracker** | Arbitrum gas in gwei |
| **Solana Priority Fee Tracker** (QuickNode) | Current Solana priority fees |
| **Blocknative Gas Estimator** | Ethereum L1 gas prediction |

---

## Skill 4: Wallet Security & OpSec

A compromised wallet = total loss. Security is non-negotiable.

### Wallet Architecture

```
Hot Wallet (MetaMask/Phantom) ← Bot trading wallet
  └── Only holds active trading capital ($100-500)
  └── Connected to Hummingbot Gateway
  └── Separate from main holdings

Cold Wallet (Ledger/Trezor) ← Main storage
  └── Bulk of crypto holdings
  └── Never connected to bots or dApps
  └── Transfer to hot wallet only as needed

Burner Wallet ← New token sniping
  └── Disposable, holds $10-50 max
  └── Used for unverified tokens/contracts
  └── Expect potential loss
```

### Security Checklist

```
□ Use dedicated trading wallet (never your main wallet)
□ Never share private keys or seed phrases
□ Hummingbot encrypts keys with GATEWAY_PASSPHRASE — use a strong one
□ Revoke token approvals after done trading (revoke.cash)
□ Set spending limits on approvals when possible
□ Run Hummingbot on a dedicated VPS (not shared machines)
□ Enable 2FA on all exchange accounts
□ Backup wallet seed phrases offline (paper/metal)
□ Regularly check wallet for unauthorized approvals
□ Use a VPN when connecting to public RPCs
```

### Approval Hygiene

Token approvals grant unlimited spending by default on EVM chains. Best practices:
- Use **revoke.cash** to audit and revoke stale approvals monthly
- Prefer **Permit2** (Uniswap V4) which uses time-bound approvals
- On Solana, SPL tokens don't require approvals (inherently safer model)

---

## Skill 5: Market Regime Detection

The most important skill for bot traders. Wrong regime = guaranteed loss.

> Full regime detection tables, YAML config overrides, and automated classification logic: see [11_expert_tips](11_expert_tips.md#market-regime-awareness-most-important-skill) and [15_edge_systems](15_edge_systems.md#system-1-automated-regime-switching).
> The regime-service automates this via MQTT — see `regime-service/` in the codebase.

### Regime Detection Tools

| Tool | Free | What It Does |
|---|---|---|
| **TradingView** | Freemium | Charts, indicators, alerts. The standard |
| **DexScreener** | Yes | Real-time DEX pair charts with volume |
| **Coinglass** | Yes | Funding rates, open interest, liquidation maps |
| **Fear & Greed Index** | Yes | Market sentiment gauge (extreme = reversal signal) |
| **Santiment** | Freemium | Social volume, dev activity, whale alerts |

---

## Skill 6: Portfolio & P&L Tracking

> Automated by `pnl-service/` (aggregates executor analytics per pair → MQTT) and `alert-service/` (Telegram alerts on win rate/Sharpe warnings).

If you can't measure it, you can't improve it.

### What to Track Daily

| Metric | Target | Action if Off |
|---|---|---|
| **Net P&L** (after gas + fees) | Positive | Review spreads, switch pairs |
| **Win rate** | > 50% for PMM, > 30% for directional | Widen spreads or tighten stops |
| **Average trade size** | Within position limits | Reduce if too large |
| **Gas as % of profit** | < 30% | Switch to cheaper chain |
| **Inventory skew** | Within 40-60% range | Enable/adjust inventory skew |
| **Drawdown from peak** | < max drawdown limit | Pause bot, reassess |
| **Fill rate** | > 2 fills/hour | Tighten spreads if too low |

### Tracking Tools

| Tool | Cost | Best For |
|---|---|---|
| **Hummingbot `history` command** | Free | Quick P&L check inside bot CLI |
| **Hummingbot Dashboard** | Free | PostgreSQL-backed analytics for bot swarms |
| **DeBank** | Free | Cross-chain portfolio view |
| **Zapper** | Free | DeFi portfolio + yield tracking |
| **CoinTracker / Koinly** | Paid | Tax-ready reports |
| **Custom spreadsheet** | Free | Manual tracking with formulas |

### Daily P&L Template

```
Date: ____
Starting Balance: $____
Ending Balance: $____
Gross P&L: $____
Gas Spent: $____
Fees Paid: $____
Net P&L: $____
Win/Loss: __/__
Best Trade: ____
Worst Trade: ____
Market Regime: [Bull/Bear/Sideways/Volatile]
Notes: ____
```

---

## Skill 7: DEX-Specific Execution Skills

### Reading AMM Pool State

Understanding pool mechanics helps you set better parameters:
- **Pool ratio**: `x * y = k`. When one token is bought, the other's price rises
- **Price impact**: Larger orders move the price more. Keep orders < 1% of pool TVL
- **Fee tiers**: Lower fee pools (0.01%, 0.05%) for stables/majors, higher (0.3%, 1%) for volatile pairs
- **Tick spacing**: On CLMM pools, tighter tick spacing = more granular LP positions

### Reading CLOB Order Books (Hyperliquid/dYdX)

- **Bid-ask spread**: Tighter = more competitive, wider = more profit per fill
- **Order book depth**: Thin book at ±1% = potential for large slippage
- **Funding rate**: Positive = longs pay shorts (bearish bias). Negative = shorts pay longs. The `funding-scanner-service` monitors all Binance Futures rates and ranks by annualized APR — see [15_edge_systems](15_edge_systems.md#system-9-multi-pair-funding-scanner--implemented)
- **Open interest**: Rising OI + rising price = strong trend. Rising OI + falling price = building short pressure

### Execution Optimization

- **Slippage settings**: 0.5% for majors, 1-2% for mid-caps, 3-5% for micro-caps
- **MEV protection**: Use Jupiter's MEV protection on Solana. Use Flashbots Protect on Ethereum
- **TX timing**: Avoid the first/last 5 minutes of major market opens (high volatility, wide spreads)
- **RPC quality**: Paid RPCs (Helius, Alchemy) provide faster block data = faster bot reactions

---

## Skill 8: Narrative & Catalyst Trading

DEX markets move in narrative waves. Identifying the current narrative = finding the highest-volatility opportunities.

### How to Identify the Current Narrative

1. **Twitter/X Crypto Feed**: Follow 20-30 alpha accounts. Track what tokens they're discussing
2. **DexScreener Trending**: Check "Trending" tab for volume spikes
3. **Coingecko Categories**: See which categories are outperforming (AI, Memes, L2s, RWA)
4. **On-chain data**: New pool creation spikes in a sector = capital flowing in

### Narrative Cycle Stages

```
1. EARLY (Best entry)
   - Only alpha accounts discussing it
   - Small pools, low liquidity
   - 1-3 tokens in the narrative

2. GROWTH (Still profitable)
   - Crypto Twitter widely discussing
   - New tokens launching daily in the category
   - Volume surging on DexScreener trending

3. PEAK (Take profit)
   - Mainstream crypto media covering it
   - Everyone on Twitter talking about it
   - Dozens of copycat tokens launching

4. DECLINE (Exit or short)
   - Volume dropping
   - New launches failing
   - Narrative fatigue setting in
```

### Applying Narratives to Bot Trading

- **Early stage**: Use Directional V2 with tight stops on 1-2 leading tokens
- **Growth stage**: PMM with wide spreads (2-5%) on high-volume narrative tokens
- **Peak stage**: Tighten stops, start taking profits
- **Decline stage**: Stop trading narrative tokens, return to majors

> The `narrative-service` automates narrative detection by scanning DexScreener per keyword and alerting on volume spikes. The `alpha-service` scores individual tokens on a 6-criteria rubric. See [15_edge_systems](15_edge_systems.md#system-10-narrativesocial-scanner--implemented).

---

## Skill 9: Troubleshooting & Recovery

### Common Bot Issues & Fixes

| Symptom | Likely Cause | Fix |
|---|---|---|
| Bot running but no fills | Spreads too wide or pair too illiquid | Tighten spreads or switch to higher-volume pair |
| Rapid inventory accumulation | Market trending against you | Enable inventory skew, check regime, pause if needed |
| TX failures | Gas too low or RPC rate limited | Increase gas, switch to paid RPC |
| Negative P&L despite fills | Gas + fees > spread profit | Widen spreads or move to cheaper chain |
| Bot disconnects frequently | VPS/network issues | Check Docker logs, restart gateway, use stable VPS |
| Slippage exceeding buffer | Pool liquidity dropped | Increase slippage buffer or reduce order size |

### Recovery After a Loss

1. **Stop the bot immediately** — don't chase losses
2. **Analyze what happened** — check `history --verbose`, review market regime at time of loss
3. **Identify the cause** — was it regime mismatch, config error, or black swan?
4. **Adjust config** — fix the root cause before restarting
5. **Paper trade the fix** — run paper mode for 24H to validate
6. **Restart with reduced size** — scale back up gradually after proven recovery

---

## Skill 10: Tax & Compliance Awareness

### General Principles (Consult a Local Tax Professional)

- Most jurisdictions treat crypto trading as **taxable events**
- Each swap on a DEX is typically a **separate taxable event**
- Bot trading generates **many taxable events** — hundreds per month
- Market making P&L is typically treated as **short-term capital gains**
- Gas fees are generally **deductible as trading expenses**

### Record-Keeping Requirements

- Keep records of **every trade**: timestamp, pair, amount, price, fees, gas
- Hummingbot saves trade history in CSV format (local) or PostgreSQL (if configured)
- Export regularly — don't wait until tax season

### Tax Tools for DEX Traders

| Tool | Chains | Cost | Features |
|---|---|---|---|
| **Koinly** | Multi-chain | $49-279/yr | Auto-import from wallets, DEX tracking, tax reports |
| **CoinTracker** | Multi-chain | $59-199/yr | Portfolio + tax, integrates with TurboTax |
| **TokenTax** | Multi-chain | $65-3499/yr | DeFi specialist, handles complex strategies |
| **Recap** | Multi-chain | Free tier | UK-focused, simple interface |

### Tips

- Use a **dedicated trading wallet** — makes tax tracking trivial
- **Export Hummingbot data** monthly to a tax tool
- Track **gas costs separately** — they're deductible in most jurisdictions
- If running multiple bots, use PostgreSQL to centralize all trade data
