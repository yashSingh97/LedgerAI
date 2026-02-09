from typing import Dict, Any, List
from db.init_client import supabase

def execute_select_query(sql_query: str) -> List[Dict[str, Any]]:
    """
    Executes a SQL SELECT query on Supabase.
    
    Args:
        sql_query: A SQL SELECT query string
        
    Returns:
        List of dictionaries containing query results
        
    Raises:
        RuntimeError: If query execution fails
    """
    print(f"[DB] Executing SQL query: {sql_query}")
    
    try:
        # Use the RPC (Remote Procedure Call) method to execute raw SQL
        result = supabase.rpc('execute_sql', {'query': sql_query}).execute()
        
        if not result.data:
            return []
            
        print(f"[DB] Query returned {len(result.data)} rows")
        return result.data
        
    except Exception as e:
        print(f"[DB] Query execution failed: {e}")
        raise RuntimeError(f"Failed to execute query: {e}")