import json
import os
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

from prompt_targetD_gen import SYSTEM_PROMPT, USER_PROMPT

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

    targeted_records = [r for r in records if r.get("doc_type") == "targeted_rule"]

    for record in tqdm(targeted_records, desc="Generating docs", unit="q"):
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
        content = response.choices[0].message.content or "{}"
        obj = json.loads(content)

        doc_record: Dict[str, Any] = {
            "id": record.get("id"),
            "db_id": record.get("db_id"),
            "question": question,
            "doc": obj.get("doc"),
            "answer": obj.get("answer"),
        }
        docs.append(doc_record)

        with OUTPUT_PATH.open("w", encoding="utf-8") as out_f:
            json.dump(docs, out_f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()


