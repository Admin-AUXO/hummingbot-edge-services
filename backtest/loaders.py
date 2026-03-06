import csv
from datetime import datetime

from backtest.models import Candle


def _to_timestamp(value):
    if value is None:
        return 0.0
    text = str(value).strip()
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _build_candle(ts, open_price, high_price, low_price, close, volume):
    return Candle(
        timestamp=ts,
        open=open_price,
        high=max(high_price, close, open_price),
        low=min(low_price, close, open_price),
        close=close,
        volume=volume,
    )


def _safe_float(val, default=0.0):
    try:
        return float(val or default)
    except (ValueError, TypeError):
        return default


def load_token_candles(csv_path):
    if csv_path.lower().endswith(".parquet"):
        return _load_parquet(csv_path)
    return _load_csv(csv_path)


def _load_csv(csv_path):
    candles = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return candles
        names = {name.lower(): name for name in reader.fieldnames}
        ts_col = names.get("timestamp") or names.get("time") or names.get("date")
        close_col = names.get("close") or names.get("price")
        open_col = names.get("open") or close_col
        high_col = names.get("high") or close_col
        low_col = names.get("low") or close_col
        volume_col = names.get("volume")
        if not ts_col or not close_col:
            raise ValueError(f"CSV requires timestamp/time/date and close/price columns: {csv_path}")
        for row in reader:
            ts = _to_timestamp(row.get(ts_col))
            close = _safe_float(row.get(close_col))
            if ts <= 0 or close <= 0:
                continue
            candles.append(_build_candle(
                ts=ts,
                open_price=_safe_float(row.get(open_col), close),
                high_price=_safe_float(row.get(high_col), close),
                low_price=_safe_float(row.get(low_col), close),
                close=close,
                volume=_safe_float(row.get(volume_col)) if volume_col else 0.0,
            ))
    candles.sort(key=lambda c: c.timestamp)
    return candles


def _load_parquet(parquet_path):
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise ImportError("pyarrow required for parquet. Install: pip install pyarrow") from exc

    table = pq.read_table(parquet_path, columns=["timestamp", "close", "open", "high", "low", "volume"])
    data = table.to_pydict()
    timestamps = data.get("timestamp", [])
    closes = data.get("close", [])
    opens = data.get("open", [])
    highs = data.get("high", [])
    lows = data.get("low", [])
    volumes = data.get("volume", [])

    candles = []
    for idx in range(len(timestamps)):
        ts = _to_timestamp(timestamps[idx])
        close = float(closes[idx]) if closes[idx] is not None else 0.0
        if ts <= 0 or close <= 0:
            continue
        candles.append(_build_candle(
            ts=ts,
            open_price=float(opens[idx]) if opens[idx] is not None else close,
            high_price=float(highs[idx]) if highs[idx] is not None else close,
            low_price=float(lows[idx]) if lows[idx] is not None else close,
            close=close,
            volume=float(volumes[idx]) if idx < len(volumes) and volumes[idx] is not None else 0.0,
        ))
    candles.sort(key=lambda c: c.timestamp)
    return candles
