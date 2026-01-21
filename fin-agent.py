import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import json
import pickle 
from google import genai
from typing import TypedDict, List, Dict, Optional, Any
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
import pandas as pd 

from nodePrompts import INTERPRETER_NODE_PROMPT, RESPONDER_AGENT_PROMPT, RESPONDER_AGENT_CONVO_PROMPT, RESPONDER_AGENT_UNKNOWN_PROMPT, GENERATE_SQL_QUERY_TOOL_PROMPT

# AGENT STATE
class AgentState(TypedDict, total=False):
    user_name: str
    user_input: str
    long_term_memory: List[Dict[str, str]]
    short_term_memory: List[Dict[str, str]]
    today_date_context: str
    tasks: List[Dict[str, Any]]
    tasks_count: Optional[int]
    current_task: Dict[str, Any]
    results: List[Dict[str, Any]]
    route_to: Optional[str]
    final_output: Optional[str]
    should_continue: bool
    

client = genai.Client(api_key="AIzaSyCUZfxUadBkzkgPHZBzIk4-12EcZOTpHv0")

# DATABASE INITIALIZATION
DB_PATH = "finance.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            date_of_transaction TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()
    print("Database initialized (transactions table ready).")


# TOOLS
@tool
def validation_tool(validation_type: str, payload: dict) -> dict:
    """
    Validate input for insert or query operations.
    
    Arguments:
        validation_type (str): "insert" or "query".
        payload (dict): Contains fields to validate.
    
    Returns:
        dict: {
            "valid": bool,
            "errors": list of strings,
            "clean_data": dict (validated data)
        }
    """
    print(f"[Validation Tool] Input received: type={validation_type}, payload={payload}")

    errors = []
    clean_data = {}
    
    allowed_categories = {
        "groceries", "transport", "eating_out", "entertainment",
        "utilities", "healthcare", "education", "miscellaneous"
    }


    # -------- INSERT VALIDATION ----------
    if validation_type == "insert":
        amount = payload.get("amount")
        category = payload.get("category")
        description = payload.get("description", "")
        date_val = payload.get("date_of_transaction")

        # amount
        try:
            clean_amount = float(amount)
            if clean_amount <= 0:
                errors.append("Amount must be greater than zero.")
            else:
                clean_data["amount"] = clean_amount
        except:
            errors.append("Amount must be numeric.")

        # category
        if not isinstance(category, str):
            errors.append("Category is missing or invalid.")
        else:
            c = category.lower()
            if c not in allowed_categories:
                errors.append(f"Category '{c}' is not allowed.")
            clean_data["category"] = c
        
        # description
        clean_data["description"] = str(description)

        # date — allow NULL; caller will convert NULL → today
        if date_val in [None, "", "NULL"]:
            clean_data["date_of_transaction"] = "NULL"
        else:
            clean_data["date_of_transaction"] = str(date_val)

    # QUERY VALIDATION
    elif validation_type == "query":
        sql = payload.get("sql", "")
        if not sql or not isinstance(sql, str):
            return {"valid": False, "errors": ["SQL is missing"], "clean_data": ""}

        sql_upper = sql.upper()

        # Make sure it's a SELECT statement
        if not sql_upper.startswith("SELECT"):
            errors.append("Only SELECT queries are allowed.")

        # Ban harmful keywords
        banned = ["DROP", "DELETE", "TRUNCATE", "ALTER", "INSERT", "UPDATE"]
        if any(b in sql_upper for b in banned):
            errors.append("SQL contains harmful operations.")

        # Must not contain semicolons
        if ";" in sql:
            errors.append("Multiple SQL statements detected.")

        # ensure transaction table only
        if "TRANSACTIONS" not in sql_upper:
            errors.append("SQL must reference the 'transactions' table only.")

        clean_data = sql.strip()

    else:
        return {
            "valid": False,
            "errors": [f"Unknown validation type: {validation_type}"],
            "clean_data": {}
        }

    valid = len(errors) == 0

    print(f"[Validation Tool] FINAL RESULT → valid={valid}, errors={errors}, clean_data={clean_data}")

    return {
        "valid": valid,
        "errors": errors,
        "clean_data": clean_data
    }

@tool
def insert_expense_tool(expense: dict) -> dict:
    """
    Insert a validated expense record into SQLite database.
    
    Arguments:
        expense (dict): Must contain keys:
            amount, category, description, date_of_transaction
    
    Returns:
        dict: {"transaction_id": int}
    """
    print(f"[Insert Expense Tool] Inserting expense: {expense}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO transactions (amount, category, description, date_of_transaction)
        VALUES (?, ?, ?, ?)
    """, (
        expense["amount"],
        expense["category"],
        expense["description"],
        expense["date_of_transaction"]
    ))

    conn.commit()
    transaction_id = cursor.lastrowid
    conn.close()

    print(f"[Insert Expense Tool] Inserted transaction_id={transaction_id}")

    return {"transaction_id": transaction_id}

@tool
def generate_sql_query_tool(query: str) -> dict:
    """
    Generate a safe SQL query based on validated query details.

    Input:
        query: query str

    Returns:
        dict: {"sql": "..."}
    """
    print(f"[Generate SQL Tool] Input details: {query}")

    # messages = [
    #     SystemMessage(content=GENERATE_SQL_QUERY_TOOL_PROMPT),
    #     HumanMessage(content=query)
    # ]
    message = f"""QUERY: {query}
    SYSTEM INSTRUCTIONS: {GENERATE_SQL_QUERY_TOOL_PROMPT}"""

    print(f"[Generate SQL Tool] Message Passed to Tool : {message}")
    
    try:
        llm_response = client.models.generate_content(model="gemini-2.5-flash", contents=message)
        print(f"[Generate SQL Tool] Raw LLM Output: {llm_response.text}")
    except Exception as e:
        print(f"[Generate SQL Tool] LLM invocation failed: {e}")
        return {"tasks": []}

    print(f"\n\n[Generate SQL Tool] LLM output: {llm_response.text}")

    # Parse JSON (removing code blocks)    
    try:
        cleaned = llm_response.text.strip().removeprefix('```json').removesuffix('```').strip()
        parsed = json.loads(cleaned)
        sql = parsed.get("sql", "")
    except Exception as e:
        print(f"[GenerateSQLTool] JSON parsing failed: {e}")
        sql = "SELECT * FROM transactions LIMIT 0"

    return {"sql": sql}

@tool
def execute_sql_query_tool(sql: str) -> dict:
    """
    Execute a validated SQL query and return results as a list of dicts.
    """
    print(f"\n[Execute SQL Tool] Executing SQL: {sql}\n")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(sql)
    rows = cursor.fetchall()

    conn.close()

    # Convert tuples → dictionaries
    results = [dict(zip([c[0] for c in cursor.description], row)) for row in rows]

    print(f"[Execute SQL Tool] Returned {len(results)} rows")
    print(f"[Execute SQL Tool] Returned rows: {results}")

    return {"rows": results}


# NODES 

def interpreter_node(state: AgentState) -> AgentState:
    user_input = state.get("user_input", "")
    short_term_memory = state.get("short_term_memory", [])
    today_date_data = state.get("today_date_context", {})

    print("\n\n===== Interpreter Node =====\n")
    print(f"[Interpreter] User Input: {user_input}")
    print(f"[Interpreter] State's ST-Memory: {short_term_memory}\n")

    # messages = [
    #     SystemMessage(content=INTERPRETER_NODE_PROMPT.replace("__TODAY_DATE_DATA__", json.dumps(today_date_data))),
    #     f"MEMORY CONTEXT: {json.dumps(short_term_memory)}",
    #     HumanMessage(content="USER_INPUT: " + user_input),
    # ]
    
    message = f"""USER_INPUT: {user_input}

MEMORY CONTEXT: {json.dumps(short_term_memory)}

SYSTEM INSTRUCTIONS: {INTERPRETER_NODE_PROMPT.replace("__TODAY_DATE_DATA__", json.dumps(today_date_data))}"""
    
    print(f"[Interpreter] Message passed to LLM: {message}\n")
    
    # Call LLM
    try:
        llm_response = client.models.generate_content(model="gemini-2.5-flash", contents=message)
        # llm_response = llm.invoke(messages)
        print(f"[Interpreter] Raw LLM Output: {llm_response.text}")
    except Exception as e:
        print(f"[Interpreter] LLM invocation failed: {e}")
        return {"tasks": []}

    # Parse JSON (removing code blocks)
    try:
        cleaned = llm_response.text.strip().removeprefix('```json').removesuffix('```').strip()
        parsed = json.loads(cleaned)
        tasks = parsed.get("tasks", [])
    except Exception as e:
        print(f"[Interpreter] JSON parsing failed: {e}")
        return {"tasks": []}

    
    has_question_mark = "?" in user_input.lower()
    
    QUERY_TRIGGER_WORDS = [ "list", "show", "display", "summary", "breakdown", "details" ]
    has_trigger_word = False

    for word in QUERY_TRIGGER_WORDS:
        if word in user_input.lower():
            has_trigger_word = True
            break
        
        
    filtered_tasks = []

    for task in tasks:
        task_type = task.get("type")

        if task_type == "query_transactions":

            # Case 1: Question mark exists → allow query
            if has_question_mark:
                filtered_tasks.append(task)
                continue

            # Case 3: No '?' but trigger words exist → allow query
            if not has_question_mark and has_trigger_word:
                filtered_tasks.append(task)
                continue

            # Case 2: No '?' and no trigger words → REMOVE query
            print("[Interpreter] Removing query_transactions task (no '?' and no trigger words).")
            continue

        # All non-query tasks always allowed
        filtered_tasks.append(task)

    tasks = filtered_tasks
            
    op_types = {"add_transaction", "query_transactions", "predict_savings"}
    respond_types = {"respond_to_user_convo", "respond_to_user_unknown"}

    op_tasks = [t for t in tasks if t.get("type") in op_types]
    respond_tasks = [t for t in tasks if t.get("type") in respond_types]
    if op_tasks and respond_tasks:
        print("[Interpreter] Found both operational and respond tasks. Keeping ONLY operational tasks.")
        tasks = op_tasks
        
        
    print(f"[Interpreter] Parsed Tasks: {tasks}")
    print(f"[Interpreter] Old State: {state}")
    
    return {
        "tasks": tasks,
        "tasks_count": len(tasks),
        "should_continue": True
    }


def orchestrator_node(state: AgentState) -> AgentState:
    """
    Deterministic workflow controller.
    - Reads state["tasks"]
    - Appends responder task at the end
    - Pops next task
    - Chooses correct agent via state["route_to"]
    - Returns updated AgentState
    """

    print("\n\n===== Orchestrator Node =====\n")
    tasks = state.get("tasks", [])
    tasks_count = state.get("tasks_count", [])
    print(f"[Orchestrator] Loaded tasks: {tasks}")

    if tasks_count == 1: 
        t = tasks[0]
        if t["type"] in ["respond_to_user_convo", "respond_to_user_unknown"]:
            print(f"[Orchestrator] Direct responder routing: {t['type']} \n {t}")
            return {
                "route_to": "Responder Agent",
                "current_task": t,
                "tasks": [],
                "should_continue": True
            }
            
    
    # Always ensure responder task is appended LAST
    if tasks[-1].get("type") != "respond_to_user":
        tasks.append({"type": "respond_to_user", "entities": {}})
        print("[Orchestrator] Appended responder task.")
    
    # Pop next task
    next_task = tasks.pop(0)
    print(f"[Orchestrator] Next Task: {next_task}")
    print(f"[Orchestrator] Remaining Task List: {tasks}")
    
    # Route based on task type
    task_type = next_task.get("type")
    route_map = {
        "add_transaction": "Data Entry Agent",
        "query_transactions": "Data Query Agent",
        "predict_savings": "Prediction Agent",
        "respond_to_user_convo": "Responder Agent",
        "respond_to_user_unknown": "Responder Agent",
    }

    route_to = route_map.get(task_type, "Responder Agent")

    print(f"[Orchestrator] Routing to: {route_to}")

    return {
        "tasks": tasks,
        "current_task": next_task,
        "route_to": route_to,
        "should_continue": True
    }

WEEKDAY_ALIASES = {
    "MON": "MON",
    "MONDAY": "MON",

    "TUE": "TUE",
    "TUESDAY": "TUE",

    "WED": "WED",
    "WEDNESDAY": "WED",

    "THU": "THU",
    "THURSDAY": "THU",

    "FRI": "FRI",
    "FRIDAY": "FRI",

    "SAT": "SAT",
    "SATURDAY": "SAT",

    "SUN": "SUN",
    "SUNDAY": "SUN",
}


WEEKDAY_INDEX = {
    "MON": 0,
    "TUE": 1,
    "WED": 2,
    "THU": 3,
    "FRI": 4,
    "SAT": 5,
    "SUN": 6,
}

def resolve_date_expression(date_expression: Optional[str]) -> str:
    """
    Resolves a controlled date_expression token into an ISO-8601 date (YYYY-MM-DD).

    Allowed date_expression values:
    - NULL or None
    - TODAY | YESTERDAY | TOMORROW
    - LAST_MON ... LAST_SUN
    - NEXT_MON ... NEXT_SUN
    - ISO date string YYYY-MM-DD (ONLY if user explicitly provided it)

    Returns:
        str: Resolved date in YYYY-MM-DD format

    Raises:
        ValueError if an unsupported token is provided.
    """

    today = datetime.now().date()

    # 1️⃣ No date provided → default to today
    if date_expression in (None, "", "NULL"):
        return today.isoformat()

    # 2️⃣ Explicit ISO date → pass through
    if isinstance(date_expression, str):
        try:
            datetime.strptime(date_expression, "%Y-%m-%d")
            return date_expression
        except ValueError:
            pass  # Not ISO, continue

    token = date_expression.upper().strip()

    if token == "LAST_WEEK":
        return (today - timedelta(days=7)).isoformat()
    
    # 3️⃣ Simple relative days
    if token == "TODAY":
        return today.isoformat()

    if token == "YESTERDAY":
        return (today - timedelta(days=1)).isoformat()

    if token == "TOMORROW":
        return (today + timedelta(days=1)).isoformat()

    # 4️⃣ Relative weekday tokens: LAST_XXX / NEXT_XXX
    if "_" in token:
        direction, day = token.split("_", 1)
        
        day = WEEKDAY_ALIASES.get(day)

        if direction not in ("LAST", "NEXT"):
            raise ValueError(f"Invalid date_expression direction: {direction}")

        if day not in WEEKDAY_INDEX:
            raise ValueError(f"Invalid weekday in date_expression: {day}")

        target_weekday = WEEKDAY_INDEX[day]
        today_weekday = today.weekday()

        if direction == "LAST":
            # Go back to the previous occurrence
            delta_days = (today_weekday - target_weekday) % 7 or 7
            return (today - timedelta(days=delta_days)).isoformat()

        if direction == "NEXT":
            # Go forward to the next occurrence
            delta_days = (target_weekday - today_weekday) % 7 or 7
            return (today + timedelta(days=delta_days)).isoformat()

    # 5️⃣ Anything else is invalid
    raise ValueError(f"Unrecognized date_expression: {date_expression}")



def data_entry_agent_node(state: AgentState) -> AgentState:
    """
    Data Entry Agent:
    - Validates transaction data
    - Inserts into DB
    - Updates memory
    - Appends results
    """

    print("\n\n===== Data Entry Agent Node =====\n")

    current_task = state.get("current_task", {})
    entities = current_task.get("entities", {})

    print(f"[Data Entry Agent] Current task: {current_task}\n")

    # VALIDATE INPUT
    validation_result = validation_tool.invoke({
        "validation_type": "insert",
        "payload": entities
    })

    print(f"[Data Entry Agent] Validation result: {validation_result}\n")

    if not validation_result["valid"]:
        # Return validation error so responder can handle it
        error_entry = {
            "type": "add_transaction_error",
            "errors": validation_result["errors"]
        }
        print("[Data Entry Agent] Validation failed.\n")
        return {
            "results": state.get("results", []) + [error_entry],
            "should_continue": True
        }

    # Clean validated data
    clean = validation_result["clean_data"]

    print(f"[Data Entry Agent] Clean validated data: {clean}\n")
    
    # DATE FALLBACK FIX
    date_val = clean.get("date_of_transaction")

    if date_val in ["YYYY-MM-DD", "XXXX-XX-XX", "NULL", "", None]:
        today = datetime.now().strftime("%Y-%m-%d")
        clean["date_of_transaction"] = today
        print(f"[Data Entry Agent] Date invalid or missing. Using today's date: {today}")
        
    try:
        resolved_date = resolve_date_expression(date_val)
    except ValueError as e:
        error_entry = {
            "type": "add_transaction_error",
            "errors": [str(e)]
        }
        return {
            "results": state.get("results", []) + [error_entry],
            "should_continue": True
        }

    clean["date_of_transaction"] = resolved_date
    
    # INSERT INTO DATABASE
    insert_result = insert_expense_tool.invoke({"expense": clean})
    transaction_id = insert_result["transaction_id"]

    print(f"[Data Entry Agent] Insert result: {insert_result}")

    # ADD RESULT TO results[]
    result_entry = {
        "type": "add_transaction",
        "transaction_id": transaction_id,
        "amount": clean["amount"],
        "category": clean["category"],
        "description": clean["description"],
        "date": clean["date_of_transaction"]
    }

    print(f"[Data Entry Agent] Result entry: {result_entry}")

    updated_results = state.get("results", []) + [result_entry]

    return {
        "results": updated_results,
        "should_continue": True
    }



def data_query_agent_node(state: AgentState) -> AgentState:
    """
    Data Query Agent:
    - Validates query parameters
    - Generates SQL via tool (LLM)
    - Executes SQL via tool
    - Updates memory
    - Appends results for responder
    """

    print("\n\n===== Data Query Agent Node =====\n")

    current_task = state.get("current_task", {})
    entities = current_task.get("entities", {})
    final_query = entities.get("finalQuery", "").strip()

    print(f"[Data Query Agent] Current task: {current_task}")
    print(f"[Data Query Agent] Final isolated query: {final_query}")

    # GENERATE SQL
    sql_result = generate_sql_query_tool.invoke({"query": final_query})
    sql = sql_result.get("sql", "")

    print(f"[Data Query Agent] SQL from TOOL: {sql}")
    
    # VALIDATE INPUT
    validation_result = validation_tool.invoke({
        "validation_type": "query",
        "payload": {"sql": sql}
    })

    print(f"[Data Query Agent] Validation result: {validation_result}")

    if not validation_result["valid"]:
        error_entry = {
            "type": "query_transactions_error",
            "errors": validation_result["errors"]
        }
        print("[Data Query Agent] Validation failed.")
        updated_results = state.get("results", []) + [error_entry]

        return {
            "results": updated_results,
            "should_continue": True
        }

    clean = validation_result["clean_data"]

    print(f"[Data Query Agent] Clean validated query: {clean}")

    # EXECUTE SQL
    sql_exec_result = execute_sql_query_tool.invoke({"sql": clean})
    rows = sql_exec_result.get("rows", [])

    print(f"[Data Query Agent] SQL Execution Result: {rows}")

    # ADD RESULT TO results[]
    result_entry = {
        "type": "query_transactions",
        "finalQuery": final_query,
        "sql": clean,
        "rows": rows
    }

    updated_results = state.get("results", []) + [result_entry]

    print(f"[Data Query Agent] Result entry: {result_entry}")

    return {
        "results": updated_results,
        "should_continue": True
    }




DEFAULT_PREDICTIONS = {
    "groceries": 10000,
    "transport": 20000,
    "eating_out": 15000,
    "entertainment": 12000,
    "utilities": 8000,
    "healthcare": 9000,
    "education": 11000,
    "miscellaneous": 5000,
}

def prediction_agent_node(state: AgentState) -> AgentState:
    """
    Prediction Agent:
    - Reads categories requested by user
    - Loads RF model and fetches transaction data from SQLite
    - Computes ML-based next-month savings predictions
    - Updates memory
    - Appends results for responder
    """
    print("\n===== Prediction Agent Node =====")
    current_task = state.get("current_task", {})
    entities = current_task.get("entities", {})
    print(f"[Prediction Agent] Current task: {current_task}")
    
    categories_requested = entities.get("categories")
    
    # All available categories
    all_categories = [
        "groceries", "transport", "eating_out", "entertainment",
        "utilities", "healthcare", "education", "miscellaneous"
    ]
    
    # Normalize categories list
    if categories_requested == "all":
        categories = all_categories
    else:
        categories = [
            c.lower() for c in categories_requested
            if c.lower() in all_categories
        ]
    
    print(f"[Prediction Agent] Final category list: {categories}")
    
    # Load the RF model
    try:
        with open('model.pkl', 'rb') as file:
            model_package = pickle.load(file)
            rf_model = model_package['model']
            metadata = model_package['metadata']
        print("[Prediction Agent] Model loaded successfully")
    except Exception as e:
        print(f"[Prediction Agent] Error loading model: {e}")
        return {
            "results": state.get("results", []) + [{
                "type": "predict_savings",
                "error": "Failed to load prediction model"
            }],
            "should_continue": True
        }
    
    # Fetch category-wise spending from SQLite
    try:
        conn = sqlite3.connect('finance.db')
        cursor = conn.cursor()
        
        # Query to get category-wise total spending
        query = """
            SELECT 
                category,
                SUM(amount) as total_spending
            FROM transactions
            GROUP BY category
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()
        
        # Create spending dictionary with proper capitalization for model
        spending_data = {}
        category_map = {
            "groceries": "Groceries",
            "transport": "Transport",
            "eating_out": "Eating_Out",
            "entertainment": "Entertainment",
            "utilities": "Utilities",
            "healthcare": "Healthcare",
            "education": "Education",
            "miscellaneous": "Miscellaneous"
        }
        
        # Initialize all categories with 0
        for cat in all_categories:
            spending_data[category_map[cat]] = 0.0
        
        # Fill in actual spending data
        for row in results:
            category_lower = row[0].lower()
            if category_lower in category_map:
                spending_data[category_map[category_lower]] = float(row[1])
        
        print(f"[Prediction Agent] Spending data: {spending_data}")
        
    except Exception as e:
        print(f"[Prediction Agent] Error fetching transaction data: {e}")
        spending_data = {
            "Groceries": 0.0, "Transport": 0.0, "Eating_Out": 0.0,
            "Entertainment": 0.0, "Utilities": 0.0, "Healthcare": 0.0,
            "Education": 0.0, "Miscellaneous": 0.0
        }
    
    # Set default values for other features
    default_features = {
        'Income': 20000.0,
        'Age': 30.0,
        'Dependents': 1.0,
        'Rent': 20000.0,
        'Loan_Repayment': 5000.0,
        'Insurance': 2000.0,
        'Desired_Savings_Percentage': 20.0,
        'Desired_Savings': 10000.0,
        'Disposable_Income': 33000.0,
        'Savings_Rate': 20.0,
        'Occupation_Professional': True,
        'Occupation_Retired': False,
        'Occupation_Self Employed': False,
        'Occupation_Student': False,
        'Occupation_Unknown': False,
        'City_Tier_TIER_1': True,
        'City_Tier_TIER_2': False,
        'City_Tier_TIER_3': False,
        'City_Tier_UNKNOWN': False
    }
    
    # Merge spending data with defaults
    input_features = {**default_features, **spending_data}
    
    # Create DataFrame with correct feature order
    feature_names = metadata['feature_names']
    input_df = pd.DataFrame([input_features], columns=feature_names)
    
    print(f"[Prediction Agent] Input features shape: {input_df.shape}")
    
    # Make predictions
    try:
        predictions_array = rf_model.predict(input_df)[0]
        target_names = metadata['target_names']
        
        # Map all predictions from model
        all_predictions = {}
        prediction_map = {
            "groceries": "Potential_Savings_Groceries",
            "transport": "Potential_Savings_Transport",
            "eating_out": "Potential_Savings_Eating_Out",
            "entertainment": "Potential_Savings_Entertainment",
            "utilities": "Potential_Savings_Utilities",
            "healthcare": "Potential_Savings_Healthcare",
            "education": "Potential_Savings_Education",
            "miscellaneous": "Potential_Savings_Miscellaneous"
        }
        
        # Extract ALL predictions from model
        for cat, target_name in prediction_map.items():
            if target_name in target_names:
                idx = target_names.index(target_name)
                all_predictions[cat] = round(float(predictions_array[idx]), 2)
        
        # Filter to only requested categories
        category_predictions = {
            cat: all_predictions[cat] 
            for cat in categories 
            if cat in all_predictions
        }
        
        print(f"[Prediction Agent] All predictions: {all_predictions}")
        print(f"[Prediction Agent] Filtered predictions for requested categories: {category_predictions}")
        
    except Exception as e:
        print(f"[Prediction Agent] Error making predictions: {e}")
        category_predictions = {cat: 0.0 for cat in categories}
    
    # Add result for responder
    result_entry = {
        "type": "predict_savings",
        "categories": categories,
        "predictions": category_predictions,
        "type_of_data": "this is prediction done for SAVINGS for NEXT MONTH, not how much user NEED"
    }
    updated_results = state.get("results", []) + [result_entry]
    print(f"[Prediction Agent] Result entry: {result_entry}")
    
    return {
        "results": updated_results,
        "should_continue": True
    }

def responder_agent_node(state: AgentState) -> AgentState:
    """
    Final responder agent:
    - Reads accumulated results
    - Uses responder_llm to craft a user-friendly message
    - Ends the workflow
    """

    print("\n\n===== Responder Agent Node =====\n")

    task_type = state["current_task"]["type"]
    user_input = state.get('user_input', "")
    if task_type == "respond_to_user_convo":
        message = f""""USER INPUT: "{user_input}
        SYSTEM INTRUCTIONS: {RESPONDER_AGENT_CONVO_PROMPT}"""
        
    elif task_type == "respond_to_user_unknown":
        message = f""""USER INPUT: "{user_input}
        SYSTEM INTRUCTIONS: {RESPONDER_AGENT_UNKNOWN_PROMPT}"""
    else: 
        results = state.get("results", [])
        print(f"[Responder Agent] Results to summarize: {results}")
    
        summary_text = json.dumps(results, indent=2)
        print(f"[Responder Agent] SUMMARY TEXT: {summary_text}")
    
        message = f""""USER INPUT: "{user_input}
        "RESULTS of the OPERATIONS BY AGENTS: "{summary_text}
        SYSTEM INTRUCTIONS: {RESPONDER_AGENT_PROMPT}"""

    print(f"\n[Responder Agent] Message Passed to Tool : {message}")
    
    try:
        llm_response = client.models.generate_content(model="gemini-2.5-flash", contents=message)
        final_output = llm_response.text
        print(f"[Responder Agent] Raw LLM Output: {llm_response.text}")
    except Exception as e:
        print(f"[Responder Agent] LLM error: {e}")
        final_output = "I'm sorry, but I couldn't generate a response."

    print(f"\n\n[Responder Agent] Final Response: {final_output}")
    
    
    # Return final state — end graph execution
    return {
        "final_output": final_output,
        "should_continue": False
    }


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("Interpreter", interpreter_node)
    graph.add_node("Orchestrator", orchestrator_node)
    graph.add_node("Data Entry Agent", data_entry_agent_node)
    graph.add_node("Data Query Agent", data_query_agent_node)
    graph.add_node("Prediction Agent", prediction_agent_node)
    graph.add_node("Responder Agent", responder_agent_node)

    graph.add_edge(START, "Interpreter")
    graph.add_edge("Interpreter", "Orchestrator")
    graph.add_edge("Data Entry Agent", "Orchestrator")
    graph.add_edge("Data Query Agent", "Orchestrator")
    graph.add_edge("Prediction Agent", "Orchestrator")
    graph.add_edge("Responder Agent", END)

    graph.add_conditional_edges(
        "Orchestrator",
        lambda state: state["route_to"],
        {
            "Data Entry Agent": "Data Entry Agent",
            "Data Query Agent": "Data Query Agent",
            "Prediction Agent": "Prediction Agent",
            "Responder Agent": "Responder Agent"
        }
    )

    app = graph.compile()
    return app


# ==== STREAMLIT UI INTEGRATION (SIMPLE) ====

# Initialize only once
if 'app' not in st.session_state:
    init_db()
    st.session_state.app = build_graph()
    print("[Streamlit] Agent initialized.")

# Set up session state for chat
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'agent_state' not in st.session_state:
    toT = datetime.now().strftime("%Y-%m-%d")
    st.session_state.agent_state = {
        "user_name": "User",
        "user_input": "",
        "long_term_memory": [],
        "short_term_memory": [],
        "today_date_context": toT,
        "tasks": [],
        "tasks_count": 0,
        "current_task": None,
        "results": [],
        "route_to": None,
        "final_output": "",
        "should_continue": True
    }

# Simple Streamlit UI
st.title("🤖 Finance AI Assistant")
st.write("Ask about expenses, add transactions, or get predictions")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Type your message..."):
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Prepare agent state
    state = st.session_state.agent_state
    state["user_input"] = prompt
    
    # Update memory
    state["long_term_memory"].append({"role": "human", "content": prompt})
    stm = state["short_term_memory"]
    stm.append({"role": "human", "content": prompt})
    state["short_term_memory"] = stm[-10:]
    
    # Run agent with spinner
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            final_state = st.session_state.app.invoke(state)
            response = final_state.get("final_output", "No response generated.")
            st.markdown(response)
    
    # Update chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
    
    # Update memory for next turn
    state["long_term_memory"].append({"role": "ai", "content": response})
    stm = state["short_term_memory"]
    stm.append({"role": "ai", "content": response})
    
    # Reset state for next interaction
    st.session_state.agent_state = {
        "user_name": state["user_name"],
        "user_input": "",
        "long_term_memory": state["long_term_memory"],
        "short_term_memory": state["short_term_memory"],
        "today_date_context": state["today_date_context"],
        "tasks": [],
        "tasks_count": 0,
        "current_task": None,
        "results": [],
        "route_to": None,
        "final_output": "",
        "should_continue": True
    }

# Optional: Add a sidebar for quick actions
with st.sidebar:
    st.header("Quick Actions")
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()
    
    # Show some stats
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM transactions")
    count = cursor.fetchone()[0]
    st.metric("Total Transactions", count)
    conn.close()