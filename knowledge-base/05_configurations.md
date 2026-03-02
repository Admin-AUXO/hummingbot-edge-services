# ⚙️ Strategy Configurations

> Ready-to-use YAML templates for Hummingbot V2 strategies

---

## PMM Simple — Conservative (Beginner)

```yaml
# File: conf/controllers/pmm_conservative.yml
# Best for: First-time users, learning the system
# Capital: $100 | Chain: Arbitrum | Risk: Low
controller_name: pmm_simple
controller_type: market_making
connector_name: uniswap_arbitrum_one
trading_pair: ETH-USDT
total_amount_quote: 100
buy_spreads: "0.005,0.01,0.015" # 0.5%, 1%, 1.5%
sell_spreads: "0.005,0.01,0.015"
buy_amounts_pct: "40,35,25"
sell_amounts_pct: "40,35,25"
executor_refresh_time: 60
cooldown_time: 15
leverage: 1
stop_loss: 0.03 # 3% stop loss
take_profit: 0.02 # 2% take profit
time_limit: 3600 # 1 hour max
```

## PMM Simple — Moderate (Intermediate)

```yaml
# File: conf/controllers/pmm_moderate.yml
# Best for: Traders with some experience
# Capital: $100 | Chain: Arbitrum | Risk: Medium
controller_name: pmm_simple
controller_type: market_making
connector_name: uniswap_arbitrum_one
trading_pair: ETH-USDT
total_amount_quote: 100
buy_spreads: "0.003,0.006,0.01,0.015" # Tighter spreads
sell_spreads: "0.003,0.006,0.01,0.015"
buy_amounts_pct: "30,30,25,15"
sell_amounts_pct: "30,30,25,15"
executor_refresh_time: 30
cooldown_time: 10
leverage: 1
stop_loss: 0.02
take_profit: 0.015
time_limit: 1800
```

## PMM Simple — Aggressive (Advanced)

```yaml
# File: conf/controllers/pmm_aggressive.yml
# Best for: Experienced traders, high-volume pairs
# Capital: $100+ | Chain: Solana | Risk: Higher
controller_name: pmm_simple
controller_type: market_making
connector_name: raydium_solana
trading_pair: SOL-USDT
total_amount_quote: 100
buy_spreads: "0.002,0.004,0.007,0.01" # Very tight
sell_spreads: "0.002,0.004,0.007,0.01"
buy_amounts_pct: "35,30,20,15"
sell_amounts_pct: "35,30,20,15"
executor_refresh_time: 15 # Fast refresh
cooldown_time: 5
leverage: 1
stop_loss: 0.015
take_profit: 0.01
time_limit: 900 # 15 min max
```

---

## AMM Arbitrage — DEX↔DEX

```yaml
# File: conf/strategies/arb_eth_sushiswap_uniswap.yml
# Best for: Exploiting DEX-DEX price gaps
# Requires: Arbitrum wallet
strategy: amm_arb
connector_1: sushiswap_arbitrum
market_1: ETH-USDT
connector_2: uniswap_arbitrum_one
market_2: ETH-USDT
min_profitability: 0.003 # 0.3% minimum profit
market_1_slippage_buffer: 0.001 # 0.1% DEX slippage
market_2_slippage_buffer: 0.002 # 0.2% DEX slippage
order_amount: 0.03 # ~0.03 ETH per trade
concurrent_orders_submission: true
```

## AMM Arbitrage — Solana Focus

```yaml
# File: conf/strategies/arb_sol_orca_raydium.yml
# Ultra-low gas on Solana side
strategy: amm_arb
connector_1: orca_solana
market_1: SOL-USDT
connector_2: jupiter_solana
market_2: SOL-USDT
min_profitability: 0.002 # 0.2% (lower threshold due to low gas)
market_1_slippage_buffer: 0.001
market_2_slippage_buffer: 0.001
order_amount: 0.5 # ~0.5 SOL per trade
concurrent_orders_submission: true
```

---

## Stablecoin Arbitrage

```yaml
# File: conf/strategies/arb_stablecoin.yml
# Lowest risk strategy
# Capital: $100+ recommended for thin margins
strategy: amm_arb
connector_1: uniswap_arbitrum_one
market_1: USDT-USDC
connector_2: sushiswap_arbitrum
market_2: USDT-USDC
min_profitability: 0.001 # 0.1%
order_amount: 100 # $100 per trade
market_1_slippage_buffer: 0.0005
market_2_slippage_buffer: 0.0005
```

---

## XEMM V2 — Cross-Exchange Market Making

```yaml
# File: conf/controllers/xemm_eth.yml
# Make on smaller DEX (wider spreads), hedge on deeper DEX (tighter book)
controller_name: xemm_v2
maker_connector: sushiswap_arbitrum
maker_trading_pair: ETH-USDT
taker_connector: uniswap_arbitrum_one
taker_trading_pair: ETH-USDT
buy_maker_levels:
  - [0.002, 20] # 0.2% spread, $20
  - [0.004, 30] # 0.4% spread, $30
  - [0.006, 50] # 0.6% spread, $50
sell_maker_levels:
  - [0.002, 20]
  - [0.004, 30]
  - [0.006, 50]
min_profitability: 0.001 # 0.1% min net
```

---

## Directional V2 — Trend Following (High Alpha)

```yaml
# File: conf/controllers/directional_momentum.yml
# Best for: Capturing 10-50% margins on $100
# Capital: $100 | Chain: Solana | Risk: High
controller_name: directional_v2
connector_name: raydium_solana
trading_pair: WIF-SOL # example high-volatility token
total_amount_quote: 100
candles_config:
  connector: raydium_solana
  trading_pair: WIF-SOL
  interval: 1m # Short timeframe for fast execution
MACD:
  fast: 12
  slow: 26
  signal: 9
BollingerBands:
  length: 20
  std_dev: 2.0
stop_loss: 0.05 # 5% stop
take_profit: 0.20 # 20% initial target
trailing_stop:
  activation_price: 0.10 # Activate trail at 10% profit
  trailing_delta: 0.03 # Trail by 3%
```

---

## Leveraged Micro-Scalping (Hypervelocity)

```yaml
# File: conf/controllers/hyperliquid_scalp_20x.yml
# Best for: Doubling $100 in < 48 Hours
# Capital: $100 | Chain: Hyperliquid | Risk: Critical/Liquidation
controller_name: directional_v2
connector_name: hyperliquid_perpetual
trading_pair: SOL-USD
total_amount_quote: 100
leverage: 20 # Controls $2,000 position on $100 capital
stop_loss: 0.02 # Strict exchange-side stop. 2% drop = 40% account loss
take_profit: 0.01 # Target 1% absolute move. At 20x, this is +20% ROI.
trailing_stop:
  activation_price: 0.005 # Activate early at 0.5% profit
  trailing_delta: 0.002
```

---

## Multi-Controller Setup (The Swarm)

```yaml
# File: conf/scripts/conf_v2_with_controllers.yml
# Run multiple instances of the same strategy on different pairs (Swarm)
controllers_config:
  - directional_meme_1.yml # $10 on WIF-SOL
  - directional_meme_2.yml # $10 on POPCAT-SOL
  - directional_meme_3.yml # $10 on GOAT-SOL
  - directional_meme_4.yml # $10 on PNUT-SOL
  - directional_meme_5.yml # $10 on MOODENG-SOL
```

---

## Inventory & Regime Add-ons

Add these blocks to any PMM config above to protect against inventory drift and adapt to market conditions. See [11_expert_tips](11_expert_tips.md#settings-adjustments-by-regime) for the full regime detection guide.

> The regime-service automates regime detection and publishes to MQTT. The inventory-service monitors skew and kill-switch drawdown.

### Inventory Protection (Add to any PMM)

```yaml
inventory_skew_enabled: true
inventory_target_base_pct: 50
inventory_range_multiplier: 0.5
filled_order_delay: 30
order_refresh_tolerance_pct: 0.002
price_ceiling: 2200
price_floor: 1800
```

### Regime Overrides

> Full YAML for each regime: see [11_expert_tips](11_expert_tips.md#settings-adjustments-by-regime)

| Regime | Key Changes |
|---|---|
| **BULL** | Tighter buys, wider sells, 65% base target |
| **BEAR** | Wider buys, tighter sells, 35% base target, tighter SL |
| **SPIKE** | Very wide spreads, tight SL, short time limit |

---

## External New Token Sniping Setup (Dynamic Pairs)

> ⚠️ Hummingbot does **not** natively scan blockchain mempools for new token creation (like `PoolCreated` events).

To achieve "Liquidity Sniping", you must use a separate script that listens to the chain and passes the token to Hummingbot.

```yaml
# File: conf/controllers/mqtt_directional_v2.yml
# This controller listens to an external service (e.g., Python script plugged into Helius)
# Your script detects the new pool, and sends an MQTT message to Hummingbot to execute the trade.
controller_name: mqtt_directional_v2
connector_name: raydium_solana
trading_pair: DYNAMIC-SOL # Pair is updated dynamically via MQTT when your script finds a new token
total_amount_quote: 10
leverage: 1
stop_loss: 0.15
take_profit: 0.50
```

---

## Data Storage & Trade Analysis Setup

Hummingbot natively stores all trade history, order book snapshots, and order states in **local `.csv` files** inside the `hummingbot_files/data/` folder.
You can view past decisions directly inside the bot by running the `history --verbose` command.

For advanced analysis (e.g., building external dashboards or analyzing past decisions with AI), you should connect Hummingbot to a **PostgreSQL** database rather than relying on CSVs.

```yaml
# File: conf/conf_client.yml (Global Configuration)
# Update these parameters via the Hummingbot CLI by typing `config db_engine`
db_engine: postgresql
db_host: 127.0.0.1
db_port: 5432
db_username: hummingbot_db_user
db_password: your_secure_password
db_name: hummingbot_db
```

---

## Deployment

> See [07_v2_framework](07_v2_framework.md) for full setup and deployment commands.
> **Before going live**: complete the [pre-launch checklist](11_expert_tips.md#checklist-before-going-live).
