import json
import logging
import os
import time

import paho.mqtt.client as mqtt
import requests
import yaml

from config import BacktestConfig
from sweep import build_backtest_config, format_report, generate_param_grid, rank_results

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_base_config(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def run_single_backtest(api_url, base_config, overrides, bt_config):
    config = build_backtest_config(base_config, overrides)
    payload = {
        "start_time": bt_config.start_time,
        "end_time": bt_config.end_time,
        "backtesting_resolution": bt_config.backtesting_resolution,
        "trade_cost": bt_config.trade_cost,
        "config": config,
    }
    resp = requests.post(f"{api_url}/backtesting/run-backtesting", json=payload, timeout=300)
    resp.raise_for_status()
    return resp.json()


def extract_metrics(result):
    return {
        "sharpe_ratio": result.get("sharpe_ratio", 0),
        "net_pnl": result.get("net_pnl", 0),
        "accuracy": result.get("accuracy", 0),
        "max_drawdown_pct": result.get("max_drawdown_pct", 0),
        "profit_factor": result.get("profit_factor", 0),
        "total_executors": result.get("total_executors", 0),
    }


def main():
    config = BacktestConfig()
    base_config = load_base_config(config.controller_config_path)
    grid = generate_param_grid(config)
    logger.info(f"Generated {len(grid)} parameter combinations")

    results = []
    successful = 0
    for i, overrides in enumerate(grid):
        logger.info(f"[{i + 1}/{len(grid)}] Testing: spread={overrides['buy_spreads']}, "
                     f"SL={overrides['stop_loss']}, TP={overrides['take_profit']}, TL={overrides['time_limit']}")
        try:
            result = run_single_backtest(config.api_base_url, base_config, overrides, config)
            metrics = extract_metrics(result)
            results.append({"params": overrides, "metrics": metrics})
            successful += 1
            logger.info(f"  Sharpe={metrics['sharpe_ratio']:.2f}, PnL={metrics['net_pnl']:.2f}, "
                         f"Executors={metrics['total_executors']}")
        except Exception as e:
            logger.warning(f"  Failed: {e}")

    logger.info(f"Completed {successful}/{len(grid)} runs")

    ranked = rank_results(results)
    report = format_report(ranked, config.top_n)

    os.makedirs(config.output_dir, exist_ok=True)
    output_path = os.path.join(config.output_dir, f"sweep_{int(time.time())}.json")
    with open(output_path, "w") as f:
        json.dump({"all_results": ranked, **report}, f, indent=2)
    logger.info(f"Results saved to {output_path}")

    mqtt_payload = {
        "target": config.target_pair,
        "total_configs_tested": len(grid),
        "successful_runs": successful,
        "top_config": report["top_configs"][0] if report["top_configs"] else None,
        "top_5": report["top_configs"][:5],
        "timestamp": int(time.time()),
    }

    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        client.username_pw_set(config.mqtt_username, config.mqtt_password)
        client.connect(config.mqtt_host, config.mqtt_port)
        topic = f"{config.report_topic}/{config.target_pair}"
        client.publish(topic, json.dumps(mqtt_payload), retain=True)
        client.disconnect()
        logger.info(f"Published summary to {topic}")
    except Exception as e:
        logger.error(f"MQTT publish failed: {e}")

    if report["top_configs"]:
        top = report["top_configs"][0]
        logger.info(f"Best config: Sharpe={top['sharpe_ratio']:.2f}, PnL={top['net_pnl']:.2f}, "
                     f"Accuracy={top['accuracy']:.2f}")


if __name__ == "__main__":
    main()
