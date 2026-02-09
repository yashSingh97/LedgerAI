from langgraph.graph import StateGraph, START, END
from core.state import AgentState
from core.planner_agent import planner_agent_node
from core.task_executor import task_executor_node 
from action.response_generator import response_generator_action 
from action.savings_prediction_savings import prediction_savings_action 
from action.add_transaction import add_transaction_action
from action.query_transaction import query_transaction_action 

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("Planner", planner_agent_node)
    graph.add_node("Executor", task_executor_node)

    graph.add_node("AddTransaction", add_transaction_action)
    graph.add_node("QueryTransactions", query_transaction_action)
    graph.add_node("PredictSavings", prediction_savings_action)
    graph.add_node("ResponseGenerator", response_generator_action)

    graph.add_edge(START, "Planner")
    graph.add_edge("Planner", "Executor")

    graph.add_edge("AddTransaction", "Executor")
    graph.add_edge("QueryTransactions", "Executor")
    graph.add_edge("PredictSavings", "Executor")
    graph.add_edge("ResponseGenerator", END)

    graph.add_conditional_edges(
        "Executor",
        lambda state: state["route_to"],
        {
            "AddTransaction": "AddTransaction",
            "QueryTransactions": "QueryTransactions",
            "PredictSavings": "PredictSavings",
            "ResponseGenerator": "ResponseGenerator",
        }
    )

    return graph.compile()