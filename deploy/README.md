# Hummingbot Edge Services — VPS Deployment Guide

Deploy the entire trading stack to a Hostinger KVM 2 VPS using Docker.

---

## What Gets Deployed

| Container           | Image                 | RAM Limit   | Purpose                    |
| ------------------- | --------------------- | ----------- | -------------------------- |
| `hbot-broker`       | emqx:5                | 512 MB      | MQTT message broker        |
| `hbot-postgres`     | postgres:16-alpine    | 256 MB      | Bot history database       |
| `hbot-api`          | hummingbot-api:latest | 256 MB      | REST API orchestration     |
| `hbot-client`       | hummingbot:latest     | 512 MB      | Trading bot CLI            |
| `hbot-gateway`      | gateway:latest        | 256 MB      | DEX on-chain routing       |
| 17× `edge-*`        | Built from repo       | 128 MB each | Python edge services       |
| 3× `edge-*` (tier4) | Built from repo       | 128 MB each | On-demand services         |
| **Total**           |                       | **~4.4 GB** | Fits in 8 GB with headroom |

---

## Option A: Hostinger Docker Manager (Recommended)

### Step 1: Push Repo to GitHub

Your repo must be on GitHub (public or private). The `deploy/` folder must be committed:

```bash
git add deploy/
git commit -m "Add VPS deployment config"
git push
```

### Step 2: Get the Compose URL

Copy the **raw URL** of the compose file:

```
https://raw.githubusercontent.com/<your-user>/<your-repo>/main/deploy/docker-compose.yml
```

### Step 3: Deploy via Hostinger

1. Log into [Hostinger hPanel](https://hpanel.hostinger.com)
2. Go to **VPS** → Select your KVM 2 → **Docker Manager**
3. Click **"Compose from URL"**
4. Paste the raw GitHub URL from Step 2
5. **Add environment variables** — copy values from `deploy/.env.example` into the Hostinger env var form. At minimum, set:
   - `ALERT_TELEGRAM_BOT_TOKEN` — your Telegram bot token
   - `ALERT_TELEGRAM_CHAT_ID` — your Telegram chat ID
   - Change all default passwords for live trading
6. Click **Deploy**

Hostinger will:

- Clone the repo
- Build the edge service image from `deploy/Dockerfile`
- Pull all pre-built images (EMQX, PostgreSQL, Hummingbot, etc.)
- Start all 26 containers

### Step 4: Verify

In Hostinger Docker Manager:

- All containers should show **Running** (green)
- Click any container → **Logs** to check for errors
- EMQX dashboard: `http://<VPS-IP>:18083` (admin / public)
- API docs: `http://<VPS-IP>:8000/docs`

---

## Option B: Manual SSH Deployment

If you prefer SSH access:

```bash
# SSH into your VPS
ssh root@<VPS-IP>

# Install Docker (if not already installed)
curl -fsSL https://get.docker.com | sh

# Clone your repo
git clone https://github.com/<your-user>/<your-repo>.git ~/Trading
cd ~/Trading/deploy

# Create .env from example
cp .env.example .env
nano .env    # Edit credentials and Telegram config

# Deploy everything
docker compose up -d

# Check status
docker compose ps
docker compose logs --tail 20
```

---

## Managing Services

### Check Status

**Hostinger:** Docker Manager → click on the project → see all container statuses.

**SSH:**

```bash
cd ~/Trading/deploy
docker compose ps
```

### View Logs

```bash
# All services
docker compose logs --tail 50

# Specific service
docker compose logs edge-alert --tail 50 -f

# Infrastructure
docker compose logs hbot-broker --tail 20
docker compose logs hbot-api --tail 20
```

### Restart Services

```bash
# Restart all
docker compose restart

# Restart one service
docker compose restart edge-regime

# Restart all edge services only
docker compose restart edge-session edge-regime edge-funding edge-correlation \
  edge-alpha edge-arb edge-funding-scanner edge-narrative edge-rewards \
  edge-inventory edge-hedge edge-pnl \
  edge-lab edge-alert edge-swarm edge-clmm edge-watchlist
```

### Start Tier 4 Services (On-Demand)

Tier 4 services (unlock, backtest, migration) are NOT started by default. To start them:

```bash
cd ~/Trading/deploy
COMPOSE_PROFILES=tier4 docker compose up -d edge-unlock edge-backtest edge-migration
```

### Stop Everything

```bash
cd ~/Trading/deploy
docker compose down

# Full reset (removes all data volumes)
docker compose down -v
```

### Update to Latest Code

```bash
cd ~/Trading
git pull
cd deploy
docker compose build     # Rebuild edge service image
docker compose up -d     # Restart with new code
```

---

## Attach to Hummingbot CLI

```bash
docker attach hbot-client
```

Inside the CLI:

- `gateway connect` — connect your wallet
- `create` — create a strategy
- `start` — start trading
- **Detach without stopping:** `Ctrl+P` then `Ctrl+Q`

---

## File Structure

```
deploy/
├── docker-compose.yml    ← The unified compose file (26 containers)
├── Dockerfile            ← Shared image for all 20 edge services
├── entrypoint.sh         ← Dispatches to correct service by SERVICE_NAME
├── .env.example          ← Template — copy to .env and edit
├── .env                  ← Your actual secrets (gitignored)
└── deploy.sh             ← Alternative: bash script for manual setup
```

---

## Resource Usage on KVM 2

| Resource      | Available   | Used (est.)       | Headroom |
| ------------- | ----------- | ----------------- | -------- |
| **RAM**       | 8 GB        | ~4.4 GB           | ~3.6 GB  |
| **CPU**       | 2 vCPU      | Light (I/O-bound) | Plenty   |
| **Disk**      | 100 GB NVMe | ~15-20 GB         | ~80 GB   |
| **Bandwidth** | 8 TB/month  | ~5-10 GB/day      | Plenty   |

---

## Ports Exposed

| Port  | Service          | Access              |
| ----- | ---------------- | ------------------- |
| 1883  | MQTT (TCP)       | Internal + external |
| 8000  | Hummingbot API   | REST endpoints      |
| 8083  | MQTT (WebSocket) | For web clients     |
| 15888 | Gateway          | DEX routing         |
| 18083 | EMQX Dashboard   | Monitoring          |
| 5432  | PostgreSQL       | Database            |

> **Security:** On production, you should restrict access to ports via Hostinger's firewall settings. Only expose what you need externally (typically just SSH + EMQX Dashboard + API).

---

## Troubleshooting

| Issue                   | Fix                                                                    |
| ----------------------- | ---------------------------------------------------------------------- |
| Edge service crashes    | Check logs: `docker compose logs edge-<name> --tail 50`                |
| MQTT connection refused | Ensure EMQX is healthy: `docker compose logs hbot-broker`              |
| Out of memory           | Reduce services or upgrade to KVM 4. Check: `docker stats`             |
| Telegram not working    | Verify `ALERT_TELEGRAM_BOT_TOKEN` and `ALERT_TELEGRAM_CHAT_ID` in .env |
| Gateway offline         | Check: `docker compose logs hbot-gateway --tail 20`                    |
| API 500 errors          | Check: `docker compose logs hbot-api --tail 20` and PostgreSQL logs    |
| Build fails             | Run: `docker compose build --no-cache` to rebuild from scratch         |
