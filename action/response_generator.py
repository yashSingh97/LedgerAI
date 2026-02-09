import json
from core.state import AgentState
from core.llm import llm_call
from prompts.responder import (
    NORMAL_CONVERSATION_PROMPT,
    UNKNOWN_PROMPT,
    FINANCIAL_PROMPT
)


def response_generator_action(state: AgentState) -> AgentState:
    """
    Final response generator node:
    - Reads accumulated results
    - Uses LLM to craft a user-facing message
    - Terminates the workflow
    """

    print("\n\n===== Response Generator Node =====\n")

    
    execution_results = state.get("results", [])

    # 0. If a fatal error exists, respond directly (NO LLM)
    for result in execution_results:
        if result.get("type") == "error" and result.get("fatal") is True:
            print("[ResponseGenerator] Fatal error detected. Skipping LLM response.")

            return {
                "final_output": result.get(
                    "message",
                    "A critical error occurred while processing your request."
                ),
                "should_continue": False
            }

    current_task_type = state.get("current_task", {}).get("type")
    user_input = state.get("user_input", "")
    memory_context = state.get("short_term_memory", []) 
    
    # 1. Choose the correct response prompt
    if current_task_type == "respond_to_user_convo":
        response_prompt = f"""USER INPUT: "{user_input}"
RECENT USER CONTEXT: 
{json.dumps(memory_context, indent=2)}

SYSTEM INSTRUCTIONS:
{NORMAL_CONVERSATION_PROMPT}"""

    elif current_task_type == "respond_to_user_unknown":
        response_prompt = f"""USER INPUT: "{user_input}"

SYSTEM INSTRUCTIONS:
{UNKNOWN_PROMPT}"""

    else:
        print(f"[ResponseGenerator] Results to summarize: {execution_results}")

        results_summary_json = json.dumps(execution_results, indent=2)
        print(f"[ResponseGenerator] Results JSON:\n{results_summary_json}")

        response_prompt = f"""USER INPUT: "{user_input}"

RESULTS OF OPERATIONS:
{results_summary_json}

SYSTEM INSTRUCTIONS:
{FINANCIAL_PROMPT}"""

    print("\n[ResponseGenerator] Prompt sent to LLM!!!!\n")

    llm_output_text, llm_error = llm_call(response_prompt)

    # 2. LLM failure fallback
    if llm_error:
        print(f"[ResponseGenerator] LLM failed: {llm_error}")

        return {
            "final_output": f"I ran into an issue while generating the response: {llm_error.get('message', 'Unknown error')}.\n.But the operations were processed. Please ask to fetch recent transactions if necessary.",
            "should_continue": False
        }

    print(f"\n[ResponseGenerator] Final Response: {llm_output_text}")

    # 3. End the workflow
    return {
        "final_output": llm_output_text,
        "should_continue": False
    }


# import json
# from core.state import AgentState
# from core.llm import llm_call
# from prompts.responder import (
#     NORMAL_CONVERSATION_PROMPT,
#     UNKNOWN_PROMPT,
#     FINANCIAL_PROMPT
# )

# def response_generator_action(state: AgentState) -> AgentState:
#     """
#     Final response generator node:
#     - Reads accumulated results
#     - Uses LLM to craft a user-facing message
#     - Terminates the workflow
#     """

#     print("\n\n===== Response Generator Node =====\n")

#     current_task_type = state["current_task"]["type"]
#     user_input = state.get("user_input", "")

#     # Choose the correct response prompt
#     if current_task_type == "respond_to_user_convo":
#         response_prompt = f"""USER INPUT: "{user_input}"
# SYSTEM INSTRUCTIONS:
# {NORMAL_CONVERSATION_PROMPT}"""

#     elif current_task_type == "respond_to_user_unknown":
#         response_prompt = f"""USER INPUT: "{user_input}"
# SYSTEM INSTRUCTIONS:
# {UNKNOWN_PROMPT}"""

#     else:
#         execution_results = state.get("results", [])
#         print(f"[ResponseGenerator] Results to summarize: {execution_results}")

#         results_summary_json = json.dumps(execution_results, indent=2)
#         print(f"[ResponseGenerator] Results JSON:\n{results_summary_json}")

#         response_prompt = f"""USER INPUT: "{user_input}"
# RESULTS OF OPERATIONS:
# {results_summary_json}

# SYSTEM INSTRUCTIONS:
# {FINANCIAL_PROMPT}"""

#     print(f"\n[ResponseGenerator] Prompt sent to LLM!!!!\n")

#     llm_output_text = llm_call(response_prompt)
#     print(f"[ResponseGenerator] Raw LLM Output: {llm_output_text}")

#     # LLM failure fallback
#     if not llm_output_text or llm_output_text == "[LLM] I'm sorry, but I couldn't generate a response.":
#         return {
#             "final_output": "I'm sorry, but I couldn't generate a response.",
#             "should_continue": False
#         }

#     print(f"\n[ResponseGenerator] Final Response: {llm_output_text}")

#     # End the workflow
#     return {
#         "final_output": llm_output_text,
#         "should_continue": False
#     }