import json
import time
from datetime import datetime, timezone


CHAIN_ALIASES = {
    "sol": "solana",
    "solana": "solana",
    "base": "base",
    "bsc": "bsc",
    "bnb": "bsc",
    "bnbchain": "bsc",
    "bnb chain": "bsc",
    "binance smart chain": "bsc",
    "arb": "arbitrum",
    "arbitrum": "arbitrum",
    "eth": "ethereum",
    "ethereum": "ethereum",
}


def normalize_chain_id(chain):
    if not chain:
        return "solana"
    normalized = str(chain).strip().lower().replace("_", " ").replace("-", " ")
    normalized = " ".join(normalized.split())
    compact = normalized.replace(" ", "")
    return CHAIN_ALIASES.get(normalized) or CHAIN_ALIASES.get(compact) or compact


def chain_address_key(chain_id, address):
    return f"{normalize_chain_id(chain_id)}:{str(address or '').strip().lower()}"


def parse_csv_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value).split(",") if item.strip()]


def parse_json_mapping(value, default=None):
    if isinstance(value, dict):
        return value
    if value is None:
        return {} if default is None else default
    raw = str(value).strip()
    if not raw:
        return {} if default is None else default
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else ({} if default is None else default)
    except json.JSONDecodeError:
        return {} if default is None else default

def fmt_usd(v):
    v = float(v or 0)
    if abs(v) >= 1_000_000_000: return f"${v / 1_000_000_000:,.2f}B"
    if abs(v) >= 1_000_000: return f"${v / 1_000_000:,.2f}M"
    if abs(v) >= 1_000: return f"${v / 1_000:,.1f}K"
    return f"${v:,.2f}"

def fmt_price(p):
    p = float(p or 0)
    if p >= 1: return f"${p:,.2f}"
    if p >= 0.01: return f"${p:.4f}"
    return f"${p:.8f}"

def fmt_pct(v, decimals=2):
    return f"{float(v or 0):.{decimals}f}%"

def fmt_ts(epoch_ms):
    if not epoch_ms:
        return "?"
    ts = epoch_ms / 1000 if epoch_ms > 1e12 else epoch_ms
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%H:%M UTC")

def fmt_hours(h):
    h = float(h or 0)
    if h >= 24:
        return f"{h / 24:.1f}d"
    return f"{h:.1f}h"

def sign(v, decimals=1):
    v = float(v or 0)
    if v > 0: return f"+{v:.{decimals}f}"
    return f"{v:.{decimals}f}"

def bar(score, max_score=10, length=5):
    val = float(score or 0)
    filled = max(0, min(length, int(round(val / max_score * length))))
    return "█" * filled + "░" * (length - filled)

def rank_emoji(i):
    return {0: "🥇", 1: "🥈", 2: "🥉"}.get(i, "🔹")

def dex_link(pair_address):
    if not pair_address or pair_address == "N/A":
        return ""
    return f' <a href="https://dexscreener.com/solana/{pair_address}">[DEX]</a>'

def token_link(address):
    if not address or address == "N/A":
        return ""
    return f' <a href="https://dexscreener.com/solana/{address}">[DEX]</a>'

def binance_link(symbol):
    if not symbol: return ""
    return f' <a href="https://www.binance.com/en/futures/{symbol}">[BN]</a>'

class TTLCache:
    def __init__(self, ttl_seconds: int, max_size: int = 20000, cleanup_interval_seconds: int = 60):
        self.ttl = ttl_seconds
        self.max_size = max_size
        self.cleanup_interval_seconds = cleanup_interval_seconds
        self._data = {}
        self._next_cleanup = 0.0

    def add(self, key):
        now = time.time()
        self._data[key] = now
        if len(self._data) > self.max_size:
            self.clear_expired(now=now, force=True)
            overflow = len(self._data) - self.max_size
            if overflow > 0:
                for stale_key, _ in sorted(self._data.items(), key=lambda item: item[1])[:overflow]:
                    self._data.pop(stale_key, None)

    def __contains__(self, key):
        if key not in self._data:
            return False
        if time.time() - self._data[key] > self.ttl:
            del self._data[key]
            return False
        return True

    def clear_expired(self, now=None, force=False):
        now = time.time() if now is None else now
        if not force and now < self._next_cleanup:
            return
        expired = [k for k, v in self._data.items() if now - v > self.ttl]
        for k in expired:
            del self._data[k]
        self._next_cleanup = now + self.cleanup_interval_seconds

    def __len__(self):
        return len(self._data)
