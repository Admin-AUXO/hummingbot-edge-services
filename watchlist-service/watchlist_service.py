import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import WatchlistConfig
from shared.utils import TTLCache, chain_address_key, normalize_chain_id, parse_csv_list
from shared.base_service import BaseService
from watchlist_manager import (
    build_arb_entry,
    build_funding_entry,
    check_staleness,
    load_state,
    parse_boost_signals,
    parse_profile_signals,
    prune_stale,
    save_state,
    seed_state,
    should_add_arb,
    should_add_funding,
    to_arb_json,
    to_funding_json,
    to_rewards_json,
)


class WatchlistService(BaseService):
    name = "watchlist"

    def __init__(self):
        super().__init__(WatchlistConfig())
        self.pending_signals = []
        self.signal_cache = TTLCache(self.config.signal_dedupe_ttl_seconds)
        self.supported_chains = [normalize_chain_id(chain) for chain in parse_csv_list(self.config.supported_chains)] or ["solana"]
        self._init_state()

    def _signal_dedupe_key(self, signal, topic):
        chain_id = normalize_chain_id(signal.get("chainId"))
        source = signal.get("source", "")
        address = signal.get("address", "")
        token = signal.get("token", "")
        identity = address or token
        return f"{topic}:{source}:{chain_id}:{identity}"

    def _passes_signal_gate(self, signal, is_alpha, is_narr):
        chain_id = normalize_chain_id(signal.get("chainId"))
        if is_alpha:
            score = signal.get("score")
            if score is not None and float(score) < self.config.min_signal_alpha_score_for(chain_id):
                return False
        if is_narr and float(signal.get("volume_spike", 0)) < self.config.min_signal_narrative_spike_for(chain_id):
            return False
        return True

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
        if not self.pending_signals:
            return {}

        signals = self.pending_signals
        self.pending_signals = []

        chain_counts = {}
        dropped_by_chain = {}
        accepted = []
        dropped_overflow = 0
        for signal in signals:
            chain = normalize_chain_id(signal.get("chainId"))
            cap = max(0, int(self.config.max_signals_per_cycle_for(chain)))
            if cap == 0:
                dropped_overflow += 1
                dropped_by_chain[chain] = dropped_by_chain.get(chain, 0) + 1
                continue
            current = chain_counts.get(chain, 0)
            if current >= cap:
                dropped_overflow += 1
                dropped_by_chain[chain] = dropped_by_chain.get(chain, 0) + 1
                continue
            chain_counts[chain] = current + 1
            accepted.append(signal)

        signals = accepted
        if dropped_overflow:
            breakdown = ", ".join(f"{chain}={count}" for chain, count in sorted(dropped_by_chain.items()))
            self.logger.info(f"Dropped {dropped_overflow} watchlist signals (per-chain cycle caps): {breakdown}")

        added = {"arb": [], "rewards": [], "funding": []}
        ex_arb = {chain_address_key(e.get("chainId"), e["address"]) for e in self.state["arb_tokens"] if "address" in e}
        ex_funding = {e["symbol"] for e in self.state["funding_symbols"] if "symbol" in e}
        dropped_dedupe = 0
        dropped_gate = 0

        for signal in signals:
            topic = signal.pop("_topic", "")
            is_alpha = "/alpha/" in topic or signal.get("source") in ("dex_boost", "dex_profile")
            is_narr = "/narrative/" in topic
            if not (is_alpha or is_narr):
                continue

            dedupe_key = self._signal_dedupe_key(signal, topic)
            if dedupe_key in self.signal_cache:
                dropped_dedupe += 1
                continue
            self.signal_cache.add(dedupe_key)

            if not self._passes_signal_gate(signal, is_alpha, is_narr):
                dropped_gate += 1
                continue

            source = signal.get("source", "alpha") if is_alpha else "narrative"

            ok, _ = should_add_arb(signal, ex_arb, self.state, self.config)
            if ok:
                entry = build_arb_entry(signal, source)
                self.state["arb_tokens"].append(entry)
                ex_arb.add(chain_address_key(entry.get("chainId"), entry["address"]))
                added["arb"].append(entry)

            ok, _ = should_add_funding(signal, ex_funding, self.state, self.config)
            if ok:
                sym = f"{signal.get('token', '')}USDT"
                entry = build_funding_entry(sym, source)
                self.state["funding_symbols"].append(entry)
                ex_funding.add(sym)
                added["funding"].append(entry)

        if dropped_dedupe or dropped_gate:
            self.logger.info(f"Signal filter: dedupe={dropped_dedupe} threshold={dropped_gate}")

        for etype, entries in added.items():
            for entry in entries:
                sym = entry.get("symbol") or entry.get("token", "?")
                chain = "global" if etype == "funding" else normalize_chain_id(entry.get("chainId"))
                self.publish(f"{self.config.mqtt_topic_prefix}/{chain}/added/{etype}/{sym}", entry)
                self.logger.info(f"ADDED {etype}: [{chain}] {sym}")

        return added

    def prune_cycle(self):
        removed = {"arb": [], "rewards": [], "funding": []}
        non_static_arb = [e for e in self.state["arb_tokens"] if e.get("source") != "static"]
        non_static_rewards = [e for e in self.state["rewards_pools"] if e.get("source") != "static"]

        market_items = [
            {"address": e["address"], "chainId": e.get("chainId")}
            for e in non_static_arb + non_static_rewards if e.get("address")
        ]
        md_batch = self.fetch_market_data(market_items)

        stale_arb = set()
        for entry in self.state["arb_tokens"]:
            md_key = chain_address_key(entry.get("chainId"), entry.get("address", ""))
            if check_staleness(entry, md_batch.get(md_key, {}), self.config):
                stale_arb.add(id(entry))
        if stale_arb:
            self.state["arb_tokens"], removed["arb"] = prune_stale(self.state["arb_tokens"], stale_arb)

        stale_rewards = set()
        for entry in self.state["rewards_pools"]:
            md_key = chain_address_key(entry.get("chainId"), entry.get("address", ""))
            if check_staleness(entry, md_batch.get(md_key, {}), self.config):
                stale_rewards.add(id(entry))
        if stale_rewards:
            self.state["rewards_pools"], removed["rewards"] = prune_stale(self.state["rewards_pools"], stale_rewards)

        for entry_type, entries in removed.items():
            for entry in entries:
                sym = entry.get("symbol", entry.get("token", "?"))
                chain = normalize_chain_id(entry.get("chainId"))
                self.publish(f"{self.config.mqtt_topic_prefix}/{chain}/removed/{entry_type}/{sym}", entry)
                self.logger.info(f"REMOVED {entry_type}: [{chain}] {sym} (stale)")

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
            "chains": self.supported_chains,
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
        try:
            resp = self.session.get(self.config.dex_boosts_url, timeout=15)
            resp.raise_for_status()
            signals = parse_boost_signals(resp.json(), supported_chains=self.supported_chains)
            for signal in signals:
                signal["_topic"] = "trending/dex"
            self.pending_signals.extend(signals)
            counts = {}
            for signal in signals:
                chain = normalize_chain_id(signal.get("chainId"))
                counts[chain] = counts.get(chain, 0) + 1
            self.logger.info(f"Boost poll: {len(signals)} tokens {counts}")
        except Exception as e:
            self.logger.error(f"Boost poll failed ({self.config.dex_boosts_url}): {e}")

    def poll_profiles(self):
        try:
            resp = self.session.get(self.config.dex_profiles_url, timeout=15)
            resp.raise_for_status()
            signals = parse_profile_signals(resp.json(), supported_chains=self.supported_chains)
            for signal in signals:
                signal["_topic"] = "trending/dex"
            self.pending_signals.extend(signals)
            counts = {}
            for signal in signals:
                chain = normalize_chain_id(signal.get("chainId"))
                counts[chain] = counts.get(chain, 0) + 1
            self.logger.info(f"Profile poll: {len(signals)} tokens {counts}")
        except Exception as e:
            self.logger.error(f"Profile poll failed ({self.config.dex_profiles_url}): {e}")

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
        last_boost_poll = 0.0
        last_profile_poll = 0.0

        while self.running:
            now = time.time()

            if (now - last_eval) >= self.config.eval_interval_seconds:
                self.eval_cycle()
                last_eval = now

            if (now - last_boost_poll) >= self.config.boost_poll_seconds:
                self.poll_trending()
                last_boost_poll = now

            if (now - last_profile_poll) >= self.config.profile_poll_seconds:
                self.poll_profiles()
                last_profile_poll = now

            self.sleep_loop(min(10, self.config.eval_interval_seconds))

        self.shutdown_mqtt()


if __name__ == "__main__":
    WatchlistService().run()
