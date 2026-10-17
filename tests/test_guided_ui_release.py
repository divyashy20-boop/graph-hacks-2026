from pathlib import Path
from fastapi.testclient import TestClient
from ugi.api import create_app
from ugi.models import Settings


def test_collaborator_ui_and_guided_assets_available():
    client = TestClient(create_app(Settings(backend="memory")))
    page = client.get("/")
    assert page.status_code == 200
    assert '/assets/app.js?v=ui-008' in page.text
    assert '/assets/guided.js?v=ugi-p5' in page.text
    assert 'id="orbitCanvas"' in page.text
    assert 'id="guidedpanel"' in page.text
    assert 'Use configured AI provider' in page.text
    assert client.get("/assets/guided.js").status_code == 200
    assert client.get("/assets/style.css").status_code == 200
    assert client.get("/assets/not-allowed.txt").status_code == 404


def test_collaborator_demo_memory_seed_and_integrated_routes():
    client = TestClient(create_app(Settings(backend="memory")))
    graph = client.get("/api/graph", headers={"X-Dataset": "showcase-b-incident"})
    assert graph.status_code == 200
    assert graph.json()["counts"]["Entity"] > 0
    from fastapi.routing import APIRoute
    routes = {r.path for r in client.app.routes if isinstance(r, APIRoute)}
    assert "/api/agent/guided" in routes
    assert "/api/agent/receipts/{receipt_id}/freshness" in routes
    assert "/api/events" in routes


def test_additive_ui_adapter_does_not_replace_native_orbit():
    root = Path(__file__).parents[1]
    app = (root / "ugi/assets/app.js").read_text(encoding="utf-8")
    guided = (root / "ugi/assets/guided.js").read_text(encoding="utf-8")
    assert 'function createOrbitRenderer(' in app
    assert 'function setViewMode(' in app
    assert '/api/agent/guided' in guided
    assert '/freshness' in guided
    assert 'queryHighlights = new Set(' in guided
    assert 'innerHTML' not in guided
