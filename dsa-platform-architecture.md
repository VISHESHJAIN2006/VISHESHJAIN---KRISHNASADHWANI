# DSA Problem-Solving Platform — Architectural Blueprint

## 1. System Overview

The platform is a web-based coding practice environment purpose-built for a college placement-preparation program. It combines a curated daily-practice workflow (driven by Placement Trainers) with a self-serve, LeetCode-style problem library available to all students free of charge.

Core design principles:
- **Separation of curation and content**: Trainers assemble *practice sets* from a shared problem catalog; they don't need to author problems from scratch for every use.
- **Language-agnostic execution**: Submissions in any supported language are evaluated through a common sandboxed execution contract.
- **External-content respect**: LeetCode problems are referenced and normalized through a controlled ingestion layer, not scraped or mirrored wholesale — see §6.
- **Horizontal scalability**: The heaviest cost centers (code execution, judging) are isolated as stateless, autoscaled workers, decoupled from the core web app.

```
                         ┌─────────────────────┐
                         │   Web/Mobile Client  │
                         └──────────┬───────────┘
                                    │ HTTPS/REST/WS
                         ┌──────────▼───────────┐
                         │     API Gateway       │
                         └──────────┬───────────┘
        ┌──────────────┬───────────┼───────────────┬──────────────┐
        ▼              ▼           ▼               ▼              ▼
 ┌────────────┐ ┌─────────────┐ ┌────────┐ ┌───────────────┐ ┌───────────┐
 │ Auth &     │ │ Problem &   │ │Submission│ │ Analytics &  │ │ Content   │
 │ User Svc   │ │ Set Svc     │ │ Judge Svc│ │ Progress Svc │ │ Ingestion │
 └─────┬──────┘ └──────┬──────┘ └────┬────┘ └──────┬───────┘ └─────┬─────┘
       │               │             │             │               │
       ▼               ▼             ▼             ▼               ▼
   Users DB      Problems DB    Job Queue →   Analytics DB   [LEETCODE_DATA_
                  Test Cases                  Executor Pool   SOURCE_URL]
                                              (sandboxed,
                                               autoscaled)
```

---

## 2. User Roles & Permissions

### 2.1 Student
| Capability | Notes |
|---|---|
| Browse full problem catalog | Filter by topic, difficulty, company tag, frequency |
| Solve problems in any supported language | Code editor with per-language templates |
| Submit code for judging | Run against sample + hidden test cases |
| View personal submission history & diffs | Track attempts, runtime/memory stats |
| Join assigned practice sets ("Daily Sheets") | Auto-enrolled by cohort/batch |
| View personal progress dashboard | Streaks, topic-wise mastery, weak-area flags |
| Discuss/comment on a problem (optional) | Peer discussion, editorial hints (trainer-gated) |
| View public leaderboards (opt-in) | Cohort-level, not forced |

Students have **read-only** access to the problem catalog and **write** access scoped strictly to their own submissions, profile, and discussion posts.

### 2.2 Placement Trainer
Trainers inherit all Student capabilities plus:

| Capability | Notes |
|---|---|
| Create/curate Practice Sets ("Sheets") | Combine catalog problems + custom problems into daily/weekly assignments |
| Assign Sheets to cohorts/batches | With due dates, visibility windows |
| Author custom problems | For internal-only questions not sourced from LeetCode |
| Edit/annotate ingested LeetCode problems | Add hints, difficulty overrides, internal tags (company-specific relevance) |
| Add/curate test cases | Especially edge cases beyond what LeetCode exposes |
| View cohort-wide analytics | Completion rates, per-topic weak spots, submission trends |
| Moderate discussions | Pin editorials, remove spam |
| Manage cohorts/batches | Add/remove students, assign trainers to batches |

Trainers do **not** get raw database or infrastructure access — all actions go through the same API surface as students, gated by an RBAC middleware layer (role claims embedded in the auth token, checked per-endpoint).

### 2.3 (Optional future role) Admin
System-level user management, integration configuration (API keys, ingestion schedules), infrastructure-facing settings. Kept separate from Trainer to avoid privilege creep — a trainer being over-permissioned is a common failure mode in these systems.

---

## 3. Data Models

Shown as logical schemas (DB-agnostic); adapt to relational or document store per §8.

### 3.1 Problem
```
Problem {
  problem_id: UUID (PK)
  title: string
  slug: string (unique, URL-safe)
  source: enum [INTERNAL, LEETCODE]
  external_ref_id: string (nullable)   // LeetCode's internal problem id/slug, if sourced
  difficulty: enum [EASY, MEDIUM, HARD]
  topics: string[]                     // e.g. ["dp", "graphs"]
  company_tags: string[]               // curated by trainers
  statement_markdown: text
  constraints_markdown: text
  starter_code: map<language, string>  // per-language boilerplate/function signature
  editorial_markdown: text (nullable, trainer-gated visibility)
  created_by: user_id
  ingestion_metadata: {
    fetched_at: timestamp
    source_url: string
    license_note: string              // tracks usage terms of ingested content
  }
  status: enum [DRAFT, PUBLISHED, ARCHIVED]
  created_at, updated_at: timestamp
}
```

### 3.2 TestCase
```
TestCase {
  test_case_id: UUID (PK)
  problem_id: UUID (FK -> Problem)
  input_payload: text | file_ref        // large inputs stored in blob storage, referenced here
  expected_output: text | file_ref
  is_sample: boolean                    // visible to students pre-submission
  is_hidden: boolean                    // used only for final judging
  weight: float (nullable)              // for partial-credit judging models
  source: enum [INTERNAL, LEETCODE, TRAINER_ADDED]
  time_limit_ms: int
  memory_limit_mb: int
  created_at: timestamp
}
```

### 3.3 Submission
```
Submission {
  submission_id: UUID (PK)
  user_id: UUID (FK -> User)
  problem_id: UUID (FK -> Problem)
  practice_set_id: UUID (nullable, FK)   // set if submitted as part of an assignment
  language: enum [PYTHON, JAVA, CPP, JS, GO, ...]
  source_code: text
  status: enum [QUEUED, RUNNING, ACCEPTED, WRONG_ANSWER, TLE, MLE, RUNTIME_ERROR, COMPILE_ERROR]
  runtime_ms: int (nullable)
  memory_kb: int (nullable)
  test_case_results: [
    { test_case_id, passed: bool, runtime_ms, actual_output_excerpt }
  ]
  submitted_at: timestamp
  judged_at: timestamp (nullable)
}
```

### 3.4 ProgressTracking
```
UserProblemProgress {
  user_id: UUID (FK)
  problem_id: UUID (FK)
  best_status: enum [NOT_ATTEMPTED, ATTEMPTED, SOLVED]
  attempts_count: int
  first_solved_at: timestamp (nullable)
  last_attempted_at: timestamp
}

UserTopicMastery {
  user_id: UUID (FK)
  topic: string
  solved_count: int
  attempted_count: int
  mastery_score: float          // derived metric, recomputed on submission events
}

PracticeSet {
  set_id: UUID (PK)
  title: string
  created_by: trainer_id
  problem_ids: UUID[]
  assigned_cohorts: UUID[]
  visible_from: timestamp
  due_at: timestamp (nullable)
}

PracticeSetCompletion {
  set_id: UUID (FK)
  user_id: UUID (FK)
  problems_completed: int
  problems_total: int
  completed_at: timestamp (nullable)
}
```

### 3.5 User
```
User {
  user_id: UUID (PK)
  role: enum [STUDENT, TRAINER, ADMIN]
  name, email, college_id: string
  cohort_id: UUID (nullable)
  auth_provider_ref: string       // SSO/college-auth linkage
  created_at: timestamp
}
```

---

## 4. Core Features

### 4.1 Problem Management (Trainer-facing)
- **Catalog browser** over ingested + internal problems with bulk-tagging tools (topic, company, difficulty).
- **Problem editor** (Markdown-based) for internal problems, with live preview matching the student-facing render.
- **Test case curation UI**: add/edit hidden test cases, mark samples, set per-language time/memory limits.
- **Sheet builder**: drag-and-drop problems into a Practice Set, schedule visibility windows, assign to one or more cohorts.
- **Review queue**: newly ingested LeetCode problems land in `DRAFT` status for trainer review/edit before `PUBLISHED`, so nothing reaches students unvetted.

### 4.2 Problem Solving Interface (Student-facing)
- Split-pane layout: problem statement + constraints on one side, code editor (Monaco or CodeMirror) on the other.
- Language switcher with saved starter code/templates per language.
- "Run" (sample test cases, instant feedback) vs. "Submit" (full hidden suite, queued judging) as distinct actions — mirrors LeetCode's UX and avoids wasting judge capacity on exploratory runs.
- Inline hints/editorial unlock rules configurable by trainers (e.g., unlock after N failed attempts or after due date passes).

### 4.3 Code Execution Environment (Multi-language)
- Each submission is dispatched as a job to a **sandboxed executor pool** — one container image per supported language, with strict CPU/memory/time limits and no network access from inside the sandbox.
- Executors are stateless and horizontally autoscaled based on queue depth (see §5 for the queue-based decoupling that makes this possible).
- A thin **language adapter** layer normalizes the invocation contract per language (compile step where needed, stdin/stdout convention, exit-code interpretation) so the Judge Service doesn't special-case each language.
- Supported languages are config-driven (a registry entry per language: image name, compile command, run command, default limits) so adding a language doesn't require code changes to the judge itself.

### 4.4 Test Case Evaluation
- Judge Service pulls a queued submission, fans it out against the problem's test cases (samples first for fast feedback, then hidden cases).
- Comparison strategy is configurable per problem: exact string match, whitespace-normalized match, or a custom checker script for problems with multiple valid outputs (needed for some graph/DP problems where output order isn't unique).
- Results are streamed back to the client incrementally (via WebSocket or polling) rather than only on full completion, so students see partial progress on large test suites.

### 4.5 Progress Tracking & Analytics
- **Student view**: per-topic mastery radar, solve streak, weak-topic recommendations, Sheet completion status.
- **Trainer view**: cohort heatmaps (who's stuck where), Sheet completion funnels, most-failed problems/test cases (signal for which problems need better hints or easier on-ramps).
- Analytics are computed as a materialized/derived layer off the Submission event stream, not queried live against the transactional Submission table, to keep dashboards fast as submission volume grows.

### 4.6 LeetCode Integration Strategy
See §6 below — kept separate since it has both architectural and compliance dimensions.

---

## 5. Scalability Considerations

- **Decouple judging from the web tier**: Submissions are pushed onto a job queue (e.g., a message broker) immediately on receipt; the API returns a `submission_id` right away and the client polls/subscribes for results. This keeps the web tier fast under load and lets the executor pool scale independently — this is the single highest-leverage decision for cost and responsiveness, since compute-heavy judging is naturally spiky (assignment deadlines, exam-week rushes).
- **Autoscale executors on queue depth**, not CPU of the web tier — the two workloads have unrelated load patterns.
- **Cache problem/test-case reads** aggressively (they're read-heavy, write-rarely) — CDN or edge cache for problem statements, in-memory cache for hot test cases.
- **Partition analytics writes** from the transactional path (event-driven: Submission → event bus → Analytics Service consumer), so a spike in judging never blocks dashboard writes or vice versa.
- **Rate-limit submissions per user** to prevent accidental (or intentional) queue flooding, e.g., during a live contest.

---

## 6. LeetCode Integration Strategy

Because direct, unrestricted access to LeetCode's backend isn't assumed, ingestion is modeled as a **controlled, reviewed pipeline** rather than a live pass-through:

1. **Ingestion source**: A configured data source — `[LEETCODE_DATA_SOURCE_URL]`, authenticated via `[LEETCODE_API_KEY]` — representing whatever legitimate access path the college secures (an official partner API, a licensed dataset, or a manually-curated import process). The architecture treats this as a pluggable adapter so the actual source can change without touching downstream services.
2. **Content Ingestion Service**: Periodically (or on-demand) pulls problem metadata, statements, and sample test cases through the adapter, normalizes them into the internal `Problem`/`TestCase` schema, and lands them in `DRAFT` status.
3. **Licensing/attribution metadata**: Every ingested problem retains `source`, `external_ref_id`, and a `license_note` field recording the terms under which it was imported — so provenance is traceable and the college can audit usage.
4. **Trainer review gate**: Nothing reaches students until a trainer reviews and publishes it — this is also where trainers supplement thin official sample cases with additional hidden test cases authored in-house (common gap, since public sample sets are usually small).
4a. **No scraping fallback**: If no formal data agreement exists, the ingestion adapter should point at a manually-maintained internal dataset (trainers/students transcribe problems they've legitimately encountered) rather than the pipeline silently scraping LeetCode's site — keeps the system compliant regardless of what access is actually secured.
5. **Sync strategy**: One-way sync (LeetCode → internal catalog) on ingestion; internal edits (hints, extra test cases, tags) are never pushed back, avoiding any two-way dependency on an external system's write API.

---

## 7. Technology Stack Recommendations

| Layer | Suggestion | Rationale |
|---|---|---|
| Frontend | React/Next.js + Monaco Editor | Rich editor support, large ecosystem, SSR for fast problem-page loads |
| API Gateway/Backend | Node.js (NestJS) or Python (FastAPI) | Both have strong async support for I/O-heavy request patterns here |
| Auth | OAuth2/OIDC via college SSO if available, else JWT-based custom auth | Avoids maintaining a separate credential store where possible |
| Primary DB | PostgreSQL | Relational integrity for Users/Problems/Submissions; JSONB columns handle flexible fields (starter_code map, tags) well |
| Blob/Object storage | S3-compatible store | Large test case inputs/outputs, avoids bloating the primary DB |
| Job Queue | Redis Streams / RabbitMQ / SQS | Decouples submission intake from judging, per §5 |
| Code Execution Sandbox | Firecracker microVMs or gVisor-isolated Docker containers | Strong isolation for untrusted student code, fast cold-start |
| Analytics store | ClickHouse or a Postgres read-replica with materialized views | Optimized for the aggregate queries dashboards need |
| Caching | Redis | Hot problem/test-case reads, rate-limiting counters |
| Deployment | Kubernetes (or a managed container service) | Independent autoscaling of web tier vs. executor pool |

Given the cost-effectiveness constraint, a smaller-scale deployment (single managed Postgres + a small autoscaled executor pool on spot/preemptible instances) is a reasonable starting point — the architecture above scales up without a rewrite, but nothing here requires paying for that scale on day one.

---

## 8. Open Design Questions (for the trainers/stakeholders to weigh in on)

- **Contest/timed-mode support**: Is a live-contest mode (leaderboard, timed window) in scope now or later? Affects whether the Submission model needs a `contest_id` field from the start.
- **Plagiarism detection**: Worth budgeting for (e.g., MOSS-style similarity checks) given free-form code submission at scale across a cohort.
- **Offline/low-bandwidth access**: Relevant if students may be practicing from hostel networks with inconsistent connectivity — affects whether the editor needs local autosave/offline queuing.
- **Data retention for submissions**: How long to retain full source code for past submissions, given storage cost vs. the pedagogical value of students reviewing old attempts.
