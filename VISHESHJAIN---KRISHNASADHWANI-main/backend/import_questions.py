import csv
import json
import sqlite3
import re

conn = sqlite3.connect("dsa_platform.db")
cursor = conn.cursor()

TRAINER_ID = 1
PROBLEMS_CSV = "problems_v2.csv"
TEST_CASES_JSON = "test_cases.json"

# NOTE: this script relies on schema.sql already having created the real
# test_cases table (problem_id, input_payload, expected_output, is_sample,
# time_limit_ms, memory_limit_mb, ...). It must NOT redefine that table here
# with a different shape -- a stray CREATE TABLE IF NOT EXISTS using an
# "input" column instead of "input_payload" used to live here and made every
# INSERT below fail with "table test_cases has no column named input".


def slugify(title):
    return re.sub(r'[^a-z0-9]+', '-', title.lower()).strip("-")


# ---------------------------------------------------------------------------
# 1. Import problems, remembering slug -> new row id
# ---------------------------------------------------------------------------
slug_to_id = {}

with open(PROBLEMS_CSV, newline="", encoding="utf-8") as file:
    reader = csv.DictReader(file)

    for row in reader:
        slug = slugify(row["title"])

        starter = {
            "python": row["starter_python"],
            "javascript": row["starter_javascript"],
        }

        cursor.execute("SELECT id FROM problems WHERE slug = ?", (slug,))
        existing = cursor.fetchone()

        if existing:
            problem_id = existing[0]
            cursor.execute("""
            UPDATE problems SET
                title = ?, source = ?, difficulty = ?, topics = ?, company_tags = ?,
                statement_md = ?, constraints_md = ?, starter_code = ?, status = ?
            WHERE id = ?
            """,
            (
                row["title"],
                "INTERNAL",
                row["difficulty"],
                json.dumps([row["topic"]]),
                json.dumps([]),
                row["statement"],
                row.get("constraints", ""),
                json.dumps(starter),
                "PUBLISHED",
                problem_id,
            ))
        else:
            cursor.execute("""
            INSERT INTO problems
            (
                slug,
                title,
                source,
                difficulty,
                topics,
                company_tags,
                statement_md,
                constraints_md,
                starter_code,
                status,
                created_by
            )
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                slug,
                row["title"],
                "INTERNAL",
                row["difficulty"],
                json.dumps([row["topic"]]),
                json.dumps([]),
                row["statement"],
                row.get("constraints", ""),
                json.dumps(starter),
                "PUBLISHED",
                TRAINER_ID,
            ))
            problem_id = cursor.lastrowid

        slug_to_id[slug] = problem_id

conn.commit()
print(f"Imported {len(slug_to_id)} problems.")

# ---------------------------------------------------------------------------
# 2. Import test cases, linked to the problem ids from step 1
# ---------------------------------------------------------------------------
imported_cases = 0
skipped = 0

with open(TEST_CASES_JSON, encoding="utf-8") as f:
    test_cases = json.load(f)

# Wipe old test cases for these problems first so reruns don't duplicate them.
for problem_id in slug_to_id.values():
    cursor.execute("DELETE FROM test_cases WHERE problem_id = ?", (problem_id,))

for tc in test_cases:
    problem_id = slug_to_id.get(tc["problem_slug"])
    if problem_id is None:
        skipped += 1
        continue

    cursor.execute("""
    INSERT INTO test_cases (problem_id, input_payload, expected_output, is_sample)
    VALUES (?, ?, ?, ?)
    """,
    (
        problem_id,
        tc["input"],
        tc["expected_output"],
        tc["is_sample"],
    ))
    imported_cases += 1

conn.commit()
conn.close()

print(f"Imported {imported_cases} test cases.")
if skipped:
    print(f"Skipped {skipped} test cases with no matching problem (slug mismatch).")

print("Imported Successfully!")