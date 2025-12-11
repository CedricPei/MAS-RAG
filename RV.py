import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List
import sys

from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

from prompts.prompt_rv import SYSTEM_PROMPT, USER_PROMPT

DB_ROOT = Path("dev_databases")
BASE_OUTPUT_DIR = Path("dataset")
TARGET_DB_IDS = [
    # "california_schools",
    "superhero",
]
TARGET_QUESTION_PER_DB = 5


def escape_braces(text: str) -> str:
    return text.replace("{", "{{").replace("}", "}}")


def load_schema_from_sqlite(db_id: str) -> str:
    db_path = DB_ROOT / db_id / f"{db_id}.sqlite"

    lines: List[str] = []
    conn = sqlite3.connect(db_path.as_posix())
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT name FROM sqlite_master " 
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]
        if not tables:
            raise ValueError(f"No tables found in database '{db_id}'.")

        for table in tables:
            cursor.execute(f"PRAGMA table_info('{table}')")
            columns = cursor.fetchall()
            lines.append(f"TABLE {table}")
            for _, col_name, col_type, _, _, _ in columns:
                display_type = col_type or "TEXT"
                lines.append(f"  - {col_name} {display_type}")
            lines.append("")
    finally:
        conn.close()

    return "\n".join(lines).strip()


def load_column_doc(db_id: str) -> str:
    doc_path = DB_ROOT / db_id / f"{db_id}.json"
    if not doc_path.exists():
        raise FileNotFoundError(f"Missing column description JSON for '{db_id}'.")

    with open(doc_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    return json.dumps(doc, ensure_ascii=False, indent=2)


def main() -> None:
    load_dotenv(override=False)

    client = OpenAI(
        base_url=os.environ["OPENAI_BASE_URL"],
        api_key=os.environ["OPENAI_API_KEY"],
    )
    model_name = "openai/gpt-5"

    BASE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if len(sys.argv) > 1:
        db_ids = [sys.argv[1]]
    else:
        db_ids = TARGET_DB_IDS

    for db_id in db_ids:
        schema_text = load_schema_from_sqlite(db_id)
        column_doc_text = load_column_doc(db_id)

        db_dir = BASE_OUTPUT_DIR / db_id
        db_dir.mkdir(parents=True, exist_ok=True)
        output_path = db_dir / f"rv_{db_id}.json"

        existing: List[Dict[str, Any]] = []
        next_id = 0

        for _ in tqdm(range(TARGET_QUESTION_PER_DB), desc=f"Generating targeted for {db_id}", unit="q"):
            existing_questions_text = "\n".join(
                [r.get("question", "") for r in existing if r.get("question")]
            ) or "(No existing questions yet)"

            user_prompt = USER_PROMPT.format(
                SCHEMA=escape_braces(schema_text),
                COLUMN_DOC=escape_braces(column_doc_text),
                EXISTING_QUESTIONS=escape_braces(existing_questions_text),
            )

            resp = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.4,
                response_format={"type": "json_object"},
            )
            obj = json.loads(resp.choices[0].message.content or "{}")
            record = {
                "id": next_id,
                "db_id": db_id,
                "question": obj.get("question"),
                "nl2sql_question": obj.get("nl2sql_question"),
                "sql_answer": obj.get("sql_answer"),
                "doc_type": "rv",
                "doc_desc": obj.get("doc_desc"),
            }
            next_id += 1
            existing.append(record)
            with output_path.open("w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()

