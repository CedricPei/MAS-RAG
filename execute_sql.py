import json
import sqlite3
from pathlib import Path

from tqdm import tqdm

DB_ROOT = Path("dev_databases")
QUESTIONS_PATH = Path("multi_source_questions.json")
OUTPUT_PATH = Path("multi_source_questions_with_target.json")


def main() -> None:
    with QUESTIONS_PATH.open("r", encoding="utf-8") as f:
        records = json.load(f)

    kept_records = []
    updated_count = 0

    for record in tqdm(records, desc="Executing SQL", unit="q"):
        db_id = record.get("db_id")
        sql = record.get("sql_answer")
        if not db_id or not sql:
            continue

        db_path = DB_ROOT / db_id / f"{db_id}.sqlite"

        try:
            conn = sqlite3.connect(db_path.as_posix())
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            conn.close()
        except Exception:
            continue
        else:
            if rows:
                record["db_instance"] = [dict(row) for row in rows]
                updated_count += 1
                kept_records.append(record)

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(kept_records, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
