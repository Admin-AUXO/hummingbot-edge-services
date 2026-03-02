# 🔗 Connection & Setup Guide for DEX Trading

> Everything you need to connect before placing your first DEX trade

---

## What You Need (Checklist)

```
Before trading on DEXs with Hummingbot, you need:

□ 1. Hummingbot Client      — running in Docker
□ 2. Gateway                — enabled in docker-compose.yml
□ 3. Blockchain Wallet      — with private key (per chain you trade on)
□ 4. Native gas tokens      — ETH, SOL, BNB, etc. for TX fees
□ 5. Trading tokens         — the tokens you're actually trading
□ 6. Token approvals        — one-time on-chain approval per token per DEX
```

---

## Step 1: Hummingbot + Gateway (Docker)

### 1a. Enable Gateway in Docker Compose

Edit your `docker-compose.yml` to uncomment/enable the Gateway service:

```yaml
gateway:
  restart: always
  container_name: gateway
  image: hummingbot/gateway:latest
  ports:
    - "15888:15888"
  volumes:
    - "./gateway-files/conf:/home/gateway/conf"
    - "./gateway-files/logs:/home/gateway/logs"
    - "./certs:/home/gateway/certs"
  environment:
    - GATEWAY_PASSPHRASE=your_passphrase # ← Change this!
    - DEV=true # HTTP mode (use DEV=false + certs for HTTPS)
```

Or enable via the compose profile:

```bash
# In .compose.env:
COMPOSE_PROFILES=gateway
```

### 1b. Start Services

```bash
docker compose up -d
docker attach hummingbot
# Set your Hummingbot password on first launch
```

### 1c. Verify Gateway is Online

After attaching, look at the top-right of the Hummingbot CLI:

```
Gateway: 🟢 ONLINE         ← You should see this
```

If it shows **OFFLINE**, check:

- Gateway container is running: `docker ps | grep gateway`
- Port 15888 is accessible
- `gateway_use_ssl` in `conf_client.yml` matches your DEV mode setting

---

## Step 2: Blockchain Wallets

You need a **separate wallet for each blockchain family** you want to trade on.

### What Hummingbot Needs

| Chain Family                                  | What You Provide         | How It's Stored                   |
| --------------------------------------------- | ------------------------ | --------------------------------- |
| **EVM** (Ethereum, Arbitrum, Base, BNB, etc.) | Private key (hex string) | Encrypted with Gateway passphrase |
| **Solana**                                    | Private key (base58)     | Encrypted with Gateway passphrase |

> ⚠️ **Security**: Hummingbot encrypts your private key locally with the `GATEWAY_PASSPHRASE`. Keys never leave your machine. Use a **dedicated trading wallet**, not your main holdings wallet.

### How to Get Your Private Key

#### MetaMask (EVM chains)

1. Open MetaMask → click the **⋮** menu next to your account
2. **Account Details** → **Show Private Key**
3. Enter your MetaMask password
4. Copy the hex string (starts with `0x...` or just hex characters)

#### Phantom (Solana)

1. Open Phantom → **Settings** (gear icon)
2. Select your account → **Show Secret Recovery Phrase** or **Export Private Key**
3. Copy the base58-encoded private key

#### Hyperliquid (Perp DEX)

Hyperliquid uses your EVM (MetaMask) wallet to sign transactions.

1. Use an existing EVM private key.
2. The connector will automatically map it to your Hyperliquid L1 address.

#### Creating a Fresh Wallet (Recommended for Bots)

For security, create a **dedicated wallet** just for bot trading:

```bash
# EVM: Use MetaMask "Create Account" for a new address
# Solana: Use Phantom "Add/Connect Wallet" → "Create New Wallet"
# Or use command-line tools:
#   solana-keygen new --outfile ~/trading-wallet.json
```

### Connect Wallet to Gateway

Inside the Hummingbot CLI:

```bash
# For EVM chains (works for Ethereum, Arbitrum, Base, BNB, Polygon, etc.)
gateway connect

# Follow the prompts:
#   Select chain: ethereum
#   Select network: arbitrum_one    (or mainnet, base, etc.)
#   Enter private key: <paste your key>

# For Solana
gateway connect
#   Select chain: solana
#   Select network: mainnet-beta
#   Enter private key: <paste your key>
```

### Verify Wallet Connection

```bash
gateway balance               # Check connected wallets and balances
gateway connectors            # List available DEX connectors
```

### One Wallet, Multiple EVM Networks

Your **same EVM private key works across all EVM chains** (Ethereum, Arbitrum, Base, BNB, Polygon, Optimism, Avalanche). You just connect it once per network:

```bash
gateway connect   # → ethereum → arbitrum_one → <same key>
gateway connect   # → ethereum → base → <same key>
gateway connect   # → ethereum → mainnet → <same key>
```

Your Solana key is separate and only works on Solana-based networks.

---

## Step 3: Fund Your Wallet

### Gas Tokens (Required)

You **must** hold the native gas token on each chain you trade on:

| Chain           | Gas Token | Where to Get                                 | Min Recommended |
| --------------- | --------- | -------------------------------------------- | --------------- |
| Ethereum L1     | ETH       | Bridge or fiat on-ramp                       | $50-100         |
| Arbitrum        | ETH       | Bridge from Ethereum                         | $5-10           |
| Base            | ETH       | Bridge from Ethereum                         | $5-10           |
| BNB Chain       | BNB       | Bridge or fiat on-ramp                       | $5-10           |
| Polygon         | MATIC/POL | Bridge or fiat on-ramp                       | $2-5            |
| Optimism        | ETH       | Bridge from Ethereum                         | $5-10           |
| Solana          | SOL       | Bridge or fiat on-ramp                       | $2-5            |
| **Hyperliquid** | **None**  | $0 Gas required. Deposit USDC from Arbitrum. | $0              |

> 💡 **Tip**: Start with L2s or Solana. Gas costs are pennies, so $5-10 of gas tokens lasts hundreds of trades.

### Trading Tokens

Deposit the tokens you plan to trade. For market making, you typically need **both tokens** in the pair:

```
Example: Market making ETH/USDT on Arbitrum
   → Need: ETH (for trading + gas) + USDT (for trading)
   → Deposit: $50 of ETH + $50 of USDT for $100 total capital
```

### Funding Methods

| Method                        | Speed    | Fee     | Best For                                       |
| ----------------------------- | -------- | ------- | ---------------------------------------------- |
| **Bridge** from another chain | 2-30 min | $0.50-5 | If you already have funds on a different chain |
| **On-ramp** (fiat → crypto)   | Minutes  | 1-3%    | Starting from scratch                          |

---

## Step 4: Token Approvals (EVM Only)

Before trading any ERC-20 token on an EVM DEX for the first time, you must **approve** that token — a one-time on-chain transaction that authorizes the DEX router contract to spend your tokens.

### How It Works

```
First trade of USDT on Uniswap (Arbitrum):
1. Hummingbot detects USDT is not yet approved for Uniswap router
2. Sends an approval TX (costs gas, ~$0.01-0.05 on L2s)
3. After confirmation, USDT can be traded on Uniswap freely
4. Approval is permanent — you never need to do this again for that token+DEX combo
```

### Manual Approval (Optional)

You can pre-approve tokens using the Gateway CLI:

```bash
# Inside Hummingbot CLI
gateway approve-token
#   chain: ethereum
#   network: arbitrum_one
#   token: USDT
#   connector: uniswap
```

### What Gets Approved

| Item                          | Needs Approval?                           |
| ----------------------------- | ----------------------------------------- |
| Native gas token (ETH, BNB)   | ❌ No (native tokens don't need approval) |
| Wrapped native (WETH, WBNB)   | ✅ Yes                                    |
| Stablecoins (USDT, USDC, DAI) | ✅ Yes, per DEX                           |
| Any ERC-20 token              | ✅ Yes, per DEX                           |
| Solana SPL tokens             | ❌ No (Solana doesn't use approvals)      |

---

## Step 5: Verify Everything

Run these checks before starting any strategy:

```bash
# 1. Gateway status
# Look for: Gateway: 🟢 ONLINE (top-right corner)

# 2. Wallet balances
gateway balance

# 4. Test a swap (optional but recommended)
gateway swap
#   chain: ethereum
#   network: arbitrum_one
#   connector: uniswap
#   from: ETH
#   to: USDT
#   amount: 0.001       # Small test amount
```

---

## Connection Summary by Strategy

| Strategy             | What You Need         | Wallet      | Gas Token      |
| -------------------- | --------------------- | ----------- | -------------- |
| **PMM on DEX**       | Gateway + wallet      | ✅ 1 chain  | ✅             |
| **AMM Arbitrage**    | Gateway + 1-2 wallets | ✅ 1-2 chn  | ✅             |
| **XEMM**             | Gateway + 1-2 wallets | ✅ 1-2 chn  | ✅             |
| **CLMM LP**          | Gateway + wallet      | ✅ 1 chain  | ✅             |
| **Stablecoin Arb**   | Gateway + 2 wallets   | ✅ 2 chains | ✅ both chains |
| **Delta-Neutral PMM** | Gateway + Solana + Hyperliquid wallets | ✅ 2 chains | ✅ SOL only (HL = $0) |

---

## Troubleshooting

| Problem                  | Solution                                                            |
| ------------------------ | ------------------------------------------------------------------- |
| Gateway shows OFFLINE    | Check `docker ps`, ensure port 15888 is free, restart gateway       |
| "Wallet not found" error | Re-run `gateway connect` with your private key                      |
| "Insufficient balance"   | Deposit gas tokens + trading tokens to your wallet                  |
| Token not approved       | Run `gateway approve-token` or let auto-approve                     |
| TX stuck / pending       | Gas price too low; on L2s this is rare. Wait or speed up via wallet |
| "Slippage exceeded"      | Increase `slippage_buffer` in your config or reduce order size      |
