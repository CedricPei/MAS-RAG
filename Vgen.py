import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

from prompt_vgen import SYSTEM_PROMPT, USER_PROMPT

INPUT_BASE = Path("dataset")
OUTPUT_BASE = Path("dataset")


def escape_braces(text: str) -> str:
    return text.replace("{", "{{").replace("}", "}}")


def process_db(db_id: str, client: OpenAI, model_name: str) -> None:
    db_dir = INPUT_BASE / db_id
    input_path = db_dir / f"exe_rv_{db_id}.json"
    if not input_path.exists():
        print(f"Input not found: {input_path}")
        return

    with input_path.open("r", encoding="utf-8") as f:
        records: List[Dict[str, Any]] = json.load(f)

    docs: List[Dict[str, Any]] = []
    targeted_records = [r for r in records if r.get("doc_type") == "rv"]
    output_path = db_dir / f"rv_doc_{db_id}.json"

    for record in tqdm(targeted_records, desc=f"Generating docs for {db_id}", unit="q"):
        db_instance = record.get("db_instance")
        question = record.get("question") or ""
        nl2sql_question = record.get("nl2sql_question") or ""
        doc_desc = record.get("doc_desc") or ""

        db_instance_json = json.dumps(db_instance, ensure_ascii=False, indent=2)

        user_prompt = USER_PROMPT.format(
            QUESTION=escape_braces(question),
            NL2SQL_QUESTION=escape_braces(nl2sql_question),
            DOC_DESC=escape_braces(doc_desc),
            DB_INSTANCE_JSON=escape_braces(db_instance_json),
        )

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        obj = json.loads(response.choices[0].message.content or "{}")

        doc_record: Dict[str, Any] = {
            "id": record.get("id"),
            "db_id": record.get("db_id"),
            "question": question,
            "doc": obj.get("doc"),
            "answer": obj.get("answer"),
        }
        docs.append(doc_record)
        with output_path.open("w", encoding="utf-8") as out_f:
            json.dump(docs, out_f, ensure_ascii=False, indent=2)


def main() -> None:
    load_dotenv(override=False)

    client = OpenAI(
        base_url=os.environ["OPENAI_BASE_URL"],
        api_key=os.environ["OPENAI_API_KEY"],
    )
    model_name = "openai/gpt-5"

    if len(sys.argv) > 1:
        process_db(sys.argv[1], client, model_name)
        return

    for db_dir in INPUT_BASE.iterdir():
        if db_dir.is_dir():
            process_db(db_dir.name, client, model_name)


if __name__ == "__main__":
    main()


