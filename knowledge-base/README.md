# 📚 Hummingbot DEX Trading Knowledge Base

> Last Updated: March 1, 2026

A comprehensive reference for running Hummingbot trading bots on decentralized exchanges.
Each file covers a single topic — cross-references link related sections to avoid duplication.

## Files

| File                                                   | Description                                                                   |
| ------------------------------------------------------ | ----------------------------------------------------------------------------- |
| [00_hummingbot_features.md](00_hummingbot_features.md) | What is Hummingbot? V2 Framework, Data Storage, Jito MEV, Extensibility       |
| [01_glossary.md](01_glossary.md)                       | Quick-reference terms — definitions only, links to deeper files               |
| [02_strategies.md](02_strategies.md)                   | Strategy mechanics: PMM, Arbitrage, XEMM, CLMM, Grid, Stablecoin, Directional |
| [03_chains_and_dexs.md](03_chains_and_dexs.md)         | Chain rankings, DEX profiles, connector reference, gas costs                  |
| [04_trading_pairs.md](04_trading_pairs.md)             | Pair selection criteria, arbitrage matrix, per-strategy pair picks            |
| [05_configurations.md](05_configurations.md)           | Copy-paste YAML configs: conservative → aggressive                            |
| [06_risk_management.md](06_risk_management.md)         | Position sizing, stop losses, drawdown rules, risk scenarios                  |
| [07_v2_framework.md](07_v2_framework.md)               | V2 architecture, controllers, scripts, deployment commands                    |
| [08_playbooks.md](08_playbooks.md)                     | Step-by-step guides: beginner ($50-100) → advanced ($1000+)                   |
| [09_order_types.md](09_order_types.md)                 | How orders work on-chain: swaps, executors, DEX limitations                   |
| [10_connection_guide.md](10_connection_guide.md)       | What you need to connect: wallets, API keys, gas, approvals                   |
| [11_expert_tips.md](11_expert_tips.md)                 | Battle-tested rules, common mistakes, dynamic spread formulas                 |
| [12_costs_and_setup.md](12_costs_and_setup.md)         | Monthly infrastructure costs vs $100 trading capital                          |
| [13_profit_scenarios.md](13_profit_scenarios.md)       | Expected profitability, timelines & reality of a $100 budget                  |
| [14_skills.md](14_skills.md)                           | Practical DEX trading skills: on-chain analysis, screening, security, tooling |
| [15_edge_systems.md](15_edge_systems.md)               | Custom edge systems — regime switching, delta-neutral hedging, lab framework, backtesting, data flywheel (most implemented as services) |

## Quick Start

1. Read the [Glossary](01_glossary.md) if new to DEX trading
2. Review [Costs & Best Setup](12_costs_and_setup.md) — know what you'll spend before you start
3. **Set up connections** using the [Connection Guide](10_connection_guide.md) — wallets, keys, funding
4. Pick a [Strategy](02_strategies.md) that matches your goals
5. Choose your [Chain & DEX](03_chains_and_dexs.md)
6. Select [Trading Pairs](04_trading_pairs.md) for your strategy
7. Grab a [Configuration](05_configurations.md) template
8. Apply [Risk Management](06_risk_management.md) rules
9. **Read the [Expert Tips](11_expert_tips.md)** before going live
10. Follow a [Playbook](08_playbooks.md) to go live
