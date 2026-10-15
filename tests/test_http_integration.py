"""Real HTTP -> FalkorDB -> persistent action -> fresh API, with tenant isolation."""
import os
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from ugi.api import create_app
from ugi.models import Settings, uid
from ugi.store import Store


@pytest.mark.integration
def test_real_http_persistence_and_isolation():
    url = os.getenv("UGI_TEST_REDIS_URL")
    if not url:
        pytest.skip("Requires actual FalkorDB: UGI_TEST_REDIS_URL")
    settings = Settings(backend="falkordb", redis_url=url,
                        graph_prefix="ugi_http_" + uuid4().hex[:12],
                        api_keys="ci-one,ci-two")
    headers = {"X-API-Key": "ci-one", "X-Dataset": "incident"}
    other = {"X-API-Key": "ci-two", "X-Dataset": "incident"}
    try:
        with TestClient(create_app(settings)) as client:
            assert client.get("/api/graph").status_code == 401
            content = (Path(__file__).parents[1] / "demo/incident.json").read_bytes()
            r = client.post("/api/uploads", headers=headers,
                            files={"file": ("incident.json", content)})
            assert r.status_code == 200 and r.json()["claims"] == 8, r.text
            r = client.post("/api/relationships", headers=headers, json={
                "subject": "Checkout", "object": "Cache",
                "predicate": "TRANSITIVELY_DEPENDS_ON"})
            assert r.status_code == 200 and r.json()["status"] == "RULE_DERIVED", r.text
            r = client.post("/api/investigations", headers=headers, json={
                "target": "Cache", "idempotency_key": "ci-case",
                "authorise_action": True})
            assert r.status_code == 200 and r.json()["executed"], r.text
            assert client.get("/api/graph", headers=other).json()["entities"] == []
        with TestClient(create_app(settings)) as client:
            cases = client.get("/api/investigations", headers=headers).json()
            assert len(cases) == 1
            task = client.get("/api/tasks", headers=headers).json()[0]
            r = client.post(f"/api/tasks/{task['id']}/decision", headers=headers,
                            json={"decision": "accepted", "reason": "Evidence reviewed"})
            assert r.status_code == 200 and r.json()["status"] == "accepted", r.text
            assert client.get("/api/investigations", headers=other).json() == []
    finally:
        # Unique prefix: only graphs created by this test may be deleted.
        for api_key in ("ci-one", "ci-two"):
            try:
                store = Store(settings, owner=uid(api_key)[:24], dataset="incident")
                store.client.execute_command("GRAPH.DELETE", store.graph)
            except Exception:
                pass
