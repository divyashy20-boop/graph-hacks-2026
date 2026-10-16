"""Synthetic identity semantics, not a calibrated real-world linking benchmark."""
import json
import os
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from ugi.api import create_app
from ugi.engine import Engine
from ugi.identity import ArtifactRequest, IdentityChange, IdentityLedger
from ugi.models import RelationQuery, Settings, uid
from ugi.store import IMMUTABLE_KINDS, Store


def row(name="Rahul Sharma", external_id=None, **kwargs):
    return dict(subject=name, subject_id=external_id, subject_type="Person",
                predicate="WORKS_AT", object="Willow", object_type="Organisation", **kwargs)


def ingest(store, records):
    return Engine(store).ingest("records.json", json.dumps(records).encode())


def snapshots(store, text="Rahul Sharma"):
    return sorted([m for m in store.list("MentionSnapshot") if m["text"] == text], key=lambda m: m["id"])


def change(operation, mids=(), **kwargs):
    return IdentityChange(operation=operation, mention_snapshot_ids=list(mids),
                          reason="Synthetic controlled identity experiment", authorise_action=True,
                          idempotency_key=kwargs.pop("idempotency_key", uuid4().hex), **kwargs)


def check_reversal_and_freshness(store):
    ingest(store, [row(external_id="registry:one"), row(external_id="registry:two"),
                   row("Noor", "registry:three")])
    ledger = IdentityLedger(store)
    mentions = snapshots(store)
    mids = [m["id"] for m in mentions]
    anchors = [ledger.assignment(mid)["cluster_id"] for mid in mids]
    assert len(set(anchors)) == 2  # Identical name, distinct supplied identifiers.
    untouched = snapshots(store, "Noor")[0]["id"]
    artifact = ledger.artifact(ArtifactRequest(mention_snapshot_ids=mids, output="Unverified test plan",
                                              idempotency_key="plan", authorise_action=True))
    unrelated = ledger.artifact(ArtifactRequest(mention_snapshot_ids=[untouched], output="Other plan",
                                               idempotency_key="other", authorise_action=True))
    assert ledger.freshness(artifact["id"])["state"] == "current_inputs_only"
    frozen = {k: deepcopy(store.list(k, 20000)) for k in IMMUTABLE_KINDS
              if k not in {"IdentityRevision", "KnowledgeRevision"}}
    claims = deepcopy(store.claims())
    request = change("provisional_merge", mids, idempotency_key="merge")
    revision = ledger.revise(request, "controlled_test")
    assert ledger.revise(request, "controlled_test") == revision
    assert revision["identifier_conflict"] and revision["status"] == "provisional"
    assert not revision["eligible_for_inference"]
    assert len({ledger.assignment(mid)["cluster_id"] for mid in mids}) == 1
    assert revision["affected_artifact_ids"] == [artifact["id"]]
    assert set(revision["affected_record_ids"]) == {m["dependent_record_id"] for m in mentions}
    assert ledger.freshness(artifact["id"])["state"] == "stale"
    assert ledger.freshness(unrelated["id"])["state"] == "current_inputs_only"
    assert len(store.list("KnowledgeRevision")) == 1
    undo = ledger.revise(change("revert", revision_id=revision["id"]), "controlled_test")
    assert undo["reverts_id"] == revision["id"]
    assert [ledger.assignment(mid)["cluster_id"] for mid in mids] == anchors
    assert ledger.freshness(artifact["id"])["state"] == "stale"  # Undo is not re-evaluation.
    assert store.claims() == claims
    for kind, before in frozen.items():
        assert store.list(kind, 20000) == before
    result = Engine(store).relationship(RelationQuery(subject="Rahul Sharma", object="Willow",
                                                      predicate="WORKS_AT"))
    assert result["status"] == "UNKNOWN"  # Provisional union never resolves name ambiguity.
    return revision, undo, artifact


def test_provisional_merge_reverse_selective_invalidation_without_evidence_loss():
    check_reversal_and_freshness(Store(Settings(backend="memory", identity_ledger=True)))


def test_typed_ids_rename_card_history_and_system_time(monkeypatch):
    store = Store(Settings(backend="memory", identity_ledger=True))
    monkeypatch.setattr("ugi.identity.now", lambda: "2026-10-16T00:00:00+00:00")
    report = ingest(store, [row("Vega", "registry:one")])
    first = snapshots(store, "Vega")[0]
    ledger = IdentityLedger(store)
    eid = first["entity_id"]
    original = ledger.card(eid)
    monkeypatch.setattr("ugi.identity.now", lambda: "2026-10-16T01:00:00+00:00")
    ingest(store, [row("Nova", "registry:one", valid_from="2020-01-01", time_precision="day")])
    second = snapshots(store, "Nova")[0]
    assert second["entity_id"] == eid
    assert second["recorded_at"].startswith("2026")
    assert store.get(second["dependent_record_id"])["valid_from"].startswith("2020")
    current = ledger.card(eid)
    assert len(current["versions"]) == 2
    assert {m["mention"]["text"] for m in current["mentions"]} == {"Vega", "Nova"}
    assert len({m["cluster_id"] for m in current["mentions"]}) == 1
    assert ledger.card(eid, "2026-10-16T00:30:00+00:00")["versions"] == original["versions"]
    assert ledger.assignment(second["id"], "2026-10-16T00:30:00+00:00") is None
    request = change("split", [first["id"]])
    revision = ledger.revise(request, "test")
    assert ledger.assignment(first["id"], "2026-10-16T00:30:00+00:00")["cluster_id"] == eid
    assert ledger.assignment(first["id"])["revision_id"] == revision["id"]
    assert ledger.assignment(second["id"])["cluster_id"] == eid
    assert store.get(report["source_id"])
    with pytest.raises(ValueError, match="timezone"):
        ledger.card(eid, "2026-10-16")


def test_name_alone_never_links_different_documents_and_duplicate_is_noop():
    store = Store(Settings(backend="memory", identity_ledger=True))
    ingest(store, [row()])
    ingest(store, [row(predicate_alias="different-source-content")])
    # Unknown source fields change source hash, not identity evidence.
    items = snapshots(store)
    assert len(items) == 2 and len({m["entity_id"] for m in items}) == 2
    before = store.counts()
    assert ingest(store, [row()])["duplicate"]
    assert before == store.counts()


def test_later_decision_and_idempotency_conflicts_reject_atomically():
    store = Store(Settings(backend="memory", identity_ledger=True))
    ingest(store, [row(external_id="id1"), row(external_id="id2")])
    ledger = IdentityLedger(store)
    mids = [m["id"] for m in snapshots(store)]
    request = change("provisional_merge", mids, idempotency_key="stable")
    revision = ledger.revise(request, "actor")
    ledger.revise(change("split", mids[:1]), "actor")
    before = deepcopy(store.records)
    with pytest.raises(ValueError, match="later identity"):
        ledger.revise(change("revert", revision_id=revision["id"]), "actor")
    with pytest.raises(ValueError, match="Idempotency"):
        ledger.revise(request.model_copy(update={"reason": "changed"}), "actor")
    assert store.records == before


@pytest.mark.parametrize("kind", sorted(IMMUTABLE_KINDS))
def test_immutable_record_guard_including_kind_changes_and_copy_isolation(kind):
    store = Store(Settings(backend="memory"))
    record = dict(id="frozen", kind=kind, text="original")
    store.commit([record])
    record["text"] = "mutated caller"
    returned = store.get("frozen")
    returned["text"] = "mutated reader"
    assert store.get("frozen")["text"] == "original"
    for update in (dict(id="frozen", kind=kind, text="new"), dict(id="frozen", kind="Entity")):
        with pytest.raises(ValueError, match="Immutable"):
            store.commit([dict(id="not-written", kind="Source"), update])
        assert store.get("not-written") is None
    store.commit([store.get("frozen")])  # Exact replay is allowed.


def test_optin_limits_and_whole_event_dependencies_are_atomic():
    store = Store(Settings(backend="memory", identity_ledger=True))
    ingest(store, [dict(relation_type="COLLABORATION", participants=[
        dict(role="researcher", name="Vega"), dict(role="researcher", name="Noor"),
        dict(role="project", name="Project")])])
    event = store.events()[0]
    assert len(store.list("MentionSnapshot")) == 3 and not store.claims()
    assert all(m["dependent_record_id"] == event["id"] for m in store.list("MentionSnapshot"))
    before = deepcopy(store.records)
    from ugi.benchmark_conversion import payload

    with pytest.raises(ValueError, match="mention budget"):
        Engine(store).ingest("over.csv", payload(101, "csv"))
    assert store.records == before
    plain = Store(Settings(backend="memory"))
    ingest(plain, [row()])
    assert not plain.list("EntityCard")


def test_revision_cross_type_unknown_mentions_and_missing_authorization_reject():
    store = Store(Settings(backend="memory", identity_ledger=True))
    ingest(store, [row()])
    ledger = IdentityLedger(store)
    mids = [m["id"] for m in store.list("MentionSnapshot")]
    with pytest.raises(ValueError, match="Cross-type"):
        ledger.revise(change("provisional_merge", mids), "actor")
    with pytest.raises(ValueError, match="Missing MentionSnapshot"):
        ledger.revise(change("split", ["unknown"]), "actor")
    with pytest.raises(ValueError, match="authorise_action"):
        ledger.revise(change("split", mids[:1]).model_copy(update={"authorise_action": False}), "actor")
    with pytest.raises(ValueError, match="authorise_action"):
        ledger.artifact(ArtifactRequest(mention_snapshot_ids=mids, output="No", idempotency_key="no"))


def test_history_and_dependency_fanout_limits_preserve_state():
    from ugi.identity import VERSION

    store = Store(Settings(backend="memory", identity_ledger=True))
    ingest(store, [row()])
    ledger = IdentityLedger(store)
    mid = snapshots(store)[0]["id"]
    head_id = uid(VERSION, "assignment", mid)
    head = store.get(head_id)
    store.commit([{**head, "version": 200}])
    before = deepcopy(store.records)
    with pytest.raises(ValueError, match="history budget"):
        ledger.revise(change("split", [mid]), "test")
    assert store.records == before
    store.commit([head])
    store.commit([dict(id="artifact"+str(i), kind="DerivedArtifact") for i in range(201)],
                 [("artifact"+str(i), mid, "USES_IDENTITY", str(i)) for i in range(201)])
    before = deepcopy(store.records)
    with pytest.raises(ValueError, match="fanout budget"):
        ledger.revise(change("split", [mid]), "test")
    assert store.records == before


def test_immutability_does_not_conflate_boolean_and_number():
    store = Store(Settings(backend="memory"))
    store.commit([dict(id="frozen", kind="MentionSnapshot", value=True)])
    with pytest.raises(ValueError, match="Immutable"):
        store.commit([dict(id="frozen", kind="MentionSnapshot", value=1)])


def test_http_optin_tenant_isolation_authorization_and_safe_projection():
    settings = Settings(backend="memory", identity_ledger=True, api_keys="test-one,test-two")
    with TestClient(create_app(settings)) as client:
        headers = {"X-API-Key": "test-one", "X-Dataset": "identity"}
        response = client.post("/api/uploads", headers=headers,
                               files={"file": ("people.json", json.dumps([row()]).encode())})
        assert response.status_code == 200, response.text
        entity = client.get("/api/entities", params={"name": "Rahul Sharma"}, headers=headers).json()[0]
        url = "/api/identity/cards/" + entity["id"]
        card = client.get(url, headers=headers).json()
        mid = card["mentions"][0]["mention"]["id"]
        assert client.get(url).status_code == 401
        assert client.get(url, headers={**headers, "X-API-Key": "test-two"}).status_code == 422
        assert client.get(url, headers={**headers, "X-Dataset": "other"}).status_code == 422
        request = change("split", [mid]).model_dump()
        assert client.post("/api/identity/revisions", headers=headers,
                           json={**request, "eligible_for_inference": True}).status_code == 422
        assert client.post("/api/identity/revisions", headers=headers,
                           json={**request, "authorise_action": False}).status_code == 422
        result = client.post("/api/identity/revisions", headers=headers, json=request)
        assert result.status_code == 200 and not result.json()["eligible_for_inference"], result.text
        artifact = client.post("/api/identity/artifacts", headers=headers, json=dict(
            mention_snapshot_ids=[mid], output="Test output", idempotency_key="http", authorise_action=True))
        assert artifact.status_code == 200, artifact.text
        assert client.get("/api/identity/artifacts/"+artifact.json()["id"], headers=headers).json()[
            "state"] == "current_inputs_only"
    with TestClient(create_app(Settings(backend="memory"))) as client:
        assert client.post("/api/identity/revisions", json=request).status_code == 403


def real_store():
    url = os.getenv("UGI_TEST_REDIS_URL")
    if not url:
        pytest.skip("Requires actual FalkorDB")
    return Store(Settings(redis_url=url, graph_prefix="ugi_id_"+uuid4().hex[:10], identity_ledger=True))


@pytest.mark.integration
def test_real_identity_reversal_freshness_reconnect_and_isolation():
    store = real_store()
    isolated = Store(store.settings, dataset="isolated")
    try:
        revision, undo, artifact = check_reversal_and_freshness(store)
        reader = Store(store.settings)
        assert reader.get(revision["id"]) == revision and reader.get(undo["id"]) == undo
        assert IdentityLedger(reader).freshness(artifact["id"])["state"] == "stale"
        assert not isolated.list("MentionSnapshot")
        before = reader.query("MATCH (n:Record) RETURN n.id,n.payload ORDER BY n.id")
        mention = reader.list("MentionSnapshot")[0]
        with pytest.raises(ValueError, match="Immutable"):
            reader.commit([dict(id="bad", kind="Source"), {**mention, "kind": "Entity"}])
        assert reader.query("MATCH (n:Record) RETURN n.id,n.payload ORDER BY n.id") == before
    finally:
        for target in (store, isolated):
            assert target.graph.startswith(store.settings.graph_prefix+"_")
            target.client.execute_command("GRAPH.DELETE", target.graph)


@pytest.mark.integration
def test_real_cards_preserve_binary_and_nary_mentions_across_sources():
    store = real_store()
    try:
        ingest(store, [row("Vega", "id1")])
        ingest(store, [row("Nova", "id1")])
        event = (Path(__file__).parents[1]/"demo/relation_events.txt").read_bytes()
        Engine(store).ingest("events.txt", event)
        reader = Store(store.settings)
        eid = snapshots(reader, "Vega")[0]["entity_id"]
        card = IdentityLedger(reader).card(eid)
        assert len(card["versions"]) == 2
        assert {a["mention"]["text"] for a in card["mentions"]} == {"Vega", "Nova"}
        assert len(reader.events()) == 4 and len(reader.claims()) == 2
        assert reader.query("MATCH ()-[r:HAS_PARTICIPANT]->() RETURN count(r)")[0][0] > 12
        assert all(reader.get(m["mention_id"]) and reader.get(m["dependent_record_id"])
                   for m in reader.list("MentionSnapshot"))
    finally:
        assert store.graph.startswith(store.settings.graph_prefix+"_")
        store.client.execute_command("GRAPH.DELETE", store.graph)


@pytest.mark.integration
def test_real_http_identity_revisions_persist_and_cannot_cross_tenants():
    seed = real_store()
    settings = seed.settings.model_copy(update={"api_keys": "ledger-one,ledger-two"})
    headers = {"X-API-Key": "ledger-one", "X-Dataset": "identity"}
    stores = [seed, *(Store(settings, owner=uid(k)[:24], dataset="identity")
                      for k in ("ledger-one", "ledger-two"))]
    try:
        with TestClient(create_app(settings)) as client:
            result = client.post("/api/uploads", headers=headers, files={
                "file": ("people.json", json.dumps([row(external_id="one"), row(external_id="two")]).encode())})
            assert result.status_code == 200, result.text
            mids = [m["id"] for m in snapshots(stores[1])]
            result = client.post("/api/identity/revisions", headers=headers,
                                 json=change("provisional_merge", mids).model_dump())
            assert result.status_code == 200 and result.json()["identifier_conflict"], result.text
            revision_id = result.json()["id"]
        with TestClient(create_app(settings)) as client:
            result = client.get("/api/records/"+revision_id, headers=headers)
            assert result.status_code == 200 and result.json()["status"] == "provisional"
            assert client.get("/api/records/"+revision_id,
                              headers={**headers, "X-API-Key": "ledger-two"}).status_code == 404
            result = client.post("/api/identity/revisions", headers=headers,
                                 json=change("revert", revision_id=revision_id).model_dump())
            assert result.status_code == 200, result.text
    finally:
        for store in stores:
            assert store.graph.startswith(settings.graph_prefix+"_")
            store.client.execute_command("GRAPH.DELETE", store.graph)
