import json
import os
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

from doc_prompt import SYSTEM_PROMPT, USER_PROMPT

INPUT_PATH = Path("multi_source_questions_with_target.json")
OUTPUT_PATH = Path("multi_source_docs.json")


def escape_braces(text: str) -> str:
    return text.replace("{", "{{").replace("}", "}}")


def main() -> None:
    load_dotenv(override=False)

    client = OpenAI(
        base_url=os.environ["OPENAI_BASE_URL"],
        api_key=os.environ["OPENAI_API_KEY"],
    )
    model_name = "gpt-5"

    with INPUT_PATH.open("r", encoding="utf-8") as f:
        records: List[Dict[str, Any]] = json.load(f)

    docs: List[Dict[str, Any]] = []

    for record in tqdm(records, desc="Generating docs", unit="q"):
        target = record.get("target_object")
        if target is None:
            continue

        question = record.get("question") or ""
        nl2sql_question = record.get("nl2sql_question") or ""
        doc_desc = record.get("doc_desc") or ""

        target_json = json.dumps(target, ensure_ascii=False, indent=2)

        user_prompt = USER_PROMPT.format(
            QUESTION=escape_braces(question),
            NL2SQL_QUESTION=escape_braces(nl2sql_question),
            DOC_DESC=escape_braces(doc_desc),
            TARGET_JSON=escape_braces(target_json),
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
        content = response.choices[0].message.content or "{}"
        obj = json.loads(content)

        doc_record: Dict[str, Any] = {
            "id": record.get("id"),
            "db_id": record.get("db_id"),
            "question": question,
            "nl2sql_question": nl2sql_question,
            "sql_answer": record.get("sql_answer"),
            "doc_type": record.get("doc_type"),
            "doc_desc": doc_desc,
            "target_object": target,
            "doc": obj.get("doc"),
            "answer": obj.get("answer"),
        }
        docs.append(doc_record)

        with OUTPUT_PATH.open("w", encoding="utf-8") as out_f:
            json.dump(docs, out_f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()


