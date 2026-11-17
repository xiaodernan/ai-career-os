#!/usr/bin/env python3
"""Pressure probe for the live install (brief item #11).

A dependency-free burst for a running CAREER-OS stack. It measures, on the
machine where it runs:

  1. read-health ramp     : N concurrent workers hit /api/v1/health for a
                            fixed window; latency p50/p90/p99/max and the
                            HTTP status distribution.
  2. concurrency ceiling   : same endpoint at escalating concurrency, to
                            find the knee in the curve before the host falls.
  3. auth gate under load  : the 10/min login limiter, tripped deliberately
                            with 100 concurrent wrong-password attempts:
                            the answer must be 429/401, never 5xx, and the
                            health endpoint must stay green afterwards.
  4. authed read           : one real registration, then K requests to
                            /api/v1/jobs with the token.

Nothing here is a demo number: every row is measured on the live install
the operator points --base at. No LLM endpoint is hit on purpose; the
provider budget is not a bot sled. The probe never registers more than one
account.

Usage:
  python scripts/load_probe.py --base http://127.0.0.1:8080
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
import uuid

import httpx


def _percentile(sorted_vals: list[float], pct: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = min(len(sorted_vals) - 1, max(0, round(pct * (len(sorted_vals) - 1))))
    return sorted_vals[idx]


async def _hammer(client: httpx.AsyncClient, url: str, workers: int,
                  duration_s: float, counter: dict[str, int]) -> dict:
    lat: list[float] = []
    stop_at = time.monotonic() + duration_s
    sem = asyncio.Semaphore(workers)
    statuses: dict[int, int] = {}

    async def one(_):
        async with sem:
            if time.monotonic() >= stop_at:
                return
            t0 = time.monotonic()
            try:
                r = await client.get(url)
                dt = (time.monotonic() - t0) * 1000
                lat.append(dt)
                statuses[r.status_code] = statuses.get(r.status_code, 0) + 1
            except httpx.HTTPError:
                lat.append((time.monotonic() - t0) * 1000)
                statuses[0] = statuses.get(0, 0) + 1

    # Each worker loops for the whole window; the semaphore bounds parallelism.
    async def worker():
        while time.monotonic() < stop_at:
            await one(None)

    await asyncio.gather(*[worker() for _ in range(workers)])
    lat.sort()
    counter["total"] += len(lat)
    return {
        "url": url,
        "workers": workers,
        "duration_s": duration_s,
        "requests": len(lat),
        "status": dict(sorted(statuses.items())),
        "p50_ms": round(_percentile(lat, 0.50), 1),
        "p90_ms": round(_percentile(lat, 0.90), 1),
        "p99_ms": round(_percentile(lat, 0.99), 1),
        "max_ms": round(lat[-1] if lat else 0.0, 1),
        "rps": round(len(lat) / duration_s, 1),
    }


async def _phase_ceiling(client: httpx.AsyncClient, base: str,
                         counter: dict[str, int]) -> list[dict]:
    rows = []
    for workers in (1, 10, 25, 50, 100):
        rows.append(await _hammer(client, f"{base}/api/v1/health", workers,
                                  4.0, counter))
    return rows


async def _phase_auth_gate(client: httpx.AsyncClient, base: str,
                           counter: dict[str, int]) -> dict:
    statuses: dict[int, int] = {}

    async def one():
        try:
            r = await client.post(
                f"{base}/api/v1/auth/login",
                json={"email": f"pressure-{uuid.uuid4().hex[:8]}@example.com",
                      "password": "WrongPass!234"},
            )
            statuses[r.status_code] = statuses.get(r.status_code, 0) + 1
        except httpx.HTTPError:
            statuses[0] = statuses.get(0, 0) + 1

    await asyncio.gather(*[one() for _ in range(100)])
    counter["total"] += 100
    # the service must still answer its health probe after the storm
    r = await client.get(f"{base}/api/v1/health")
    return {
        "attempts": 100,
        "status": dict(sorted(statuses.items())),
        "post_storm_health_http": r.status_code,
    }


async def _phase_authed_read(client: httpx.AsyncClient, base: str,
                             counter: dict[str, int]) -> dict:
    email = f"pressure-{uuid.uuid4().hex[:8]}@example.com"
    reg = await client.post(
        f"{base}/api/v1/auth/register",
        json={"email": email, "password": "Passw0rd!234",
              "displayName": "Pressure Probe"},
    )
    if reg.status_code not in (200, 201, 409):
        return {"registered": False, "http": reg.status_code}
    token = reg.json().get("data", {}).get("tokens", {}).get("accessToken")
    if not token:
        return {"registered": False, "http": reg.status_code, "note": "no token in envelope"}
    statuses: dict[int, int] = {}
    lat: list[float] = []

    async def one():
        t0 = time.monotonic()
        r = await client.get("/api/v1/jobs", headers={"Authorization": f"Bearer {token}"})
        lat.append((time.monotonic() - t0) * 1000)
        statuses[r.status_code] = statuses.get(r.status_code, 0) + 1

    await asyncio.gather(*[one() for _ in range(60)])
    lat.sort()
    counter["total"] += 60
    return {
        "registered": True,
        "requests": len(lat),
        "status": dict(sorted(statuses.items())),
        "p50_ms": round(_percentile(lat, 0.50), 1),
        "p90_ms": round(_percentile(lat, 0.90), 1),
        "max_ms": round(lat[-1] if lat else 0.0, 1),
    }


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8080")
    args = ap.parse_args()
    base = args.base.rstrip("/")
    counter = {"total": 0}

    limits = httpx.Limits(max_connections=200, max_keepalive_connections=50)
    async with httpx.AsyncClient(base_url=base, timeout=httpx.Timeout(8.0),
                                 limits=limits) as client:
        print("== phase 2: concurrency ceiling (read-health ramp) ==", flush=True)
        ramp = await _phase_ceiling(client, base, counter)
        for row in ramp:
            print(json.dumps(row, ensure_ascii=False), flush=True)

        print("== phase 4: authed read ==", flush=True)
        authed = await _phase_authed_read(client, base, counter)
        print(json.dumps(authed, ensure_ascii=False), flush=True)

        print("== phase 3: auth gate under a 100-way wrong-password storm ==", flush=True)
        gate = await _phase_auth_gate(client, base, counter)
        print(json.dumps(gate, ensure_ascii=False), flush=True)

    print(json.dumps({"total_requests": counter["total"]}))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
