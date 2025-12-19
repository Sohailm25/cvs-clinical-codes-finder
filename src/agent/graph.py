# ABOUTME: LangGraph definition for the Clinical Codes Finder agent.
# ABOUTME: Defines the state machine with Plan-Execute-Reflect-Consolidate pattern.

import time
import uuid
from typing import AsyncGenerator, Any

from langgraph.graph import StateGraph, END

from src.agent.state import AgentState, create_initial_state
from src.agent.nodes.classify import classify_node
from src.agent.nodes.plan import plan_node
from src.agent.nodes.execute import execute_node
from src.agent.nodes.reflect import reflect_node, should_refine
from src.agent.nodes.consolidate import consolidate_node
from src.agent.nodes.summarize import summarize_node
from src.agent.multi_hop import multi_hop_node
from src.config import config


def should_multi_hop(state: AgentState) -> str:
    """Determine if multi-hop expansion should run."""
    if state.get("multi_hop_enabled", False):
        return "multi_hop"
    return "execute"


def build_graph() -> StateGraph:
    """
    Build the Clinical Codes Finder agent graph.

    Flow:
    classify -> plan -> [multi_hop if enabled] -> execute -> reflect -> [refine: plan | consolidate] -> summarize -> END
    """
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("classify", classify_node)
    graph.add_node("plan", plan_node)
    graph.add_node("multi_hop", multi_hop_node)
    graph.add_node("execute", execute_node)
    graph.add_node("reflect", reflect_node)
    graph.add_node("consolidate", consolidate_node)
    graph.add_node("summarize", summarize_node)

    # Add edges
    graph.add_edge("classify", "plan")

    # Conditional: plan -> multi_hop (if enabled) or -> execute
    graph.add_conditional_edges(
        "plan",
        should_multi_hop,
        {
            "multi_hop": "multi_hop",
            "execute": "execute",
        },
    )

    # multi_hop always leads to execute
    graph.add_edge("multi_hop", "execute")
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


def compile_graph(checkpointer: Any = None):
    """
    Compile the graph for execution.

    Args:
        checkpointer: Optional checkpointer for state persistence.
                      If None and CHECKPOINT_ENABLED, uses MemorySaver.
    """
    graph = build_graph()
    return graph.compile(checkpointer=checkpointer)


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


async def run_agent_streaming(
    query: str,
    *,
    multi_hop_enabled: bool = False,
    user_clarification: str | None = None,
    thread_id: str | None = None,
    checkpointer: Any = None,
) -> AsyncGenerator[dict, None]:
    """
    Run the Clinical Codes Finder agent with streaming updates.

    Yields events as each node completes, enabling real-time UI updates.

    Args:
        query: Clinical term to search for
        multi_hop_enabled: Whether to expand searches with clinical relationships
        user_clarification: User's chosen intent to override ambiguity
        thread_id: Optional thread ID for checkpointing (generated if not provided)
        checkpointer: Optional checkpointer for state persistence

    Yields:
        dict with keys:
            - node: Name of the node that just completed
            - state: Updated state from that node
            - timestamp: Unix timestamp of the event
            - thread_id: The thread ID used for this run
    """
    app = compile_graph(checkpointer=checkpointer)
    initial_state = create_initial_state(
        query,
        multi_hop_enabled=multi_hop_enabled,
    )

    # Apply user clarification if provided
    if user_clarification:
        initial_state["user_clarification"] = user_clarification

    # Generate thread_id if checkpointing is enabled
    effective_thread_id = thread_id or str(uuid.uuid4())

    # Build config with thread_id for checkpointing
    run_config = {"configurable": {"thread_id": effective_thread_id}}

    async for event in app.astream(initial_state, config=run_config, stream_mode="updates"):
        for node_name, state_update in event.items():
            yield {
                "node": node_name,
                "state": state_update,
                "timestamp": time.time(),
                "thread_id": effective_thread_id,
            }


async def resume_agent_streaming(
    thread_id: str,
    checkpointer: Any,
    updated_state: dict | None = None,
) -> AsyncGenerator[dict, None]:
    """
    Resume an interrupted agent run from a checkpoint.

    Args:
        thread_id: The thread ID of the interrupted run
        checkpointer: The checkpointer with saved state
        updated_state: Optional state updates to apply before resuming

    Yields:
        Streaming updates as the agent continues execution.
    """
    app = compile_graph(checkpointer=checkpointer)

    run_config = {"configurable": {"thread_id": thread_id}}

    # If state updates provided, get current state and merge
    if updated_state:
        current_state = await app.aget_state(run_config)
        if current_state and current_state.values:
            merged_state = {**current_state.values, **updated_state}
            await app.aupdate_state(run_config, merged_state)

    # Resume from checkpoint
    async for event in app.astream(None, config=run_config, stream_mode="updates"):
        for node_name, state_update in event.items():
            yield {
                "node": node_name,
                "state": state_update,
                "timestamp": time.time(),
                "thread_id": thread_id,
            }
