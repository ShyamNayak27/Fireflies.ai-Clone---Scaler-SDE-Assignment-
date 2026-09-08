"""A real load test against the running API — not a claimed number, a measured one.

Usage: python -m scripts.loadtest [--url URL] [--concurrency N] [--requests N]

Hits a realistic mix of the endpoints an actual session would call: browsing the
library, opening a meeting, paging its transcript, and searching. Reports p50/p95/p99
latency and achieved throughput. Results are recorded in docs/ARCHITECTURE.md §13.1.
"""

from __future__ import annotations

import argparse
import asyncio
import random
import time

import httpx

ENDPOINTS = [
    "/api/meetings?limit=20",
    "/api/meetings/1",
    "/api/meetings/2",
    "/api/meetings/3/transcript?limit=50",
    "/api/search?q=battery",
    "/api/search?q=deploy",
    "/healthz",
]


async def worker(client: httpx.AsyncClient, results: list, errors: list, n: int) -> None:
    for _ in range(n):
        path = random.choice(ENDPOINTS)
        t0 = time.perf_counter()
        try:
            resp = await client.get(path)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            if resp.status_code >= 500:
                errors.append((path, resp.status_code))
            else:
                results.append(elapsed_ms)
        except Exception as exc:  # noqa: BLE001
            errors.append((path, str(exc)))


def percentile(data: list[float], p: float) -> float:
    if not data:
        return 0.0
    data = sorted(data)
    idx = min(len(data) - 1, int(len(data) * p))
    return data[idx]


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--concurrency", type=int, default=50)
    parser.add_argument("--requests", type=int, default=40, help="requests per worker")
    args = parser.parse_args()

    results: list[float] = []
    errors: list = []

    async with httpx.AsyncClient(base_url=args.url, timeout=10.0) as client:
        t0 = time.perf_counter()
        await asyncio.gather(
            *[worker(client, results, errors, args.requests) for _ in range(args.concurrency)]
        )
        wall_seconds = time.perf_counter() - t0

    total = len(results) + len(errors)
    print(f"total requests:   {total}")
    print(f"concurrency:      {args.concurrency}")
    print(f"wall time:        {wall_seconds:.2f}s")
    print(f"throughput:       {total / wall_seconds:.1f} req/s")
    print(f"errors (5xx/exc): {len(errors)}")
    if results:
        print(f"latency p50:      {percentile(results, 0.50):.1f} ms")
        print(f"latency p95:      {percentile(results, 0.95):.1f} ms")
        print(f"latency p99:      {percentile(results, 0.99):.1f} ms")
        print(f"latency max:      {max(results):.1f} ms")
    if errors[:5]:
        print("sample errors:", errors[:5])


if __name__ == "__main__":
    asyncio.run(main())
