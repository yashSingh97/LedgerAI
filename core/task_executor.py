from core.state import AgentState

def task_executor_node(state: AgentState) -> AgentState:
    """
    Deterministic workflow controller.
    - Reads planned tasks from state["tasks"]
    - Ensures a final response task exists
    - Pops the next task to execute
    - Chooses the correct handler via state["route_to"]
    """

    print("\n\n===== Task Executor Node =====\n")

    # 🔹 NEW: stop immediately if a fatal error already exists
    for result in state.get("results", []):
        if result.get("type") == "error" and result.get("fatal") is True:
            print("[Executor] Fatal error detected. Routing directly to ResponseGenerator.")

            return {
                "route_to": "ResponseGenerator",
                "should_continue": True
            }

    pending_tasks = state.get("tasks", [])
    total_task_count = state.get("tasks_count", 0)

    print(f"[Executor] Loaded pending tasks: {pending_tasks}")

    # Special case: only one task and it is already a response task
    if total_task_count == 1:
        single_task = pending_tasks[0]

        if single_task["type"] in ["respond_to_user_convo", "respond_to_user_unknown"]:
            print(f"[Executor] Direct routing to ResponseGenerator for task type: {single_task['type']}")
            print(f"[Executor] Task: {single_task}")

            return {
                "route_to": "ResponseGenerator",
                "current_task": single_task,
                "tasks": [],
                "should_continue": True
            }

    # Always ensure a final responder task exists at the end
    if pending_tasks and pending_tasks[-1].get("type") != "respond_to_user":
        pending_tasks.append({"type": "respond_to_user", "entities": {}})
        print("[Executor] Appended final respond_to_user task.")

    # Pop the next task to execute
    next_task_to_execute = pending_tasks.pop(0)

    print(f"[Executor] Next task to execute: {next_task_to_execute}")
    print(f"[Executor] Remaining task queue: {pending_tasks}")

    # Decide routing based on task type
    task_type = next_task_to_execute.get("type")

    routing_table = {
        "add_transaction": "AddTransaction",
        "query_transactions": "QueryTransactions",
        "predict_savings": "PredictSavings",
        "respond_to_user_convo": "ResponseGenerator",
        "respond_to_user_unknown": "ResponseGenerator",
        "respond_to_user": "ResponseGenerator"
    }

    target_node = routing_table.get(task_type, "ResponseGenerator")

    print(f"[Executor] Routing to node: {target_node}")

    return {
        "tasks": pending_tasks,
        "current_task": next_task_to_execute,
        "route_to": target_node,
        "should_continue": True
    }
