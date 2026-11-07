import pytest
from app.core.memgraph_client import MemgraphClient


def test_memgraph_client_snapshot_and_summary():
    client = MemgraphClient()

    # Simulate Cypher query execution
    sample_cyphers = [
        "MERGE (c:Component {name: 'AuthService', type: 'service'});",
        "MERGE (f:File {path: 'app/auth.py', language: 'python'});",
    ]
    client.execute_batch(sample_cyphers)

    snapshot = client.get_graph_snapshot()
    assert "nodes" in snapshot
    assert "edges" in snapshot
    assert len(snapshot["nodes"]) >= 2

    # Context summary test
    summary = client.get_context_summary()
    assert "Memgraph" in summary
    assert "nodes" in summary
    assert "relationships" in summary
