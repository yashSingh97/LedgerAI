import json
from core.state import AgentState
from prompts.planner import PLANNER_NODE_PROMPT
from core.llm import llm_call


def planner_agent_node(state: AgentState) -> AgentState:
    user_input = state.get("user_input", "")
    short_term_memory = state.get("short_term_memory", [])

    print("\n\n===== Planner Agent Node =====\n")
    print(f"[Planner] User Input: {user_input}")
    print(f"[Planner] Short-Term Memory: {short_term_memory}\n")

    planner_prompt = f"""USER_INPUT: {user_input}
MEMORY CONTEXT: {json.dumps(short_term_memory)}
SYSTEM INSTRUCTIONS: {PLANNER_NODE_PROMPT}"""

    print(f"[Planner] Prompt sent to LLM!!!!!")

    # 🔹 UPDATED: unpack llm_call result
    llm_output_text, llm_error = llm_call(planner_prompt)

    # 🔹 LLM failure → propagate (fatal)
    if llm_error:
        return {
            "results": state.get("results", []) + [llm_error],
            "tasks": [],
            "tasks_count": 0,
            "should_continue": False
        }

    print(f"[Planner] Raw LLM Output: {llm_output_text}")

    # 🔹 JSON parsing is the ONLY try/except in planner
    try:
        clean_json_text = (
            llm_output_text
            .strip()
            .removeprefix("```json")
            .removesuffix("```")
            .strip()
        )

        parsed_output = json.loads(clean_json_text)
        planned_tasks = parsed_output.get("tasks", [])

    except Exception as e:
        print(f"[Planner] JSON parsing failed: {e}")

        error_entry = {
            "type": "error",
            "source": "planner",
            "message": f"Failed to parse JSON: {e}",
            "fatal": True,
        }

        return {
            "results": state.get("results", []) + [error_entry],
            "tasks": [],
            "tasks_count": 0,
            "should_continue": False
        }

    # 🔹 Filter mixed intent responses (unchanged logic)
    operational_types = {"add_transaction", "query_transactions", "predict_savings"}
    response_types = {"respond_to_user_convo", "respond_to_user_unknown"}

    operational_tasks = [t for t in planned_tasks if t.get("type") in operational_types]
    response_tasks = [t for t in planned_tasks if t.get("type") in response_types]

    if operational_tasks and response_tasks:
        print("[Planner] Found both operational and response tasks. Keeping ONLY operational tasks.")
        planned_tasks = operational_tasks

    print(f"[Planner] Final Planned Tasks: {planned_tasks}")
    print(f"[Planner] Incoming State: {state}")

    return {
        "tasks": planned_tasks,
        "tasks_count": len(planned_tasks),
        "should_continue": True
    }



# import json
# from core.state import AgentState
# from prompts.planner import PLANNER_NODE_PROMPT
# from core.llm import llm_call

# def planner_agent_node(state: AgentState) -> AgentState:
#     user_input = state.get("user_input", "")
#     short_term_memory = state.get("short_term_memory", [])

#     print("\n\n===== Planner Agent Node =====\n")
#     print(f"[Planner] User Input: {user_input}")
#     print(f"[Planner] Short-Term Memory: {short_term_memory}\n")

#     planner_prompt = f"""USER_INPUT: {user_input}
# MEMORY CONTEXT: {json.dumps(short_term_memory)}
# SYSTEM INSTRUCTIONS: {PLANNER_NODE_PROMPT}"""

#     print(f"[Planner] Prompt sent to LLM!!!!!")

#     llm_output_text = llm_call(planner_prompt)
#     print(f"[Planner] Raw LLM Output: {llm_output_text}")

#     # LLM failure fallback
#     if not llm_output_text or llm_output_text == "[LLM] I'm sorry, but I couldn't generate a response.":
#         return {"tasks": []}

#     try:
#         clean_json_text = (
#             llm_output_text
#             .strip()
#             .removeprefix("```json")
#             .removesuffix("```")
#             .strip()
#         )

#         parsed_output = json.loads(clean_json_text)
#         planned_tasks = parsed_output.get("tasks", [])

#     except Exception as e:
#         print(f"[Planner] JSON parsing failed: {e}")
#         return {"tasks": []}

#     # Filter mixed intent responses
#     operational_types = {"add_transaction", "query_transactions", "predict_savings"}
#     response_types = {"respond_to_user_convo", "respond_to_user_unknown"}

#     operational_tasks = [t for t in planned_tasks if t.get("type") in operational_types]
#     response_tasks = [t for t in planned_tasks if t.get("type") in response_types]

#     if operational_tasks and response_tasks:
#         print("[Planner] Found both operational and response tasks. Keeping ONLY operational tasks.")
#         planned_tasks = operational_tasks

#     print(f"[Planner] Final Planned Tasks: {planned_tasks}")
#     print(f"[Planner] Incoming State: {state}")

#     return {
#         "tasks": planned_tasks,
#         "tasks_count": len(planned_tasks),
#         "should_continue": True
#     }