import logging
from langgraph.graph import StateGraph, END
from app.agent.state import AgentState
from app.agent.nodes.ingestion import node_ingest_repository
from app.agent.nodes.elicitation import node_feature_elicitation
from app.agent.nodes.planning import node_comprehensive_planning
from app.agent.nodes.graph_sync import node_graph_sync
from app.agent.nodes.implementation import node_code_implementation

logger = logging.getLogger(__name__)


def should_continue_to_planning(state: AgentState) -> str:
    """Conditional router: checks if human clarification is needed before planning."""
    if state.get("requires_clarification"):
        logger.info("Clarification needed from user before proceeding to planning.")
        return "await_clarification"
    return "planning"


def build_agent_graph():
    """
    Constructs the LangGraph state machine orchestrating Phase 1 through Phase 5.
    """
    workflow = StateGraph(AgentState)

    # Register Nodes
    workflow.add_node("ingestion", node_ingest_repository)
    workflow.add_node("elicitation", node_feature_elicitation)
    workflow.add_node("planning", node_comprehensive_planning)
    workflow.add_node("implementation", node_code_implementation)
    workflow.add_node("graph_sync", node_graph_sync)

    # Workflow entry point
    workflow.set_entry_point("ingestion")

    # Transitions
    workflow.add_edge("ingestion", "elicitation")

    workflow.add_conditional_edges(
        "elicitation",
        should_continue_to_planning,
        {
            "await_clarification": END,
            "planning": "planning",
        },
    )

    workflow.add_edge("planning", END)  # Pauses for user approval of plans before implementation
    workflow.add_edge("implementation", END)

    app = workflow.compile()
    return app


# Compiled LangGraph agent workflow
agent_workflow = build_agent_graph()
