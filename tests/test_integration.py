import os
from pathlib import Path
from uuid import uuid4

import pytest

from ugi.engine import Engine
from ugi.models import InvestigationRequest, RelationQuery, Settings
from ugi.store import Store


@pytest.mark.integration
def test_real_falkordb_action_reconnect_evidence_and_isolation():
    url = os.getenv("UGI_TEST_REDIS_URL")
    if not url:
        pytest.skip("UGI_TEST_REDIS_URL absent: real server not exercised")
    settings = Settings(redis_url=url, graph_prefix="ugi_test_" + uuid4().hex[:12])
    store = Store(settings)
    other = None
    try:
        assert store.ping()
        engine = Engine(store)
        data = (Path(__file__).parents[1] / "demo/incident.json").read_bytes()
        assert engine.ingest("incident.json", data)["claims"] == 8
        case = engine.investigate(InvestigationRequest(target="Cache", idempotency_key="real",
                                                       authorise_action=True), "integration")
        assert case["executed"] and len(case["affected_entity_ids"]) == 2
        reconnected = Store(settings)
        assert reconnected.get(case["id"])["kind"] == "Investigation"
        assert reconnected.list("ReviewTask") and reconnected.list("AgentAction")
        assert Engine(reconnected).relationship(RelationQuery(
            subject="Checkout", object="Cache", predicate="TRANSITIVELY_DEPENDS_ON"))["status"] == "RULE_DERIVED"
        assert engine.ingest("incident.json", data)["duplicate"]
        assert store.query("MATCH ()-[r:RELATES]->() RETURN count(r)") == [[8]]
        other = Store(settings, dataset="isolated")
        assert not other.list("Entity")
        # Failed write must be atomic in the actual graph engine.
        with pytest.raises(Exception):
            store.query("FOREACH(i IN [1,0] | CREATE (:RollbackProbe {v:1/i}))")
        assert store.query("MATCH (n:RollbackProbe) RETURN count(n)") == [[0]]
    finally:
        for target in [store, other]:
            if target is not None:
                assert target.graph.startswith(settings.graph_prefix + "_")
                target.client.execute_command("GRAPH.DELETE", target.graph)
