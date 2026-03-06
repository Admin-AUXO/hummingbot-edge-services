# 🏗️ Hummingbot V2 Framework

> Last reviewed: March 6, 2026
> This file reflects the current V2 model used across recent Hummingbot releases.

---

## 1. The V2 Stack

Hummingbot V2 is built from three layers.

### Scripts

Use scripts when you want:

- a simple entry point
- one strategy in one file
- faster experimentation

The standard multi-controller launcher is still `v2_with_controllers.py`.

### Controllers

Controllers are reusable strategy modules.

They:

- read market data
- produce trading actions
- create or stop executors
- work well for production deployments

### Executors

Executors are the units that actually manage trade workflows.

Current executor families in this repo:

- `position_executor`
- `arbitrage_executor`
- `grid_executor`
- `dca_executor`
- `twap_executor`
- `xemm_executor`
- `lp_executor`

## 2. Current Controller Families

### Market making

- `pmm_simple`
- `pmm_dynamic`
- `dman_maker_v2`

### Directional trading

- `bollinger_v1`
- `bollinger_v2`
- `macd_bb_v1`
- `supertrend_v1`
- `dman_v3`

### Generic / multi-venue

- `xemm_multiple_levels`
- `arbitrage_controller`
- `grid_strike`
- `lp_rebalancer`

## 3. What Is Outdated Now

Do not anchor on older names such as:

- `xemm_v2`
- `gridstrike_v2`
- `directional_v2`

Those names still appear in older guides, but current local controller files and official docs use the controller names listed above.

## 4. Current Architecture Pattern

```text
Market Data Provider
    ↓
Controller
    ↓
ExecutorActions
    ↓
Executors
    ↓
Connector / Gateway / Exchange
```

## 5. Best Way to Work With V2

### Local or learning workflow

- Hummingbot Client
- generate config
- run one controller or a small controller bundle

### Multi-bot / production workflow

- Hummingbot API
- external services for signals and operations
- Dashboard / MCP / automation around API-driven deployments

## 6. Multi-Controller Usage

Use multiple controllers when:

- you want several pairs in one bot
- you want separate logic per market
- you want one risk profile per controller

Example structure:

```yaml
controllers_config:
  - pmm_base_weth.yml
  - pmm_sol_usdc.yml
  - dir_newtoken_base.yml
```

## 7. LP Is Now Part of the Main Story

V2 now includes:

- `lp_executor`
- `lp_rebalancer`

That means concentrated-liquidity automation should be treated as a first-class V2 workflow, not an afterthought.

## 8. Practical Strategy Mapping

| Use case | Best V2 component |
| --- | --- |
| Single-pair prototype | Script |
| Reusable production market making | Controller |
| Directional token scanner entry | Directional controller |
| Cross-venue hedge / MM | `xemm_multiple_levels` |
| CLMM automation | `lp_rebalancer` + `lp_executor` |
| API-triggered single workflow | Executor |

## 9. File Locations

| What | Typical path |
| --- | --- |
| Controller code | `controllers/` |
| Executors | `hummingbot/strategy_v2/executors/` |
| Controller configs | `conf/controllers/` |
| Script configs | `conf/scripts/` |

---

Next reads:

- [05_configurations.md](05_configurations.md)
- [02_strategies.md](02_strategies.md)
- [15_edge_systems.md](15_edge_systems.md)
