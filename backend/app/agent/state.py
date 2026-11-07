from typing import TypedDict, List, Dict, Any, Optional


class AgentState(TypedDict):
    """
    Central state container for the LangGraph workflow across all 5 phases.
    """
    # Phase 1: Ingestion
    repo_url_or_path: str
    repo_name: str
    repo_path: str
    repo_summary: str
    analysis: Dict[str, Any]

    # Phase 2: Feature Elicitation & Impact Assessment
    feature_description: str
    impact_assessment: Dict[str, Any]
    source_context: Dict[str, Any]
    assumptions: List[str]
    elicitation_questions: List[str]
    clarifications: Dict[str, str]
    risks: List[str]
    requires_clarification: bool

    # Phase 3: Comprehensive Planning
    user_story: str
    design_document: str
    work_plan: List[str]
    risk_mitigation_plan: str

    # Phase 4 & 5: Implementation & State Update
    implementation_code: Dict[str, str]
    cypher_updates: List[str]
    context_summary: str

    # Control flags
    status: str
    error: Optional[str]
