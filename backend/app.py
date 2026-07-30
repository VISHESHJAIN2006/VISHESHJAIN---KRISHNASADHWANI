import os
import json
import functools
import datetime

import jwt
from flask import Flask, request, jsonify, g, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash

from db import get_connection, init_db, row_to_dict, rows_to_list
from judge import judge_submission, LANGUAGE_REGISTRY

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-me")
JWT_ALGO = "HS256"
TOKEN_TTL_HOURS = 24

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")


# --------------------------------------------------------------------------
# Auth helpers
# --------------------------------------------------------------------------

def make_token(user):
    payload = {
        "sub": str(user["id"]),   # <-- convert to string
        "role": user["role"],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=TOKEN_TTL_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def decode_token(token):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.PyJWTError:
        return None


def require_auth(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401
        payload = decode_token(auth_header.split(" ", 1)[1])
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401
        conn = get_connection()
        user = conn.execute("SELECT * FROM users WHERE id = ?", (payload["sub"],)).fetchone()
        conn.close()
        if not user:
            return jsonify({"error": "User not found"}), 401
        g.user = row_to_dict(user)
        return f(*args, **kwargs)
    return wrapper


def require_trainer(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if g.user["role"] != "TRAINER":
            return jsonify({"error": "Trainer role required"}), 403
        return f(*args, **kwargs)
    return wrapper


def public_user(user):
    return {"id": user["id"], "name": user["name"], "email": user["email"],
            "role": user["role"], "cohort_id": user["cohort_id"]}


# --------------------------------------------------------------------------
# Static frontend
# --------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


# --------------------------------------------------------------------------
# Auth routes
# --------------------------------------------------------------------------

@app.post("/api/auth/signup")
def signup():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = data.get("role") or "STUDENT"
    cohort_name = (data.get("cohort_name") or "").strip()

    if not name or not email or len(password) < 6:
        return jsonify({"error": "name, email, and a password (min 6 chars) are required"}), 400
    if role not in ("STUDENT", "TRAINER"):
        return jsonify({"error": "role must be STUDENT or TRAINER"}), 400

    conn = get_connection()
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        conn.close()
        return jsonify({"error": "An account with this email already exists"}), 409

    cohort_id = None
    if cohort_name:
        row = conn.execute("SELECT id FROM cohorts WHERE name = ?", (cohort_name,)).fetchone()
        if row:
            cohort_id = row["id"]
        else:
            cur = conn.execute("INSERT INTO cohorts (name) VALUES (?)", (cohort_name,))
            cohort_id = cur.lastrowid

    pw_hash = generate_password_hash(password)
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash, role, cohort_id) VALUES (?, ?, ?, ?, ?)",
        (name, email, pw_hash, role, cohort_id),
    )
    conn.commit()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()

    user = row_to_dict(user)
    return jsonify({"token": make_token(user), "user": public_user(user)}), 201


@app.post("/api/auth/login")
def login():
    data = request.get_json(force=True)
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    user = row_to_dict(user)
    return jsonify({"token": make_token(user), "user": public_user(user)})


@app.get("/api/auth/me")
@require_auth
def me():
    return jsonify({"user": public_user(g.user)})


# --------------------------------------------------------------------------
# Problems
# --------------------------------------------------------------------------

def problem_to_public_dict(row, include_editorial=False):
    d = row_to_dict(row)
    d["topics"] = json.loads(d["topics"])
    d["company_tags"] = json.loads(d["company_tags"])
    d["starter_code"] = json.loads(d["starter_code"])
    if not include_editorial:
        d.pop("editorial_md", None)
    return d


@app.get("/api/languages")
def languages():
    return jsonify({"languages": [{"id": k, "label": v["label"]} for k, v in LANGUAGE_REGISTRY.items()]})


@app.get("/api/problems")
@require_auth
def list_problems():
    conn = get_connection()
    if g.user["role"] == "TRAINER":
        rows = conn.execute("SELECT * FROM problems ORDER BY created_at DESC").fetchall()
    else:
        rows = conn.execute("SELECT * FROM problems WHERE status = 'PUBLISHED' ORDER BY created_at DESC").fetchall()
    conn.close()

    problems = [problem_to_public_dict(r) for r in rows]

    if g.user["role"] == "STUDENT":
        conn = get_connection()
        progress_rows = conn.execute(
            "SELECT problem_id, best_status FROM user_problem_progress WHERE user_id = ?", (g.user["id"],)
        ).fetchall()
        conn.close()
        progress_map = {r["problem_id"]: r["best_status"] for r in progress_rows}
        for p in problems:
            p["my_status"] = progress_map.get(p["id"], "NOT_ATTEMPTED")

    return jsonify({"problems": problems})


@app.get("/api/problems/<slug>")
@require_auth
def get_problem(slug):
    conn = get_connection()
    row = conn.execute("SELECT * FROM problems WHERE slug = ?", (slug,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Problem not found"}), 404
    if g.user["role"] != "TRAINER" and row["status"] != "PUBLISHED":
        conn.close()
        return jsonify({"error": "Problem not found"}), 404

    samples = conn.execute(
        "SELECT id, input_payload, expected_output FROM test_cases WHERE problem_id = ? AND is_sample = 1",
        (row["id"],),
    ).fetchall()
    conn.close()

    d = problem_to_public_dict(row, include_editorial=(g.user["role"] == "TRAINER"))
    d["sample_test_cases"] = rows_to_list(samples)
    return jsonify({"problem": d})


@app.post("/api/problems")
@require_auth
@require_trainer
def create_problem():
    data = request.get_json(force=True)
    required = ["slug", "title", "difficulty", "statement_md"]
    missing = [k for k in required if not data.get(k)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
    if data["difficulty"] not in ("EASY", "MEDIUM", "HARD"):
        return jsonify({"error": "difficulty must be EASY, MEDIUM, or HARD"}), 400

    conn = get_connection()
    existing = conn.execute("SELECT id FROM problems WHERE slug = ?", (data["slug"],)).fetchone()
    if existing:
        conn.close()
        return jsonify({"error": "A problem with this slug already exists"}), 409

    cur = conn.execute(
        """INSERT INTO problems
           (slug, title, source, external_ref_id, difficulty, topics, company_tags,
            statement_md, constraints_md, starter_code, editorial_md, status, created_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data["slug"], data["title"], data.get("source", "INTERNAL"), data.get("external_ref_id"),
            data["difficulty"], json.dumps(data.get("topics", [])), json.dumps(data.get("company_tags", [])),
            data["statement_md"], data.get("constraints_md", ""), json.dumps(data.get("starter_code", {})),
            data.get("editorial_md"), data.get("status", "DRAFT"), g.user["id"],
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM problems WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return jsonify({"problem": problem_to_public_dict(row, include_editorial=True)}), 201


@app.put("/api/problems/<int:problem_id>")
@require_auth
@require_trainer
def update_problem(problem_id):
    data = request.get_json(force=True)
    conn = get_connection()
    row = conn.execute("SELECT * FROM problems WHERE id = ?", (problem_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Problem not found"}), 404

    fields = {}
    for key in ["title", "difficulty", "statement_md", "constraints_md", "editorial_md", "status", "external_ref_id"]:
        if key in data:
            fields[key] = data[key]
    for key in ["topics", "company_tags", "starter_code"]:
        if key in data:
            fields[key] = json.dumps(data[key])

    if fields:
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        conn.execute(f"UPDATE problems SET {set_clause} WHERE id = ?", (*fields.values(), problem_id))
        conn.commit()

    row = conn.execute("SELECT * FROM problems WHERE id = ?", (problem_id,)).fetchone()
    conn.close()
    return jsonify({"problem": problem_to_public_dict(row, include_editorial=True)})


@app.get("/api/problems/<int:problem_id>/testcases")
@require_auth
@require_trainer
def list_testcases(problem_id):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM test_cases WHERE problem_id = ? ORDER BY id", (problem_id,)).fetchall()
    conn.close()
    return jsonify({"test_cases": rows_to_list(rows)})


@app.post("/api/problems/<int:problem_id>/testcases")
@require_auth
@require_trainer
def add_testcase(problem_id):
    data = request.get_json(force=True)
    if "expected_output" not in data:
        return jsonify({"error": "expected_output is required"}), 400

    conn = get_connection()
    problem = conn.execute("SELECT id FROM problems WHERE id = ?", (problem_id,)).fetchone()
    if not problem:
        conn.close()
        return jsonify({"error": "Problem not found"}), 404

    cur = conn.execute(
        """INSERT INTO test_cases (problem_id, input_payload, expected_output, is_sample, time_limit_ms, memory_limit_mb)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            problem_id, data.get("input_payload", ""), data["expected_output"],
            1 if data.get("is_sample") else 0, data.get("time_limit_ms", 2000), data.get("memory_limit_mb", 256),
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM test_cases WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return jsonify({"test_case": row_to_dict(row)}), 201


# --------------------------------------------------------------------------
# Submissions / Judging
# --------------------------------------------------------------------------

def update_progress(conn, user_id, problem_id, solved):
    row = conn.execute(
        "SELECT * FROM user_problem_progress WHERE user_id = ? AND problem_id = ?", (user_id, problem_id)
    ).fetchone()
    now = datetime.datetime.utcnow().isoformat()
    if row:
        new_status = "SOLVED" if (solved or row["best_status"] == "SOLVED") else "ATTEMPTED"
        first_solved = row["first_solved_at"] or (now if solved else None)
        conn.execute(
            """UPDATE user_problem_progress
               SET best_status = ?, attempts_count = attempts_count + 1,
                   first_solved_at = ?, last_attempted_at = ?
               WHERE user_id = ? AND problem_id = ?""",
            (new_status, first_solved, now, user_id, problem_id),
        )
    else:
        conn.execute(
            """INSERT INTO user_problem_progress
               (user_id, problem_id, best_status, attempts_count, first_solved_at, last_attempted_at)
               VALUES (?, ?, ?, 1, ?, ?)""",
            (user_id, problem_id, "SOLVED" if solved else "ATTEMPTED", now if solved else None, now),
        )


@app.post("/api/submissions")
@require_auth
def create_submission():
    data = request.get_json(force=True)
    problem_id = data.get("problem_id")
    language = data.get("language")
    source_code = data.get("source_code", "")
    mode = data.get("mode", "SUBMIT").upper()
    practice_set_id = data.get("practice_set_id")

    if not problem_id or not language or not source_code.strip():
        return jsonify({"error": "problem_id, language, and source_code are required"}), 400
    if language not in LANGUAGE_REGISTRY:
        return jsonify({"error": f"Unsupported language: {language}"}), 400
    if mode not in ("RUN", "SUBMIT"):
        return jsonify({"error": "mode must be RUN or SUBMIT"}), 400

    conn = get_connection()
    problem = conn.execute("SELECT * FROM problems WHERE id = ?", (problem_id,)).fetchone()
    if not problem:
        conn.close()
        return jsonify({"error": "Problem not found"}), 404

    if mode == "RUN":
        test_cases = conn.execute(
            "SELECT * FROM test_cases WHERE problem_id = ? AND is_sample = 1", (problem_id,)
        ).fetchall()
    else:
        test_cases = conn.execute("SELECT * FROM test_cases WHERE problem_id = ?", (problem_id,)).fetchall()

    if not test_cases:
        conn.close()
        return jsonify({"error": "This problem has no test cases configured yet"}), 422

    test_cases = rows_to_list(test_cases)
    status, results, total_runtime = judge_submission(language, source_code, test_cases)

    cur = conn.execute(
        """INSERT INTO submissions
           (user_id, problem_id, practice_set_id, mode, language, source_code, status,
            runtime_ms, results_json, judged_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            g.user["id"], problem_id, practice_set_id, mode, language, source_code, status,
            total_runtime, json.dumps(results), datetime.datetime.utcnow().isoformat(),
        ),
    )

    if mode == "SUBMIT" and g.user["role"] == "STUDENT":
        update_progress(conn, g.user["id"], problem_id, solved=(status == "ACCEPTED"))

    conn.commit()
    submission = conn.execute("SELECT * FROM submissions WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()

    d = row_to_dict(submission)
    d["results"] = json.loads(d.pop("results_json"))
    # Hide hidden test cases' actual output/input from students; sample results already carry excerpts.
    return jsonify({"submission": d}), 201


@app.get("/api/submissions")
@require_auth
def list_submissions():
    problem_id = request.args.get("problem_id")
    conn = get_connection()
    if g.user["role"] == "TRAINER" and request.args.get("all") == "true":
        query = "SELECT * FROM submissions"
        params = ()
    else:
        query = "SELECT * FROM submissions WHERE user_id = ?"
        params = (g.user["id"],)
    if problem_id:
        query += (" AND" if "WHERE" in query else " WHERE") + " problem_id = ?"
        params = params + (problem_id,)
    query += " ORDER BY submitted_at DESC LIMIT 100"
    rows = conn.execute(query, params).fetchall()
    conn.close()

    out = []
    for r in rows:
        d = row_to_dict(r)
        d["results"] = json.loads(d.pop("results_json")) if d.get("results_json") else []
        out.append(d)
    return jsonify({"submissions": out})


# --------------------------------------------------------------------------
# Practice Sets ("Sheets")
# --------------------------------------------------------------------------

@app.post("/api/sheets")
@require_auth
@require_trainer
def create_sheet():
    data = request.get_json(force=True)
    title = data.get("title")
    problem_ids = data.get("problem_ids", [])
    cohort_ids = data.get("cohort_ids", [])
    due_at = data.get("due_at")

    if not title or not problem_ids:
        return jsonify({"error": "title and at least one problem_id are required"}), 400

    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO practice_sets (title, created_by, due_at) VALUES (?, ?, ?)",
        (title, g.user["id"], due_at),
    )
    set_id = cur.lastrowid
    for idx, pid in enumerate(problem_ids):
        conn.execute(
            "INSERT INTO practice_set_problems (set_id, problem_id, order_index) VALUES (?, ?, ?)",
            (set_id, pid, idx),
        )
    for cid in cohort_ids:
        conn.execute("INSERT INTO practice_set_cohorts (set_id, cohort_id) VALUES (?, ?)", (set_id, cid))
    conn.commit()
    conn.close()
    return jsonify({"sheet_id": set_id}), 201


@app.get("/api/sheets")
@require_auth
def list_sheets():
    conn = get_connection()
    if g.user["role"] == "TRAINER":
        rows = conn.execute("SELECT * FROM practice_sets ORDER BY created_at DESC").fetchall()
    else:
        if g.user["cohort_id"]:
            rows = conn.execute(
                """SELECT DISTINCT ps.* FROM practice_sets ps
                   JOIN practice_set_cohorts psc ON psc.set_id = ps.id
                   WHERE psc.cohort_id = ? ORDER BY ps.created_at DESC""",
                (g.user["cohort_id"],),
            ).fetchall()
        else:
            rows = []

    sheets = []
    for r in rows:
        d = row_to_dict(r)
        problems = conn.execute(
            """SELECT p.id, p.slug, p.title, p.difficulty FROM practice_set_problems pp
               JOIN problems p ON p.id = pp.problem_id
               WHERE pp.set_id = ? ORDER BY pp.order_index""",
            (d["id"],),
        ).fetchall()
        d["problems"] = rows_to_list(problems)
        sheets.append(d)
    conn.close()
    return jsonify({"sheets": sheets})


# --------------------------------------------------------------------------
# Cohorts
# --------------------------------------------------------------------------

@app.get("/api/cohorts")
@require_auth
def list_cohorts():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM cohorts ORDER BY name").fetchall()
    conn.close()
    return jsonify({"cohorts": rows_to_list(rows)})


# --------------------------------------------------------------------------
# Analytics
# --------------------------------------------------------------------------

@app.get("/api/analytics/me")
@require_auth
def my_analytics():
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.difficulty, upp.best_status, p.topics
           FROM user_problem_progress upp JOIN problems p ON p.id = upp.problem_id
           WHERE upp.user_id = ?""",
        (g.user["id"],),
    ).fetchall()
    conn.close()

    solved = sum(1 for r in rows if r["best_status"] == "SOLVED")
    attempted = len(rows)
    by_difficulty = {"EASY": 0, "MEDIUM": 0, "HARD": 0}
    topic_counts = {}
    for r in rows:
        if r["best_status"] == "SOLVED":
            by_difficulty[r["difficulty"]] = by_difficulty.get(r["difficulty"], 0) + 1
            for t in json.loads(r["topics"]):
                topic_counts[t] = topic_counts.get(t, 0) + 1

    return jsonify({
        "solved_count": solved,
        "attempted_count": attempted,
        "solved_by_difficulty": by_difficulty,
        "solved_by_topic": topic_counts,
    })


@app.get("/api/analytics/cohort/<int:cohort_id>")
@require_auth
@require_trainer
def cohort_analytics(cohort_id):
    conn = get_connection()
    students = conn.execute("SELECT id, name FROM users WHERE cohort_id = ? AND role = 'STUDENT'", (cohort_id,)).fetchall()
    student_ids = [s["id"] for s in students]

    result = []
    for s in students:
        row = conn.execute(
            "SELECT COUNT(*) as solved FROM user_problem_progress WHERE user_id = ? AND best_status = 'SOLVED'",
            (s["id"],),
        ).fetchone()
        result.append({"student_id": s["id"], "name": s["name"], "solved_count": row["solved"]})

    hardest = conn.execute(
        """SELECT p.title, p.slug, COUNT(*) as fail_count
           FROM submissions sub JOIN problems p ON p.id = sub.problem_id
           WHERE sub.status != 'ACCEPTED' AND sub.mode = 'SUBMIT'
           GROUP BY sub.problem_id ORDER BY fail_count DESC LIMIT 5"""
    ).fetchall()
    conn.close()

    return jsonify({"students": result, "most_failed_problems": rows_to_list(hardest)})


if __name__ == "__main__":
    if not os.path.exists(os.path.join(os.path.dirname(__file__), "dsa_platform.db")):
        init_db()
    app.run(host="0.0.0.0", port=5050, debug=True)
