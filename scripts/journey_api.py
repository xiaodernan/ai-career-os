# -*- coding: utf-8 -*-
"""The golden journey as one API script, against the containerized stack.

Every station of MASTER_PROMPT §35's user journey, in order, with per-call latency
recorded (§36's baseline). Writes its report to stdout; exits non-zero when a
station fails, so the journey doubles as a regression gate.
"""
import json
import time
import urllib.request
import uuid

BASE = "http://127.0.0.1:8080/api/v1"
AI = "http://127.0.0.1:8000"
EMAIL = f"journey-{uuid.uuid4().hex[:8]}@example.com"
PASS = "Str0ngPassphrase!23"
timings: list[tuple[str, float]] = []


def call(name, method, path, token=None, body=None, base=BASE, raw=False):
    req = urllib.request.Request(base + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    data = json.dumps(body).encode("utf-8") if body is not None else None
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, data=data, timeout=120) as res:
            payload = json.loads(res.read().decode("utf-8"))
            ms = (time.perf_counter() - t0) * 1000
            timings.append((name, ms))
            print(f"[ok  {ms:7.0f}ms] {name}")
            return payload.get("data") if not raw else payload
    except urllib.error.HTTPError as e:
        ms = (time.perf_counter() - t0) * 1000
        body_text = e.read().decode("utf-8", "replace")[:200]
        print(f"[FAIL{ms:7.0f}ms] {name}: HTTP {e.code} {body_text}")
        raise SystemExit(1)


print("== the golden journey, one API call per station ==")

# 1. register / who am I
me = call("register", "POST", "/auth/register",
          body={"email": EMAIL, "password": PASS, "displayName": "Journey Walker"})
token = me["tokens"]["accessToken"]
call("who am I", "GET", "/users/me", token)

# 2. career profile
call("save profile", "PATCH", "/users/me/profile", token,
     {"headline": "Backend engineer, 5 years", "targetRoles": ["Senior Backend Engineer"]})

# 3. upload a resume (multipart) -- urllib multipart by hand
boundary = uuid.uuid4().hex
resume_text = (
    "%PDF-1.4\n% mock\n"
    "Senior Backend Engineer with 5 years of Java, Spring Boot, PostgreSQL and Redis.\n"
    "Built payment platforms handling 10k TPS; led a team of four; migrated a monolith\n"
    "to services on Kubernetes. ran under load. %%EOF\n"
)
mp = (
    f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
    f"filename=\"journey.pdf\"\r\nContent-Type: application/pdf\r\n\r\n{resume_text}\r\n"
    f"--{boundary}\r\nContent-Disposition: form-data; name=\"title\"\r\n\r\nJourney Resume\r\n"
    f"--{boundary}--\r\n"
)
req = urllib.request.Request(BASE + "/resumes/upload", method="POST",
                             data=mp.encode("utf-8"))
req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
req.add_header("Authorization", f"Bearer {token}")
t0 = time.perf_counter()
with urllib.request.urlopen(req, timeout=120) as res:
    up = json.loads(res.read().decode("utf-8"))["data"]
ms = (time.perf_counter() - t0) * 1000
timings.append(("upload resume (ingests)", ms))
print(f"[ok  {ms:7.0f}ms] upload resume -> resumeId={up['resumeId'][:8]} doc={up['documentId'][:8]}")

# 4. resume detail (the parsed profile the upload's ingestion produced asynchronously)
rid = up["resumeId"]
detail = call("resume detail", "GET", f"/resumes/{rid}", token)

# 5. knowledge: paste text, list sources
call("ingest text", "POST", "/knowledge/text", token,
     {"title": "Journey notes", "text": "I care about distributed systems, event-driven design, and mentoring. My strongest language is Java; I have shipped Kafka pipelines in production.", "kind": "note"})
sources = call("list knowledge", "GET", "/knowledge/sources?page=0&size=5", token)
print(f"        knowledge sources: {sources['total']}")

# 6. search jobs
jobs = call("search jobs", "GET", "/jobs?page=0&size=5&q=backend&sort=relevance", token)
job_id = jobs["items"][0]["id"]
print(f"        jobs: {jobs['total']} total, first: {jobs['items'][0]['title']}")

# 7. JD analysis + the stored read the dialog's rehydrate path makes (71.3)
jd = call("jd analyze", "POST", "/jds", token,
          {"rawText": "Senior Backend Engineer. Required: Java, Spring Boot, PostgreSQL, Kubernetes, Kafka. Preferred: Redis, gRPC, OpenAPI. Responsibilities: design payment services, mentor engineers."})
stored = call("jd stored read", "GET", f"/jds/{jd['id']}", token)
assert stored.get("id") == jd["id"], "the stored read must answer the row the analysis stored"

# 8. match
match = call("job match", "POST", f"/jobs/{job_id}/match", token,
             {"resumeVersionId": detail.get("currentVersionId")})
print(f"        match score present: {bool((match.get('match') or {}).get('score') or match.get('matchId'))}")

# 9. skill gap comes inside the match block; tailor next
tailor = call("tailor resume", "POST", f"/jobs/{job_id}/tailor", token,
              {"resumeVersionId": detail.get("currentVersionId")})
print(f"        tailored version: {str(tailor)[:80]}")

# 10. cover letter
call("cover letter", "POST", f"/jobs/{job_id}/cover-letter", token,
     {"resumeVersionId": detail.get("currentVersionId"), "mode": "generate",
      "tone": "professional", "length": "short", "goal": "Get an interview", "previous": ""})

# 11. mock interview
session = call("interview session", "POST", "/interview/sessions", token,
               {"companyId": None, "jobId": job_id, "mode": "behavioral", "positionTitle": "Senior Backend Engineer", "difficulty": 0.5})
sid = session["id"]
opening = call("interview opening", "POST", f"/interview/sessions/{sid}/opening", token, {})
call("interview answer", "POST", f"/interview/sessions/{sid}/answer", token,
     {"answer": "I led the migration of a monolith to services on Kubernetes, cutting deploy time from hours to minutes.",
      "question": (opening or {}).get("question", "Tell me about a system you designed."),
      "turns": []})
call("interview finalize", "POST", f"/interview/sessions/{sid}/finalize", token,
     {"turns": [{"role": "interviewer", "content": "Tell me about a system you designed."},
                {"role": "candidate", "content": "I led the migration of a monolith to services."}]})

# 12. tracker: a card for the posting the match was computed for, then a status
# move. A match does not create an application by itself -- the old script assumed
# one appeared, printed `applications: 0`, and skipped the whole tracker leg while
# still claiming the journey covered it. Create the card explicitly and assert both
# halves, so the script really is the regression gate its docstring claims to be.
card = call("create application", "POST", "/applications", token,
            {"jobId": job_id, "title": jobs["items"][0]["title"]})
apps = call("list applications", "GET", "/applications?page=0&size=5", token)
print(f"        applications: {apps['total']}")
assert apps["total"] >= 1, "the card just created must appear in the pipeline"
assert any(row["id"] == card["id"] for row in apps["items"]), (
    "the pipeline must list the card the journey created")
moved = call("move application", "PATCH", f"/applications/{card['id']}", token,
             {"status": "applied"})
assert str(moved.get("status", "")).lower() == "applied", (
    f"the status move must answer the moved state: {moved}")

# 13. growth report (the 10.2 bridge)
call("growth report", "POST", "/growth-report", token,
     {"targetRole": "Senior Backend Engineer (Java)"})

# 13.5 notes: a tagged note and the tag vocabulary it creates (69.2)
call("create note", "POST", "/knowledge/notes", token,
     {"title": "Journey note", "content": "The dial states live in one table the sweeps read.",
      "tags": ["journey", "infrastructure"]})
tags = call("tag vocabulary", "GET", "/knowledge/notes/tags", token)
print(f"        tags: {[(t_.get('tag'), t_.get('count')) for t_ in (tags or [])][:4]}")
assert any(t_.get("tag") == "journey" for t_ in (tags or [])), "the created note's tag must count"

# 14. contacts
contact = call("create contact", "POST", "/contacts", token,
               {"name": "李雷", "role": "Staff Engineer", "company": "Acme", "relation": "referrer"})
call("list contacts", "GET", "/contacts", token)
# 14.5 boards answering words (70.3): the registry narrows to one word
by_word = call("contacts by word", "GET", "/contacts?q=%E6%9D%8E%E9%9B%B7", token)
rows = by_word.get("items", by_word) if isinstance(by_word, dict) else by_word
print(f"        contacts matching 李雷: {len(rows)}")

# 15. copilot turn (search-backed artifact — the regression this run family caught)
chat = call("copilot chat", "POST", "/copilot/chat", token,
            {"message": "帮我找几个适合我的后端岗位"})
print(f"        artifacts: {[a.get('type') for a in chat.get('artifacts', [])]}")
assert chat.get("artifacts"), "the copilot turn must yield a job_list artifact"

# 16. export bundle (13.x) + import plan round-trip
bundle = call("export bundle", "POST", "/data-portability/export", token, {"anonymized": False})
# `call()` already unwraps `{success, data, error}`; `bundle["data"]` is the sections
# payload, not another envelope. Reaching into it used to print an empty section list
# for a bundle that was in fact full.
counts = bundle.get("manifest", {}).get("counts", {})
print(f"        bundle sections: {sorted(counts.keys())}")
assert counts, "the export bundle must name the sections it carries"
call("import plan", "POST", "/data-portability/import-plan", token, {"bundle": bundle})

# 16.5 mail dials: read the three dials, flip one, read again (42.2)
mail = call("mail settings", "GET", "/me/mail/settings", token)
print(f"        dials: weekly={mail.get('weekly')} signals={mail.get('signals')} reminders={mail.get('reminders')}")
flipped = call("flip weekly dial", "PUT", "/me/mail/settings/weekly", token, {"enabled": False})
print(f"        weekly after flip: {flipped.get('weekly')}")
assert flipped.get("weekly") is False, "the dial flip must answer the moved state"
call("flip weekly back", "PUT", "/me/mail/settings/weekly", token, {"enabled": True})

# 16.6 markdown render (13.1): the quick look at the bundle in the reader's language
rendered = call("render markdown", "POST", "/data-portability/render", token,
                {"bundle": bundle, "format": "markdown", "locale": "en"})
print(f"        markdown: {len(rendered.get('markdown', ''))} chars")

# 17. dashboard
dash = call("dashboard", "GET", "/reports/dashboard", token)
print(f"        dashboard keys: {sorted(k for k in dash if k)[:6]}...")

print("\n== latency baseline (§36) ==")
for name, ms in sorted(timings, key=lambda kv: -kv[1]):
    print(f"{ms:8.0f}ms  {name}")
slow = [t for t in timings if t[1] > 5000]
print(f"\nstations over 5s: {len(slow)}")
print(f"JOURNEY OK — {len(timings)} stations")
