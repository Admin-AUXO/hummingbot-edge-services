# Hummingbot & Python Edge Services Architecture

This document visualizes how the core Hummingbot stack interacts with the Python-based edge microservices.

```mermaid
flowchart TD
    %% Define External Entities
    subgraph External["External APIs & Platforms"]
        DexScreener["DexScreener API"]
        Jupiter["Jupiter Strict List"]
        Binance["Binance / CEXs"]
        OnChain["On-Chain DEXs"]
        Telegram["Telegram Bot"]
    end

    %% Define Broker and Core
    subgraph Infrastructure["Core Infrastructure & Messaging"]
        MQTT{"EMQX Broker (MQTT)"}
        DB[("PostgreSQL DB")]
    end

    subgraph HummingbotStack["Hummingbot Core Stack"]
        API["Hummingbot API (REST Interface)"]
        HBot["Hummingbot Client (Trading Engine)"]
        Gateway["Hummingbot Gateway (DEX Middleware)"]
    end

    %% Define Service Tiers
    subgraph Tier1["Tier 1: Independent Scanners"]
        Alpha["edge-alpha"]
        Regime["edge-regime"]
        Funding["edge-funding"]
        Corr["edge-correlation"]
        Scanners["Other Scanners (arb, narrative, rewards)"]
    end

    subgraph Tier2["Tier 2: API Integrated Services"]
        Hedge["edge-hedge"]
        Inventory["edge-inventory"]
        PnL["edge-pnl"]
    end

    subgraph Tier3["Tier 3: Consumers & Actuators"]
        Alert["edge-alert"]
        Swarm["edge-swarm"]
        Clmm["edge-clmm"]
        Lab["edge-lab"]
    end

    subgraph Tier4["Tier 4: Manual / On-Demand"]
        Backtest["edge-backtest"]
        Migration["edge-migration"]
    end

    %% Tier 1 Connections
    DexScreener --> Alpha
    Jupiter --> Alpha
    Binance --> Regime
    Binance --> Funding

    Alpha -- "Publish Signals" --> MQTT
    Regime -- "Publish States" --> MQTT
    Funding -- "Publish Rates" --> MQTT
    Corr -- "Publish Corr" --> MQTT
    Scanners -- "Publish" --> MQTT

    %% Tier 2 Connections
    Hedge -- "Read/Write via REST (Fetch balances, Place orders)" --> API
    Inventory -- "Read Balances" --> API
    PnL -- "Read Trade History" --> API

    Hedge -- "Publish Status" --> MQTT
    Inventory -- "Publish Status" --> MQTT
    PnL -- "Publish Report" --> MQTT

    %% Tier 3 Connections
    MQTT -- "Subscribe to Signals" --> Alert
    MQTT -- "Subscribe & Wait" --> Swarm
    MQTT -- "Subscribe" --> Clmm
    MQTT -- "Subscribe" --> Lab

    Alert -- "Send Notifications" --> Telegram

    %% Core Stack Connections
    API <--> DB
    API <--> Gateway
    HBot <--> Gateway
    Gateway <--> OnChain
    HBot <--> Binance
    API -- "Control/Read" --> HBot

    %% Tier 4 connections
    Backtest -. "History" .-> API
    Migration -- "Migrate" --> MQTT

    %% Styling
    classDef ext fill:#f9f9f9,stroke:#333,stroke-width:2px;
    classDef infra fill:#fce4ec,stroke:#e91e63,stroke-width:2px;
    classDef hbot fill:#e3f2fd,stroke:#2196f3,stroke-width:2px;
    classDef tier1 fill:#e8f5e9,stroke:#4caf50,stroke-width:2px;
    classDef tier2 fill:#fff3e0,stroke:#ff9800,stroke-width:2px;
    classDef tier3 fill:#f3e5f5,stroke:#9c27b0,stroke-width:2px;
    classDef tier4 fill:#eceff1,stroke:#607d8b,stroke-width:2px;

    class DexScreener,Jupiter,Binance,Telegram,OnChain ext;
    class MQTT,DB infra;
    class API,HBot,Gateway hbot;
    class Alpha,Regime,Funding,Corr,Scanners tier1;
    class Hedge,Inventory,PnL tier2;
    class Alert,Swarm,Clmm,Lab tier3;
    class Backtest,Migration tier4;
```

### Key Interactions:

1. **Tier 1 (Data Ingest & Analysis)**: Independent microservices (`alpha`, `regime`, `correlation`, etc.) pull data from external APIs (like DexScreener and Jupiter), crunch numbers/scores, and publish their findings to specific topics on the **EMQX MQTT Broker**.
2. **Tier 2 (Hummingbot Interoperability)**: Services like `hedge`, `inventory`, and `pnl` need direct access to reading bot states and executing trades. They achieve this by combining **MQTT** (for sharing state) and the **Hummingbot API** (via REST: `http://hummingbot-api:8000`) to place orders, check balances, and fetch trade histories.
3. **Hummingbot Core**: The API handles interaction requests and persists states into the **PostgreSQL DB**. Both API and Hummingbot depend on the **Gateway** to translate commands for decentralized interactions (e.g. interacting with solana/EVM DEXs).
4. **Tier 3 (Execution & Notification)**: Services like `alert` and `swarm` act as passive listeners. They subscribe to topics on **MQTT**, and when conditions are met (like a high-score Alpha matching a Bullish Regime), they trigger events like sending Telegram alerts or spawning new trading bots based on rules.
