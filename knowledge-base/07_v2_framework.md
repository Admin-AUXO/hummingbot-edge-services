# 🏗️ Hummingbot V2 Framework

> Architecture, controllers, scripts, and multi-strategy deployment

---

## Architecture

```
V2 Strategy Framework
├── Scripts (Python entry points)
│   ├── v2_with_controllers.py       # Generic controller loader
│   └── v2_directional_rsi.py        # RSI-based directional
├── Controllers (Strategy Logic)
│   ├── market_making/pmm_simple
│   ├── arbitrage/xemm_v2
│   └── grid/gridstrike_v2
├── Executors (Order Management)
│   ├── ArbitrageExecutor
│   ├── PositionExecutor
│   └── DCAExecutor
└── Market Data Provider (Candles + Indicators)
```

## Creating Configs

```bash
# Interactive (inside Hummingbot CLI):
create --controller-config market_making.pmm_simple
# Saves to: /conf/controllers/<name>.yml

# Run single controller:
start --script v2_with_controllers.py --conf my_config.yml
```

## Multi-Controller Setup

```yaml
# conf/scripts/conf_v2_with_controllers.yml
controllers_config:
  - pmm_eth_usdt.yml
  - pmm_sol_usdt.yml
  - arb_eth_cross.yml
```

## File Locations

| What               | Path                 |
| ------------------ | -------------------- |
| Scripts            | `/scripts/`          |
| Controller configs | `/conf/controllers/` |
| Script configs     | `/conf/scripts/`     |
| Logs               | `/logs/`             |

## V2 Strategies (latest: v2.11.0)

- **PMM Simple**: Pure Market Making (modernized in v2.5 with PositionsHeld)
- **PMM Dynamic**: Volatility-adaptive spreads using NATR
- **XEMM V2**: Cross-Exchange Market Making with hedging
- **GridStrike V2**: Grid trading with strike support
- **CLMM**: Concentrated liquidity on Solana DEXs
- **Directional V2**: Trend-following with MACD/Bollinger indicators
- **DMAN V3**: Bollinger Band mid-price shifting
- **Jupiter integration**: Swap routing on Solana

## Recent V2 Changes (v2.5-v2.11)

- Global stop-loss and per-strategy leverage support
- Automatic position-reduction on opposite signals
- 40%+ backtesting performance improvement (ExecutorSimulation)
- Improved Solana/EVM connector reliability (pool discovery, CLMM stability)
- Jupiter migrated to new API
