import csv
import json
import sqlite3
import re

conn = sqlite3.connect("dsa_platform.db")
cursor = conn.cursor()

TRAINER_ID = 1

with open("questions.csv", newline="", encoding="utf-8") as file:
    reader = csv.DictReader(file)

    for row in reader:

        slug = re.sub(r'[^a-z0-9]+', '-', row["title"].lower()).strip("-")

        starter = {
            "python": row["starter_python"],
            "javascript": row["starter_javascript"]
        }

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
            "",
            json.dumps(starter),
            "PUBLISHED",
            TRAINER_ID
        ))

conn.commit()
conn.close()

print("Imported Successfully!")