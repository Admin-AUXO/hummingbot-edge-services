# 🤖 Hummingbot Core Features

> An overview of the open-source algorithmic trading framework's capabilities

---

## 1. Modular Trading Framework (V2)

Hummingbot's V2 architecture separates strategy logic into distinct, reusable components:

- **Controllers**: The "brain". Analyzes data, calculates trends, and decides _what_ orders to create (e.g., `pmm_simple`, `pmm_dynamic`, `directional_v2`, `dman_v3`, `xemm_v2`).
- **Executors**: The "hands". Manages the lifecycle of an order (e.g., `position_executor` for stop-loss/take-profit tracking, `dca_executor` for averaging in). v2.5+ added global stop-loss and per-strategy leverage.
- **Indicators & Oracles**: Natively ingests trading view style technical indicators (MACD, Bollinger Bands, NATR) and on-chain oracle data.

## 2. Universal Connectivity

Hummingbot acts as a unified translation layer between your logic and the blockchain/exchange:

- **CEX & DEX Support**: Connects to over 100+ exchanges including Binance, Uniswap V3/V4, Raydium, and Jupiter. Latest: v2.11.0.
- **Zero-Gas CLOBs**: Native support for high-performance decentralized order books like **Hyperliquid** (up to 50x, HyperEVM) and **dYdX v4** (up to 50x, Cosmos appchain), enabling CEX-like execution speeds without giving up self-custody.
- **Wallet Gateway**: Uses a secure local Gateway server to map your Web3 wallets to DEXs across Arbitrum, Optimism, Base, Solana, and Avalanche. Private keys never leave your machine.

## 3. Advanced Execution Capabilities

- **Jito MEV Integration**: On Solana, standard priority fees often fail for extreme high-frequency strategies. Hummingbot's ecosystem supports sending transactions as Jito Bundles with out-of-protocol tip mechanics to bypass the mempool and snipe block-0 events.
- **Latency Arbitrage**: Capable of executing cross-venue strategies (e.g., matching Coinbase Centralized API prices against Aerodrome Base DEX pairs) in milliseconds.

## 4. Extensibility & Third-Party Integrations

- **MQTT External Triggers**: By enabling the EMQX broker, Hummingbot can listen to external Python/Node.js scripts. This allows you to run separate chain-scrapers that detect new token pools and instantly feed the contract address to Hummingbot via MQTT.
- **Custom Scripts**: Users can write custom execution logic in lightweight Python scripts that interact with the core engine, entirely bypassing the need to compile the C++ backend.
- **Edge Services Ecosystem**: Python microservices publishing signals to MQTT. Core: regime detection, session timing, inventory monitoring, delta-neutral hedging, PnL analytics, correlation analysis, funding rates, and Telegram alerts. Scanners: alpha pipeline (DexScreener scoring), cross-DEX arb, multi-pair funding scanner, narrative/social momentum, LP reward tracking, and watchlist automation. Orchestration: CLMM range optimizer. See [15_edge_systems](15_edge_systems.md) and [01_glossary](01_glossary.md#edge-services-custom-mqtt-microservices).

## 5. Storage & Analytics

Hummingbot respects data ownership and provides multiple layers of historical trade analysis:

- **Local Data**: Trade history, order states, and full order book snapshots are auto-saved as `.csv` files locally.
- **SQLite Tracker**: Tracks high-density real-time market data internally via SQLite.
- **PostgreSQL Scaling**: For users running a "Swarm" of multiple bots, Hummingbot natively connects to standard PostgreSQL databases to aggregate all PnL and decision data into a unified, queryable location.
- **Internal Dashboard**: Users can analyze past decisions directly in the CLI by typing `history --verbose` or export them for custom AI analysis tools.

---

> Start exploring the specific implementations: [02_strategies](02_strategies.md) and [05_configurations](05_configurations.md).
