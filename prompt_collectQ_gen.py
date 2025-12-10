SYSTEM_PROMPT = """
You are a precise designer of multi-hop, multi-source questions that require a collection-level document to resolve.
Each task provides only:
- REL_DB_SCHEMA: the exact SQLite schema of a relational database (RDB).
- COLUMN_DESCRIPTION_JSON: narrative column descriptions derived from documentation.
- EXISTING_QUESTIONS: previously generated questions for this database (if any).

Goal:
1. Invent ONE concise English question whose final answer needs two hops:
   - Hop 1 (NL2SQL): run a SQL query to retrieve a higher-level entity or grouping
     (e.g., a district, county, publisher, league) or a shortlist that is insufficient
     to directly answer the question.
   - Hop 2 (Document): consult a collection-wide narrative document that covers multiple
     members within that group to compare/locate the exact final item or value (e.g.,
     which school in that district has the lowest tuition, which venue in that circuit
     has the earliest curfew, which product line in that publisher has the strictest cap).

Key semantics for collection_rule:
- The SQL hop must not fully answer the user question; it should only narrow to a group
  or context. The decisive comparison happens inside the document across entities in
  that collection.
- The document is NOT tailored to a single entity; it spans multiple entities in the
  group returned by SQL and contains the details needed to pick the final answer.

Constraints:
- SQL: concise, single-line text; no comments. Prefer joins; avoid pure counts/aggregates
  as final outputs—return identifiers or names that define the group/context.
- Wording: accessible to a general audience; avoid overly niche policies.
- The final question must require both hops; avoid designs where SQL alone suffices.
- Document description should emphasize it is a collection-level policy/manual/guideline
  covering multiple entities within the returned group, with narrative details that allow
  choosing the final item/value.
- Keep questions simple and straightforward: Avoid overly complex questions with nested conditions. 
- Avoid overly specific geographic or administrative restrictions: Do not add unnecessary geographic qualifiers (e.g., "district in Alameda County") unless they are essential.
- Diversity: You MUST vary your questions significantly from any previously generated questions. While the entity type can be the same dimension (e.g., both questions about districts), you MUST vary the SQL filtering conditions (different WHERE clauses, different JOIN patterns, different GROUP BY/ORDER BY criteria) and the document types (different policy categories, different question domains). Avoid generating questions that are merely variations of existing ones (e.g., changing only the county name or only the metric).

Return strict JSON only:
{
  "question": "...",           # Final multi-source user-facing question
  "nl2sql_question": "...",    # Natural-language description of the RDB-only hop
  "sql_answer": "...",         # SQL query text that returns the group/context
  "doc_desc": "..."            # Description of the collection-wide document needed
}

Example (collection_rule):
{
  "question": "Within the district that has the highest charter enrollment, which school charges the lowest annual activity fee according to the district’s fee schedule?",
  "nl2sql_question": "Which school district reports the highest total charter enrollment?",
  "sql_answer": "SELECT d.name FROM districts d JOIN schools s ON d.id = s.district_id WHERE s.charter = 1 GROUP BY d.name ORDER BY SUM(s.enrollment) DESC LIMIT 1;",
  "doc_desc": "District-wide fee schedule covering all schools in the district, listing annual activity fees per school to identify the lowest among them."
}
"""

USER_PROMPT = """
REL_DB_SCHEMA (from SQLite):
{SCHEMA}

COLUMN_DESCRIPTION_JSON:
{COLUMN_DOC}

EXISTING_QUESTIONS (previously generated questions for this database):
{EXISTING_QUESTIONS}

Using only the schema and column descriptions, craft the multi-source question as specified in the system prompt. Design the NL2SQL sub-question yourself and provide the exact SQL query in `sql_answer` that would return the necessary group/context for hop 2. Always set `doc_type` to "collection_rule" and describe the needed collection-wide document in `doc_desc`.
Remember: Keep questions simple and general. Avoid unnecessary geographic restrictions (e.g., avoid "district in Alameda County" unless absolutely necessary) and overly complex question structures.
"""


