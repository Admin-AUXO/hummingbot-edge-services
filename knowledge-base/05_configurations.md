# ⚙️ Current Configuration Patterns

> Last reviewed: March 6, 2026
> Use this file as a **starter map**, not as a substitute for generating fresh configs from your installed Hummingbot version.

---

## 1. Important Rule

Do **not** trust old copy-paste YAML from older guides.

Controller names and connector identifiers have changed over time. The safe workflow is:

1. Generate a fresh controller config from the current client
2. Edit the generated file
3. Keep only parameters that exist in your installed version

## 2. Create Fresh Controller Configs First

Examples:

```bash
create --controller-config market_making.pmm_simple
create --controller-config market_making.pmm_dynamic
create --controller-config directional_trading.macd_bb_v1
create --controller-config directional_trading.bollinger_v2
create --controller-config generic.xemm_multiple_levels
create --controller-config generic.grid_strike
```

If your version exposes `lp_rebalancer`, create that from the generic controller menu in the client.

## 3. Connector Naming Guidance

Use the exact connector name exposed by your installed version.

Current official connector families to prefer:

- `jupiter`
- `raydium`
- `orca`
- `meteora`
- `uniswap`
- `pancakeswap`
- `hyperliquid`
- `hyperliquid_perpetual`

Do not assume older chain-suffixed names unless your client actually generated them.

---

## 4. Starter Pattern: `pmm_simple`

Best for:

- mature pairs
- established liquidity
- later-stage new-token market making after the first price-discovery phase

```yaml
id: pmm-base-weth-usdc
controller_name: pmm_simple
controller_type: market_making
connector_name: uniswap
trading_pair: WETH-USDC
total_amount_quote: 300
buy_spreads: "0.004,0.008"
sell_spreads: "0.004,0.008"
buy_amounts_pct: "50,50"
sell_amounts_pct: "50,50"
executor_refresh_time: 180
cooldown_time: 15
leverage: 1
stop_loss: 0.03
take_profit: 0.015
time_limit: 2700
trailing_stop: "0.01,0.004"
```

Use on:

- Base / Uniswap majors
- Arbitrum / Uniswap majors
- mature Raydium pairs after volatility cools

## 5. Starter Pattern: `pmm_dynamic`

Best for:

- variable volatility
- directional drift where static spreads are too brittle

```yaml
id: pmm-sol-dynamic
controller_name: pmm_dynamic
controller_type: market_making
connector_name: raydium
trading_pair: SOL-USDC
total_amount_quote: 300
buy_spreads: "1,2,4"
sell_spreads: "1,2,4"
buy_amounts_pct: "40,35,25"
sell_amounts_pct: "40,35,25"
executor_refresh_time: 120
cooldown_time: 15
leverage: 1
stop_loss: 0.025
take_profit: 0.02
time_limit: 1800
candles_connector: raydium
candles_trading_pair: SOL-USDC
interval: 3m
macd_fast: 21
macd_slow: 42
macd_signal: 9
natr_length: 14
```

Use on:

- SOL majors
- Base majors
- new tokens only after liquidity is stable enough for two-way flow

## 6. Starter Pattern: `macd_bb_v1`

Best for:

- new tokens
- narrative rotations
- breakout-style entries

```yaml
id: dir-base-newtoken
controller_name: macd_bb_v1
controller_type: directional_trading
connector_name: uniswap
trading_pair: TOKEN-WETH
total_amount_quote: 100
max_executors_per_side: 1
cooldown_time: 600
leverage: 1
stop_loss: 0.04
take_profit: 0.12
time_limit: 3600
trailing_stop: "0.05,0.02"
candles_connector: uniswap
candles_trading_pair: TOKEN-WETH
interval: 3m
bb_length: 100
bb_std: 2.0
bb_long_threshold: 0.0
bb_short_threshold: 1.0
macd_fast: 21
macd_slow: 42
macd_signal: 9
```

Best non-Solana uses:

- Base / Uniswap new-token rotation
- BNB Chain / PancakeSwap retail tokens
- Arbitrum / Uniswap listings that already have some depth

## 7. Starter Pattern: `bollinger_v2`

Best for:

- mean-reversion entries
- stretched tokens after initial breakout

```yaml
id: dir-bnb-bollinger
controller_name: bollinger_v2
controller_type: directional_trading
connector_name: pancakeswap
trading_pair: TOKEN-WBNB
total_amount_quote: 100
max_executors_per_side: 1
cooldown_time: 900
leverage: 1
stop_loss: 0.035
take_profit: 0.10
time_limit: 3600
trailing_stop: "0.04,0.015"
candles_connector: pancakeswap
candles_trading_pair: TOKEN-WBNB
interval: 3m
bb_length: 100
bb_std: 2.0
bb_long_threshold: 0.1
bb_short_threshold: 0.9
```

## 8. Starter Pattern: `xemm_multiple_levels`

Best for:

- later-stage tokens with one wider venue and one deeper hedge venue

```yaml
id: xemm-arb-token
controller_name: xemm_multiple_levels
maker_connector: uniswap
maker_trading_pair: TOKEN-WETH
taker_connector: hyperliquid
taker_trading_pair: TOKEN-USD
total_amount_quote: 300
buy_levels_targets_amount: "0.004,40-0.008,60"
sell_levels_targets_amount: "0.004,40-0.008,60"
min_profitability: 0.001
max_profitability: 0.01
max_executors_imbalance: 1
```

Only use when:

- both venues are genuinely tradeable
- hedge leg has reliable fills
- token has moved beyond single-pool chaos

## 9. Starter Pattern: `grid_strike`

Best for:

- range-defined environments
- established tokens, not first-wave listings

```yaml
id: grid-arb-eth
controller_name: grid_strike
controller_type: generic
connector_name: uniswap
trading_pair: WETH-USDC
side: BUY
start_price: 2200
end_price: 2700
limit_price: 2150
total_amount_quote: 500
min_spread_between_orders: 0.003
min_order_amount_quote: 25
max_open_orders: 3
max_orders_per_batch: 1
order_frequency: 10
keep_position: false
leverage: 1
```

## 10. Starter Pattern: `lp_rebalancer`

Best for:

- mature CLMM pools
- active fee markets
- not the first 24-72h of a fresh listing

```yaml
id: lp-sol-stable-range
controller_name: lp_rebalancer
controller_type: generic
connector_name: meteora
network: solana-mainnet-beta
trading_pair: SOL-USDC
pool_address: <pool_address>
total_amount_quote: 300
side: 0
position_width_pct: 0.5
position_offset_pct: 0.01
rebalance_seconds: 60
rebalance_threshold_pct: 0.1
```

## 11. New-Token Defaults by Chain

| Chain | First controller to try | Second controller after stabilization |
| --- | --- | --- |
| **Solana** | `macd_bb_v1` on Jupiter / Raydium | `pmm_dynamic` or later `xemm_multiple_levels` |
| **Base** | `macd_bb_v1` on Uniswap | `pmm_dynamic` |
| **BNB Chain** | `bollinger_v2` or `macd_bb_v1` on PancakeSwap | `pmm_simple` or `pmm_dynamic` |
| **Arbitrum** | `macd_bb_v1` for fresh listings, otherwise `pmm_dynamic` | `xemm_multiple_levels` |

## 12. Do Not Use These as Blind Defaults

- `pmm_simple` on a token that just launched minutes ago
- `lp_rebalancer` on a brand-new pool without stable volume
- chain-specific connector IDs copied from old posts without checking your installed version

---

Next reads:

- [07_v2_framework.md](07_v2_framework.md)
- [03_chains_and_dexs.md](03_chains_and_dexs.md)
- [02_strategies.md](02_strategies.md)
