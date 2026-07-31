
import json
import random
import importlib.util

SEED = 42
CASES_PER_PROBLEM = 100

spec = importlib.util.spec_from_file_location("problems_def", "problems_def.py")
problems = importlib.util.module_from_spec(spec)
spec.loader.exec_module(problems)

rng = random.Random(SEED)
bank = problems.make_bank()

def slugify(title):
    return (
        title.lower()
        .replace("&", "and")
        .replace("/", " ")
        .replace("(", "")
        .replace(")", "")
        .replace(",", "")
        .replace("-", " ")
        .split()
    )

def make_slug(title):
    return "-".join(slugify(title))

def serialize_input(args):
    if len(args) == 1:
        return json.dumps(args[0], separators=(",", ":"))
    return json.dumps(list(args), separators=(",", ":"))

out = []

for problem in bank:
    slug = make_slug(problem["title"])
    gen = problem["gen_cases"]
    solve = problem["solve"]

    for i in range(CASES_PER_PROBLEM):
        args = gen(rng)
        if not isinstance(args, tuple):
            args = (args,)
        expected = solve(*args)

        out.append({
            "problem_slug": slug,
            "input": serialize_input(args),
            "expected_output": json.dumps(expected, separators=(",", ":")),
            "is_sample": 1 if i < 3 else 0
        })

with open("test_cases.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)

print(f"Generated {len(out)} test cases.")
