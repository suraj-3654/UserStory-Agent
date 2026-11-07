import json
import logging
from app.agent.state import AgentState
from app.agent.prompts import SYSTEM_ARCHITECT_PROMPT, PHASE2_ELICITATION_PROMPT
from app.core.model_router import model_router
from app.core.memgraph_client import memgraph_client
from app.core.code_analyzer import code_analyzer

logger = logging.getLogger(__name__)


def node_feature_elicitation(state: AgentState) -> AgentState:
    """
    Phase 2: Feature Analysis & Elicitation (Code-Context Driven)
    - Deeply analyzes the customer's requirement against the ingested source code.
    - Spots implicit assumptions and architectural dependencies.
    - Only asks a question if an unavoidable business ambiguity exists.
    """
    feature = state.get("feature_description", "")
    repo_path = state.get("repo_path", "")
    analysis = state.get("analysis", {})
    components = list(analysis.get("components", {}).keys())

    # Deep source-code context search
    source_context = code_analyzer.search_source_context(repo_path, feature)
    context_summary = memgraph_client.get_context_summary()

    matched_files_str = ", ".join(source_context.get("matched_files", [])) or "None identified"
    extension_points_str = ", ".join(source_context.get("extension_points", [])) or "Root service layer"

    user_prompt = f"""
Source-Code Architectural Context:
- Repository: {state.get('repo_name')}
- Architecture Summary: {state.get('repo_summary')}
- Detected Framework: {source_context.get('detected_framework')}
- Execution Model: {source_context.get('execution_model')}
- Data Modeling Pattern: {source_context.get('modeling_pattern')}
- Relevant Existing Files: {matched_files_str}
- Architectural Extension Points: {extension_points_str}
- Live Graph State: {context_summary}

Customer Feature Requirement:
"{feature}"

Analyze this requirement using the source-code context.
Spot implicit assumptions from the existing code conventions.
Only include clarification questions if there is an unavoidable, critical ambiguity that CANNOT be resolved from the codebase.
"""

    response_text = model_router.generate(
        task_type="elicitation",
        system_prompt=f"{SYSTEM_ARCHITECT_PROMPT}\n{PHASE2_ELICITATION_PROMPT}",
        user_prompt=user_prompt,
    )

    # Parse response
    impact = {}
    assumptions = []
    questions = []
    risks = []

    try:
        clean_text = response_text.strip()
        if "```json" in clean_text:
            clean_text = clean_text.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_text:
            clean_text = clean_text.split("```")[1].split("```")[0].strip()

        data = json.loads(clean_text)
        impact = {
            "modified_modules": data.get("modified_modules", []),
            "new_dependencies": data.get("new_dependencies", []),
            "potential_breaking_changes": data.get("potential_breaking_changes", []),
        }
        assumptions = data.get("assumptions", [])
        questions = data.get("clarification_questions", [])
        risks = data.get("risks", [])
    except Exception:
        # Fallback using actual source-code analysis findings
        impact = {
            "modified_modules": source_context.get("extension_points", components[:2]),
            "new_dependencies": [],
            "potential_breaking_changes": ["Ensure new endpoints/methods preserve backward compatibility"],
        }
        assumptions = [
            f"Adopt existing {source_context.get('detected_framework')} conventions and {source_context.get('execution_model')}.",
            f"Model device state and parameters using {source_context.get('modeling_pattern')}.",
            f"Integrate service handlers into {extension_points_str}.",
        ]
        # Never hardcode generic questions!
        questions = []
        risks = [
            f"Device connectivity: Ensure timeout handling if the target device is unreachable.",
            f"State synchronization: Handle idempotent commands gracefully.",
        ]

    # Filter out generic canned questions if the LLM outputted any
    filtered_questions = []
    for q in questions:
        q_lower = q.lower()
        if "synchronous or asynchronous" in q_lower or "security and access tier" in q_lower:
            # Code context already gives this answer
            assumptions.append(f"Inferred execution style: {source_context.get('execution_model')}")
            continue
        filtered_questions.append(q)

    # If no assumptions were provided, infer them from source code
    if not assumptions:
        assumptions = [
            f"Follows established {source_context.get('detected_framework')} architectural patterns.",
            f"Adopts {source_context.get('execution_model')} to prevent blocking I/O calls.",
            f"Validates inputs via {source_context.get('modeling_pattern')}.",
        ]

    state["impact_assessment"] = impact
    state["source_context"] = source_context
    state["assumptions"] = assumptions
    state["elicitation_questions"] = filtered_questions
    state["risks"] = risks

    has_clarifications = bool(state.get("clarifications"))
    state["requires_clarification"] = len(filtered_questions) > 0 and not has_clarifications
    state["status"] = "awaiting_clarification" if state["requires_clarification"] else "elicitation_complete"

    return state
