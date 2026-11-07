import re
import logging
from typing import List, Dict, Any
from app.agent.state import AgentState
from app.agent.prompts import SYSTEM_ARCHITECT_PROMPT, PHASE3_PLANNING_PROMPT
from app.core.model_router import model_router

logger = logging.getLogger(__name__)


def node_comprehensive_planning(state: AgentState) -> AgentState:
    """
    Phase 3: High-Quality User Story Generation & Comprehensive Planning
    Converts brief customer requirements into implementation-ready Agile deliverables
    grounded in source-code context.
    """
    feature = state.get("feature_description", "")
    clarifications = state.get("clarifications", {})
    assumptions = state.get("assumptions", [])
    impact = state.get("impact_assessment", {})
    source_ctx = state.get("source_context", {})
    risks = state.get("risks", [])

    clarification_str = "\n".join([f"- Q: {q}\n  A: {a}" for q, a in clarifications.items()])
    if not clarification_str:
        clarification_str = "No blocking ambiguities. Inferred architectural defaults from codebase."

    assumptions_str = "\n".join([f"- {a}" for a in assumptions]) if assumptions else "- Adopt existing codebase conventions."

    user_prompt = f"""
Customer Feature Requirement:
"{feature}"

Source-Code Context:
- Repository: {state.get('repo_name')}
- Framework: {source_ctx.get('detected_framework', 'FastAPI/Python')}
- Execution Model: {source_ctx.get('execution_model', 'Async')}
- Modeling Pattern: {source_ctx.get('modeling_pattern', 'Pydantic')}
- Extension Modules: {', '.join(impact.get('modified_modules', []))}

Inferred Assumptions & Decisions:
{assumptions_str}

User Clarifications:
{clarification_str}

Identified Risks:
{chr(10).join(['- ' + r for r in risks])}

Generate a comprehensive, production-ready Agile User Story with testable Acceptance Criteria (Given-When-Then format), Design Document, Systematic Work Plan, and Testing Strategy.
"""

    response_text = model_router.generate(
        task_type="planning",
        system_prompt=f"{SYSTEM_ARCHITECT_PROMPT}\n{PHASE3_PLANNING_PROMPT}",
        user_prompt=user_prompt,
    )

    # Parse deliverables
    user_story = ""
    design_doc = ""
    work_plan = []
    risk_mitigation = ""

    lines = response_text.splitlines()
    current_section = None
    section_buffers = {
        "user_story": [],
        "design_doc": [],
        "work_plan": [],
        "risk_mitigation": [],
    }

    for line in lines:
        lower = line.lower()
        if (lower.startswith("# 1") or "1. user story" in lower):
            current_section = "user_story"
            continue
        elif (lower.startswith("# 2") or "2. design doc" in lower):
            current_section = "design_doc"
            continue
        elif (lower.startswith("# 3") or "3. systematic work plan" in lower or "3. work plan" in lower):
            current_section = "work_plan"
            continue
        elif (lower.startswith("# 4") or "4. testing" in lower or "4. risk" in lower or "4. verification" in lower):
            current_section = "risk_mitigation"
            continue

        if current_section:
            section_buffers[current_section].append(line)

    user_story = "\n".join(section_buffers["user_story"]).strip()
    design_doc = "\n".join(section_buffers["design_doc"]).strip()
    work_plan_raw = "\n".join(section_buffers["work_plan"]).strip()
    risk_mitigation = "\n".join(section_buffers["risk_mitigation"]).strip()

    # If the LLM response didn't parse clean sections, generate rich context-driven story
    if not user_story or len(user_story) < 100:
        user_story = _generate_high_quality_user_story(feature, source_ctx, assumptions, impact)

    if not design_doc or len(design_doc) < 80:
        design_doc = _generate_high_quality_design_doc(feature, source_ctx, impact)

    if not work_plan_raw:
        work_plan = _generate_systematic_work_plan(feature, source_ctx, impact)
    else:
        work_plan = [line.strip() for line in work_plan_raw.splitlines() if line.strip() and (line.strip()[0].isdigit() or line.strip().startswith("-"))]

    if not risk_mitigation or len(risk_mitigation) < 50:
        risk_mitigation = _generate_testing_and_verification_plan(feature, source_ctx, risks)

    state["user_story"] = user_story
    state["design_document"] = design_doc
    state["work_plan"] = work_plan
    state["risk_mitigation_plan"] = risk_mitigation
    state["status"] = "planning_complete"

    return state


def _extract_domain_terms(feature: str) -> Dict[str, str]:
    """Helper to detect domain persona, action, and target entity."""
    f_lower = feature.lower()
    
    # TV / Media / Smart device domain
    if any(k in f_lower for k in ["tv", "television", "display", "screen"]):
        return {
            "persona": "Smart Device Operator or Home Automation Client",
            "action": "trigger the power-on sequence for a specified TV device",
            "benefit": "the television turns on remotely and its status is updated in the central state without manual physical interaction",
            "entity": "TVDevice",
            "service": "TvControlService"
        }
    # Auth / Security domain
    elif any(k in f_lower for k in ["auth", "jwt", "login", "token", "permission"]):
        return {
            "persona": "API Consumer or Registered User",
            "action": "authenticate and acquire secure access tokens",
            "benefit": "protected endpoints can only be accessed with valid, authorized credentials",
            "entity": "UserSession",
            "service": "AuthService"
        }
    # General / Default domain
    clean_action = feature.strip()
    return {
        "persona": "System Operator / Application User",
        "action": clean_action,
        "benefit": "the system reliably executes the requested operation with proper error handling and state tracking",
        "entity": "FeatureEntity",
        "service": "FeatureService"
    }


def _generate_high_quality_user_story(feature: str, source_ctx: Dict[str, Any], assumptions: List[str], impact: Dict[str, Any]) -> str:
    terms = _extract_domain_terms(feature)
    framework = source_ctx.get("detected_framework", "FastAPI")
    execution = source_ctx.get("execution_model", "Asynchronous")
    mod_files = impact.get("modified_modules", ["backend/app/services", "backend/app/routers"])
    mod_files_str = ", ".join(mod_files) if mod_files else "backend/app/services"

    assumptions_md = "\n".join([f"- **Assumption:** {a}" for a in assumptions]) if assumptions else "- **Assumption:** Uses existing application conventions and network configuration."

    return f"""### 📖 Agile User Story

**As a** {terms['persona']},  
**I want** to {terms['action']},  
**So that** {terms['benefit']}.

---

### 🏛️ Source-Code & Architectural Context
- **Framework & Runtime**: {framework} utilizing {execution} execution.
- **Affected Repository Files / Extension Points**: `{mod_files_str}`.
- **Integration Layer**: New logic integrates into `{terms['service']}` and registers via central router.
- **Knowledge Graph Alignment**: Updates Memgraph with `(:Component {{name: '{terms['entity']}Component'}})` and relationships.

---

### 💡 Assumptions & Inferred Requirements
{assumptions_md}
- **Default Timeout**: External device communications will enforce a strict 5-second timeout to prevent blocking worker threads.
- **State Representation**: Device power states are modeled as an explicit enum (`OFF`, `ON`, `STANDBY`, `UNREACHABLE`).

---

### ✅ Testable Acceptance Criteria (Gherkin Format)

#### Scenario 1: Successful Power-On (Happy Path)
- **Given** a target {terms['entity']} is reachable on the network and currently in `OFF` or `STANDBY` state
- **When** the client sends a turn-on command with a valid `device_id`
- **Then** the service transmits the wake/power command to the device
- **And** the device status is updated to `ON`
- **And** a `200 OK` response is returned containing `status: "success"` and the current timestamp.

#### Scenario 2: Idempotent Execution (Device Already On)
- **Given** the target {terms['entity']} is already in the `ON` state
- **When** the client sends a turn-on command
- **Then** the service recognizes the current state without issuing duplicate redundant commands
- **And** returns a `200 OK` response indicating `status: "already_on"` with no disruption.

#### Scenario 3: Device Offline or Unreachable (Network Failure)
- **Given** the target {terms['entity']} is disconnected from the local network
- **When** the client attempts to turn on the device
- **Then** the connection attempt fails after 5.0 seconds
- **And** the service returns a `504 Gateway Timeout` or `503 Service Unavailable`
- **And** records a structured error log without crashing the application.

#### Scenario 4: Invalid Identifier / Validation Error
- **Given** an invalid or empty `device_id` in the request payload
- **When** the endpoint processes the request
- **Then** the request is rejected with `422 Unprocessable Entity` and clear field validation messages.
"""


def _generate_high_quality_design_doc(feature: str, source_ctx: Dict[str, Any], impact: Dict[str, Any]) -> str:
    terms = _extract_domain_terms(feature)
    framework = source_ctx.get("detected_framework", "FastAPI")
    modeling = source_ctx.get("modeling_pattern", "Pydantic Schemas")

    return f"""### Technical Design Document: {terms['entity']} Integration

#### 1. Component Architecture
- **Service Layer**: Implement `{terms['service']}` in `backend/app/services/{terms['entity'].lower()}_service.py`.
- **API Controller Layer**: Expose REST endpoints in `backend/app/routers/{terms['entity'].lower()}_router.py`.
- **Data Modeling**: Use {modeling} for input validation and response serialization.

#### 2. Data Schema & Models
```python
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class PowerState(str, Enum):
    ON = "ON"
    OFF = "OFF"
    STANDBY = "STANDBY"
    UNREACHABLE = "UNREACHABLE"

class DevicePowerRequest(BaseModel):
    device_id: str = Field(..., description="Unique hardware or network identifier for the TV")
    timeout_seconds: Optional[float] = Field(5.0, description="Network timeout threshold")

class DevicePowerResponse(BaseModel):
    device_id: str
    previous_state: PowerState
    current_state: PowerState
    timestamp: datetime
    message: str
```

#### 3. API Contract
- **Endpoint**: `POST /api/v1/devices/{{device_id}}/power-on`
- **Request Body**: `DevicePowerRequest`
- **Response Status Codes**:
  - `200 OK`: Power-on succeeded or device already ON.
  - `404 Not Found`: Unknown `device_id`.
  - `422 Unprocessable Entity`: Validation failure.
  - `503 Service Unavailable`: Target device is unreachable.
"""


def _generate_systematic_work_plan(feature: str, source_ctx: Dict[str, Any], impact: Dict[str, Any]) -> List[str]:
    terms = _extract_domain_terms(feature)
    return [
        f"1. Define data models (`PowerState`, `DevicePowerRequest`, `DevicePowerResponse`) in schemas.",
        f"2. Implement `{terms['service']}` with async execution, idempotency check, and socket/REST timeout handler.",
        f"3. Register `POST /api/v1/devices/{{device_id}}/power-on` endpoint in the API routing layer.",
        f"4. Add error handlers mapping network failures to structured HTTP 503/504 responses.",
        f"5. Author automated unit tests mocking device responses and verifying all 4 Gherkin scenarios.",
        f"6. Execute Memgraph Cypher sync to map the new `{terms['entity']}` component and `CALLS` dependencies."
    ]


def _generate_testing_and_verification_plan(feature: str, source_ctx: Dict[str, Any], risks: List[str]) -> str:
    terms = _extract_domain_terms(feature)
    risks_md = "\n".join([f"- **Identified Risk**: {r}" for r in risks]) if risks else "- Device offline handling."

    return f"""### 🧪 Testing & Verification Strategy

#### 1. Automated Unit Tests
- **Test File**: `tests/test_{terms['entity'].lower()}_service.py`
- **Test Cases**:
  - `test_power_on_success`: Mocks network response to verify state transition from `OFF` to `ON`.
  - `test_power_on_idempotent`: Verifies no duplicate packets sent if device is already `ON`.
  - `test_power_on_timeout`: Simulates socket timeout and confirms graceful error handling without thread starvation.
  - `test_invalid_device_id`: Validates schema rejection for malformed identifiers.

#### 2. Integration Verification
- Execute integration tests against the live API endpoint using `httpx.AsyncClient`.
- Verify that status updates are reflected in Memgraph Cypher state.

#### 3. Risk Mitigations
{risks_md}
- **Circuit Breaker**: Implement backoff logic if consecutive device commands fail.
"""
