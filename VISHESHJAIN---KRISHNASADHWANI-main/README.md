# CodePractice — DSA Platform (MVP)

A working implementation of the architecture in `dsa-platform-architecture.md`:
Flask + SQLite backend, a subprocess-sandboxed multi-language judge (Python &
JavaScript), and a vanilla-JS frontend — all runnable locally with no build step.

This is a real, working full-stack application, not a mockup or a UI-only
prototype. Every route, every workflow, and the judge itself run against a
live server and were exercised end-to-end during development (see
[What was actually tested](#what-was-actually-tested-not-just-written) below).
A handful of deliberate scope cuts were made to fit a single-machine local
MVP, and every one of them is called out explicitly in this README so nothing
is ever mistaken for the production design described in the architecture doc.

## Table of contents

- [Live demo](#live-demo)
- [Quick start](#run-it)
- [Demo accounts](#demo-accounts-created-by-seedpy)
- [What's implemented vs. simplified from the architecture doc](#whats-implemented-vs-simplified-from-the-architecture-doc)
- [Project layout](#project-layout)
- [What was actually tested (not just written)](#what-was-actually-tested-not-just-written)
- [Suggested next steps, in priority order](#suggested-next-steps-in-priority-order)

## Live Demo

**[https://visheshjain-krishnasadhwani-2.onrender.com](https://visheshjain-krishnasadhwani-2.onrender.com)**

Deployed on Render. Use the demo accounts below to log in and try it out —
no local setup required if you just want to click through the product.

> **Cold start note:** free Render instances spin down after a period of
> inactivity. If the app has been idle, the first request after that can take
> roughly **30–60 seconds** while the dyno wakes back up and the Flask process
> restarts. This is a hosting-tier characteristic, not an application bug —
> subsequent requests are fast once the instance is warm. If you want to
> verify things are running correctly rather than just waiting on a cold
> boot, it's worth reloading once after the first slow response.

## Run it

For anyone who wants to run the platform locally instead of (or in addition
to) using the hosted demo — for example, to read logs, inspect the SQLite
database directly, or modify the judge — here is the full local setup:

```bash
cd backend
pip install -r requirements.txt --break-system-packages   # Flask, PyJWT, Werkzeug
python3 seed.py                                            # creates + seeds dsa_platform.db
python3 app.py                                              # serves on http://localhost:5050
```

Step by step, what each command does:

1. `cd backend` — all Python code and the Flask app live in the `backend/`
   directory (see [Project layout](#project-layout) below).
2. `pip install -r requirements.txt --break-system-packages` — installs the
   three backend dependencies: **Flask** (the web framework and routing
   layer), **PyJWT** (issues and verifies the JWTs used for auth/role
   gating), and **Werkzeug** (password hashing and Flask's underlying WSGI
   utilities). The `--break-system-packages` flag is needed on systems where
   pip refuses to install outside a virtual environment by default.
3. `python3 seed.py` — creates the SQLite database file `dsa_platform.db`
   from scratch (via `schema.sql`) and populates it with the full demo data
   set: 1 trainer account, 1 student account, 1 cohort, 3 LeetCode-sourced
   problems, and 1 sheet. Safe to re-run if you want a clean slate.
4. `python3 app.py` — starts the Flask development server, listening on
   `http://localhost:5050`.

Once running, open `http://localhost:5050` in a browser to reach the
single-page frontend, which talks to the Flask API automatically.

### Requirements

- `python3` on PATH — runs the Flask app itself **and** is invoked by the
  judge to execute Python submissions.
- `node` on PATH — invoked by the judge to execute JavaScript submissions.

Both interpreters are required even if you personally only plan to submit in
one language, because the judge needs to be able to run submissions in
either language on demand.

## Demo accounts (created by `seed.py`)

| Role    | Email                 | Password    |
|---------|-----------------------|-------------|
| Trainer | trainer@college.edu   | trainer123  |
| Student | student@college.edu   | student123  |

Use the **Trainer** account to see the authoring/publishing side (creating
problems, publishing drafts, viewing cohort analytics). Use the **Student**
account to see the learner-facing side (solving problems, submitting code,
tracking progress, viewing assigned sheets). Logging into both in separate
sessions is the fastest way to see the full role-gated workflow described
under [What was actually tested](#what-was-actually-tested-not-just-written).

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

A bit more detail on each of these, since the table above is intentionally
terse:

- **Job processing.** The architecture doc calls for judging to happen on an
  async job queue backed by an autoscaled pool of executors, so submission
  load never blocks the request/response cycle. In this MVP, judging runs
  **synchronously**, inline in the same request that submitted the code.
  That's a fine trade-off at demo scale — a handful of students submitting
  one at a time won't notice — but it will not hold up once more than a
  handful of students submit concurrently, because each submission ties up a
  request thread for as long as the judge takes to run. Architecture §5
  walks through why the queue is the right production answer.
- **Sandboxing and isolation.** The architecture doc calls for hardware- or
  kernel-level isolation via Firecracker microVMs or gVisor, which is what
  you'd want for true multi-tenant isolation against hostile input. This MVP
  instead uses plain OS-level `subprocess` execution combined with `resource`
  rlimits — capping CPU time, address space (where it's safe to do so),
  process count, and file size — plus wall-clock timeouts. To be explicit:
  **this is not safe multi-tenant isolation.** It's good enough for a
  trusted classroom deployment where the "adversary" is, at worst, a student
  submitting a buggy or slow solution — not for a public, hostile-input
  environment. The real sandbox needs to go in before this is opened to the
  public internet.
- **Problem ingestion.** The architecture doc describes a LeetCode ingestion
  pipeline driven by a `LEETCODE_API_KEY` and a `LEETCODE_DATA_SOURCE_URL`.
  Since no such data source was available for the MVP, `seed.py` instead
  hand-seeds a small set of `LEETCODE`-sourced problems directly — but it
  populates the **same provenance fields** (`source`, `external_ref_id`)
  that the real pipeline would populate, so the data model doesn't need to
  change when real ingestion is added later.
- **Problem format.** The architecture doc's target UX is the familiar
  LeetCode-style function-signature format (e.g. `def twoSum(nums, target):`),
  which requires generating a per-problem, per-language test harness. This
  MVP instead uses a much simpler **stdin → stdout contract**: the submitted
  program reads its input from stdin and prints its output to stdout, and
  the judge compares that output directly. It's meaningfully easier to judge
  correctly without harness generation, at the cost of a less polished,
  less LeetCode-identical submission UX. This is flagged as the
  **highest-value next increment** if LeetCode-identical UX matters.
- **Infrastructure.** The architecture doc's production stack is
  PostgreSQL, Redis, Kubernetes, and ClickHouse. The MVP intentionally
  collapses all of that down to SQLite plus the Flask development server
  running as a single process, so the entire platform can run on one
  machine with zero external infrastructure to stand up.
- **Answer checking.** The architecture doc anticipates custom checkers for
  problems that have multiple valid outputs (e.g. any correct ordering).
  This MVP only supports exact-match string comparison, with whitespace
  normalized — problems requiring a custom checker are out of scope for now.

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

What lives in each file, in more detail:

- **`backend/app.py`** — the Flask application itself: every route in the
  system lives here, spanning authentication, problem CRUD, submission
  handling, sheet management, and cohort analytics. This is the single
  entry point that ties the rest of the backend together.
- **`backend/judge.py`** — the sandboxed code execution engine: spawns the
  `subprocess`-based sandbox described above, applies the rlimits and
  timeouts, runs submitted code against each test case, and performs the
  output comparison that decides ACCEPTED / WRONG_ANSWER / RUNTIME_ERROR /
  TIME_LIMIT_EXCEEDED.
- **`backend/db.py`** — a small SQLite connection helper used by the rest of
  the backend to talk to `dsa_platform.db`.
- **`backend/schema.sql`** — the full database schema, deliberately written
  to mirror the data models defined in the architecture document, so the
  MVP's data model and the production data model stay in sync conceptually
  even though the underlying database engine differs.
- **`backend/seed.py`** — populates a freshly created database with the
  complete demo data set: 1 trainer, 1 student, 1 cohort, 3 LeetCode-sourced
  problems, and 1 sheet. This is also the script that seeds the demo
  accounts listed above.
- **`frontend/index.html`, `frontend/style.css`, `frontend/app.js`** —
  together these form a single-page application with **no build step at
  all**. `app.js` calls the Flask API directly; there's no bundler, no
  framework, and nothing to compile before the frontend will run.
- **`dsa-platform-architecture.md`** — the original architecture document
  that this entire MVP is an implementation of, and the source of every
  comparison in the [scope-cuts table](#whats-implemented-vs-simplified-from-the-architecture-doc)
  above (including its §5 on why production needs a real job queue).

## What was actually tested (not just written)

Every piece below was run against the live server during development, not just
inspected by eye — including two real bugs it caught:

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
  instead, and both still get the CPU-time and wall-clock limits. This
  matters if you're ever debugging why every single JavaScript submission
  is coming back RUNTIME_ERROR on a fresh environment — check the rlimit
  configuration for the language before assuming the judge logic itself is
  broken.
- Also caught an error in my own seed test data (an expected output that
  didn't actually match its stated input) by running a correct solution
  against it and watching it fail — fixed before shipping. This is a useful
  reminder that seed/test data needs the same scrutiny as application code:
  a correct solution failing against a seeded problem is a strong signal
  the *data* is wrong, not the *solution*.
- Progress tracking updates correctly after a SUBMIT (solved count, per-topic,
  per-difficulty breakdown)
- Sheet creation and cohort-scoped visibility (student only sees sheets
  assigned to their own cohort)
- Cohort analytics (per-student solved counts, most-failed problems)

## Suggested next steps, in priority order

1. Swap synchronous judging for a real queue (even a simple one) once more
   than a handful of students submit concurrently — see architecture §5.
   This is priority #1 because it's the scope cut most likely to actually
   break under real usage, as opposed to the others, which are safe
   simplifications at classroom scale.
2. Harden the sandbox before trusting it with adversarial input — the current
   one is fine for a cohort of students trying to pass their own tests, not
   for someone actively trying to escape it. This should happen before any
   deployment that's reachable by untrusted/public traffic.
3. Add more languages (C++, Java) — the registry in `judge.py` is designed
   so this is a config entry, not a rewrite, making it comparatively low
   effort relative to the first two items.
4. Real LeetCode ingestion once a data source is secured, replacing the
   hand-seeded stand-in in `seed.py`. Because the provenance fields
   (`source`, `external_ref_id`) are already populated correctly by the
   hand-seeded data, this should be a drop-in replacement of the ingestion
   step rather than a schema or data-model change.
