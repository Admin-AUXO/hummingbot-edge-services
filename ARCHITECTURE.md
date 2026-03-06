# Hummingbot & Python Edge Services Architecture

This document shows the current DEX-lean production architecture and the optional API-extended profile.

```mermaid
flowchart TD
    subgraph External["External APIs & Platforms"]
        DexScreener["DexScreener API"]
        Jupiter["Jupiter Strict List"]
        Binance["Binance Market Data"]
        OnChain["On-Chain DEXs"]
        Telegram["Telegram Bot"]
    end

    subgraph Infrastructure["Core Infrastructure"]
        MQTT{"EMQX Broker (MQTT)"}
        DB[("PostgreSQL DB\napi-extended")]
    end

    subgraph HummingbotStack["Hummingbot Core Stack"]
        API["Hummingbot API\napi-extended"]
        HBot["Hummingbot Client"]
        Gateway["Hummingbot Gateway"]
    end

    subgraph Tier1["Tier 1: Independent Scanners (Default)"]
        Session["edge-session"]
        Alpha["edge-alpha"]
        Arb["edge-arb"]
        Narrative["edge-narrative"]
        Rewards["edge-rewards"]
    end

    subgraph Tier2["Tier 2: API Integrated (api-extended)"]
        Inventory["edge-inventory"]
        Hedge["edge-hedge"]
        PnL["edge-pnl"]
    end

    subgraph Tier3["Tier 3: Consumers & Actuators (Default)"]
        Alert["edge-alert"]
        Clmm["edge-clmm"]
        Watchlist["edge-watchlist"]
    end

    DexScreener --> Alpha
    DexScreener --> Arb
    DexScreener --> Narrative
    DexScreener --> Rewards
    Jupiter --> Alpha
    Binance --> Clmm

    Session -- "Publish" --> MQTT
    Alpha -- "Publish" --> MQTT
    Arb -- "Publish" --> MQTT
    Narrative -- "Publish" --> MQTT
    Rewards -- "Publish" --> MQTT
    Watchlist -- "Publish list updates" --> MQTT

    MQTT -- "Subscribe hbot/#" --> Alert
    MQTT -- "Subscribe strategy topics" --> Clmm
    MQTT -- "Subscribe alpha/narrative" --> Watchlist

    Alert -- "Send notifications" --> Telegram

    Inventory -- "Read balances" --> API
    Hedge -- "Read/Write orders" --> API
    PnL -- "Read trade history" --> API

    Inventory -- "Publish status" --> MQTT
    Hedge -- "Publish status" --> MQTT
    PnL -- "Publish analytics" --> MQTT

    API <--> DB
    API <--> Gateway
    HBot <--> Gateway
    Gateway <--> OnChain
    API -- "Control/Read" --> HBot

    classDef ext fill:#f9f9f9,stroke:#333,stroke-width:2px;
    classDef infra fill:#fce4ec,stroke:#e91e63,stroke-width:2px;
    classDef hbot fill:#e3f2fd,stroke:#2196f3,stroke-width:2px;
    classDef tier1 fill:#e8f5e9,stroke:#4caf50,stroke-width:2px;
    classDef tier2 fill:#fff3e0,stroke:#ff9800,stroke-width:2px;
    classDef tier3 fill:#f3e5f5,stroke:#9c27b0,stroke-width:2px;

    class DexScreener,Jupiter,Binance,Telegram,OnChain ext;
    class MQTT,DB infra;
    class API,HBot,Gateway hbot;
    class Session,Alpha,Arb,Narrative,Rewards tier1;
    class Inventory,Hedge,PnL tier2;
    class Alert,Clmm,Watchlist tier3;
```

### Runtime Profiles

- **Default DEX-lean profile**: `emqx`, `hummingbot`, `gateway`, `edge-session`, `edge-alpha`, `edge-arb`, `edge-narrative`, `edge-rewards`, `edge-alert`, `edge-clmm`, `edge-watchlist`.
- **Optional `api-extended` profile**: adds `postgres`, `hummingbot-api`, `edge-inventory`, `edge-hedge`, `edge-pnl`.

### Key Interactions

1. **Tier 1 (Data ingest + signal generation)**: `session`, `alpha`, `arb`, `narrative`, and `rewards` publish market and strategy signals to EMQX.
2. **Tier 2 (Optional API interoperability)**: `inventory`, `hedge`, and `pnl` consume Hummingbot API endpoints while also publishing state and analytics to MQTT.
3. **Tier 3 (Signal consumers)**: `alert`, `clmm`, and `watchlist` subscribe to MQTT topics; `alert` pushes operator notifications to Telegram.
4. **Core trading path**: Hummingbot and API coordinate through Gateway for on-chain execution, with PostgreSQL persistence enabled only in `api-extended`.
