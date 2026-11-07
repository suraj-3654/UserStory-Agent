import os
import json
import streamlit as st
import streamlit.components.v1 as components
import requests

# Set page config
st.set_page_config(
    page_title="Repository-Aware Developer & Memgraph Agent",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Custom CSS for modern styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #1E88E5, #43A047);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #616161;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        border: 1px solid #e0e0e0;
    }
    .summary-box {
        background-color: #e3f2fd;
        border-left: 5px solid #1976d2;
        padding: 15px;
        border-radius: 4px;
        margin: 10px 0;
    }
    .risk-box {
        background-color: #fff3e0;
        border-left: 5px solid #f57c00;
        padding: 15px;
        border-radius: 4px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)


def fetch_backend_health():
    try:
        res = requests.get(f"{BACKEND_URL}/api/health", timeout=3)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return None


def render_visjs_graph(nodes, edges, height=450):
    """
    Renders an interactive network graph using Vis.js embedded HTML component.
    """
    color_map = {
        "Repository": "#673AB7",
        "Component": "#2196F3",
        "File": "#4CAF50",
        "Service": "#FF9800",
        "DatabaseTable": "#E91E63",
        "Class": "#009688",
        "Function": "#00BCD4",
    }

    vis_nodes = []
    for n in nodes:
        grp = n.get("group", "File")
        color = color_map.get(grp, "#9E9E9E")
        vis_nodes.append({
            "id": n["id"],
            "label": n["label"],
            "title": n.get("title", f"{grp}: {n['label']}"),
            "color": color,
            "shape": "dot" if grp == "File" else "box",
            "size": 25 if grp == "Component" else 15,
            "font": {"color": "#333333"},
        })

    vis_edges = []
    for e in edges:
        vis_edges.append({
            "from": e["from"],
            "to": e["to"],
            "label": e.get("label", ""),
            "arrows": "to",
            "font": {"align": "middle", "size": 10},
            "color": {"color": "#B0BEC5"},
        })

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
        <style type="text/css">
            #network {{
                width: 100%;
                height: {height}px;
                border: 1px solid #e0e0e0;
                background-color: #fafafa;
                border-radius: 8px;
            }}
        </style>
    </head>
    <body>
        <div id="network"></div>
        <script type="text/javascript">
            var nodes = new vis.DataSet({json.dumps(vis_nodes)});
            var edges = new vis.DataSet({json.dumps(vis_edges)});
            var container = document.getElementById('network');
            var data = {{ nodes: nodes, edges: edges }};
            var options = {{
                physics: {{
                    solver: 'forceAtlas2Based',
                    forceAtlas2Based: {{
                        gravitationalConstant: -40,
                        centralGravity: 0.01,
                        springLength: 90,
                        springConstant: 0.08
                    }},
                    maxVelocity: 50,
                    minVelocity: 0.1,
                    stabilization: {{ iterations: 100 }}
                }},
                interaction: {{ hover: true, tooltipDelay: 150, zoomView: true, dragView: true }}
            }};
            var network = new vis.Network(container, data, options);
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=height + 20)


# Initialize Session State
if "repo_path" not in st.session_state:
    st.session_state.repo_path = ""
if "repo_summary" not in st.session_state:
    st.session_state.repo_summary = ""
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "planning_result" not in st.session_state:
    st.session_state.planning_result = None
if "implementation_result" not in st.session_state:
    st.session_state.implementation_result = None

# Sidebar - System Status & Resilient Model Routing
st.sidebar.title("🤖 System Control")
health = fetch_backend_health()

if health:
    st.sidebar.success("Backend: Online")
    if health.get("memgraph_connected"):
        st.sidebar.success(f"Memgraph: Connected ({health.get('memgraph_nodes', 0)} nodes)")
    else:
        st.sidebar.warning("Memgraph: Emulation Mode (Offline)")

    st.sidebar.markdown("---")
    st.sidebar.subheader("🎯 Dynamic Model Routing")
    st.sidebar.caption(f"Provider: **{health.get('active_llm_provider', 'ollama').upper()}**")
    
    tiers = health.get("active_model_tiers", {})
    st.sidebar.write(f"- **Scanning:** `{tiers.get('scanning', 'llama3.2:3b')}`")
    st.sidebar.write(f"- **Elicitation:** `{tiers.get('elicitation', 'llama3.1:8b')}`")
    st.sidebar.write(f"- **Planning:** `{tiers.get('planning', 'llama3.1:8b')}`")
    st.sidebar.write(f"- **Cypher/Graph:** `{tiers.get('cypher', 'qwen2.5-coder:7b')}`")
    st.sidebar.write(f"- **Coding:** `{tiers.get('coding', 'qwen2.5-coder:7b')}`")
else:
    st.sidebar.error("Backend: Disconnected")
    st.sidebar.info(f"Targeting: {BACKEND_URL}")

st.sidebar.markdown("---")
st.sidebar.markdown(
    "💡 **Memgraph Lab**: Open [http://localhost:3000](http://localhost:3000) for native Cypher graph querying."
)

# Header
st.markdown('<div class="main-header">Repository-Aware Developer & Memgraph Agent</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Autonomous repository ingestion, feature elicitation, Agile planning, and live Memgraph knowledge graph synchronization.</div>',
    unsafe_allow_html=True,
)

# Main Navigation Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📂 1. Repository Ingestion & Graph",
    "🔍 2. Feature Elicitation & Impact",
    "📋 3. Agile Deliverables",
    "💻 4. Implementation & Code Sync",
])

# ==========================================================
# TAB 1: REPOSITORY INGESTION & GRAPH
# ==========================================================
with tab1:
    st.subheader("Phase 1 & 4: Ingestion & Live Structural Map")
    col1, col2 = st.columns([3, 1])
    with col1:
        repo_input = st.text_input(
            "Repository URL or Local Path",
            value=st.session_state.repo_path or ".",
            help="Provide a GitHub HTTPS/SSH clone URL or a path on the local filesystem.",
        )
    with col2:
        st.write("")
        st.write("")
        ingest_btn = st.button("🚀 Ingest & Build Graph", use_container_width=True)

    if ingest_btn and repo_input:
        with st.spinner("Analyzing codebase and generating initial Memgraph knowledge graph..."):
            try:
                res = requests.post(f"{BACKEND_URL}/api/ingest", json={"repo_url_or_path": repo_input}, timeout=60)
                if res.status_code == 200:
                    data = res.json()
                    st.session_state.repo_path = data["repo_path"]
                    st.session_state.repo_summary = data["summary"]
                    st.success(f"Ingested '{data['repo_name']}' successfully! ({data['node_count']} nodes, {data['edge_count']} relationships)")
                else:
                    st.error(f"Ingestion failed: {res.text}")
            except Exception as e:
                st.error(f"Connection error: {e}")

    # Display 3-sentence summary
    if st.session_state.repo_summary:
        st.markdown(
            f'<div class="summary-box"><strong>Codebase Ingestion Summary:</strong><br>{st.session_state.repo_summary}</div>',
            unsafe_allow_html=True,
        )

    # Live Memgraph Graph Visualization
    st.markdown("#### Live System Architecture (Memgraph)")
    try:
        graph_res = requests.get(f"{BACKEND_URL}/api/graph", timeout=5)
        if graph_res.status_code == 200:
            graph_data = graph_res.json()
            nodes = graph_data.get("nodes", [])
            edges = graph_data.get("edges", [])

            if nodes:
                # Legend
                st.caption(
                    "🟣 Repository | 🔵 Component | 🟢 File | 🟠 Service | 🔴 Database Table"
                )
                render_visjs_graph(nodes, edges, height=480)

                # Short context summary
                summary_res = requests.get(f"{BACKEND_URL}/api/graph/summary", timeout=5)
                if summary_res.status_code == 200:
                    st.info(summary_res.json().get("context_summary", ""))
            else:
                st.info("No nodes in the knowledge graph yet. Ingest a repository above to populate.")
    except Exception as e:
        st.warning(f"Could not load graph visualizer: {e}")

# ==========================================================
# TAB 2: FEATURE ELICITATION & IMPACT
# ==========================================================
with tab2:
    st.subheader("Phase 2: Feature Analysis & Elicitation")
    feature_input = st.text_area(
        "Enter Feature Description (1-2 lines)",
        placeholder="e.g. Add JWT authentication middleware and token refresh endpoint to protect user routes.",
        height=75,
    )

    analyze_btn = st.button("🔎 Analyze Impact & Elicit Requirements")

    if analyze_btn and feature_input:
        if not st.session_state.repo_path:
            st.warning("Please ingest a repository first in Tab 1.")
        else:
            with st.spinner("Cross-referencing feature with Memgraph and assessing architectural impact..."):
                try:
                    payload = {
                        "repo_path": st.session_state.repo_path,
                        "feature_description": feature_input,
                    }
                    res = requests.post(f"{BACKEND_URL}/api/feature/analyze", json=payload, timeout=60)
                    if res.status_code == 200:
                        st.session_state.analysis_result = res.json()
                        st.success("Impact assessment and elicitation complete!")
                    else:
                        st.error(f"Analysis failed: {res.text}")
                except Exception as e:
                    st.error(f"Error: {e}")

    if st.session_state.analysis_result:
        ar = st.session_state.analysis_result
        col_imp, col_risk = st.columns(2)

        with col_imp:
            st.markdown("#### 🎯 Impact Assessment")
            impact = ar.get("impact_assessment", {})
            st.write(f"- **Modified Modules:** {', '.join(impact.get('modified_modules', [])) or 'None'}")
            st.write(f"- **New Dependencies:** {', '.join(impact.get('new_dependencies', [])) or 'None'}")
            st.write(f"- **Potential Breaking Changes:** {', '.join(impact.get('potential_breaking_changes', [])) or 'None'}")

        with col_risk:
            st.markdown("#### ⚠️ Technical & Security Risks")
            risks = ar.get("risks", [])
            for r in risks:
                st.markdown(f'<div class="risk-box">{r}</div>', unsafe_allow_html=True)

        st.markdown("---")
        
        # Display Source-Code Context & Assumptions
        col_ctx, col_assump = st.columns(2)
        with col_ctx:
            st.markdown("#### 🔍 Discovered Codebase Conventions")
            s_ctx = ar.get("source_context", {})
            st.write(f"- **Framework:** {s_ctx.get('detected_framework', 'FastAPI/Python')}")
            st.write(f"- **Execution Model:** {s_ctx.get('execution_model', 'Async')}")
            st.write(f"- **Modeling Pattern:** {s_ctx.get('modeling_pattern', 'Pydantic Schemas')}")
            ext_files = s_ctx.get("extension_points", [])
            st.write(f"- **Natural Extension Points:** {', '.join(ext_files[:3]) if ext_files else 'Service layer'}")

        with col_assump:
            st.markdown("#### 💡 Inferred Assumptions & Technical Decisions")
            assumptions = ar.get("assumptions", [])
            if assumptions:
                for a in assumptions:
                    st.write(f"- {a}")
            else:
                st.write("- Adopting standard codebase conventions and non-blocking I/O.")

        st.markdown("---")

        questions = ar.get("elicitation_questions", [])
        answers = {}

        if questions:
            st.markdown("#### 💬 Clarification Questions (Architectural Elicitation)")
            st.caption("Please confirm or clarify the targeted requirements before proceeding to planning:")
            for idx, q in enumerate(questions):
                answers[q] = st.text_input(f"Q{idx+1}: {q}", key=f"q_{idx}")
            btn_label = "✅ Confirm Answers & Proceed to Planning"
        else:
            st.success("✨ **Source-Code Context is Clear**: No blocking clarification questions are necessary! The agent has resolved technical dependencies and spotted implicit requirements directly from existing code patterns.")
            btn_label = "🚀 Generate High-Quality Agile User Story"

        if st.button(btn_label, type="primary"):
            with st.spinner("Generating implementation-ready Agile User Story from source code context..."):
                try:
                    clarify_payload = {
                        "repo_path": ar["repo_path"],
                        "feature_description": ar["feature_description"],
                        "clarifications": answers,
                        "impact_assessment": impact,
                        "risks": risks,
                    }
                    plan_res = requests.post(f"{BACKEND_URL}/api/feature/clarify", json=clarify_payload, timeout=90)
                    if plan_res.status_code == 200:
                        st.session_state.planning_result = plan_res.json()
                        st.success("Agile User Story & Documentation generated! Navigate to Tab 3 to review.")
                    else:
                        st.error(f"Planning failed: {plan_res.text}")
                except Exception as e:
                    st.error(f"Error: {e}")

# ==========================================================
# TAB 3: AGILE DELIVERABLES
# ==========================================================
with tab3:
    st.subheader("Phase 3: Comprehensive Planning Deliverables")
    if not st.session_state.planning_result:
        st.info("Complete feature analysis and clarification in Tab 2 to generate Agile planning deliverables.")
    else:
        pr = st.session_state.planning_result

        deliv_tabs = st.tabs([
            "📖 1. User Story",
            "📐 2. Design Document",
            "📝 3. Systematic Work Plan",
            "🛡️ 4. Risk Mitigation Plan",
        ])

        with deliv_tabs[0]:
            st.markdown("### Agile User Story & Acceptance Criteria")
            st.markdown(pr.get("user_story", ""))

        with deliv_tabs[1]:
            st.markdown("### Technical Design Document")
            st.markdown(pr.get("design_document", ""))

        with deliv_tabs[2]:
            st.markdown("### Systematic Work Plan Checklist")
            work_items = pr.get("work_plan", [])
            for item in work_items:
                st.checkbox(item, value=False, key=f"wp_{item[:20]}")

        with deliv_tabs[3]:
            st.markdown("### Risk Mitigation Plan")
            st.markdown(pr.get("risk_mitigation_plan", ""))

        st.markdown("---")
        if st.button("🚀 Approve Deliverables & Implement Code (Phase 5)", type="primary"):
            with st.spinner("Writing production code and synchronizing Memgraph knowledge graph..."):
                try:
                    impl_payload = {
                        "repo_path": pr["repo_path"],
                        "feature_description": pr["feature_description"],
                        "user_story": pr["user_story"],
                        "design_document": pr["design_document"],
                        "work_plan": pr["work_plan"],
                    }
                    impl_res = requests.post(f"{BACKEND_URL}/api/feature/implement", json=impl_payload, timeout=90)
                    if impl_res.status_code == 200:
                        st.session_state.implementation_result = impl_res.json()
                        st.success("Feature implemented and Memgraph state synchronized!")
                    else:
                        st.error(f"Implementation failed: {impl_res.text}")
                except Exception as e:
                    st.error(f"Error: {e}")

# ==========================================================
# TAB 4: IMPLEMENTATION & CODE SYNC
# ==========================================================
with tab4:
    st.subheader("Phase 5: Implementation & Live Graph State Sync")
    if not st.session_state.implementation_result:
        st.info("Approve the Agile deliverables in Tab 3 to trigger code generation and state update.")
    else:
        ir = st.session_state.implementation_result

        st.markdown("#### 📦 Generated Production Code")
        files = ir.get("generated_files", {})
        for filepath, code in files.items():
            with st.expander(f"📄 {filepath}", expanded=True):
                st.code(code, language="python")

        st.markdown("---")
        st.markdown("#### ⚡ Synchronized Memgraph Cypher Statements")
        cyphers = ir.get("cypher_updates", [])
        if cyphers:
            st.code("\n".join(cyphers), language="cypher")
        else:
            st.caption("No new Cypher statements generated.")

        st.markdown("---")
        st.markdown("#### 🔄 Updated Architectural Context Summary")
        st.info(ir.get("context_summary", "Graph state synchronized."))
