from core.state import AgentState
from utils.validation import validate_select_sql
from utils.generate_sql_query import generate_sql_query
from utils.execute_sql_query import execute_select_query


def query_transaction_action(state: AgentState) -> AgentState:
    """
    Query Transactions Action:
    - Uses LLM to generate SQL from natural language
    - Validates SQL
    - Executes SQL
    - Appends result rows
    """

    print("\n===== Query Transactions Action =====")

    current_task = state.get("current_task", {})
    task_payload = current_task.get("entities", {})

    print(f"[QueryTransactions] Current task: {current_task}")

    # 0. Ambiguous query (NON-FATAL)
    if task_payload.get("ambiguous", False) is True:
        error_entry = {
            "type": "error",
            "source": "query_transactions",
            "message": task_payload.get(
                "ambiguity_reason",
                "Your query is ambiguous. Please provide more details."
            ),
            "fatal": False
        }

        return {
            "results": state.get("results", []) + [error_entry],
            "should_continue": True
        }

    natural_language_query = task_payload.get("custom_query", "").strip()
    print(f"[QueryTransactions] User query: {natural_language_query}")

    # 1. Generate SQL via LLM
    sql, llm_error = generate_sql_query(natural_language_query)

    if llm_error:
        return {
            "results": state.get("results", []) + [llm_error],
            "should_continue": True
        }

    print(f"[QueryTransactions] Generated SQL:\n{sql}")

    # 2. Validate SQL (NON-FATAL)
    validation_result = validate_select_sql(sql)
    print(f"[QueryTransactions] SQL validation result: {validation_result}")

    if not validation_result["valid"]:
        error_entry = {
            "type": "error",
            "source": "query_transactions",
            "message": "The generated database query is invalid.",
            "details": validation_result["errors"],
            "fatal": False
        }

        print("[QueryTransactions] SQL validation failed")

        return {
            "results": state.get("results", []) + [error_entry],
            "should_continue": True
        }

    clean_sql = validation_result["clean_data"]

    # 3. Execute SQL (SYSTEM BOUNDARY)
    try:
        rows = execute_select_query(clean_sql)
    except RuntimeError as e:
        error_entry = {
            "type": "error",
            "source": "query_transactions",
            "message": str(e),
            "fatal": False
        }

        print(f"[QueryTransactions] SQL execution failed: {e}")

        return {
            "results": state.get("results", []) + [error_entry],
            "should_continue": True
        }

    print(f"[QueryTransactions] Returned {len(rows)} rows")

    # 4. Build success result entry
    result_entry = {
        "type": "query_transactions",
        "custom_query": natural_language_query,
        "sql": clean_sql,
        "data_fetched_from_database": rows
    }

    print(f"[QueryTransactions] Result entry: {result_entry}")

    return {
        "results": state.get("results", []) + [result_entry],
        "should_continue": True
    }


# from core.state import AgentState
# from utils.validation import validate_select_sql
# from utils.generate_sql_query import generate_sql_query
# from utils.execute_sql_query import execute_select_query

# def query_transaction_action(state: AgentState) -> AgentState:
#     """
#     Query Transactions Action:
#     - Uses LLM to generate SQL from natural language
#     - Validates SQL
#     - Executes SQL
#     - Appends result rows
#     """

#     print("\n===== Query Transactions Action =====")

#     current_task = state.get("current_task", {})
#     task_payload = current_task.get("entities", {})

#     if task_payload.get("ambiguous", False) is True:
#         error_entry = {
#             "type": "query_transactions_error",
#             "errors": [
#                 f"Ambiguous_query: {task_payload.get('ambiguity_reason', 'More details required.')}"
#             ]
#         }

#         return {
#             "results": state.get("results", []) + [error_entry],
#             "should_continue": True
#         }
        
#     natural_language_query = task_payload.get("custom_query", "").strip()

#     print(f"[QueryTransactions] Current task: {current_task}")
#     print(f"[QueryTransactions] User query: {natural_language_query}")

#     # 1. Generate SQL via LLM
#     sql = generate_sql_query(natural_language_query)
#     print(f"[QueryTransactions] Generated SQL:\n{sql}")

#     # 2. Validate SQL
#     validation_result = validate_select_sql(sql)
#     print(f"[QueryTransactions] SQL validation result: {validation_result}")

#     if not validation_result["valid"]:
#         error_entry = {
#             "type": "query_transactions_error",
#             "errors": validation_result["errors"],
#         }

#         print("[QueryTransactions] SQL validation failed")

#         return {
#             "results": state.get("results", []) + [error_entry],
#             "should_continue": True,
#         }

#     clean_sql = validation_result["clean_data"]

#     # 3. Execute SQL
#     rows = execute_select_query(clean_sql)

#     print(f"[QueryTransactions] Returned {len(rows)} rows")

#     # 4. Build result entry
#     result_entry = {
#         "type": "query_transactions",
#         "custom_query": natural_language_query,
#         "sql": clean_sql,
#         "rows": rows,
#     }

#     print(f"[QueryTransactions] Result entry: {result_entry}")

#     updated_results = state.get("results", []) + [result_entry]

#     return {
#         "results": updated_results,
#         "should_continue": True,
#     }
