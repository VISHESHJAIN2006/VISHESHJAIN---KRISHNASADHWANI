# CodePractice — DSA Platform (MVP)

A working implementation of the architecture in `dsa-platform-architecture.md`:
Flask + SQLite backend, a subprocess-sandboxed multi-language judge (Python &
JavaScript), and a vanilla-JS frontend — all runnable locally with no build step.

## Run it

```bash
cd backend
pip install -r requirements.txt --break-system-packages   # Flask, PyJWT, Werkzeug
python3 seed.py                                            # creates + seeds dsa_platform.db
python3 app.py                                              # serves on http://localhost:5050
```

Open `http://localhost:5050`. Demo accounts (created by `seed.py`):

| Role    | Email                 | Password    |
|---------|-----------------------|-------------|
| Trainer | trainer@college.edu   | trainer123  |
| Student | student@college.edu   | student123  |

Requires `python3` and `node` on PATH (both used by the judge to actually run
submitted code).

## What's implemented vs. simplified from the architecture doc

This is a real, working full-stack app — not a mockup — but a few deliberate
scope cuts were made to fit a single-machine local MVP. Each is called out so
nothing is mistaken for the production design:

| Architecture doc | This MVP |
|---|---|
| Async job queue + autoscaled executor pool | Judging runs synchronously in the request (fine at demo scale; §5 of the architecture doc explains why production needs the queue) |
| Firecracker microVMs / gVisor sandboxing | `subprocess` + `resource` rlimits (CPU, address space where safe, process count, file size) + timeouts. **This is not safe multi-tenant isolation** — good enough for a trusted classroom deployment, not for hostile input at scale. Swap in the real sandbox before opening this to the public internet. |
| LeetCode ingestion pipeline (`[LEETCODE_API_KEY]`, `[LEETCODE_DATA_SOURCE_URL]`) | Hand-seeded `LEETCODE`-sourced problems in `seed.py`, with the same provenance fields (`source`, `external_ref_id`) the real pipeline would populate |
| Function-signature problem format (`def twoSum(nums, target):`) | stdin → stdout contract (read input, print output) — much simpler to judge correctly without per-problem, per-language harness generation. Swapping to function-signature problems is the highest-value next increment if you want LeetCode-identical UX. |
| PostgreSQL, Redis, Kubernetes, ClickHouse | SQLite + Flask dev server, single process |
| Custom checkers for multi-valid-output problems | Exact-match string comparison (whitespace-normalized) only |

## Project layout

```
backend/
  app.py          Flask app: all routes (auth, problems, submissions, sheets, analytics)
  judge.py        Sandboxed code execution + test case comparison
  db.py           SQLite connection helper
  schema.sql      Full schema (mirrors the data models in the architecture doc)
  seed.py         Demo data: 1 trainer, 1 student, 1 cohort, 3 LeetCode-sourced problems, 1 sheet
frontend/
  index.html, style.css, app.js    Single-page app, no build step, calls the Flask API
dsa-platform-architecture.md        The original architecture document
```

## What was actually tested (not just written)

Every piece below was run against the live server during development, not just
inspected by eye — including a bug it caught:

- Signup/login, JWT auth, role gating (student blocked from trainer-only routes → 403)
- Draft → publish workflow (students can't see DRAFT problems; can immediately
  after a trainer publishes)
- Full submission judging in **both** Python and JavaScript against a real
  correct solution (all test cases ACCEPTED)
- Wrong answer, runtime error (uncaught exception), and time-limit-exceeded
  (infinite loop) paths, in both languages
- **Found and fixed a real bug during testing**: `RLIMIT_AS` (virtual memory
  cap) kills Node.js on startup because V8 reserves a large address range
  up front regardless of actual usage — every JS submission was failing as
  `RUNTIME_ERROR` before the fix. Python doesn't have this problem (its
  memory footprint tracks real usage), so it's a per-language concern now:
  Python gets the hard `RLIMIT_AS` ceiling, JS gets `--max-old-space-size`
  instead, and both still get the CPU-time and wall-clock limits.
- Also caught an error in my own seed test data (an expected output that
  didn't actually match its stated input) by running a correct solution
  against it and watching it fail — fixed before shipping.
- Progress tracking updates correctly after a SUBMIT (solved count, per-topic,
  per-difficulty breakdown)
- Sheet creation and cohort-scoped visibility (student only sees sheets
  assigned to their own cohort)
- Cohort analytics (per-student solved counts, most-failed problems)

## Suggested next steps, in priority order

1. Swap synchronous judging for a real queue (even a simple one) once more
   than a handful of students submit concurrently — see architecture §5.
2. Harden the sandbox before trusting it with adversarial input — the current
   one is fine for a cohort of students trying to pass their own tests, not
   for someone actively trying to escape it.
3. Add more languages (C++, Java) — the registry in `judge.py` is designed
   so this is a config entry, not a rewrite.
4. Real LeetCode ingestion once a data source is secured, replacing the
   hand-seeded stand-in in `seed.py`.
