import logging
from app.agent.state import AgentState
from app.core.code_analyzer import code_analyzer
from app.core.memgraph_client import memgraph_client

logger = logging.getLogger(__name__)


def node_ingest_repository(state: AgentState) -> AgentState:
    """
    Phase 1: Initialization & Repository Ingestion
    - Clones/inspects codebase.
    - Static AST scanning of architecture, modules, dependencies.
    - Builds initial Memgraph graph with Cypher queries.
    - Produces a 3-sentence high-level summary.
    """
    repo_input = state.get("repo_url_or_path")
    if not repo_input:
        state["error"] = "No repository URL or path provided."
        state["status"] = "error"
        return state

    try:
        repo_name, repo_path = code_analyzer.ingest_repository(repo_input)
        analysis = code_analyzer.analyze_repository(repo_path, repo_name)

        # Initialize schema constraints & indexes in Memgraph
        memgraph_client.initialize_schema()

        # Generate and execute initial Cypher graph creation
        cypher_batch = code_analyzer.generate_initial_cypher(analysis)
        memgraph_client.execute_batch(cypher_batch)

        state["repo_name"] = repo_name
        state["repo_path"] = repo_path
        state["repo_summary"] = analysis["summary"]
        state["analysis"] = analysis
        state["status"] = "ingested"
        state["error"] = None

        logger.info(f"Phase 1 complete for repo '{repo_name}'. Created {len(cypher_batch)} Cypher statements.")
    except Exception as e:
        logger.error(f"Error during repository ingestion: {e}")
        state["error"] = str(e)
        state["status"] = "error"

    return state
