import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

from prompt_targetQ_gen import SYSTEM_PROMPT as TARGET_SYSTEM_PROMPT, USER_PROMPT as TARGET_USER_PROMPT
from prompt_collectQ_gen import SYSTEM_PROMPT as COLLECTION_SYSTEM_PROMPT, USER_PROMPT as COLLECTION_USER_PROMPT

DB_ROOT = Path("dev_databases")
OUTPUT_PATH = "multi_source_questions.json"
TARGET_DB_IDS = [
    "california_schools",
    # "superhero",
]
TARGET_QUESTION_PER_DB = 5
COLLECTION_QUESTION_PER_DB = 0


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
    model_name = "gpt-5"

    existing: List[Dict[str, Any]] = []
    try:
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            existing = json.load(f)
    except FileNotFoundError:
        existing = []

    next_id = 0
    if existing:
        ids = [int(record.get("id", -1)) for record in existing]
        next_id = max(ids) + 1 if ids else 0

    for db_id in TARGET_DB_IDS:
        schema_text = load_schema_from_sqlite(db_id)
        column_doc_text = load_column_doc(db_id)

        # Targeted questions (generate one by one)
        user_prompt = TARGET_USER_PROMPT.format(
            SCHEMA=escape_braces(schema_text),
            COLUMN_DOC=escape_braces(column_doc_text),
        )
        for _ in tqdm(range(TARGET_QUESTION_PER_DB), desc=f"Generating targeted for {db_id}", unit="q"):
            targeted_resp = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": TARGET_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.8,
                response_format={"type": "json_object"},
            )
            content = targeted_resp.choices[0].message.content or "{}"
            obj = json.loads(content)
            record = {
                "id": next_id,
                "db_id": db_id,
                "question": obj.get("question"),
                "nl2sql_question": obj.get("nl2sql_question"),
                "sql_answer": obj.get("sql_answer"),
                "doc_type": "targeted_rule",
                "doc_desc": obj.get("doc_desc"),
            }
            next_id += 1
            existing.append(record)
            with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)

        collection_prompt = COLLECTION_USER_PROMPT.format(
            SCHEMA=escape_braces(schema_text),
            COLUMN_DOC=escape_braces(column_doc_text),
        )
        for _ in tqdm(range(COLLECTION_QUESTION_PER_DB), desc=f"Generating collection for {db_id}", unit="q"):
            collection_resp = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": COLLECTION_SYSTEM_PROMPT},
                    {"role": "user", "content": collection_prompt},
                ],
                temperature=0.4,
                response_format={"type": "json_object"},
            )
            content = collection_resp.choices[0].message.content or "{}"
            obj = json.loads(content)
            record = {
                "id": next_id,
                "db_id": db_id,
                "question": obj.get("question"),
                "nl2sql_question": obj.get("nl2sql_question"),
                "sql_answer": obj.get("sql_answer"),
                "doc_type": "collection_rule",
                "doc_desc": obj.get("doc_desc"),
            }
            next_id += 1
            existing.append(record)
            with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()

