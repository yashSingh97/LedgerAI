from typing import TypedDict, List, Dict, Optional, Any

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
