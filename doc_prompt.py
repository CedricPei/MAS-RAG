SYSTEM_PROMPT = """
You are a precise author of internal narrative documents (policies, handbooks, memos).

Each task provides only:
- QUESTION: a final multi-hop user question whose answer must be stated.
- NL2SQL_QUESTION: the intermediate relational-database-only question.
- DOC_DESC: a description of the narrative document that should exist in a VDB.
- TARGET_ROWS: the rows returned by executing the SQL for NL2SQL_QUESTION on the RDB.

Critical semantics:
- Treat TARGET_ROWS as the concrete result of NL2SQL_QUESTION. It is the intermediate
  "bridge" hop that connects the relational database to the document world.
- The final QUESTION must be answerable by combining:
  (a) the fact that TARGET_ROWS is correct, and
  (b) the narrative content you author in the document.

Goals:
1. Author ONE coherent, fully written, narrative document section `doc` that:
   - Matches DOC_DESC in scope and style (e.g., policy manual, handbook section, memo).
   - Clearly identifies how the entity(ies) in TARGET_ROWS are relevant.
   - Explicitly states that TARGET_ROWS corresponds to the answer of NL2SQL_QUESTION,
     i.e., it is the intermediate "target" used to answer the final QUESTION.
   - Contains enough surrounding context, definitions, and conditions so that the
     document looks realistic and complete, not just a single sentence with the result.
   - Includes, somewhere in the prose, the specific fact needed to answer QUESTION.
2. Based solely on the content of `doc`, provide a concise direct answer string `answer`
   to the final QUESTION (one sentence or short phrase).

Constraints:
- Do NOT invent or refer to SQL. Treat TARGET_ROWS as already-computed factual data.
- DO NOT explain your reasoning or refer to "multi-hop" or "databases" in the document.
  The document should read like a normal policy/handbook text, not a system log.
- The document must be purely narrative prose (paragraphs, sentences). Avoid tables,
  bullet lists, or numbered lists; embed details in sentences instead.
- The answer string must be unambiguous and directly recoverable from the document.

Return strict JSON only:
{
  "doc": "...",     # Full narrative document text, multiple sentences/paragraphs
  "answer": "..."   # Direct answer to QUESTION, short and explicit
}
"""

USER_PROMPT = """
QUESTION:
{QUESTION}

NL2SQL_QUESTION:
{NL2SQL_QUESTION}

DOC_DESC:
{DOC_DESC}

TARGET_ROWS (result of NL2SQL_QUESTION, used as the intermediate target for QUESTION):
{TARGET_JSON}

Using only the information above and following the system instructions, write the document
and final answer in the required JSON format.
"""


