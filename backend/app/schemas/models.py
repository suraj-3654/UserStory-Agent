from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class IngestRepoRequest(BaseModel):
    repo_url_or_path: str = Field(..., description="Git remote repository URL or local path")


class IngestRepoResponse(BaseModel):
    status: str
    repo_name: str
    repo_path: str
    summary: str
    node_count: int
    edge_count: int


class FeatureAnalyzeRequest(BaseModel):
    repo_path: str = Field(..., description="Path to ingested repository")
    feature_description: str = Field(..., description="1-2 line description of requested feature")


class FeatureAnalyzeResponse(BaseModel):
    repo_path: str
    feature_description: str
    impact_assessment: Dict[str, Any]
    assumptions: List[str] = Field(default_factory=list)
    source_context: Dict[str, Any] = Field(default_factory=dict)
    elicitation_questions: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    requires_clarification: bool


class ClarifyRequest(BaseModel):
    repo_path: str
    feature_description: str
    clarifications: Dict[str, str] = Field(..., description="Map of question to user answers")
    impact_assessment: Optional[Dict[str, Any]] = None
    risks: Optional[List[str]] = None


class PlanningResponse(BaseModel):
    repo_path: str
    feature_description: str
    user_story: str
    design_document: str
    work_plan: List[str]
    risk_mitigation_plan: str


class ImplementRequest(BaseModel):
    repo_path: str
    feature_description: str
    user_story: str
    design_document: str
    work_plan: List[str]


class ImplementResponse(BaseModel):
    status: str
    generated_files: Dict[str, str] = Field(..., description="Filepath relative to repo -> Code content")
    cypher_updates: List[str]
    context_summary: str


class GraphNode(BaseModel):
    id: str
    label: str
    group: str
    title: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    from_node: str = Field(alias="from")
    to_node: str = Field(alias="to")
    label: str

    class Config:
        populate_by_name = True


class GraphData(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


class HealthResponse(BaseModel):
    status: str
    memgraph_connected: bool
    memgraph_nodes: int
    active_llm_provider: str
    active_model_tiers: Dict[str, str]
