"""Regression checks for UI/backend contracts and empty graph states."""
from pathlib import Path

from fastapi.testclient import TestClient

from ugi.api import create_app
from ugi.models import Settings


def test_empty_dataset_returns_supported_empty_shape():
    client = TestClient(create_app(Settings(backend="memory")))
    headers = {"X-Dataset": "brand_new_empty_graph"}
    response = client.get("/api/graph", headers=headers)
    assert response.status_code == 200
    graph = response.json()
    assert graph["entities"] == []
    assert graph["claims"] == []
    assert graph["events"] == []
    assert client.get("/api/tasks", headers=headers).json() == []
    assert client.get("/api/investigations", headers=headers).json() == []


def test_three_demo_presets_have_evidence_in_memory_mode():
    client = TestClient(create_app(Settings(backend="memory")))
    for dataset in ("showcase-b-incident", "showcase-b-supply", "showcase-b-research"):
        result = client.get("/api/graph", headers={"X-Dataset": dataset})
        assert result.status_code == 200
        assert result.json()["counts"]["Entity"] > 0


def test_latest_3d_assets_and_fallback_available():
    client = TestClient(create_app(Settings(backend="memory")))
    assert client.get("/assets/3d-force-graph.min.js").status_code == 200
    assert client.get("/assets/bg.js").status_code == 200
    page = client.get("/").text
    assert 'id="hero-graph-canvas"' in page
    assert page.index("/assets/3d-force-graph.min.js") < page.index("/assets/app.js")
    assert 'id="fallback2d"' in page


def test_ui_does_not_require_unrelated_panels_to_load_graph():
    js = (Path(__file__).parents[1] / "ugi/assets/app.js").read_text()
    assert "Promise.allSettled" in js
    assert 'if (graphResult.status !== "fulfilled") throw graphResult.reason' in js
    assert "Saved investigations unavailable" in js
    assert "Review queue unavailable" in js
    assert "non-JSON response" in js


def test_demo_seed_is_manual_and_never_calls_paid_ai():
    script = (Path(__file__).parents[1] / "ugi/seed_demo.py").read_text()
    assert "--confirm-falkordb" in script
    assert "use_ai=False" in script
    assert 'if store.list("Source", 1):' in script
