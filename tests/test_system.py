import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ugi.api import create_app
from ugi.engine import Engine
from ugi.extract import grounded, parse, text_candidates, verify
from ugi.models import Candidate, InvestigationRequest, RelationQuery, Settings
from ugi.store import Store

ROOT = Path(__file__).parents[1]


@pytest.fixture
def engine():
    return Engine(Store(Settings(backend="memory")))


def relation(engine, s, o, p, **kwargs):
    return engine.relationship(RelationQuery(subject=s, object=o, predicate=p, **kwargs))


def incident(engine):
    return engine.ingest("incident.json", (ROOT / "demo/incident.json").read_bytes())


def test_full_agent_action_idempotent_and_evidence(engine):
    report = incident(engine)
    assert report["claims"] == 8
    assert engine.ingest("incident.json", (ROOT / "demo/incident.json").read_bytes())["duplicate"]
    assert relation(engine, "Checkout", "Gateway", "DEPENDS_ON")["status"] == "SOURCE_ASSERTED"
    answer = relation(engine, "Checkout", "Cache", "TRANSITIVELY_DEPENDS_ON")
    assert answer["status"] == "RULE_DERIVED" and answer["rules"]
    for item in answer["evidence"]:
        ev = item["evidence"]
        chunk = engine.store.get(ev["chunk_id"])
        assert chunk["text"][ev["start"]:ev["end"]] == ev["quote"]
    request = InvestigationRequest(target="Cache", idempotency_key="case-1", authorise_action=True)
    case = engine.investigate(request, "tester")
    assert case["executed"] and len(case["affected_entity_ids"]) == 2
    assert case["priority"] == "high"
    assert len(engine.store.list("Investigation")) == 1
    assert len(engine.store.list("AgentAction")) == 1
    assert engine.store.list("ReviewTask")
    assert engine.investigate(request, "tester")["duplicate"]
    assert len(engine.store.list("AgentAction")) == 1


@pytest.mark.parametrize("s,o,p,status", [
    ("Cache", "Redis", "USES", "CONTRADICTED"),
    ("Checkout", "Cache", "DEPENDS_ON", "CONNECTED_ONLY"),
    ("Checkout", "Cache", "CAUSED", "CONNECTED_ONLY"),
    ("Cache", "Incident 7", "CAUSED", "UNKNOWN"),
    ("Nobody", "Cache", "DEPENDS_ON", "UNKNOWN"),
    ("Cache", "Legacy Store", "USES", "UNKNOWN"),
])
def test_status_semantics(engine, s, o, p, status):
    incident(engine)
    assert relation(engine, s, o, p)["status"] == status


def test_historical_and_current_queries(engine):
    incident(engine)
    assert relation(engine, "Cache", "Legacy Store", "USES", as_of="2021-06-01")["status"] == "SOURCE_ASSERTED"
    assert relation(engine, "Cache", "Legacy Store", "USES", as_of="2024-01-01")["status"] == "UNKNOWN"
    # Undated dependency is not evidence of validity at an arbitrary historical date.
    assert relation(engine, "Checkout", "Gateway", "DEPENDS_ON", as_of="1990-01-01")["status"] == "UNKNOWN"


def test_hypotheses_separate_and_reevaluated(engine):
    incident(engine)
    h = relation(engine, "Cache", "Checkout", "MAY_AFFECT", allow_hypothesis=True)
    assert h["status"] == "HYPOTHESIS" and h["hypotheses"][0]["missing_evidence"]
    assert engine.store.counts()["Claim"] == 8
    update = [{"subject": "Cache", "subject_id": "svc:cache", "subject_type": "Service",
               "object": "Checkout", "object_id": "svc:checkout", "object_type": "Service",
               "predicate": "MAY_AFFECT", "polarity": "negative"}]
    engine.ingest("update.json", json.dumps(update).encode())
    assert engine.store.list("Hypothesis")[0]["evaluation_status"] == "SOURCE_NEGATED"
    assert engine.store.list("Hypothesis")[0]["state"] == "resolved"


def test_shared_employer_is_not_friendship(engine):
    engine.ingest("people.txt", b"Alice works at Acme. Bob works at Acme.")
    answer = relation(engine, "Alice", "Bob", "FRIENDS_WITH", allow_hypothesis=True)
    assert answer["status"] == "CONNECTED_ONLY" and not answer["hypotheses"]


def test_same_name_identity_collision_and_alias(engine):
    for identifier in ["person:1", "person:2"]:
        engine.ingest(identifier + ".json", json.dumps([{
            "subject": "Alex", "subject_id": identifier, "subject_aliases": ["A. Lee"],
            "predicate": "owns", "object": identifier + " Car",
        }]).encode())
    assert engine.resolve("Alex") is None and engine.resolve("A. Lee") is None
    assert len(engine.store.entities("Alex")) == 2
    assert engine.store.list("MergeDecision")


def test_no_cross_document_name_only_merge(engine):
    engine.ingest("one.txt", b"Alex owns Blue Car.")
    engine.ingest("two.txt", b"Alex owns Red Car.")
    assert len(engine.store.entities("Alex")) == 2


def test_unrelated_domain_open_predicates(engine):
    report = engine.ingest("supply.csv", (ROOT / "demo/supply_chain.csv").read_bytes())
    assert report["claims"] == 4
    assert relation(engine, "Orchard Cooperative", "Green Council", "CERTIFIED_BY")["status"] == "SOURCE_ASSERTED"
    assert relation(engine, "Orchard Cooperative", "Northport", "LOCATED_IN")["status"] == "CONNECTED_ONLY"
    report = engine.ingest("open.txt", (ROOT / "demo/open_text.txt").read_bytes())
    assert report["claims"] == 5
    assert "LICENSES_DESIGNS_TO" in {c["predicate"] for c in engine.store.claims()}
    temporal = next(c for c in engine.store.claims() if c["subject"] == "Flora")
    assert temporal["valid_from"] == "2020-01-01" and temporal["valid_to"] == "2022-12-31"


@pytest.mark.parametrize("payload,filename", [
    (b"", "x.txt"), (b"[]", "x.json"), (b"{no", "x.json"),
    (b"data", "x.exe"), (b"a,a\n1,2", "x.csv"), (b"a,b\n1", "x.csv"),
    (b"\xff", "x.txt"), (b'{"x":1}\ninvalid', "x.jsonl"),
])
def test_bad_inputs_are_rejected(engine, payload, filename):
    with pytest.raises(ValueError):
        engine.ingest(filename, payload)
    assert engine.store.counts()["Claim"] == 0


def test_limits_atomic_quota(engine):
    limited = Engine(Store(Settings(backend="memory", max_nodes=1)))
    with pytest.raises(ValueError, match="quota"):
        limited.ingest("test.txt", b"Alice owns Acme.")
    assert limited.store.counts()["Source"] == 0
    with pytest.raises(ValueError):
        parse("test.txt", b"a" * 20, Settings(max_upload_bytes=10))
    with pytest.raises(ValueError):
        parse("test.json", b"[1,2]", Settings(max_records=1))


@pytest.mark.parametrize("proposed,reason", [
    ({"subject": "Acme", "object": "Alice", "predicate": "owns"}, "direction"),
    ({"subject": "Alice", "object": "Acme", "predicate": "knows"}, "predicate"),
    ({"subject": "Alice", "object": "Acme", "predicate": "owns", "polarity": "negative"}, "negation"),
])
def test_cooccurrence_does_not_prove_relation(proposed, reason):
    chunk = {"text": "Alice owns Acme.", "record": None}
    candidate = Candidate(**proposed, evidence=chunk["text"])
    assert grounded(candidate, chunk)[0]
    assert not verify(candidate, chunk)[0], reason


def test_invented_dates_and_lost_speculation():
    chunk = {"text": "Alice may own Acme.", "record": None}
    assert not verify(Candidate(subject="Alice", object="Acme", predicate="own",
                                evidence=chunk["text"]), chunk)[0]
    candidate = Candidate(subject="Alice", object="Acme", predicate="own", modality="possible",
                          evidence=chunk["text"], valid_from="1999-01-01")
    assert not grounded(candidate, chunk)[0]


def test_action_preview_unknown_and_concurrency(engine):
    incident(engine)
    preview = engine.investigate(InvestigationRequest(target="Cache", idempotency_key="preview"), "me")
    assert not preview["executed"] and not engine.store.list("Investigation")
    assert not engine.investigate(InvestigationRequest(target="Missing", idempotency_key="x"), "me")["executed"]
    request = InvestigationRequest(target="Cache", idempotency_key="once", authorise_action=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: engine.investigate(request, "me"), range(4)))
    assert all(r["executed"] for r in results)
    assert len(engine.store.list("AgentAction")) == 1


def test_traversal_limit_is_visible(engine):
    incident(engine)
    engine.settings.max_expansions = 1
    with pytest.raises(ValueError, match="budget"):
        relation(engine, "Checkout", "Cache", "FRIENDS_WITH")


def test_api_full_flow_auth_isolation_and_review():
    app = create_app(Settings(backend="memory", api_keys="key-one,key-two"))
    with TestClient(app) as client:
        assert client.get("/api/graph").status_code == 401
        headers = {"X-API-Key": "key-one", "X-Dataset": "incident"}
        uploaded = client.post("/api/uploads", headers=headers,
                               files={"file": ("incident.json", (ROOT / "demo/incident.json").read_bytes())})
        assert uploaded.status_code == 200, uploaded.text
        query = client.post("/api/relationships", headers=headers, json={
            "subject": "Checkout", "object": "Cache", "predicate": "TRANSITIVELY_DEPENDS_ON"})
        assert query.json()["status"] == "RULE_DERIVED"
        case = client.post("/api/investigations", headers=headers, json={
            "target": "Cache", "idempotency_key": "api-case", "authorise_action": True})
        assert case.status_code == 200 and case.json()["executed"]
        task = client.get("/api/tasks", headers=headers).json()[0]
        decision = client.post(f'/api/tasks/{task["id"]}/decision', headers=headers,
                               json={"decision": "accepted", "reason": "Reviewed the cited evidence"})
        assert decision.status_code == 200
        assert client.post(f'/api/tasks/{task["id"]}/decision', headers=headers,
                           json={"decision": "rejected", "reason": "Attempting a second decision"}).status_code == 409
        assert not client.get("/api/graph", headers={"X-API-Key": "key-two", "X-Dataset": "incident"}).json()["entities"]
        assert not client.get("/api/graph", headers={"X-API-Key": "key-one", "X-Dataset": "other"}).json()["entities"]
        assert client.get("/api/records/unknown", headers=headers).status_code == 404
        assert "Universal Graph Intelligence" in client.get("/").text


def test_api_rate_limit_and_invalid_query():
    client = TestClient(create_app(Settings(backend="memory", requests_per_minute=1)))
    assert client.get("/api/graph").status_code == 200
    assert client.get("/api/graph").status_code == 429
    fresh = TestClient(create_app(Settings(backend="memory")))
    assert fresh.post("/api/relationships", json={"subject": "a", "object": "b", "predicate": "x",
                                                "as_of": "invalid"}).status_code == 422


def test_temporal_negation_grammar():
    candidates = text_candidates("Rhea does not work for Nova. Iris may advise Oak. "
                                 "Pine previously owns Quartz.")
    assert len(candidates) == 3
    assert candidates[0].polarity == "negative"
    assert candidates[1].modality == "possible"
    assert candidates[2].historical
