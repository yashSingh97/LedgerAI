from typing import Dict, Any, List
from datetime import datetime

ALLOWED_CATEGORIES = {
    "groceries", "transport", "eating_out", "entertainment",
    "utilities", "healthcare", "education", "miscellaneous"
}

def validate_insert_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    print(f"[Validation] Validating insert payload: {payload}")

    errors = []
    clean_data = {}

    # -------- Amount (REQUIRED) --------
    amount = payload.get("amount", "MISSING")

    if amount == "MISSING":
        errors.append("Amount is missing.")
    else:
        try:
            clean_amount = float(amount)
            if clean_amount <= 0:
                errors.append("Amount must be greater than zero.")
            else:
                clean_data["amount"] = clean_amount
        except Exception:
            errors.append("Amount must be numeric.")

    # -------- Category (REQUIRED) --------
    category = payload.get("category", "MISSING")

    if category == "MISSING":
        errors.append("Category is missing.")
    elif not isinstance(category, str):
        errors.append("Category is invalid.")
    else:
        category_normalized = category.lower()
        if category_normalized not in ALLOWED_CATEGORIES:
            errors.append(f"Category '{category_normalized}' is not allowed.")
        else:
            clean_data["category"] = category_normalized

    # -------- Description (OPTIONAL) --------
    description = payload.get("description", "unspecified expense")
    clean_data["description"] = str(description)

    # -------- Date (REQUIRED) --------
    date_val = payload.get("date_of_transaction", "MISSING")

    if date_val == "MISSING":
        errors.append("Date of transaction is missing.")
    else:
        if not isinstance(date_val, str):
            errors.append("Date of transaction must be a string.")
        else:
            clean_data["date_of_transaction"] = date_val.strip()


    is_valid = len(errors) == 0

    print(f"[Validation] valid={is_valid}, errors={errors}, clean={clean_data}")

    return {
        "valid": is_valid,
        "errors": errors,
        "clean_data": clean_data
    }

def validate_select_sql(sql: str) -> Dict[str, Any]:
    """
    Validate that a SQL query is a safe SELECT query over the transactions table.

    Returns:
        {
            "valid": bool,
            "errors": List[str],
            "clean_data": str
        }
    """

    print(f"[Validation] Validating SQL: {sql}")

    errors = []

    if not sql or not isinstance(sql, str):
        return {
            "valid": False,
            "errors": ["SQL is missing or not a string."],
            "clean_data": ""
        }

    sql_stripped = sql.strip()
    sql_upper = sql_stripped.upper()

    # Must be SELECT
    if not sql_upper.startswith("SELECT"):
        errors.append("Only SELECT queries are allowed.")

    # Block dangerous keywords
    banned_keywords = ["DROP", "DELETE", "TRUNCATE", "ALTER", "INSERT", "UPDATE"]
    if any(keyword in sql_upper for keyword in banned_keywords):
        errors.append("SQL contains forbidden operations.")

    # No multi-statements
    if ";" in sql_stripped:
        errors.append("Multiple SQL statements are not allowed.")

    # Must reference transactions table
    if "TRANSACTIONS" not in sql_upper:
        errors.append("SQL must reference the 'transactions' table.")

    is_valid = len(errors) == 0

    print(f"[Validation] SQL valid={is_valid}, errors={errors}")

    return {
        "valid": is_valid,
        "errors": errors,
        "clean_data": sql_stripped
    }
