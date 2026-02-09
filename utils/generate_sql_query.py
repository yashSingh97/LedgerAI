import json
from prompts.sql_query_generator import GENERATE_SQL_QUERY_TOOL_PROMPT
from core.llm import llm_call


def generate_sql_query(natural_language_query: str):
    print(f"[SQLGen] User query: {natural_language_query}")

    prompt = f"""
QUERY:
{natural_language_query}

SYSTEM INSTRUCTIONS:
{GENERATE_SQL_QUERY_TOOL_PROMPT}
"""

    llm_output_text, llm_error = llm_call(prompt)

    if llm_error:
        return None, llm_error

    print(f"[SQLGen] Raw LLM Output:\n{llm_output_text}")

    try:
        cleaned_json = (
            llm_output_text
            .strip()
            .removeprefix("```json")
            .removesuffix("```")
            .strip()
        )

        parsed = json.loads(cleaned_json)
        sql = parsed.get("sql")

        if not sql:
            raise ValueError("No SQL found")

        return sql, None

    except Exception as e:
        error_entry = {
            "type": "error",
            "source": "sql_generator",
            "message": f"Couldn't generate a valid database query. Error: {e}",
            "fatal": False
        }

        return None, error_entry


# import json
# from prompts.sql_query_generator import GENERATE_SQL_QUERY_TOOL_PROMPT
# from core.llm import llm_call


# def generate_sql_query(natural_language_query: str) -> str:
#     """
#     Uses LLM to generate a safe SQL SELECT query from natural language.

#     Returns:
#         str: SQL query string
#     """

#     print(f"[SQLGen] User query: {natural_language_query}")

#     prompt = f"""
# QUERY:
# {natural_language_query}

# SYSTEM INSTRUCTIONS:
# {GENERATE_SQL_QUERY_TOOL_PROMPT}
# """

#     llm_output_text = llm_call(prompt)
#     print(f"[SQLGen] Raw LLM Output:\n{llm_output_text}")

#     # LLM failure fallback
#     if not llm_output_text or llm_output_text == "[LLM] I'm sorry, but I couldn't generate a response.":
#         print("[SQLGen] LLM failed, returning safe fallback SQL")
#         return "SELECT * FROM transactions LIMIT 0"

#     try:
#         cleaned_json = (
#             llm_output_text
#             .strip()
#             .removeprefix("```json")
#             .removesuffix("```")
#             .strip()
#         )

#         parsed = json.loads(cleaned_json)
#         sql = parsed.get("sql", "")

#         if not sql:
#             raise ValueError("No SQL found in LLM output")

#         print(f"[SQLGen] Generated SQL:\n{sql}")
#         return sql

#     except Exception as e:
#         print(f"[SQLGen] JSON parsing failed: {e}")
#         return "SELECT * FROM transactions LIMIT 0"
