import json
import sqlite3
import sys
from pathlib import Path

from tqdm import tqdm

DB_ROOT = Path("dev_databases")
INPUT_BASE = Path("dataset")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python execute_sql.py <db_id>")
        return

    db_id = sys.argv[1]
    input_path = INPUT_BASE / db_id / f"rv_{db_id}.json"
    if not input_path.exists():
        print(f"Input file not found: {input_path}")
        return

    with input_path.open("r", encoding="utf-8") as f:
        records = json.load(f)

    kept = []
    for record in tqdm(records, desc=f"Executing SQL for {db_id}", unit="q"):
        db_id_rec = record.get("db_id") or db_id
        sql = record.get("sql_answer")
        if not db_id_rec or not sql:
            continue

        db_path = DB_ROOT / db_id_rec / f"{db_id_rec}.sqlite"
        try:
            conn = sqlite3.connect(db_path.as_posix())
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            conn.close()
        except Exception:
            continue

        if rows:
            record["db_instance"] = [dict(row) for row in rows]
            kept.append(record)

    output_path = input_path.parent / f"exe_rv_{db_id}.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(kept, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()