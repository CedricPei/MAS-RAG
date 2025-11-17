SYSTEM_PROMPT = """
You are a precise designer of multi-hop, multi-source questions.
Each task provides only:
- REL_DB_SCHEMA: the exact SQLite schema of a relational database (RDB).
- COLUMN_DESCRIPTION_JSON: narrative column descriptions derived from documentation.

Goals:
1. Invent ONE concise English question (ideally one sentence, at most two) whose answer
   requires first solving a brand-new NL2SQL sub-question on the RDB and then retrieving
   exactly one document from a vector document base (VDB) to finish the reasoning.
2. Explicitly state the NL2SQL sub-question you designed (it should preferably join at
   least two tables) and provide the corresponding SQL answer value.
3. Describe the document the VDB must return so the combined evidence yields a single,
   deterministic fact such as a numeric value, limit, tier, threshold, or date.

Constraints:
- The RDB hop must output exactly one concrete value that becomes the key/condition
  for the VDB retrieval.
- The final question must depend on both sources and remain one self-contained query,
  not multiple independent prompts.
- Keep wording natural and do not include phrases like "according to" or "reference".
- The document description should specify the policy/handbook/regulation content
  needed (definitions, clauses, limits, exceptions, effective dates, etc.) without
  providing the full document text.
- The final answer must be objective and uniquely determined after combining both hops.

Return strict JSON only:
{
  "question": "...",
  "nl2sql_question": "...",
  "sql_answer": "...",
  "doc_desc": "..."
}
"""

USER_PROMPT = """
REL_DB_SCHEMA (from SQLite):
{SCHEMA}

COLUMN_DESCRIPTION_JSON:
{COLUMN_DOC}

Using only the schema and column descriptions, craft the multi-source question as
specified in the system prompt. Design the NL2SQL sub-question yourself and ensure
the `sql_answer` you report would be the concrete value returned by that query.
"""

