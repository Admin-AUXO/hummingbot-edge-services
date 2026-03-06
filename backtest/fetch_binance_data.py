import argparse
import csv
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests


BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"


def fetch_klines(symbol, interval, start_ms, end_ms, request_delay, max_retries):
    rows = []
    cursor = start_ms
    session = requests.Session()
    rate_limit_hits = 0
    while cursor < end_ms:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": cursor,
            "endTime": end_ms,
            "limit": 1000,
        }
        chunk = None
        for attempt in range(max_retries + 1):
            try:
                response = session.get(BINANCE_KLINES_URL, params=params, timeout=30)
                if response.status_code == 429:
                    rate_limit_hits += 1
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        try:
                            wait_seconds = max(0.2, float(retry_after))
                        except ValueError:
                            wait_seconds = 1.0
                    else:
                        wait_seconds = min(8.0, (2 ** attempt) * 0.8)
                    time.sleep(wait_seconds)
                    continue
                response.raise_for_status()
                chunk = response.json()
                break
            except requests.RequestException:
                if attempt >= max_retries:
                    raise
                time.sleep((2 ** attempt) * 0.4)
        if not chunk:
            break
        rows.extend(chunk)
        last_open = int(chunk[-1][0])
        if last_open <= cursor:
            break
        cursor = last_open + 1
        if request_delay > 0:
            time.sleep(request_delay)
    return rows, rate_limit_hits


def write_csv(symbol, rows, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    token = symbol.replace("USDT", "")
    path = os.path.join(output_dir, f"{token}.csv")
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "close", "open", "high", "low", "volume"])
        for row in rows:
            open_time = int(row[0]) // 1000
            open_price = row[1]
            high_price = row[2]
            low_price = row[3]
            close_price = row[4]
            volume = row[5]
            writer.writerow([open_time, close_price, open_price, high_price, low_price, volume])
    return path


def write_parquet(symbol, rows, output_dir, compression):
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise ImportError("pyarrow is required for parquet output. Install with: pip install pyarrow") from exc

    os.makedirs(output_dir, exist_ok=True)
    token = symbol.replace("USDT", "")
    path = os.path.join(output_dir, f"{token}.parquet")

    timestamps = []
    closes = []
    opens = []
    highs = []
    lows = []
    volumes = []

    for row in rows:
        timestamps.append(int(row[0]) // 1000)
        opens.append(float(row[1]))
        highs.append(float(row[2]))
        lows.append(float(row[3]))
        closes.append(float(row[4]))
        volumes.append(float(row[5]))

    table = pa.table(
        {
            "timestamp": timestamps,
            "close": closes,
            "open": opens,
            "high": highs,
            "low": lows,
            "volume": volumes,
        }
    )

    parquet_compression = None if compression.lower() == "none" else compression.lower()
    pq.write_table(table, path, compression=parquet_compression)
    return path


def write_dataset(symbol, rows, output_dir, output_format, compression):
    if output_format == "csv":
        return write_csv(symbol=symbol, rows=rows, output_dir=output_dir)
    return write_parquet(symbol=symbol, rows=rows, output_dir=output_dir, compression=compression)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", default="BTCUSDT,ETHUSDT,SOLUSDT")
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--hours", type=int, default=0)
    parser.add_argument("--output-dir", default="backtest/data")
    parser.add_argument("--output-format", choices=["csv", "parquet"], default="parquet")
    parser.add_argument("--compression", choices=["snappy", "gzip", "zstd", "none"], default="snappy")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=12)
    parser.add_argument("--request-delay", type=float, default=0.10)
    parser.add_argument("--max-retries", type=int, default=3)
    return parser.parse_args()


def _chunks(items, size):
    size = max(1, size)
    for idx in range(0, len(items), size):
        yield items[idx : idx + size]


def _fetch_one_symbol(symbol, interval, start_ms, end_ms, request_delay, max_retries, output_dir, output_format, compression):
    rows, rate_limit_hits = fetch_klines(
        symbol=symbol,
        interval=interval,
        start_ms=start_ms,
        end_ms=end_ms,
        request_delay=request_delay,
        max_retries=max_retries,
    )
    if not rows:
        return symbol, None, 0, rate_limit_hits
    out = write_dataset(
        symbol=symbol,
        rows=rows,
        output_dir=output_dir,
        output_format=output_format,
        compression=compression,
    )
    return symbol, out, len(rows), rate_limit_hits


def main():
    args = parse_args()
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    end_ms = int(time.time() * 1000)
    lookback_ms = max(1, args.days) * 24 * 3600 * 1000
    if int(args.hours) > 0:
        lookback_ms = int(args.hours) * 3600 * 1000
    start_ms = end_ms - lookback_ms

    workers = max(1, int(args.workers))
    batch_size = max(1, int(args.batch_size))

    print(
        f"Downloading {args.interval} candles for {len(symbols)} symbols from Binance "
        f"(format={args.output_format}, compression={args.compression}, workers={workers}, batch_size={batch_size})..."
    )
    saved = []
    failed = []
    current_workers = workers
    clean_batches = 0

    for batch_index, batch in enumerate(_chunks(symbols, batch_size), start=1):
        print(f"Batch {batch_index}: fetching {len(batch)} symbols with workers={current_workers}")
        with ThreadPoolExecutor(max_workers=min(current_workers, len(batch))) as executor:
            future_map = {
                executor.submit(
                    _fetch_one_symbol,
                    symbol,
                    args.interval,
                    start_ms,
                    end_ms,
                    args.request_delay,
                    args.max_retries,
                    args.output_dir,
                    args.output_format,
                    args.compression,
                ): symbol
                for symbol in batch
            }

            batch_rate_limit_hits = 0

            for future in as_completed(future_map):
                symbol = future_map[future]
                try:
                    resolved_symbol, out, row_count, rate_limit_hits = future.result()
                    batch_rate_limit_hits += rate_limit_hits
                    if out is None:
                        print(f"No data for {resolved_symbol}")
                        failed.append(resolved_symbol)
                        continue
                    if rate_limit_hits > 0:
                        print(f"Saved {resolved_symbol}: {row_count} rows -> {out} (429 hits: {rate_limit_hits})")
                    else:
                        print(f"Saved {resolved_symbol}: {row_count} rows -> {out}")
                    saved.append(out)
                except Exception as exc:
                    print(f"Failed {symbol}: {exc}")
                    failed.append(symbol)

        if batch_rate_limit_hits > 0:
            new_workers = max(1, current_workers - 1)
            if new_workers < current_workers:
                print(
                    f"Auto-throttle: detected {batch_rate_limit_hits} rate-limit responses; "
                    f"reducing workers {current_workers} -> {new_workers}"
                )
            current_workers = new_workers
            clean_batches = 0
        else:
            clean_batches += 1
            if clean_batches >= 2 and current_workers < workers:
                current_workers += 1
                clean_batches = 0
                print(f"Auto-throttle recovery: increasing workers to {current_workers}")

    if not saved:
        raise ValueError("No datasets downloaded. Check symbols/interval.")

    if failed:
        print(f"Completed with failures ({len(failed)}): {', '.join(sorted(set(failed)))}")

    print("Done.")


if __name__ == "__main__":
    main()