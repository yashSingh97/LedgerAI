from core.state import AgentState
from utils.date_resolver import resolve_date_expression
from utils.validation import validate_insert_payload
from utils.insert_data import insert_transaction


def add_transaction_action(state: AgentState) -> AgentState:
    """
    Add Transaction Action:
    - Validates transaction payload
    - Resolves and normalizes date
    - Inserts transaction into database
    - Appends result entry for response generation
    """

    print("\n===== Add Transaction Action =====")

    current_task = state.get("current_task", {})
    task_payload = current_task.get("entities", {})

    print(f"[AddTransaction] Current task: {current_task}")

    # 1. Validate input (NON-FATAL)
    validation_result = validate_insert_payload(task_payload)
    print(f"[AddTransaction] Validation result: {validation_result}")

    if not validation_result["valid"]:
        error_entry = {
            "type": "error",
            "source": "add_transaction",
            "task": {
                "original_task": current_task.get("entities")
            },
            "message": "Failed to validate payload.",
            "details": validation_result["errors"],
            "fatal": False
        }

        print("[AddTransaction] Validation failed")

        return {
            "results": state.get("results", []) + [error_entry],
            "should_continue": True
        }

    # 2. Extract clean payload
    clean_payload = validation_result["clean_data"]
    print(f"[AddTransaction] Clean payload: {clean_payload}")

    # 3. Resolve date (NON-FATAL, external boundary)
    try:
        resolved_date = resolve_date_expression(clean_payload["date_of_transaction"])
        clean_payload["date_of_transaction"] = resolved_date
    except ValueError as e:
        error_entry = {
            "type": "error",
            "source": "add_transaction",
            "task": {
                "original_task": current_task.get("entities")
            },
            "message": "The transaction date could not be understood.",
            "details": [str(e)],
            "fatal": False
        }

        print(f"[AddTransaction] Date resolution failed: {e}")

        return {
            "results": state.get("results", []) + [error_entry],
            "should_continue": True
        }

    # 4. Insert into database (SYSTEM BOUNDARY)
    try:
        insert_result = insert_transaction(clean_payload)
        transaction_id = insert_result.get("transaction_id")
    except Exception as e:
        error_entry = {
            "type": "error",
            "source": "add_transaction",
            "task": {
                "original_task": current_task.get("entities")
            },
            "message": "Failed to save the transaction.",
            "details": [str(e)],
            "fatal": False
        }

        print(f"[AddTransaction] Database insert failed: {e}")

        return {
            "results": state.get("results", []) + [error_entry],
            "should_continue": True
        }

    print(f"[AddTransaction] Inserted transaction_id={transaction_id}")

    # 5. Build success result entry
    result_entry = {
        "type": "add_transaction",
        "status": "success",
        "transaction_id": transaction_id,
        "amount": clean_payload["amount"],
        "category": clean_payload["category"],
        "description": clean_payload["description"],
        "date": clean_payload["date_of_transaction"]
    }

    print(f"[AddTransaction] Result entry: {result_entry}")

    return {
        "results": state.get("results", []) + [result_entry],
        "should_continue": True
    }


# from core.state import AgentState
# from utils.date_resolver import resolve_date_expression
# from utils.validation import validate_insert_payload
# from utils.insert_data import insert_transaction


# def add_transaction_action(state: AgentState) -> AgentState:
#     """
#     Add Transaction Action:
#     - Validates transaction payload
#     - Resolves and normalizes date
#     - Inserts transaction into database
#     - Appends result entry for response generation
#     """

#     print("\n===== Add Transaction Action =====")

#     current_task = state.get("current_task", {})
#     task_payload = current_task.get("entities", {})

#     print(f"[AddTransaction] Current task: {current_task}")

#     # 1. Validate input
#     validation_result = validate_insert_payload(task_payload)
#     print(f"[AddTransaction] Validation result: {validation_result}")

#     if not validation_result["valid"]:
#         error_entry = {
#             "type": "add_transaction_error",
#             "errors": validation_result["errors"]
#         }

#         print("[AddTransaction] Validation failed")

#         return {
#             "results": state.get("results", []) + [error_entry],
#             "should_continue": True
#         }

#     # 2. Extract clean payload
#     clean_payload = validation_result["clean_data"]
#     print(f"[AddTransaction] Clean payload: {clean_payload}")

#     # 3. Resolve date
#     try:
#         resolved_date = resolve_date_expression(clean_payload["date_of_transaction"])
#         clean_payload["date_of_transaction"] = resolved_date
#     except ValueError as e:
#         error_entry = {
#             "type": "add_transaction_error",
#             "errors": [str(e)]
#         }

#         print(f"[AddTransaction] Date resolution failed: {e}")

#         return {
#             "results": state.get("results", []) + [error_entry],
#             "should_continue": True
#         }

#     # 4. Insert into database
#     insert_result = insert_transaction(clean_payload)
#     transaction_id = insert_result["transaction_id"]

#     print(f"[AddTransaction] Inserted transaction_id={transaction_id}")

#     # 5. Build result entry
#     result_entry = {
#         "type": "add_transaction",
#         "transaction_id": transaction_id,
#         "amount": clean_payload["amount"],
#         "category": clean_payload["category"],
#         "description": clean_payload["description"],
#         "date": clean_payload["date_of_transaction"]
#     }

#     print(f"[AddTransaction] Result entry: {result_entry}")

#     updated_results = state.get("results", []) + [result_entry]

#     return {
#         "results": updated_results,
#         "should_continue": True
#     }
