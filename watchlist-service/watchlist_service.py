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
        if not self.pending_signals: return {}
        
        added = {"arb": [], "rewards": [], "funding": []}
        ex_arb = {e["address"] for e in self.state["arb_tokens"] if "address" in e}
        ex_rewards = {e["address"] for e in self.state["rewards_pools"] if "address" in e}
        ex_funding = {e["symbol"] for e in self.state["funding_symbols"] if "symbol" in e}

        for signal in self.pending_signals:
            topic = signal.pop("_topic", "")
            is_alpha = "/alpha/" in topic or signal.get("source") in ("dex_boost", "dex_profile")
            is_narr = "/narrative/" in topic
            
            if is_alpha or is_narr:
                source = signal.get("source", "alpha") if is_alpha else "narrative"
                
                # Check Arb
                ok, _ = should_add_arb(signal, ex_arb, self.state, self.config)
                if ok:
                    entry = build_arb_entry(signal, source)
                    self.state["arb_tokens"].append(entry)
                    ex_arb.add(entry["address"])
                    added["arb"].append(entry)

                # Check Funding
                ok, _ = should_add_funding(signal, ex_funding, self.state, self.config)
                if ok:
                    sym = f"{signal.get('token', '')}USDT"
                    entry = build_funding_entry(sym, source)
                    self.state["funding_symbols"].append(entry)
                    ex_funding.add(sym)
                    added["funding"].append(entry)

        self.pending_signals.clear()
        
        for etype, entries in added.items():
            for entry in entries:
                sym = entry.get("symbol") or entry.get("token", "?")
                self.publish(f"{self.config.mqtt_topic_prefix}/added/{etype}/{sym}", entry)
                self.logger.info(f"ADDED {etype}: {sym}")

        return added

    def prune_cycle(self):
        removed = {"arb": [], "rewards": [], "funding": []}
        non_static_arb = [e for e in self.state["arb_tokens"] if e.get("source") != "static"]
        non_static_rewards = [e for e in self.state["rewards_pools"] if e.get("source") != "static"]

        addrs = [e["address"] for e in non_static_arb + non_static_rewards if e.get("address")]
        md_batch = self.fetch_market_data(addrs)

        stale_arb = set()
        for entry in self.state["arb_tokens"]:
            if check_staleness(entry, md_batch.get(entry.get("address", ""), {}), self.config):
                stale_arb.add(id(entry))
        if stale_arb:
            self.state["arb_tokens"], removed["arb"] = prune_stale(self.state["arb_tokens"], stale_arb)

        stale_rewards = set()
        for entry in self.state["rewards_pools"]:
            if check_staleness(entry, md_batch.get(entry.get("address", ""), {}), self.config):
                stale_rewards.add(id(entry))
        if stale_rewards:
            self.state["rewards_pools"], removed["rewards"] = prune_stale(self.state["rewards_pools"], stale_rewards)

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
                resp = self.session.get(url, timeout=15)
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
