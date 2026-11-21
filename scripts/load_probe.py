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
    # A probe reports, never crashes: right after a saturation ramp the registration
    # can miss the client timeout while the server thread pool drains. That is a
    # measured FAIL for --strict, not a traceback that hides the whole verdict.
    try:
        reg = await client.post(
        f"{base}/api/v1/auth/register",
        json={"email": email, "password": "Passw0rd!234",
              "displayName": "Pressure Probe"},
        )
    except httpx.HTTPError as e:
        return {"registered": False, "http": 0,
                "note": f"registration transport: {type(e).__name__}"}
    if reg.status_code not in (200, 201, 409):
        return {"registered": False, "http": reg.status_code}
    try:
        token = reg.json().get("data", {}).get("tokens", {}).get("accessToken")
    except ValueError:
        return {"registered": False, "http": reg.status_code, "note": "non-JSON envelope"}
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


async def _phase_llm_coalesce(client: httpx.AsyncClient, base: str,
                               counter: dict[str, int], concurrency: int) -> dict:
    """Epic 363 — one flight per key, measured through the real stack.

    N readers send the SAME deterministic question at the same moment. The engine
    coalesces them into one provider call, so the wall clock should be roughly one
    call's latency rather than N of them, and every reader must get an answer.

    This phase spends real tokens, so it is opt-in (--llm-coalesce) and bounded to
    a small concurrency: the point is to prove the merge, not to run a sled against
    somebody else's API. The provider budget is not a load-testing tool.
    """
    email = f"coalesce-{uuid.uuid4().hex[:8]}@example.com"
    try:
        reg = await client.post(
            f"{base}/api/v1/auth/register",
            json={"email": email, "password": "Passw0rd!234",
                  "displayName": "Coalesce Probe"},
        )
    except httpx.HTTPError as e:
        return {"measured": False, "note": f"registration transport: {type(e).__name__}"}
    if reg.status_code not in (200, 201, 409):
        return {"measured": False, "http": reg.status_code}
    token = reg.json().get("data", {}).get("tokens", {}).get("accessToken")
    if not token:
        return {"measured": False, "note": "no token in envelope"}

    # One deterministic question, byte-identical across every reader: that identity
    # is what makes them one flight rather than N.
    body = {"targetRole": "Senior Backend Engineer (Java)", "locale": "en"}
    statuses: dict[int, int] = {}
    lat: list[float] = []
    answers: set[str] = set()

    async def one():
        t0 = time.monotonic()
        r = await client.post("/api/v1/gap-analysis",
                              json=body,
                              headers={"Authorization": f"Bearer {token}"})
        lat.append((time.monotonic() - t0) * 1000)
        statuses[r.status_code] = statuses.get(r.status_code, 0) + 1
        if r.status_code == 200:
            try:
                answers.add(r.text)
            except ValueError:
                pass

    t0 = time.monotonic()
    await asyncio.gather(*[one() for _ in range(concurrency)])
    wall = (time.monotonic() - t0) * 1000
    lat.sort()
    counter["total"] += concurrency
    return {
        "measured": True,
        "concurrency": concurrency,
        "wall_ms": round(wall, 1),
        "p50_ms": round(_percentile(lat, 0.50), 1),
        "p99_ms": round(_percentile(lat, 0.99), 1),
        "status": dict(sorted(statuses.items())),
        # Every reader must be answered, and all of them with the same bytes: that
        # is what "one flight" means from the outside.
        "distinct_answers": len(answers),
        "all_answered": all(code == 200 for code in statuses),
    }


def _strict_failures(ramp: list[dict], authed: dict, gate: dict) -> list[str]:
    """Turn measurements into a PASS/FAIL verdict.

    A load probe that only prints numbers cannot gate CI. These are the
    invariants the install must hold under pressure — saturation is fine, falling
    over is not: no 5xx anywhere, the credential storm must be answered (never a
    connection error), no wrong password may succeed, and health must recover.
    Kept as a pure function so the verdict is unit-testable without a live stack.
    """
    failures: list[str] = []
    for row in ramp:
        server_errors = {s: n for s, n in row["status"].items() if s >= 500}
        conn_errors = row["status"].get(0, 0)
        if server_errors:
            failures.append(f"health@{row['workers']} 5xx={server_errors}")
        if conn_errors:
            failures.append(f"health@{row['workers']} connection_errors={conn_errors}")
    if not authed.get("registered"):
        failures.append(f"authed read: registration failed http={authed.get('http')}")
    else:
        bad = {s: n for s, n in authed["status"].items() if s >= 400}
        if bad:
            failures.append(f"authed read: unexpected errors={bad}")
    gate_status = gate["status"]
    if 200 in gate_status:
        failures.append(f"auth gate: {gate_status[200]} wrong-password logins SUCCEEDED")
    bad_gate = {s: n for s, n in gate_status.items() if s >= 500}
    if bad_gate:
        failures.append(f"auth gate: 5xx={bad_gate}")
    if gate_status.get(0):
        failures.append(f"auth gate: connection_errors={gate_status[0]}")
    if gate["post_storm_health_http"] != 200:
        failures.append(f"health after storm http={gate['post_storm_health_http']}")
    return failures


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8080")
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero when a pressure invariant is violated (CI gate)")
    ap.add_argument("--llm-coalesce", type=int, default=0, metavar="N",
                    help="also measure Epic 363's one-flight-per-key merge: N readers "
                         "send the same deterministic question. Spends real tokens, "
                         "so it is opt-in and bounded.")
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

        # Let the server drain the saturation ramp before the write-heavy authed
        # phase: a burst probe should measure each phase, not the previous one's
        # thread-pool debt. One second is enough for in-flight health reads to finish.
        await asyncio.sleep(1.0)

        print("== phase 4: authed read ==", flush=True)
        authed = await _phase_authed_read(client, base, counter)
        print(json.dumps(authed, ensure_ascii=False), flush=True)

        print("== phase 3: auth gate under a 100-way wrong-password storm ==", flush=True)
        gate = await _phase_auth_gate(client, base, counter)
        print(json.dumps(gate, ensure_ascii=False), flush=True)

        if args.llm_coalesce > 0:
            print(f"== phase 5: one flight per key ({args.llm_coalesce} readers) ==", flush=True)
            coalesce = await _phase_llm_coalesce(client, base, counter, args.llm_coalesce)
            print(json.dumps(coalesce, ensure_ascii=False), flush=True)

    print(json.dumps({"total_requests": counter["total"]}))
    if args.strict:
        failures = _strict_failures(ramp, authed, gate)
        print(json.dumps({"verdict": "FAIL" if failures else "PASS",
                          "failures": failures}, ensure_ascii=False), flush=True)
        return 1 if failures else 0
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
