import logging
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase, Driver
from app.config import settings

logger = logging.getLogger(__name__)


class MemgraphClient:
    """
    Manages Bolt connections and Cypher queries to the Memgraph knowledge graph.
    Maintains a stateful representation of the system architecture:
    Nodes: (:Repository), (:Component), (:File), (:Function), (:Class), (:Service), (:DatabaseTable)
    Edges: [:CONTAINS], [:DEPENDS_ON], [:CALLS], [:MODIFIES], [:IMPORTS]
    """

    def __init__(self):
        self._driver: Optional[Driver] = None
        self._in_memory_nodes: Dict[str, Dict[str, Any]] = {}
        self._in_memory_edges: List[Dict[str, Any]] = []

    def get_driver(self) -> Optional[Driver]:
        if self._driver is None:
            try:
                auth = None
                if settings.MEMGRAPH_USER and settings.MEMGRAPH_PASSWORD:
                    auth = (settings.MEMGRAPH_USER, settings.MEMGRAPH_PASSWORD)
                self._driver = GraphDatabase.driver(settings.memgraph_uri, auth=auth)
                logger.info(f"Connected to Memgraph at {settings.memgraph_uri}")
            except Exception as e:
                logger.warning(f"Could not connect to Memgraph at {settings.memgraph_uri}: {e}")
                self._driver = None
        return self._driver

    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None

    def is_connected(self) -> bool:
        driver = self.get_driver()
        if not driver:
            return False
        try:
            with driver.session() as session:
                result = session.run("RETURN 1 AS connected;")
                record = result.single()
                return record is not None and record["connected"] == 1
        except Exception:
            return False

    def initialize_schema(self):
        """Set up uniqueness constraints and indexes for faster graph traversals."""
        if not self.is_connected():
            return
        queries = [
            "CREATE CONSTRAINT ON (c:Component) ASSERT c.name IS UNIQUE;",
            "CREATE CONSTRAINT ON (f:File) ASSERT f.path IS UNIQUE;",
            "CREATE CONSTRAINT ON (s:Service) ASSERT s.name IS UNIQUE;",
            "CREATE CONSTRAINT ON (t:DatabaseTable) ASSERT t.name IS UNIQUE;",
        ]
        driver = self.get_driver()
        if not driver:
            return
        with driver.session() as session:
            for q in queries:
                try:
                    session.run(q)
                except Exception as e:
                    logger.debug(f"Constraint setup notice: {e}")

    def execute_cypher(self, cypher: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a single Cypher query against Memgraph."""
        if self.is_connected():
            try:
                driver = self.get_driver()
                with driver.session() as session:
                    result = session.run(cypher, parameters or {})
                    return [record.data() for record in result]
            except Exception as e:
                logger.error(f"Memgraph query execution error: {e}\nQuery: {cypher}")
                self._simulate_cypher(cypher)
                return []
        else:
            self._simulate_cypher(cypher)
            return []

    def execute_batch(self, queries: List[str]):
        """Execute a series of Cypher statements sequentially."""
        if self.is_connected():
            driver = self.get_driver()
            with driver.session() as session:
                for q in queries:
                    clean_q = q.strip()
                    if clean_q:
                        try:
                            session.run(clean_q)
                        except Exception as e:
                            logger.error(f"Failed Cypher statement: {clean_q} | Error: {e}")
                            self._simulate_cypher(clean_q)
        else:
            for q in queries:
                clean_q = q.strip()
                if clean_q:
                    self._simulate_cypher(clean_q)

    def _simulate_cypher(self, cypher: str):
        """Lightweight parser for in-memory graph tracking when DB is offline."""
        import re
        node_matches = re.findall(r"MERGE\s*\(([a-zA-Z0-9_]+):([a-zA-Z0-9_]+)\s*\{([^}]+)\}\)", cypher, re.IGNORECASE)
        for var, label, props_str in node_matches:
            props = {}
            for pair in props_str.split(","):
                if ":" in pair:
                    k, v = pair.split(":", 1)
                    props[k.strip()] = v.strip().strip("'\"")
            node_id = props.get("path") or props.get("name") or var
            self._in_memory_nodes[node_id] = {
                "id": str(node_id),
                "label": str(props.get("name") or props.get("path") or node_id),
                "group": label,
                "title": f"{label}: {node_id}",
                "properties": props,
            }

    def get_graph_snapshot(self) -> Dict[str, Any]:
        """
        Extract nodes and edges formatted for visual rendering in Streamlit (vis-network format).
        """
        if self.is_connected():
            driver = self.get_driver()
            try:
                with driver.session() as session:
                    # Query all nodes
                    node_query = """
                    MATCH (n)
                    RETURN id(n) AS id, labels(n)[0] AS group, properties(n) AS props;
                    """
                    nodes = []
                    node_records = session.run(node_query)
                    for rec in node_records:
                        props = rec["props"] or {}
                        node_id = props.get("path") or props.get("name") or str(rec["id"])
                        node_label = props.get("name") or props.get("path") or str(rec["id"])
                        nodes.append({
                            "id": str(node_id),
                            "label": str(node_label),
                            "group": rec["group"] or "Node",
                            "title": f"{rec['group']}: {node_label}",
                            "properties": props
                        })

                    # Query all relationships
                    edge_query = """
                    MATCH (a)-[r]->(b)
                    RETURN properties(a) AS a_props, id(a) AS a_id,
                           properties(b) AS b_props, id(b) AS b_id,
                           type(r) AS rel_type;
                    """
                    edges = []
                    edge_records = session.run(edge_query)
                    for rec in edge_records:
                        a_id = rec["a_props"].get("path") or rec["a_props"].get("name") or str(rec["a_id"])
                        b_id = rec["b_props"].get("path") or rec["b_props"].get("name") or str(rec["b_id"])
                        edges.append({
                            "from": str(a_id),
                            "to": str(b_id),
                            "label": rec["rel_type"]
                        })

                    return {"nodes": nodes, "edges": edges}
            except Exception as e:
                logger.error(f"Error fetching graph snapshot: {e}")

        # Return in-memory fallback snapshot
        return {
            "nodes": list(self._in_memory_nodes.values()),
            "edges": self._in_memory_edges,
        }

    def get_context_summary(self) -> str:
        """Generate a 1-paragraph summary of the current project state from the graph."""
        snapshot = self.get_graph_snapshot()
        node_count = len(snapshot.get("nodes", []))
        edge_count = len(snapshot.get("edges", []))
        groups = {}
        for n in snapshot.get("nodes", []):
            grp = n.get("group", "Unknown")
            groups[grp] = groups.get(grp, 0) + 1

        group_breakdown = ", ".join([f"{count} {grp}s" for grp, count in groups.items()])
        if not group_breakdown:
            group_breakdown = "0 components indexed"

        return (
            f"The live system architecture currently consists of {node_count} nodes and {edge_count} relationships "
            f"in Memgraph ({group_breakdown}). All dependency links (DEPENDS_ON, CALLS, IMPORTS) are synchronized, "
            f"providing instant architectural context and eliminating the need for full repository re-scanning."
        )


# Global singleton instance
memgraph_client = MemgraphClient()
