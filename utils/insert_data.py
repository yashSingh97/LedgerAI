from typing import Dict, Any 
from db.init_client import supabase

def insert_transaction(expense: Dict[str, Any]) -> Dict[str, int]:
    print(f"[DB] Inserting transaction: {expense}")

    data = {
        "amount": expense["amount"],
        "category": expense["category"],
        "date_of_transaction": expense["date_of_transaction"],
        "description": expense.get("description"),
    }

    result = supabase.table("transactions").insert(data).execute()

    if not result.data:
        raise RuntimeError("Insert into Supabase database failed")

    inserted_row = result.data[0]

    transaction_id = inserted_row.get("id") or inserted_row.get("transaction_id")
    if not transaction_id:
        raise RuntimeError("Insert succeeded but no transaction ID returned")

    print(f"[DB] Inserted transaction_id = {transaction_id}")

    return {"transaction_id": transaction_id}
