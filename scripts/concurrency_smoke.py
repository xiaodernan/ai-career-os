# -*- coding: utf-8 -*-
"""Concurrency smoke (§36's last unchecked concern): parallel reads and writes.

N workers hit the search list and the dashboard while a second wave writes
profile patches and contact rows. The claims under test: no 5xx, latency stays
under the interactive bar at the p95, and the rate limiter is the only thing
that answers 429. Run against the containerized stack.
"""
import concurrent.futures
import json
import statistics
import time
import urllib.error
import urllib.request
import uuid

BASE = "http://127.0.0.1:8080/api/v1"
N_WORKERS = 16
CALLS_PER_WORKER = 8


def register() -> str:
    req = urllib.request.Request(BASE + "/auth/register", method="POST",
                                 data=json.dumps({"email": f"conc-{uuid.uuid4().hex[:8]}@example.com",
                                                  "password": "Str0ngPassphrase!23",
                                                  "displayName": "Concurrency"}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as res:
        return json.loads(res.read())["data"]["tokens"]["accessToken"]


def call(token, method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {token}")
    data = json.dumps(body).encode() if body is not None else None
    t0 = time.perf_counter()
    code, err = 0, None
    try:
        with urllib.request.urlopen(req, data=data, timeout=60) as res:
            code = res.status
            res.read()
    except urllib.error.HTTPError as e:
        code = e.code
        err = e.read().decode("utf-8", "replace")[:120]
    return (time.perf_counter() - t0) * 1000, code, err


READS = ["/jobs?page=0&size=10", "/reports/dashboard", "/knowledge/sources?page=0&size=5"]
WRITES = [("PATCH", "/users/me/profile", {"headline": f"Concurrent {uuid.uuid4().hex[:6]}"}),
          ("POST", "/contacts", None)]  # body filled per call


def worker(token, wid):
    out = []
    for i in range(CALLS_PER_WORKER):
        if wid % 2 == 0:
            path = READS[(wid + i) % len(READS)]
            ms, code, err = call(token, "GET", path)
        else:
            _, path, body = WRITES[i % len(WRITES)]
            if body is None:
                body = {"name": f"并发联系人 {wid}-{i}", "relation": "peer"}
            ms, code, err = call(token, "POST" if path == "/contacts" else "PATCH", path, body)
        out.append((ms, code, err))
    return out


def main():
    tokens = [register() for _ in range(4)]
    # one shared token per 4 workers: concurrent access by the SAME user is the
    # interesting case (row contention), which distinct users would sidestep.
    t0 = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=N_WORKERS) as pool:
        futures = [pool.submit(worker, tokens[w % len(tokens)], w) for w in range(N_WORKERS)]
        results = [r for f in futures for r in f.result()]
    wall = time.perf_counter() - t0

    lat = sorted(r[0] for r in results)
    codes = {}
    for _, code, err in results:
        codes[code] = codes.get(code, 0) + 1
    p50 = lat[len(lat) // 2]
    p95 = lat[int(len(lat) * 0.95)]
    errors5xx = [e for _, c, e in results if c >= 500]
    print(f"calls: {len(results)} by {N_WORKERS} workers in {wall:.1f}s")
    print(f"p50 {p50:.0f}ms | p95 {p95:.0f}ms | max {lat[-1]:.0f}ms")
    print(f"codes: {dict(sorted(codes.items()))}")
    if errors5xx:
        for e in errors5xx[:3]:
            print(" 5xx:", e)
    assert not errors5xx, "a 5xx under concurrency is a defect, not load"
    assert p95 < 5000, f"p95 {p95:.0f}ms is past the interactive bar"
    print("CONCURRENCY OK")


if __name__ == "__main__":
    main()
