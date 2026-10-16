from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ugi.api import create_app
from ugi.models import Settings


def test_dashboard_assets_and_historical_view_are_real_backend_results():
    client = TestClient(create_app(Settings(backend="memory")))
    assert client.get("/").status_code == 200
    assert client.get("/assets/app.js").status_code == 200
    assert client.get("/assets/style.css").status_code == 200
    assert client.get("/assets/not-allowed.txt").status_code == 404
    fixture = Path(__file__).parents[1] / "demo/research_network.json"
    uploaded = client.post("/api/uploads", files={"file": (fixture.name, fixture.read_bytes())})
    assert uploaded.json()["claims"] == 2
    graph = client.get("/api/graph?as_of=2021-06-01").json()
    assert len(graph["claims"]) == 2 and len(graph["events"]) == 1
    later = client.get("/api/graph?as_of=2023-06-01").json()
    assert len(later["claims"]) == 1 and not later["events"]
    assert later["unknown_dates_excluded"]
    assert client.get("/api/graph?as_of=invalid").status_code == 422


def test_memory_showcase_selection_populates_the_named_demo_dataset():
    client = TestClient(create_app(Settings(backend="memory")))
    graph = client.get("/api/graph", headers={"X-Dataset": "showcase-b-incident"}).json()
    assert graph["counts"]["Entity"] > 0
    assert graph["counts"]["Claim"] > 0


@pytest.mark.parametrize("precision,point,inside,outside", [
    ("year", "2021-01-01", "2021-06-15", "2022-01-01"),
    ("month", "2021-06-01", "2021-06-15", "2021-07-01"),
    ("day", "2021-06-15", "2021-06-15", "2021-06-16"),
])
def test_graph_and_event_endpoints_agree_on_event_precision(precision, point, inside, outside):
    import json

    client = TestClient(create_app(Settings(backend="memory")))
    event = {"relation_type": "PROVISION", "event_time": point, "time_precision": precision,
             "participants": [{"role": role, "name": name} for role, name in
                              [("provider", "Ada"), ("item", "Sensor"), ("recipient", "Factory")]]}
    response = client.post("/api/uploads", files={"file": ("event.json", json.dumps([event]).encode())})
    assert response.status_code == 200 and response.json()["relation_events"] == 1
    for endpoint in ("/api/graph", "/api/events"):
        assert len(client.get(endpoint + "?as_of=" + inside).json()["events"]) == 1
        assert not client.get(endpoint + "?as_of=" + outside).json()["events"]
