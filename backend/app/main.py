import logging
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.schemas.models import (
    IngestRepoRequest,
    IngestRepoResponse,
    FeatureAnalyzeRequest,
    FeatureAnalyzeResponse,
    ClarifyRequest,
    PlanningResponse,
    ImplementRequest,
    ImplementResponse,
    GraphData,
    HealthResponse,
)
from app.core.memgraph_client import memgraph_client
from app.core.code_analyzer import code_analyzer
from app.core.model_router import model_router
from app.agent.nodes.ingestion import node_ingest_repository
from app.agent.nodes.elicitation import node_feature_elicitation
from app.agent.nodes.planning import node_comprehensive_planning
from app.agent.nodes.implementation import node_code_implementation
from app.agent.state import AgentState

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("UserStoryAgent")

app = FastAPI(
    title="Repository-Aware Developer & Memgraph Agent API",
    description="Agentic backend orchestrating repository ingestion, feature analysis, elicitation, Agile planning, and Memgraph knowledge graph updates.",
    version="1.0.0",
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ephemeral in-memory store for active session states
active_sessions: Dict[str, AgentState] = {}


@app.get("/api/health", response_model=HealthResponse)
def get_health():
    """Health check endpoint showing backend status, Memgraph connectivity, and active models."""
    connected = memgraph_client.is_connected()
    snapshot = memgraph_client.get_graph_snapshot()
    node_count = len(snapshot.get("nodes", []))

    return HealthResponse(
        status="healthy",
        memgraph_connected=connected,
        memgraph_nodes=node_count,
        active_llm_provider=settings.PRIMARY_LLM_PROVIDER,
        active_model_tiers=model_router.task_model_map,
    )


@app.post("/api/ingest", response_model=IngestRepoResponse)
def ingest_repository(request: IngestRepoRequest):
    """
    Phase 1: Ingest repository, perform static AST analysis,
    build initial Memgraph knowledge graph, and return 3-sentence summary.
    """
    state: AgentState = {
        "repo_url_or_path": request.repo_url_or_path,
        "repo_name": "",
        "repo_path": "",
        "repo_summary": "",
        "analysis": {},
        "feature_description": "",
        "impact_assessment": {},
        "elicitation_questions": [],
        "clarifications": {},
        "risks": [],
        "requires_clarification": False,
        "user_story": "",
        "design_document": "",
        "work_plan": [],
        "risk_mitigation_plan": "",
        "implementation_code": {},
        "cypher_updates": [],
        "context_summary": "",
        "status": "starting",
        "error": None,
    }

    state = node_ingest_repository(state)
    if state.get("error"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=state["error"])

    # Cache state by repo_path
    active_sessions[state["repo_path"]] = state

    snapshot = memgraph_client.get_graph_snapshot()
    return IngestRepoResponse(
        status="success",
        repo_name=state["repo_name"],
        repo_path=state["repo_path"],
        summary=state["repo_summary"],
        node_count=len(snapshot.get("nodes", [])),
        edge_count=len(snapshot.get("edges", [])),
    )


@app.post("/api/feature/analyze", response_model=FeatureAnalyzeResponse)
def analyze_feature(request: FeatureAnalyzeRequest):
    """
    Phase 2: Analyze feature request, assess impact on codebase,
    identify risks, and formulate targeted clarification questions if ambiguous.
    """
    state = active_sessions.get(request.repo_path)
    if not state:
        # Re-initialize lightweight state from repo_path
        repo_name, repo_path = code_analyzer.ingest_repository(request.repo_path)
        analysis = code_analyzer.analyze_repository(repo_path, repo_name)
        state = {
            "repo_url_or_path": request.repo_path,
            "repo_name": repo_name,
            "repo_path": repo_path,
            "repo_summary": analysis["summary"],
            "analysis": analysis,
            "feature_description": request.feature_description,
            "impact_assessment": {},
            "elicitation_questions": [],
            "clarifications": {},
            "risks": [],
            "requires_clarification": True,
            "user_story": "",
            "design_document": "",
            "work_plan": [],
            "risk_mitigation_plan": "",
            "implementation_code": {},
            "cypher_updates": [],
            "context_summary": "",
            "status": "ready",
            "error": None,
        }

    state["feature_description"] = request.feature_description
    state = node_feature_elicitation(state)
    active_sessions[request.repo_path] = state

    return FeatureAnalyzeResponse(
        repo_path=state["repo_path"],
        feature_description=request.feature_description,
        impact_assessment=state["impact_assessment"],
        assumptions=state.get("assumptions", []),
        source_context=state.get("source_context", {}),
        elicitation_questions=state["elicitation_questions"],
        risks=state["risks"],
        requires_clarification=state["requires_clarification"],
    )


@app.post("/api/feature/clarify", response_model=PlanningResponse)
def clarify_and_plan(request: ClarifyRequest):
    """
    Phase 3: Accept user answers to clarification questions and generate the 4 Agile deliverables:
    1. User Story
    2. Design Document
    3. Systematic Work Plan
    4. Risk Mitigation Plan
    """
    state = active_sessions.get(request.repo_path)
    if not state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository session not found. Please ingest first.")

    state["clarifications"] = request.clarifications
    if request.impact_assessment:
        state["impact_assessment"] = request.impact_assessment
    if request.risks:
        state["risks"] = request.risks

    state = node_comprehensive_planning(state)
    active_sessions[request.repo_path] = state

    return PlanningResponse(
        repo_path=state["repo_path"],
        feature_description=state["feature_description"],
        user_story=state["user_story"],
        design_document=state["design_document"],
        work_plan=state["work_plan"],
        risk_mitigation_plan=state["risk_mitigation_plan"],
    )


@app.post("/api/feature/implement", response_model=ImplementResponse)
def implement_and_update_graph(request: ImplementRequest):
    """
    Phase 5 & 4: Implement code changes according to work plan,
    write files, and execute Cypher MERGE/MATCH queries to sync Memgraph.
    """
    state = active_sessions.get(request.repo_path)
    if not state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found. Ingest and plan first.")

    state["user_story"] = request.user_story
    state["design_document"] = request.design_document
    state["work_plan"] = request.work_plan

    state = node_code_implementation(state)
    active_sessions[request.repo_path] = state

    return ImplementResponse(
        status="completed",
        generated_files=state["implementation_code"],
        cypher_updates=state["cypher_updates"],
        context_summary=state["context_summary"],
    )


@app.get("/api/graph", response_model=GraphData)
def get_graph():
    """Retrieve full live knowledge graph snapshot (nodes & edges) for interactive UI rendering."""
    snapshot = memgraph_client.get_graph_snapshot()
    return GraphData(
        nodes=snapshot.get("nodes", []),
        edges=snapshot.get("edges", []),
    )


@app.get("/api/graph/summary")
def get_graph_summary():
    """Retrieve 1-paragraph summary of current project state from Memgraph."""
    summary = memgraph_client.get_context_summary()
    return {"context_summary": summary}
