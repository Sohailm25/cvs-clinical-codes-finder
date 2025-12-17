# ABOUTME: LangGraph definition for the Clinical Codes Finder agent.
# ABOUTME: Defines the state machine with Plan-Execute-Reflect-Consolidate pattern.

from langgraph.graph import StateGraph, END

from src.agent.state import AgentState, create_initial_state
from src.agent.nodes.classify import classify_node
from src.agent.nodes.plan import plan_node
from src.agent.nodes.execute import execute_node
from src.agent.nodes.reflect import reflect_node, should_refine
from src.agent.nodes.consolidate import consolidate_node
from src.agent.nodes.summarize import summarize_node


def build_graph() -> StateGraph:
    """
    Build the Clinical Codes Finder agent graph.

    Flow:
    classify -> plan -> execute -> reflect -> [refine: plan | consolidate] -> summarize -> END
    """
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("classify", classify_node)
    graph.add_node("plan", plan_node)
    graph.add_node("execute", execute_node)
    graph.add_node("reflect", reflect_node)
    graph.add_node("consolidate", consolidate_node)
    graph.add_node("summarize", summarize_node)

    # Add edges
    graph.add_edge("classify", "plan")
    graph.add_edge("plan", "execute")
    graph.add_edge("execute", "reflect")

    # Conditional edge: reflect decides if we refine or consolidate
    graph.add_conditional_edges(
        "reflect",
        should_refine,
        {
            "refine": "plan",
            "consolidate": "consolidate",
        },
    )

    graph.add_edge("consolidate", "summarize")
    graph.add_edge("summarize", END)

    # Set entry point
    graph.set_entry_point("classify")

    return graph


def compile_graph():
    """Compile the graph for execution."""
    graph = build_graph()
    return graph.compile()


async def run_agent(query: str) -> AgentState:
    """
    Run the Clinical Codes Finder agent on a query.

    Args:
        query: Clinical term to search for

    Returns:
        Final agent state with results and summary
    """
    app = compile_graph()
    initial_state = create_initial_state(query)

    result = await app.ainvoke(initial_state)

    return result
