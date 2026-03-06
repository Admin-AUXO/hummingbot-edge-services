# 📖 Key Terms & Glossary for DEX Trading

> Quick-reference definitions. For deeper coverage see the dedicated files linked below.

---

## Core Concepts

| Term            | Definition                                                                               |
| --------------- | ---------------------------------------------------------------------------------------- |
| **DEX**         | Decentralized Exchange — trades via smart contracts, non-custodial. (Uniswap, Raydium)   |
| **AMM**         | Automated Market Maker — uses pool formulas (`x·y=k`) instead of order books for pricing |
| **CLMM**        | Concentrated Liquidity Market Maker — V3-style AMM where LPs pick a price range          |
| **DLMM**        | Dynamic Liquidity Market Maker — Meteora's bin-based CLMM variant on Solana              |
| **CLOB**        | Central Limit Order Book — traditional order matching, used by dYdX, Hyperliquid         |
| **Hyperliquid** | A zero-gas Perpetual DEX operating an L1 CLOB with HyperEVM (Feb 2025), up to 50x leverage, Portfolio Margin |
| **PumpSwap**    | Pump.fun's native DEX where graduated meme tokens migrate (replaced Raydium routing, March 2025) |

## Price & Order Terminology

| Term             | Definition                                                       |
| ---------------- | ---------------------------------------------------------------- |
| **Spread**       | Gap between best bid and best ask. `(Ask-Bid)/Mid × 100%`        |
| **Bid / Ask**    | Bid = highest buy price; Ask = lowest sell price                 |
| **Mid-Price**    | `(Bid + Ask) / 2`                                                |
| **Slippage**     | Difference between expected and actual execution price           |
| **Market Depth** | Volume of orders at each price level; deeper = less price impact |
| **Limit Order**  | Executes only at your specified price or better                  |
| **Market Order** | Executes immediately at best available price                     |
| **Maker**        | Adds liquidity (limit order resting on book) — lower fees        |
| **Taker**        | Removes liquidity (fills existing orders) — higher fees          |

## DeFi & Blockchain

| Term                 | Definition                                                                                        |
| -------------------- | ------------------------------------------------------------------------------------------------- |
| **Gas**              | TX cost paid in chain's native token. Directly impacts bot profitability                          |
| **L1 / L2**          | L1 = base chain (Ethereum, Solana); L2 = scaling layer (Arbitrum, Base)                           |
| **EVM / SVM**        | Ethereum/Solana Virtual Machine — smart-contract runtime environments                             |
| **Smart Contract**   | Self-executing on-chain code powering all DEX swaps and LP operations                             |
| **Wallet**           | Stores private keys for signing TXs. MetaMask (EVM), Phantom (Solana)                             |
| **Private Key**      | Cryptographic proof of wallet ownership. **Never share.** Encrypted by Hummingbot config password |
| **Token Approval**   | One-time on-chain TX authorizing a DEX contract to spend your tokens                              |
| **Wrapped Token**    | 1:1 pegged representation on another chain. WETH = ERC-20 ETH; WBTC = BTC on Ethereum             |
| **TVL**              | Total Value Locked — assets deposited in a protocol. Higher = deeper liquidity                    |
| **Liquidity Pool**   | Smart contract holding token reserves that traders swap against                                   |
| **LP**               | Liquidity Provider — deposits tokens into a pool, earns trading fees                              |
| **Impermanent Loss** | Unrealized loss from LP price-ratio changes vs. simply holding. Worse with volatile pairs         |
| **APR / APY**        | APR = simple yearly return; APY = compounded yearly return                                        |
| **MEV**              | Maximal Extractable Value — validator profit from TX reordering                                   |
| **Front-Running**    | Seeing a pending TX and trading ahead of it for profit                                            |
| **Sandwich Attack**  | MEV: place buy before + sell after a victim's large swap                                          |
| **DEX Aggregator**   | Routes trades across multiple pools for best price. Jupiter (Solana), 1inch (EVM)                 |
| **Hooks (Uni V4)**   | Plugin contracts customizing pool behavior — dynamic fees, TWAMM, MEV rebates. Live Jan 2025      |
| **HyperEVM**         | Hyperliquid's EVM layer enabling Solidity smart contracts on the Hyperliquid L1 (Feb 2025)        |
| **Jito Bundle**      | Group of up to 5 Solana TXs executed atomically. Tip (min 1K lamports) paid to validator via Block Engine |

## Hummingbot-Specific

| Term                     | Definition                                                                                        | See Also                                      |
| ------------------------ | ------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| **Gateway**              | Middleware translating Hummingbot commands → blockchain TXs. Port 15888                           | [03_chains](03_chains_and_dexs.md)            |
| **Connector**            | Module for a specific decentralized exchange (via Gateway)                                        | [03_chains](03_chains_and_dexs.md)            |
| **Controller**           | V2 strategy brain — configured via YAML, backtestable                                             | [07_v2_framework](07_v2_framework.md)         |
| **Executor**             | Autonomous order/position manager (Position, Arb, DCA, Grid, XEMM)                                | [09_order_types](09_order_types.md)           |
| **Inventory Skew**       | Auto-adjusts order sizes to maintain target base/quote ratio                                      | [06_risk](06_risk_management.md)              |
| **Hanging Orders**       | Opposite-side order stays open after its pair fills                                               |                                               |
| **Ping Pong**            | Alternates buy/sell after each fill for inventory balance                                         |                                               |
| **Order Refresh Time**   | Seconds between order cancel/replace cycles                                                       |                                               |
| **Minimum Spread**       | Safety floor — cancels any order tighter than this                                                |                                               |
| **EMQX / MQTT**          | Message broker for real-time bot ↔ API communication                                              |                                               |
| **Liquidity Sniping**    | Monitoring block events to execute buy orders in the first blocks of a new token listing          | [02_strategies](02_strategies.md)             |
| **Swarm Method**         | Running many small bots (e.g., 10 bots with $10) across different pairs to catch outsized winners | [11_expert_tips](11_expert_tips.md)           |
| **Time to Double (T2D)** | The projected time required to double starting capital based on strategy mathematical modeling    | [13_profit_scenarios](13_profit_scenarios.md) |

## Risk & Position Management

| Term                  | Definition                                                                 | See Also                            |
| --------------------- | -------------------------------------------------------------------------- | ----------------------------------- |
| **Stop Loss**         | Auto-close at a specified loss %                                           | [06_risk](06_risk_management.md)    |
| **Take Profit**       | Auto-close at a specified profit %                                         | [06_risk](06_risk_management.md)    |
| **Trailing Stop**     | Dynamic SL that moves with profit, stays fixed on reversal                 | [06_risk](06_risk_management.md)    |
| **Drawdown**          | Peak-to-trough decline in account value                                    | [06_risk](06_risk_management.md)    |
| **Position Sizing**   | Capital allocated per trade. Rule: never risk > 2% per trade               | [06_risk](06_risk_management.md)    |
| **Risk-Reward Ratio** | Potential loss vs. gain. Aim ≥ 1:2                                         | [06_risk](06_risk_management.md)    |
| **Leverage**          | Borrowed capital multiplier. 5x = $100 controls $500. Amplifies both sides |                                     |
| **DCA**               | Dollar-Cost Averaging — split buys over time/price to reduce impact        | [09_order_types](09_order_types.md) |

## Edge Services (Custom MQTT Microservices)

| Term | Definition | See Also |
| --- | --- | --- |
| **regime-service** | Classifies market as BULL/BEAR/SIDEWAYS/SPIKE using NATR + BB Width, publishes to MQTT | [15_edge_systems](15_edge_systems.md#system-1-automated-regime-switching) |
| **inventory-service** | Monitors spot portfolio skew and kill-switch drawdown, publishes to MQTT | [06_risk](06_risk_management.md#inventory-management) |
| **hedge-service** | Delta-neutral coordinator — hedges Raydium spot with Hyperliquid short via API | [15_edge_systems](15_edge_systems.md#system-2-delta-neutral-market-making--implemented) |
| **pnl-service** | Aggregates executor PnL analytics per trading pair, publishes to MQTT | |
| **funding-service** | Monitors Binance perp funding rates, calculates spread bias | |
| **correlation-service** | Tracks SOL correlation vs ETH/BTC using z-scores for mean-reversion signals | |
| **session-service** | Time-zone config switching (Asia/EU/US sessions) | [15_edge_systems](15_edge_systems.md#time-zone-config-switching) |
| **alert-service** | Routes all MQTT signals to Telegram alerts with state-change detection | |
