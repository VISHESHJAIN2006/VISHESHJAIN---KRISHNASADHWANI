"""Seeds the database with a trainer, a student, a cohort, and a few sample
problems (LeetCode-sourced, as this platform would ingest them per the
architecture doc's ingestion pipeline -- here hand-entered as a stand-in
for that pipeline since no live data source is configured)."""
import json
from werkzeug.security import generate_password_hash
from db import init_db, get_connection

PY_STARTER = {
    "two-sum": (
        "import sys\n\n"
        "def solve(input_text: str) -> str:\n"
        "    lines = input_text.strip().split('\\n')\n"
        "    nums = list(map(int, lines[0].split()))\n"
        "    target = int(lines[1])\n"
        "    # TODO: return '<i> <j>' (0-indexed, i < j) such that nums[i] + nums[j] == target\n"
        "    return ''\n\n"
        "if __name__ == '__main__':\n"
        "    print(solve(sys.stdin.read()))\n"
    ),
    "reverse-integer": (
        "import sys\n\n"
        "def solve(input_text: str) -> str:\n"
        "    x = int(input_text.strip())\n"
        "    # TODO: reverse the digits of x (32-bit signed overflow -> return '0')\n"
        "    return ''\n\n"
        "if __name__ == '__main__':\n"
        "    print(solve(sys.stdin.read()))\n"
    ),
    "maximum-subarray": (
        "import sys\n\n"
        "def solve(input_text: str) -> str:\n"
        "    nums = list(map(int, input_text.strip().split()))\n"
        "    # TODO: return the largest sum of a contiguous subarray, as a string\n"
        "    return ''\n\n"
        "if __name__ == '__main__':\n"
        "    print(solve(sys.stdin.read()))\n"
    ),
}

JS_STARTER = {
    "two-sum": (
        "function solve(inputText) {\n"
        "  const lines = inputText.trim().split('\\n');\n"
        "  const nums = lines[0].trim().split(/\\s+/).map(Number);\n"
        "  const target = parseInt(lines[1], 10);\n"
        "  // TODO: return '<i> <j>' (0-indexed, i < j) such that nums[i] + nums[j] === target\n"
        "  return '';\n"
        "}\n\n"
        "const chunks = [];\n"
        "process.stdin.on('data', d => chunks.push(d));\n"
        "process.stdin.on('end', () => console.log(solve(chunks.join(''))));\n"
    ),
    "reverse-integer": (
        "function solve(inputText) {\n"
        "  const x = parseInt(inputText.trim(), 10);\n"
        "  // TODO: reverse the digits of x (32-bit signed overflow -> return '0')\n"
        "  return '';\n"
        "}\n\n"
        "const chunks = [];\n"
        "process.stdin.on('data', d => chunks.push(d));\n"
        "process.stdin.on('end', () => console.log(solve(chunks.join(''))));\n"
    ),
    "maximum-subarray": (
        "function solve(inputText) {\n"
        "  const nums = inputText.trim().split(/\\s+/).map(Number);\n"
        "  // TODO: return the largest sum of a contiguous subarray, as a string\n"
        "  return '';\n"
        "}\n\n"
        "const chunks = [];\n"
        "process.stdin.on('data', d => chunks.push(d));\n"
        "process.stdin.on('end', () => console.log(solve(chunks.join(''))));\n"
    ),
}

PROBLEMS = [
    {
        "slug": "two-sum",
        "title": "Two Sum",
        "source": "LEETCODE",
        "external_ref_id": "1",
        "difficulty": "EASY",
        "topics": ["array", "hash-table"],
        "company_tags": ["Amazon", "Google", "Microsoft"],
        "statement_md": (
            "Given an array of integers `nums` and an integer `target`, return the "
            "indices of the two numbers such that they add up to `target`.\n\n"
            "Assume exactly one valid answer exists, and each input has only one solution "
            "(you may not use the same element twice).\n\n"
            "**Input format**\n```\n<space-separated nums>\n<target>\n```\n"
            "**Output format**: two 0-indexed indices `i j` (i < j), space-separated."
        ),
        "constraints_md": "2 <= nums.length <= 1000\n-10^9 <= nums[i] <= 10^9",
        "test_cases": [
            {"input_payload": "2 7 11 15\n9", "expected_output": "0 1", "is_sample": True},
            {"input_payload": "3 2 4\n6", "expected_output": "1 2", "is_sample": True},
            {"input_payload": "3 3\n6", "expected_output": "0 1", "is_sample": False},
            {"input_payload": "-1 -2 -3 -4 -5\n-8", "expected_output": "2 4", "is_sample": False},
            {"input_payload": "1 5 3 9 7\n16", "expected_output": "3 4", "is_sample": False},
        ],
    },
    {
        "slug": "reverse-integer",
        "title": "Reverse Integer",
        "source": "LEETCODE",
        "external_ref_id": "7",
        "difficulty": "MEDIUM",
        "topics": ["math"],
        "company_tags": ["Apple", "Bloomberg"],
        "statement_md": (
            "Given a signed 32-bit integer `x`, return `x` with its digits reversed. "
            "If reversing causes the value to go outside the signed 32-bit integer range "
            "`[-2^31, 2^31 - 1]`, return `0`.\n\n"
            "**Input format**: a single integer.\n**Output format**: the reversed integer."
        ),
        "constraints_md": "-2^31 <= x <= 2^31 - 1",
        "test_cases": [
            {"input_payload": "123", "expected_output": "321", "is_sample": True},
            {"input_payload": "-123", "expected_output": "-321", "is_sample": True},
            {"input_payload": "120", "expected_output": "21", "is_sample": False},
            {"input_payload": "0", "expected_output": "0", "is_sample": False},
            {"input_payload": "1534236469", "expected_output": "0", "is_sample": False},
        ],
    },
    {
        "slug": "maximum-subarray",
        "title": "Maximum Subarray",
        "source": "LEETCODE",
        "external_ref_id": "53",
        "difficulty": "MEDIUM",
        "topics": ["array", "dynamic-programming", "divide-and-conquer"],
        "company_tags": ["Microsoft", "LinkedIn"],
        "statement_md": (
            "Given an integer array `nums`, find the contiguous subarray (containing at "
            "least one number) which has the largest sum, and return that sum.\n\n"
            "**Input format**: space-separated integers.\n**Output format**: a single integer (the max sum)."
        ),
        "constraints_md": "1 <= nums.length <= 10^5\n-10^4 <= nums[i] <= 10^4",
        "test_cases": [
            {"input_payload": "-2 1 -3 4 -1 2 1 -5 4", "expected_output": "6", "is_sample": True},
            {"input_payload": "1", "expected_output": "1", "is_sample": True},
            {"input_payload": "5 4 -1 7 8", "expected_output": "23", "is_sample": False},
            {"input_payload": "-1 -2 -3", "expected_output": "-1", "is_sample": False},
        ],
    },
]


def run():
    init_db(reset=True)
    conn = get_connection()

    cur = conn.execute("INSERT INTO cohorts (name) VALUES (?)", ("CSE Batch 2027",))
    cohort_id = cur.lastrowid

    trainer_pw = generate_password_hash("trainer123")
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash, role, cohort_id) VALUES (?, ?, ?, 'TRAINER', ?)",
        ("Priya Sharma", "trainer@college.edu", trainer_pw, cohort_id),
    )
    trainer_id = cur.lastrowid

    student_pw = generate_password_hash("student123")
    conn.execute(
        "INSERT INTO users (name, email, password_hash, role, cohort_id) VALUES (?, ?, ?, 'STUDENT', ?)",
        ("Rahul Verma", "student@college.edu", student_pw, cohort_id),
    )

    problem_ids = {}
    for p in PROBLEMS:
        starter_code = {"python": PY_STARTER[p["slug"]], "javascript": JS_STARTER[p["slug"]]}
        cur = conn.execute(
            """INSERT INTO problems
               (slug, title, source, external_ref_id, difficulty, topics, company_tags,
                statement_md, constraints_md, starter_code, status, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PUBLISHED', ?)""",
            (
                p["slug"], p["title"], p["source"], p["external_ref_id"], p["difficulty"],
                json.dumps(p["topics"]), json.dumps(p["company_tags"]), p["statement_md"],
                p["constraints_md"], json.dumps(starter_code), trainer_id,
            ),
        )
        pid = cur.lastrowid
        problem_ids[p["slug"]] = pid
        for tc in p["test_cases"]:
            conn.execute(
                """INSERT INTO test_cases (problem_id, input_payload, expected_output, is_sample)
                   VALUES (?, ?, ?, ?)""",
                (pid, tc["input_payload"], tc["expected_output"], 1 if tc["is_sample"] else 0),
            )

    cur = conn.execute(
        "INSERT INTO practice_sets (title, created_by, due_at) VALUES (?, ?, ?)",
        ("Week 1: Arrays Warm-up", trainer_id, None),
    )
    set_id = cur.lastrowid
    for idx, slug in enumerate(["two-sum", "maximum-subarray"]):
        conn.execute(
            "INSERT INTO practice_set_problems (set_id, problem_id, order_index) VALUES (?, ?, ?)",
            (set_id, problem_ids[slug], idx),
        )
    conn.execute("INSERT INTO practice_set_cohorts (set_id, cohort_id) VALUES (?, ?)", (set_id, cohort_id))

    conn.commit()
    conn.close()
    print("Seeded database:")
    print("  Trainer login: trainer@college.edu / trainer123")
    print("  Student login: student@college.edu / student123")


if __name__ == "__main__":
    run()
