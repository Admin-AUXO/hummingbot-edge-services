import json
import os
import sys
import time

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import WatchlistConfig
from shared.base_service import BaseService
from watchlist_manager import (
    build_arb_entry,
    build_funding_entry,
    build_rewards_entry,
    check_staleness,
    load_state,
    parse_boost_signals,
    parse_profile_signals,
    prune_stale,
    save_state,
    seed_state,
    should_add_arb,
    should_add_funding,
    should_add_rewards,
    to_arb_json,
    to_funding_json,
    to_rewards_json,
)


class WatchlistService(BaseService):
    name = "watchlist"

    def __init__(self):
        super().__init__(WatchlistConfig())
        self.pending_signals = []
        self._init_state()

    def _init_state(self):
        self.state = load_state(self.config.state_file)
        if not self.state["arb_tokens"] and not self.state["rewards_pools"] and not self.state["funding_symbols"]:
            self.logger.info("No existing state, seeding from static files")
            self.state = seed_state(
                self._resolve(self.config.arb_tokens_file),
                self._resolve(self.config.rewards_pools_file),
                self._resolve(self.config.funding_symbols_file),
            )
            save_state(self.state, self.config.state_file)
            self.logger.info(
                f"Seeded: {len(self.state['arb_tokens'])} arb, "
                f"{len(self.state['rewards_pools'])} rewards, "
                f"{len(self.state['funding_symbols'])} funding"
            )

    def _resolve(self, rel_path):
        return os.path.normpath(os.path.join(os.path.dirname(__file__), rel_path))

    def on_shutdown(self):
        save_state(self.state, self.config.state_file)

    def _on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            data["_topic"] = msg.topic
            self.pending_signals.append(data)
        except Exception as e:
            self.logger.error(f"Message handler error: {e}")

    def process_signals(self):
        added = {"arb": [], "rewards": [], "funding": []}

        for signal in self.pending_signals:
            topic = signal.pop("_topic", "")

            if "/alpha/" in topic or signal.get("source") in ("dex_boost", "dex_profile"):
                ok, reason = should_add_arb(signal, self.state, self.config)
                if ok:
                    entry = build_arb_entry(signal, signal.get("source", "alpha"))
                    self.state["arb_tokens"].append(entry)
                    added["arb"].append(entry)

                ok, reason = should_add_funding(signal, self.state, self.config)
                if ok:
                    sym = f"{signal.get('token', '')}USDT"
                    entry = build_funding_entry(sym, signal.get("source", "alpha"))
                    self.state["funding_symbols"].append(entry)
                    added["funding"].append(entry)

            elif "/narrative/" in topic:
                ok, reason = should_add_arb(signal, self.state, self.config)
                if ok:
                    entry = build_arb_entry(signal, "narrative")
                    self.state["arb_tokens"].append(entry)
                    added["arb"].append(entry)

                ok, reason = should_add_funding(signal, self.state, self.config)
                if ok:
                    sym = f"{signal.get('token', '')}USDT"
                    entry = build_funding_entry(sym, "narrative")
                    self.state["funding_symbols"].append(entry)
                    added["funding"].append(entry)

        self.pending_signals.clear()

        for entry_type, entries in added.items():
            for entry in entries:
                sym = entry.get("symbol", entry.get("token", "?"))
                self.publish(f"{self.config.mqtt_topic_prefix}/added/{entry_type}/{sym}", entry)
                self.logger.info(f"ADDED {entry_type}: {sym}")

        return added

    def _fetch_market_data(self, addresses):
        if not addresses:
            return {}
        try:
            url = f"{self.config.dex_token_url}/{','.join(addresses[:30])}"
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            result = {}
            for pair in resp.json():
                addr = pair.get("baseToken", {}).get("address", "")
                if addr and addr not in result:
                    result[addr] = {
                        "volume_24h": float(pair.get("volume", {}).get("h24", 0)),
                        "liquidity": float(pair.get("liquidity", {}).get("usd", 0)),
                    }
            return result
        except Exception as e:
            self.logger.error(f"Market data fetch failed: {e}")
            return {}

    def prune_cycle(self):
        removed = {"arb": [], "rewards": [], "funding": []}

        non_static_arb = [e for e in self.state["arb_tokens"] if e.get("source") != "static"]
        non_static_rewards = [e for e in self.state["rewards_pools"] if e.get("source") != "static"]

        addresses = [e["address"] for e in non_static_arb + non_static_rewards if e.get("address")]
        market_data = self._fetch_market_data(addresses)

        stale_arb = set()
        for entry in self.state["arb_tokens"]:
            md = market_data.get(entry.get("address", ""), {})
            if check_staleness(entry, md, self.config):
                stale_arb.add(id(entry))

        if stale_arb:
            kept, pruned = prune_stale(self.state["arb_tokens"], stale_arb)
            self.state["arb_tokens"] = kept
            removed["arb"] = pruned

        stale_rewards = set()
        for entry in self.state["rewards_pools"]:
            md = market_data.get(entry.get("address", ""), {})
            if check_staleness(entry, md, self.config):
                stale_rewards.add(id(entry))

        if stale_rewards:
            kept, pruned = prune_stale(self.state["rewards_pools"], stale_rewards)
            self.state["rewards_pools"] = kept
            removed["rewards"] = pruned

        for entry_type, entries in removed.items():
            for entry in entries:
                sym = entry.get("symbol", entry.get("token", "?"))
                self.publish(f"{self.config.mqtt_topic_prefix}/removed/{entry_type}/{sym}", entry)
                self.logger.info(f"REMOVED {entry_type}: {sym} (stale)")

        return removed

    def write_json_files(self):
        arb_path = self._resolve(self.config.arb_tokens_file)
        with open(arb_path, "w") as f:
            json.dump(to_arb_json(self.state["arb_tokens"]), f, indent=2)

        rewards_path = self._resolve(self.config.rewards_pools_file)
        with open(rewards_path, "w") as f:
            json.dump(to_rewards_json(self.state["rewards_pools"]), f, indent=2)

        funding_path = self._resolve(self.config.funding_symbols_file)
        with open(funding_path, "w") as f:
            json.dump(to_funding_json(self.state["funding_symbols"]), f, indent=2)

    def publish_status(self):
        status = {
            "arb_tokens": len(self.state["arb_tokens"]),
            "rewards_pools": len(self.state["rewards_pools"]),
            "funding_symbols": len(self.state["funding_symbols"]),
            "timestamp": time.time(),
        }
        self.publish(f"{self.config.mqtt_topic_prefix}/status", status)

    def eval_cycle(self):
        added = self.process_signals()
        removed = self.prune_cycle()
        self.write_json_files()
        save_state(self.state, self.config.state_file)
        self.publish_status()

        total_added = sum(len(v) for v in added.values())
        total_removed = sum(len(v) for v in removed.values())
        self.logger.info(
            f"Eval cycle: +{total_added} -{total_removed} | "
            f"arb={len(self.state['arb_tokens'])} "
            f"rewards={len(self.state['rewards_pools'])} "
            f"funding={len(self.state['funding_symbols'])}"
        )

    def poll_trending(self):
        for url, parser in [
            (self.config.dex_boosts_url, parse_boost_signals),
            (self.config.dex_profiles_url, parse_profile_signals),
        ]:
            try:
                resp = requests.get(url, timeout=15)
                resp.raise_for_status()
                signals = parser(resp.json())
                for s in signals:
                    s["_topic"] = "trending/dex"
                self.pending_signals.extend(signals)
                self.logger.info(f"Trending poll: {len(signals)} Solana tokens from {url.split('/')[-2]}")
            except Exception as e:
                self.logger.error(f"Trending poll failed ({url}): {e}")

    def run(self):
        self.connect_mqtt(
            subscriptions=["hbot/alpha/#", "hbot/narrative/#"],
            on_message=self._on_message,
        )
        self.logger.info(
            f"Watchlist service started | "
            f"arb={len(self.state['arb_tokens'])} "
            f"rewards={len(self.state['rewards_pools'])} "
            f"funding={len(self.state['funding_symbols'])}"
        )

        last_eval = 0.0
        last_trending = 0.0

        while self.running:
            now = time.time()

            if (now - last_eval) >= self.config.eval_interval_seconds:
                self.eval_cycle()
                last_eval = now

            if (now - last_trending) >= self.config.boost_poll_seconds:
                self.poll_trending()
                last_trending = now

            self.sleep_loop(min(10, self.config.eval_interval_seconds))

        self.shutdown_mqtt()


if __name__ == "__main__":
    WatchlistService().run()
