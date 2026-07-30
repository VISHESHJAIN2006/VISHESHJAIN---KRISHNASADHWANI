-- DSA Platform schema (SQLite)

CREATE TABLE IF NOT EXISTS cohorts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('STUDENT', 'TRAINER')),
    cohort_id INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (cohort_id) REFERENCES cohorts(id)
);

CREATE TABLE IF NOT EXISTS problems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'INTERNAL' CHECK(source IN ('INTERNAL', 'LEETCODE')),
    external_ref_id TEXT,
    difficulty TEXT NOT NULL CHECK(difficulty IN ('EASY', 'MEDIUM', 'HARD')),
    topics TEXT NOT NULL DEFAULT '[]',        -- JSON array
    company_tags TEXT NOT NULL DEFAULT '[]',  -- JSON array
    statement_md TEXT NOT NULL,
    constraints_md TEXT NOT NULL DEFAULT '',
    starter_code TEXT NOT NULL DEFAULT '{}',  -- JSON: {"python": "...", "javascript": "..."}
    editorial_md TEXT,
    status TEXT NOT NULL DEFAULT 'DRAFT' CHECK(status IN ('DRAFT', 'PUBLISHED', 'ARCHIVED')),
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS test_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    problem_id INTEGER NOT NULL,
    input_payload TEXT NOT NULL DEFAULT '',
    expected_output TEXT NOT NULL,
    is_sample INTEGER NOT NULL DEFAULT 0,
    time_limit_ms INTEGER NOT NULL DEFAULT 2000,
    memory_limit_mb INTEGER NOT NULL DEFAULT 256,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (problem_id) REFERENCES problems(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    problem_id INTEGER NOT NULL,
    practice_set_id INTEGER,
    mode TEXT NOT NULL DEFAULT 'SUBMIT' CHECK(mode IN ('RUN', 'SUBMIT')),
    language TEXT NOT NULL,
    source_code TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'QUEUED',
    runtime_ms INTEGER,
    results_json TEXT,
    submitted_at TEXT NOT NULL DEFAULT (datetime('now')),
    judged_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (problem_id) REFERENCES problems(id)
);

CREATE TABLE IF NOT EXISTS user_problem_progress (
    user_id INTEGER NOT NULL,
    problem_id INTEGER NOT NULL,
    best_status TEXT NOT NULL DEFAULT 'ATTEMPTED' CHECK(best_status IN ('ATTEMPTED', 'SOLVED')),
    attempts_count INTEGER NOT NULL DEFAULT 0,
    first_solved_at TEXT,
    last_attempted_at TEXT,
    PRIMARY KEY (user_id, problem_id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (problem_id) REFERENCES problems(id)
);

CREATE TABLE IF NOT EXISTS practice_sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    created_by INTEGER NOT NULL,
    visible_from TEXT NOT NULL DEFAULT (datetime('now')),
    due_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS practice_set_problems (
    set_id INTEGER NOT NULL,
    problem_id INTEGER NOT NULL,
    order_index INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (set_id, problem_id),
    FOREIGN KEY (set_id) REFERENCES practice_sets(id) ON DELETE CASCADE,
    FOREIGN KEY (problem_id) REFERENCES problems(id)
);

CREATE TABLE IF NOT EXISTS practice_set_cohorts (
    set_id INTEGER NOT NULL,
    cohort_id INTEGER NOT NULL,
    PRIMARY KEY (set_id, cohort_id),
    FOREIGN KEY (set_id) REFERENCES practice_sets(id) ON DELETE CASCADE,
    FOREIGN KEY (cohort_id) REFERENCES cohorts(id)
);
