import logging
from typing import List
from app.agent.state import AgentState
from app.agent.prompts import SYSTEM_ARCHITECT_PROMPT, PHASE4_CYPHER_PROMPT
from app.core.model_router import model_router
from app.core.memgraph_client import memgraph_client

logger = logging.getLogger(__name__)


def node_graph_sync(state: AgentState) -> AgentState:
    """
    Phase 4: Knowledge Graph Management (Memgraph)
    - Generates Cypher queries mapping new components, files, services, and edges.
    - Executes Cypher MERGE/MATCH statements in Memgraph.
    - Produces a 1-paragraph short context summary of the live project state.
    """
    feature = state.get("feature_description", "")
    plan = "\n".join(state.get("work_plan", []))
    files_created = list(state.get("implementation_code", {}).keys())

    user_prompt = f"""
Existing Repository State:
- Repo Name: {state.get('repo_name')}
- Current Summary: {state.get('repo_summary')}

Implemented Feature:
"{feature}"

Planned/Generated Components and Files:
{', '.join(files_created) if files_created else 'Component based on plan: ' + plan[:100]}

Generate valid Cypher MERGE queries for Memgraph to register these new components and relationships (e.g. DEPENDS_ON, CALLS).
"""

    cypher_text = model_router.generate(
        task_type="cypher",
        system_prompt=f"{SYSTEM_ARCHITECT_PROMPT}\n{PHASE4_CYPHER_PROMPT}",
        user_prompt=user_prompt,
    )

    # Clean Cypher statements
    queries: List[str] = []
    for chunk in cypher_text.split(";"):
        clean_q = chunk.strip()
        if "```cypher" in clean_q:
            clean_q = clean_q.split("```cypher")[1]
        if "```" in clean_q:
            clean_q = clean_q.replace("```", "")
        clean_q = clean_q.strip()
        if clean_q and ("MERGE" in clean_q or "MATCH" in clean_q or "CREATE" in clean_q):
            queries.append(clean_q + ";")

    # If no valid cypher was parsed from LLM, generate deterministic fallback
    if not queries:
        safe_name = "".join(c for c in feature if c.isalnum() or c in "_ ")[:25].strip().replace(" ", "_") or "NewFeature"
        queries = [
            f"MERGE (c:Component {{name: '{safe_name}Component', type: 'feature'}});",
            f"MERGE (s:Service {{name: '{safe_name}Service'}});",
            f"MATCH (c:Component {{name: '{safe_name}Component'}}), (s:Service {{name: '{safe_name}Service'}})\n"
            f"MERGE (c)-[:DEPENDS_ON]->(s);",
        ]

    # Execute queries in Memgraph
    try:
        memgraph_client.execute_batch(queries)
        logger.info(f"Successfully executed {len(queries)} Cypher updates in Memgraph.")
    except Exception as e:
        logger.error(f"Error updating Memgraph graph: {e}")

    # Generate the 1-paragraph live context summary
    context_summary = memgraph_client.get_context_summary()

    state["cypher_updates"] = queries
    state["context_summary"] = context_summary

    return state
