# 🚀 Playbooks: Beginner → Advanced

> Step-by-step guides for different experience levels
> **Before any live deployment**: complete the [pre-launch checklist](11_expert_tips.md#checklist-before-going-live)

---

## Beginner: "First Week" ($50-100)

**Goal:** Learn the system safely

### Day 1-2: Paper Trading

```bash
docker attach hummingbot
# Set password, then:
paper_trade              # Enable paper trading mode
create --controller-config market_making.pmm_simple
# Settings: ETH-USDT, $100, 0.5% spread, 120s refresh, 3% SL
start --script v2_with_controllers.py --conf your_config.yml
status                   # Monitor
```

### Day 3-4: Real Money ($50)

- Disable paper trading
- Use Solana (lowest gas, best for $50 budget)
- Set spread to 0.7%, order amount $10
- Monitor every 2 hours

### Day 5-7: Evaluate & Adjust

- Check `history` and `pnl`
- If profitable → increase to $100
- If losing → widen spreads to 1%
- **Check market regime** — is it sideways (good for PMM) or trending (pause or adjust)?
- Review [expert tips on common mistakes](11_expert_tips.md#top-10-mistakes-to-avoid)

---

## Intermediate: "Steady Income" ($250-$500)

**Goal:** Consistent daily returns

### Portfolio Split

| Strategy   | Allocation | Pair      | Chain       |
| ---------- | ---------- | --------- | ----------- |
| PMM        | 40%        | ETH/USDT  | Arbitrum    |
| PMM        | 30%        | SOL/USDT  | Raydium     |
| Stable Arb | 30%        | USDT/USDC | Cross-chain |

### Setup

```bash
# Create 3 controller configs, then:
start --script v2_with_controllers.py --conf multi_strategy.yml
```

### Target: 0.5-1% daily combined

### Key Practices

- Check market regime daily — adjust spreads per [expert tips](11_expert_tips.md#settings-adjustments-by-regime)
- Enable inventory skew on all PMM strategies
- Track net P&L (after gas + fees) not gross

---

## Advanced: "Alpha Seeker" ($1000+)

**Goal:** Maximum returns with active management

### Portfolio Split

| Strategy   | Allocation | Pair        | Details             |
| ---------- | ---------- | ----------- | ------------------- |
| XEMM V2    | 30%        | ETH/USDT    | DEX→DEX hedge       |
| AMM Arb    | 25%        | SOL/USDT    | Jupiter↔Orca        |
| CLMM LP    | 25%        | ETH/USDC    | Uniswap V3 Arbitrum |
| **Sniper** | **20%**    | **Meme/AI** | **Directional V2**  |

### Requires

- Multiple DEX wallets initialized (MetaMask + Phantom)
- Core edge services running: regime-service, session-service, inventory-service, hedge-service, pnl-service, correlation-service, alert-service
- Manual experiment tracking across PRODUCTION/TESTING/EXPLORATION tiers
- Scanners: alpha-service (token scoring), arb-service (cross-DEX spreads), funding-scanner-service (multi-pair funding rates), narrative-service (social momentum)
- Orchestration: clmm-service (range optimization) + operator-run multi-bot workflow
- Target: 1-3% daily combined
- Use [dynamic spread controllers](11_expert_tips.md#technique-1-volatility-adaptive-spreads) (pmm_dynamic, dman_v3) instead of fixed spreads
- Implement [multi-timeframe regime filter](11_expert_tips.md#technique-3-multi-timeframe-regime-filter) before placing orders

---

## ⚡ Hyper-Velocity: "The 48-Hour 2x" ($100 to $200)

**Goal:** Double capital in the shortest possible window. _High risk of total loss._

### Option A: The "Swarm" (Spot DEX)

> _Theory and mechanics: see [02_strategies.md](02_strategies.md#8-liquidity-sniping-v2-custom)_

- **Chain**: Solana
- **Capital**: $100 split across 10 separate bot instances ($10 each) via Docker Compose.
- **Action**: Run the `mqtt_directional_v2.yml` config. Use an external script to feed trending 1-minute token pairs via MQTT.
- **Target/Risk**: 50% Take Profit, 15% Stop Loss. Needs 4 out of 10 wins to double total capital.

### Option B: Leveraged Micro-Scalping (Perp DEX)

> _Theory and mechanics: see [02_strategies.md](02_strategies.md#9-hyper-leverage-perps-hyperliquiddydx)_

- **Chain**: Hyperliquid L1 (Zero Gas)
- **Capital**: Full $100 deposit.
- **Action**: Run the `hyperliquid_scalp_20x.yml` controller.
- **Target/Risk**: Wait for volatility, capture five 1% price moves at 20x leverage (20% ROI per scalp).
- **Execution**: Strictly enforce the 2% exchange-side Stop Loss.

---

## Quick Reference Commands

```bash
docker attach hummingbot      # Enter bot CLI
gateway connect               # Add DEX wallet
create --controller-config    # Create strategy
start --script ... --conf ... # Start trading
status / balance / history    # Monitor
stop                          # Stop strategy
exit                          # Exit CLI
```

---

## Resources

| Resource          | URL                                |
| ----------------- | ---------------------------------- |
| Hummingbot Docs   | https://hummingbot.org/docs/       |
| V2 Strategies     | https://hummingbot.org/strategies/ |
| Gateway Guide     | https://hummingbot.org/gateway/    |
| API Swagger       | http://localhost:8000/docs         |
| EMQX Dashboard    | http://localhost:18083             |
| Community Discord | https://discord.gg/hummingbot      |
