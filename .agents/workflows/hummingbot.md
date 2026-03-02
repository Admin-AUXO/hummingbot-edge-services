---
description: How to manage Hummingbot trading bot (start, stop, attach, update)
---

# Hummingbot Management Workflow

## Hummingbot Client (CLI Bot)

### Location

All commands should be run from: `a:\Trading\hummingbot`

### Start Hummingbot + Gateway (DEX Trading)

// turbo-all

```powershell
cd a:\Trading\hummingbot
$env:COMPOSE_PROFILES="gateway"; docker compose up -d
```

### Attach to Hummingbot CLI

```powershell
docker attach hummingbot
```

> **Note:** To detach without stopping, press `Ctrl+P` then `Ctrl+Q`

### Check Running Containers

// turbo

```powershell
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### Stop Hummingbot

```powershell
cd a:\Trading\hummingbot
docker compose --profile gateway down
```

### Update to Latest Version

```powershell
cd a:\Trading\hummingbot
git pull
$env:COMPOSE_PROFILES="gateway"; docker compose pull
$env:COMPOSE_PROFILES="gateway"; docker compose up -d
```

### View Logs

```powershell
docker logs hummingbot --tail 50
docker logs gateway --tail 50
```

---

## Hummingbot API (REST API Server)

### Location

All commands should be run from: `a:\Trading\hummingbot-api`

### Start API + Broker + DB

```powershell
cd a:\Trading\hummingbot-api
docker compose up -d
```

### Stop API Services

```powershell
cd a:\Trading\hummingbot-api
docker compose down
```

### Check API Health

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/" -Method Get
```

### Access Points

- **Swagger UI (API Docs):** http://localhost:8000/docs
- **Alternative Docs:** http://localhost:8000/redoc
- **EMQX Dashboard:** http://localhost:18083 (admin/public)

### API Credentials (from .env)

- Username: `admin`
- Password: `admin`
- Config Password: `admin`

### View API Logs

```powershell
docker logs hummingbot-api --tail 50
docker logs hummingbot-broker --tail 20
docker logs hummingbot-postgres --tail 20
```

### Update API

```powershell
cd a:\Trading\hummingbot-api
git pull
docker compose pull
docker compose up -d
```

---

## Key Hummingbot CLI Commands (inside the bot)

- `connect` — List available exchanges
- `connect <exchange>` — Connect exchange API keys
- `balance` — Check connected balances
- `create` — Create a new trading strategy
- `start` — Start the active strategy
- `stop` — Stop the active strategy
- `exit` — Exit the Hummingbot client

## DEX Trading Setup (inside Hummingbot)

1. Verify Gateway is ONLINE (upper right corner)
2. Connect your wallet: `gateway connect`
3. Choose your DEX (Uniswap, PancakeSwap, Raydium, etc.)
4. Create an AMM strategy: `create`

## Full Stack Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│ Hummingbot API  │────│  EMQX Broker │────│  Hummingbot Bot │
│   :8000         │    │    :1883     │    │   (CLI client)  │
└────────┬────────┘    └──────────────┘    └────────┬────────┘
         │                                          │
    ┌────┴────┐                              ┌──────┴──────┐
    │PostgreSQL│                              │  Gateway    │
    │  :5432   │                              │   :15888    │
    └──────────┘                              └──────┬──────┘
                                                     │
                                              ┌──────┴──────┐
                                              │   DEX       │
                                              │ (Uniswap,   │
                                              │ PancakeSwap)│
                                              └─────────────┘
```
