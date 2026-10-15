"""Whole-event semantics, backward compatibility, adversarial evidence and real graph tests."""
import os
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from ugi.api import create_app
from ugi.engine import Engine
from ugi.extract import verify
from ugi.models import (
    BatchVerdicts,
    Candidate,
    CompactExtraction,
    RelationEventCandidate,
    RelationQuery,
    Settings,
)
from ugi.nary import event_records, signature, text_events, verify_event, verify_events
from ugi.store import Store

ROOT = Path(__file__).parents[1]
BETWEEN = "Azure Isle lies between Birch Isle, Coral Isle and Dune Isle."


def engine():
    return Engine(Store(Settings(backend="memory")))


def test_text_event_complete_roles_no_binary_projection():
    e = engine()
    report = e.ingest("group.txt", BETWEEN.encode())
    assert report["relation_events"] == 1 and report["claims"] == 0
    assert report["entities"] == 4
    event = e.store.events()[0]
    assert event["relation_type"] == "BETWEEN"
    assert sorted(p["role"] for p in event["participants"]) == ["anchor", "anchor", "anchor", "subject"]
    assert not e.store.claims()
    ev = e.store.get(event["evidence_id"])
    chunk = e.store.get(event["chunk_id"])
    assert chunk["text"][ev["start"]:ev["end"]] == BETWEEN
    assert e.ingest("group.txt", BETWEEN.encode())["duplicate"]
    assert len(e.store.events()) == 1
    assert e.relationship(RelationQuery(subject="Azure Isle", object="Birch Isle", predicate="BETWEEN"))["status"] == "UNKNOWN"


@pytest.mark.parametrize("text,kind,roles", [
    ("Nova Supply provides Sensor Unit to Harbor Factory.", "PROVISION", {"provider", "item", "recipient"}),
    ("Amber Holdings acquired Cedar Labs for USD 5 million in 2024.", "ACQUISITION", {"buyer", "acquired", "consideration"}),
    ("Rhea and Sora collaborated on Atlas Project at Meridian Institute.", "COLLABORATION", {"researcher", "project", "institution"}),
])
def test_cross_domain_events(text, kind, roles):
    e = engine()
    report = e.ingest("example.txt", text.encode())
    assert report["relation_events"] == 1 and report["claims"] == 0
    event = e.store.events()[0]
    assert event["relation_type"] == kind
    assert {p["role"] for p in event["participants"]} == roles
    if kind == "ACQUISITION":
        assert event["event_time"] == "2024-01-01" and event["time_precision"] == "year"
        assert event["recorded_at"] != event["event_time"]


def test_event_qualifiers_and_structured_binary_compatibility():
    e = engine()
    data = (ROOT / "demo/relation_events.json").read_bytes()
    report = e.ingest("mixed.json", data)
    assert report["relation_events"] == 1 and report["claims"] == 1
    event = e.store.events()[0]
    assert event["modality"] == "possible" and event["valid_from"] == "2026-01-01"
    assert event["attribution"] == "Synthetic contract proposal"
    factory_id = next(p["entity_id"] for p in event["participants"] if p["role"] == "recipient")
    assert e.store.claims(factory_id)[0]["predicate"] == "LOCATED_IN"
    assert len(e.store.events(factory_id)) == 1


@pytest.mark.parametrize("mutate", ["drop_anchor", "swap_role", "negation", "uncertainty", "quote", "date", "historical"])
def test_event_rejects_semantic_distortion(mutate):
    event = text_events(BETWEEN)[0].model_copy(deep=True)
    if mutate == "drop_anchor":
        event.participants.pop()
    elif mutate == "swap_role":
        event.participants[0].role, event.participants[1].role = "anchor", "subject"
    elif mutate == "negation":
        event.polarity = "negative"
    elif mutate == "uncertainty":
        event.modality = "possible"
    elif mutate == "quote":
        event.evidence = BETWEEN.replace("Azure", "A-zure")
    elif mutate == "date":
        event.valid_from = "1990-01-01"
    else:
        event.historical = True
    assert verify_event(event, {"text": BETWEEN, "record": None})[0] is False


def test_event_role_order_dedup_occurrences_and_normalization():
    original = text_events(BETWEEN)[0]
    reversed_roles = original.model_copy(deep=True)
    reversed_roles.participants.reverse()
    assert signature(original) == signature(reversed_roles)
    equivalent = original.model_copy(update={"relation_type": "SITUATED_BETWEEN"})
    assert signature(original) == signature(equivalent)
    chunk = {"id": "chunk", "source_id": "source", "text": BETWEEN, "record": None, "location": {}}
    store = Store(Settings(backend="memory"))
    _, _, events, _ = event_records([original, reversed_roles, equivalent], chunk, store, {})
    assert len(events) == 1
    separate = original.model_copy(update={"occurrence_id": "different occurrence"})
    _, _, events, _ = event_records([original, separate], chunk, store, {})
    assert len(events) == 2


def test_repeated_occurrences_preserve_distinct_evidence_offsets():
    e = engine()
    text = BETWEEN + "\n" + BETWEEN
    report = e.ingest("repeated.txt", text.encode())
    assert report["relation_events"] == 2
    offsets = [e.store.get(event["evidence_id"])["start"] for event in e.store.events()]
    assert sorted(offsets) == [0, len(BETWEEN) + 1]


def test_hallucinated_offset_and_day_are_rejected():
    event = text_events(BETWEEN)[0].model_copy(update={"evidence_start": 10})
    assert not verify_event(event, {"text": BETWEEN, "record": None})[0]
    text = "Atlas, Birch and Cedar attended the gathering in 2024."
    candidate = RelationEventCandidate(
        relation_type="ATTENDANCE", participants=[{"role": "attendee", "name": n}
                                                    for n in ["Atlas", "Birch", "Cedar"]],
        evidence=text, event_time="2024-05-12", time_precision="day",
    )
    assert not verify_event(candidate, {"text": text, "record": None})[0]


def test_model_cannot_invent_external_identity_links():
    candidate = text_events(BETWEEN)[0].model_copy(deep=True)
    candidate.participants[0].external_id = "guessed:known-record"
    assert not verify_event(candidate, {"text": BETWEEN, "record": None})[0]


def test_event_schema_validation():
    original = text_events(BETWEEN)[0].model_dump()
    with pytest.raises(ValidationError):
        RelationEventCandidate.model_validate({**original, "participants": original["participants"][:2]})
    with pytest.raises(ValidationError):
        RelationEventCandidate.model_validate({**original, "valid_from": "2025-01-01", "valid_to": "2020-01-01"})
    with pytest.raises(ValidationError):
        RelationEventCandidate.model_validate({**original, "participants": [original["participants"][0]] * 3})


def test_unsupported_binary_group_remains_withheld():
    for p in ["LIES_BETWEEN", "SITUATED_BETWEEN", "IS_LOCATED_BETWEEN"]:
        c = Candidate(subject="Azure Isle", predicate=p, object="Birch Isle", evidence=BETWEEN)
        assert not verify(c, {"text": BETWEEN, "record": None})[0]


def test_ambiguous_actor_and_malformed_group_abstain():
    e = engine()
    text = "Atlas is a region beside Birch, which is situated between Cedar and Delta."
    assert not text_events(text)
    assert not e.ingest("ambiguous.txt", text.encode())["relation_events"]
    assert not text_events("Atlas lies between Birch.")


def test_compact_local_event_conversion_without_extra_call_for_clear_grammar():
    class Local:
        is_local = True
        usage = {"calls": 0}

        def request(self, prompt, schema):
            self.usage["calls"] += 1
            assert schema is CompactExtraction
            return CompactExtraction(relations=[], events=text_events(BETWEEN))

    e = engine()
    local = Local()
    e.provider_factory = lambda: local
    result = e.ingest("local.txt", BETWEEN.encode(), use_ai=True)
    assert result["relation_events"] == 1 and local.usage["calls"] == 1


def test_unparsed_event_batch_omissions_and_provider_failure_fail_closed():
    text = "Atlas, with Birch and Cedar, took part in the joint trial."
    event = RelationEventCandidate(relation_type="JOINT_TRIAL", evidence=text, participants=[
        {"role": "participant", "name": name} for name in ["Atlas", "Birch", "Cedar"]])

    class Reviewer:
        def request(self, prompt, schema):
            assert schema is BatchVerdicts
            return BatchVerdicts(decisions=[])

    assert not verify_events([event], {"text": text, "record": None}, Reviewer())[0][0]

    class Broken:
        def request(self, *_):
            raise ValueError("budget exhausted")

    assert "unavailable" in verify_events([event], {"text": text, "record": None}, Broken())[0][1]


def test_event_api_isolation_historical_filter_and_evidence():
    client = TestClient(create_app(Settings(backend="memory", api_keys="owner-a,owner-b")))
    headers = {"X-API-Key": "owner-a", "X-Dataset": "research"}
    assert client.post("/api/uploads", headers=headers, files={"file": (
        "events.json", (ROOT / "demo/relation_events.json").read_bytes())}).status_code == 200
    events = client.get("/api/events", headers=headers).json()["events"]
    assert len(events) == 1
    assert client.get("/api/events?as_of=2020-01-01", headers=headers).json()["events"] == []
    assert len(client.get("/api/events?as_of=2026-06-01", headers=headers).json()["events"]) == 1
    assert client.get("/api/events?as_of=invalid", headers=headers).status_code == 422
    participant = events[0]["participants"][0]["entity_id"]
    assert client.get("/api/events", headers=headers, params={"entity_id": participant}).json()["events"]
    assert client.get("/api/graph", headers=headers).json()["events"]
    assert not client.get("/api/events", headers={"X-API-Key": "owner-b", "X-Dataset": "research"}).json()["events"]
    evidence_id = events[0]["evidence_id"]
    assert client.get("/api/records/" + evidence_id, headers=headers).json()["quote"]


@pytest.mark.integration
def test_real_nary_roles_reconnect_atomicity_and_isolation():
    url = os.getenv("UGI_TEST_REDIS_URL")
    if not url:
        pytest.skip("Requires real FalkorDB")
    settings = Settings(redis_url=url, graph_prefix="ugi_nary_" + uuid4().hex[:12])
    store, other = Store(settings), None
    try:
        e = Engine(store)
        report = e.ingest("events.txt", (ROOT / "demo/relation_events.txt").read_bytes())
        assert report["relation_events"] == 4 and report["claims"] == 0
        rows = store.query("MATCH (:RelationEvent)-[p:HAS_PARTICIPANT]->(:Entity) "
                           "RETURN p.role,count(p)")
        assert sum(row[1] for row in rows) == 14
        assert dict(rows)["anchor"] == 3 and dict(rows)["researcher"] == 2
        again = Store(settings)
        assert len(again.events()) == 4
        participant = again.events()[0]["participants"][0]["entity_id"]
        assert again.events(participant)
        assert not store.claims()
        assert store.query("MATCH ()-[r:RELATES]->() RETURN count(r)") == [[0]]
        other = Store(settings, dataset="other")
        assert not other.events()
        assert e.ingest("events.txt", (ROOT / "demo/relation_events.txt").read_bytes())["duplicate"]
    finally:
        for target in [store, other]:
            if target:
                assert target.graph.startswith(settings.graph_prefix + "_")
                target.client.execute_command("GRAPH.DELETE", target.graph)
