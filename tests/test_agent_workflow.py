import os
import tempfile
import pytest
from app.agent.nodes.ingestion import node_ingest_repository
from app.agent.nodes.elicitation import node_feature_elicitation
from app.agent.nodes.planning import node_comprehensive_planning
from app.agent.nodes.implementation import node_code_implementation
from app.agent.state import AgentState


def test_agent_workflow_phases():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create sample repo file
        sample_file = os.path.join(tmp_dir, "main.py")
        with open(sample_file, "w") as f:
            f.write("def run():\n    print('Hello World')\n")

        state: AgentState = {
            "repo_url_or_path": tmp_dir,
            "repo_name": "",
            "repo_path": "",
            "repo_summary": "",
            "analysis": {},
            "feature_description": "Add user authentication middleware",
            "impact_assessment": {},
            "source_context": {},
            "assumptions": [],
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

        # Phase 1: Ingestion
        state = node_ingest_repository(state)
        assert state["status"] == "ingested"
        assert state["repo_summary"] != ""
        assert len(state["analysis"]["files"]) >= 1

        # Phase 2: Feature Elicitation & Impact Assessment
        state = node_feature_elicitation(state)
        assert "modified_modules" in state["impact_assessment"]
        assert len(state["assumptions"]) > 0
        assert len(state["risks"]) > 0

        # Phase 3: Comprehensive Planning & User Story Generation
        state = node_comprehensive_planning(state)
        assert state["user_story"] != ""
        assert "Acceptance Criteria" in state["user_story"]
        assert state["design_document"] != ""
        assert len(state["work_plan"]) > 0
        assert state["risk_mitigation_plan"] != ""

        # Phase 5 & 4: Implementation and Memgraph Cypher sync
        state = node_code_implementation(state)
        assert state["status"] == "completed"
        assert len(state["implementation_code"]) > 0
        assert len(state["cypher_updates"]) > 0


def test_tv_functionality_user_story_generation():
    """
    Verifies that a 1-2 line requirement ('Add a turn on tv functionality in the current tool')
    is converted into a high-quality Agile User Story with testable Acceptance Criteria
    WITHOUT asking generic/canned questions.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        state: AgentState = {
            "repo_url_or_path": tmp_dir,
            "repo_name": "smart_tool",
            "repo_path": tmp_dir,
            "repo_summary": "Smart automation tool repository.",
            "analysis": {"components": {"services": [], "routers": []}, "files": []},
            "feature_description": "Add a turn on tv functionality in the current tool",
            "impact_assessment": {},
            "source_context": {},
            "assumptions": [],
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

        # Run Elicitation
        state = node_feature_elicitation(state)

        # Must NOT contain the old generic questions
        for q in state.get("elicitation_questions", []):
            assert "synchronous or asynchronous" not in q.lower()
            assert "security and access tier" not in q.lower()

        # Inferred assumptions must be captured
        assert len(state.get("assumptions", [])) > 0

        # Run Planning
        state = node_comprehensive_planning(state)

        # Verify User Story contents
        user_story = state["user_story"]
        assert "As a" in user_story
        assert "I want" in user_story
        assert "So that" in user_story
        assert "Acceptance Criteria" in user_story
        assert "Scenario 1" in user_story or "Given" in user_story
        assert "Scenario" in user_story
        # Verify specific design doc and work plan
        assert state["design_document"] != ""
        assert len(state["work_plan"]) >= 4
