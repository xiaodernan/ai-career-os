# -*- coding: utf-8 -*-
"""Epic 234 — adversarial fuzz of the register door.

Fires malformed-but-plausible payloads at /api/v1/auth/register and asserts the
backend keeps the door in its hands: every answer is either a 2xx (accepted),
4xx (refused), or 409 (conflict); a 5xx means the validation or the SQL layer
flinched — the failure this harness exists to catch.

Six classes, ~120 requests total: RFC-violating emails, control-character
injection in every field, length boundary crossings (min/max), wrong JSON
types (arrays where objects belong, nulls), CRLF header-injection attempts,
and a concurrency burst on one email (the register race fix from Epic 226).

Exit code 1 on any 5xx, or any answer that is not a structured envelope.
"""

import json
import random
import string
import sys
import time
import urllib.request
import urllib.error
import uuid
from concurrent.futures import ThreadPoolExecutor

BASE = "http://127.0.0.1:8080/api/v1"
EMAIL = lambda local: f"{local}@example.com"
PASS = "Str0ngPassphrase!23"

cases = []

for local in [
    "", "missing@at", "a@@b.com", "a..b@example.com", "trailing.@example.com",
    ".@example.com", "user@", "@example.com", "user name@example.com",
    "user+tag@example.com", "user@exa mple.com", "ünïcodé@example.com",
    "emoji😀@example.com", "user@例子.中国", "user@example", "a" * 250 + "@x.com",
    "user@example.com\r\nBCC: victim@example.org", "user@example.com\nInjected: 1",
    "user@[127.0.0.1]", "user@example..com", "\"quoted\"@example.com",
    "user%40example.com@example.com", "a@b.c", "очень_длинный@пример.рф",
    "user@examp le.com", "换行@example.com",
]:
    cases.append(("email", {"email": EMAIL(local) if "@" not in local or local == "" else local, "password": PASS, "displayName": f"fuzzprobe {local[:12]}"}))

for pwd, cls in [
    ("", "empty"), ("short", "too-short"), ("1234567", "7-chars"), ("12345678", "8-chars-ok"),
    ("a" * 72, "72-chars-ok"), ("a" * 73, "73-chars-too-long"), ("密码密码密码密码", "unicode-short-bytes"),
    ("密码" * 9, "unicode-ok-72"), ("with\tcontrol\x7fdel", "control-chars"), ("with\nnewline", "newline"),
    ("emoji😀😀😀😀😀", "emoji-bytes"), ("'; DROP TABLE users;--", "sql"),
    ("<script>alert(1)</script>", "xss"), ("pass woord", "space"),
]:
    cases.append(("password", {"email": EMAIL(f"fuzzprobe-{uuid.uuid4().hex[:8]}"), "password": pwd, "displayName": "Fuzz Probe"}))

for name in [
    "", " ", "  ", "a" * 120, "a" * 121, "Line\nBreak", "Null\x00Byte", "RTL‮Override",
    "ZWJ‍Break", "Zero᠎Width", "<b>bold</b>", "'; DROP TABLE users;--", "<script>",
    "\u0007bell", "𝕳𝖆𝖈𝖐𝖊𝖗", "‮ＲＴＬ",
]:
    cases.append(("displayName", {"email": EMAIL(f"fuzzprobe-{uuid.uuid4().hex[:8]}"), "password": PASS, "displayName": name}))

# Wrong JSON shapes — types where objects belong, missing keys, explicit nulls.
weird_bodies = [
    ("array body", b"[]"),
    ("bare string", b"\"hello\""),
    ("number body", b"42"),
    ("null body", b"null"),
    ("empty object", b"{}"),
    ("missing password", json.dumps({"email": "fuzzprobe@example.com", "displayName": "x"}).encode()),
    ("null email", json.dumps({"email": None, "password": PASS, "displayName": "x"}).encode()),
    ("null password", json.dumps({"email": "fuzzprobe@example.com", "password": None, "displayName": "x"}).encode()),
    ("null displayName", json.dumps({"email": "fuzzprobe@example.com", "password": PASS, "displayName": None}).encode()),
    ("number email", json.dumps({"email": 12345, "password": PASS, "displayName": "x"}).encode()),
    ("bool password", json.dumps({"email": "fuzzprobe@example.com", "password": True, "displayName": "x"}).encode()),
    ("nested array", json.dumps({"email": ["a@b.com"], "password": PASS, "displayName": "x"}).encode()),
    ("unicode escape bomb", ("{\"email\": \"" + "\\u0041" * 100 + "@example.com\", \"password\": \"" + PASS + "\", \"displayName\": \"x\"}").encode()),
]


def post_raw(body: bytes):
    req = urllib.request.Request(BASE + "/auth/register", method="POST", data=body)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            raw = res.read().decode("utf-8", "replace")
            try:
                payload = json.loads(raw)
                return res.status, payload.get("success"), (payload.get("error") or {}).get("code"), raw
            except json.JSONDecodeError:
                return res.status, None, "UNPARSED", raw[:200]
    except urllib.error.HTTPError as e:
        raw_full = e.read().decode("utf-8", "replace")
        try:
            payload = json.loads(raw_full)
            return e.code, payload.get("success"), (payload.get("error") or {}).get("code"), raw_full
        except json.JSONDecodeError:
            return e.code, None, "UNPARSED", raw_full[:200]


failures = []
counts = {"2xx": 0, "4xx": 0, "5xx": 0}

print("== adversarial payloads ==")
for cls, body in cases:
    raw = json.dumps(body).encode("utf-8")
    status, success, code, note = post_raw(raw)
    bucket = "2xx" if status < 300 else "5xx" if status >= 500 else "4xx"
    counts[bucket] += 1
    ok = bucket != "5xx"
    flag = " " if ok else "!"
    if not ok or code == "UNPARSED":
        failures.append((cls, body, status, code))
        flag = "!" if not ok else "?"
    if cls == "email" and body["email"] in ("", "user@", "@example.com"):
        pass
    print(f"{flag} [{status}] {cls}: {json.dumps(body, ensure_ascii=False)[:130]} -> {code}")

print("\n== wrong JSON shapes ==")
for name, body in weird_bodies:
    status, success, code, note = post_raw(body)
    bucket = "2xx" if status < 300 else "5xx" if status >= 500 else "4xx"
    counts[bucket] += 1
    ok = bucket != "5xx" and code != "UNPARSED"
    flag = " " if ok else "!"
    if not ok:
        failures.append(("shape:" + name, body, status, code))
    print(f"{flag} [{status}] {name}: -> {code}")

print("\n== concurrency burst: one email, 12 registers at once ==")
burst_email = EMAIL(f"fuzzprobe-burst-{uuid.uuid4().hex[:8]}")
burst_body = json.dumps({"email": burst_email, "password": PASS, "displayName": "Burst Probe"}).encode()
def _burst(_):
    return post_raw(burst_body)[0]
with ThreadPoolExecutor(max_workers=12) as pool:
    codes = list(pool.map(_burst, range(12)))
created = codes.count(201) + codes.count(200)
conflicts = sum(1 for c in codes if c == 409)
fivxx = sum(1 for c in codes if c >= 500)
print(f"         statuses: {sorted(codes)} -> created={created} conflicts={conflicts} 5xx={fivxx}")
counts["5xx"] += fivxx
if fivxx:
    failures.append(("burst", burst_email, fivxx, ""))
if created > 1:
    failures.append(("burst", burst_email, created, "more than one row created?"))

print(f"\n== tally: 2xx={counts['2xx']} 4xx={counts['4xx']} 5xx={counts['5xx']} ==")
if failures:
    print("\nFAILURES:")
    for cls, body, status, code in failures:
        print(f"  - {cls}: status={status} code={code}")
    sys.exit(1)
print("FUZZ OK — the door held.")
