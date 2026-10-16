"""Controlled logic fixtures. No independently human-reviewed identity claims."""
import json
import os
from copy import deepcopy
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from ugi.api import create_app
from ugi.engine import Engine
from ugi.models import Settings
from ugi.resolution import POSTING_QUERY, AuthorityObservation, IdentityResolver
from ugi.store import Store, literal


def settings(**kwargs):
    return Settings(backend="memory", identity_ledger=True, identity_resolution="dry_run",
                    identity_authorities={"fixture-registry": ["fixture:org", "fixture:other"]}, **kwargs)


def source(store, name, value=None, namespace="fixture:org", entity_type="Organisation", **extra):
    record = dict(subject=name, subject_type=entity_type, predicate="USES", object="Tool",
                  **extra)
    if value is not None:
        record["identity"] = [dict(name=name, entity_type=entity_type, namespace=namespace, value=value)]
    report = Engine(store).ingest("record.json", json.dumps([record]).encode())
    return next(m for m in store.list("MentionSnapshot")
                if m["source_id"] == report["source_id"] and m["text"] == name)


def observe(store, mention, value, namespace="fixture:org", **kwargs):
    return IdentityResolver(store).observe(AuthorityObservation(
        mention_snapshot_id=mention["id"], authority="fixture-registry",
        identifiers=[dict(namespace=namespace, value=value)], authorise_action=True,
        idempotency_key=kwargs.pop("idempotency_key", uuid4().hex), **kwargs), "fixture_connector")


@pytest.mark.parametrize("left,right,expected", [
    ("Acme Corporation", "Acme Corp.", "SAME_ENTITY"),
    ("Acme", "Acme", "SAME_ENTITY"),
])
def test_renamed_identity_requires_policy_evidence(left, right, expected):
    store = Store(settings())
    a = source(store, left, "123")
    b = source(store, right, "123", revision="second source")
    resolver = IdentityResolver(store)
    assert resolver.compare(a["id"], b["id"])["decision"] != "SAME_ENTITY"
    observe(store, a, "123")
    observe(store, b, "123")
    assert a["id"] in resolver.candidates(b["id"])["candidate_ids"]
    result = resolver.compare(a["id"], b["id"])
    assert result["decision"] == expected and not result["calibrated"]
    assert not result["eligible_for_inference"]


def test_conflicting_namespaces_types_untrusted_ids_and_soft_names():
    store = Store(settings())
    a = source(store, "Rahul Sharma", "one", entity_type="Person", subject_id="reused-untrusted")
    b = source(store, "Rahul Sharma", "two", entity_type="Person", subject_id="reused-untrusted")
    resolver = IdentityResolver(store)
    assert resolver.compare(a["id"], b["id"])["decision"] == "POSSIBLY_SAME"
    from ugi.identity import IdentityLedger

    assert IdentityLedger(store).assignment(a["id"])["cluster_id"] != IdentityLedger(store).assignment(b["id"])["cluster_id"]
    observe(store, a, "one")
    observe(store, b, "two")
    assert resolver.compare(a["id"], b["id"])["decision"] == "DIFFERENT_ENTITY"
    c = source(store, "Other", "one", namespace="fixture:other")
    observe(store, c, "one", namespace="fixture:other")
    assert resolver.compare(a["id"], c["id"])["decision"] == "DIFFERENT_ENTITY"  # Type constraint.
    d = source(store, "Other Person", "one", namespace="fixture:other", entity_type="Person")
    observe(store, d, "one", namespace="fixture:other")
    assert resolver.compare(a["id"], d["id"])["decision"] == "UNRESOLVED"


def test_uploaded_trust_flags_and_ungrounded_authority_cannot_enable_identity():
    store = Store(settings())
    a = source(store, "Acme", "123", trusted=True, authority="fixture-registry")
    b = source(store, "ACME", "123")
    resolver = IdentityResolver(store)
    assert resolver.compare(a["id"], b["id"])["decision"] == "POSSIBLY_SAME"
    before = deepcopy(store.records)
    with pytest.raises(ValueError, match="structured source"):
        observe(store, a, "invented")
    with pytest.raises(ValueError, match="operator policy"):
        observe(store, a, "123", namespace="unapproved")
    request = AuthorityObservation(mention_snapshot_id=a["id"], authority="fixture-registry",
        identifiers=[dict(namespace="fixture:org", value="123")], idempotency_key="no")
    with pytest.raises(ValueError, match="authorization"):
        resolver.observe(request, "test")
    assert store.records == before


def test_authority_evidence_replay_replacement_and_candidate_overflow():
    store = Store(settings(identity_candidate_limit=1))
    mentions = [source(store, "Acme", "123", occurrence=i) for i in range(3)]
    resolver = IdentityResolver(store)
    retrieval = resolver.candidates(mentions[0]["id"])
    assert len(retrieval["candidate_ids"]) == 1 and not retrieval["complete"]
    first = observe(store, mentions[0], "123", idempotency_key="replay")
    assert observe(store, mentions[0], "123", idempotency_key="replay") == first
    assert Engine(store).ingest("repeat.json", json.dumps([dict(subject="Acme", subject_type="Organisation",
        predicate="USES", object="Tool", occurrence=0, identity=[dict(name="Acme", entity_type="Organisation",
        namespace="fixture:org", value="123")])]).encode())["duplicate"]


def test_resolution_http_authority_gate_and_tenant_isolation():
    app = create_app(settings(api_keys="fixture-one,fixture-two"))
    store = app.state.store_for("unused", "demo")  # Separate from authenticated owner.
    source(store, "Unused", "123")
    with TestClient(app) as client:
        assert client.get("/api/identity/compare", params=dict(left="x", right="y")).status_code == 401
        headers = {"X-API-Key": "fixture-one"}
        assert client.get("/api/identity/candidates/unknown", headers=headers).status_code == 422
    with pytest.raises(ValueError, match="requires identity_ledger"):
        Settings(identity_resolution="dry_run")


@pytest.mark.integration
def test_real_indexed_candidates_evidence_reconnect_atomicity_and_scope():
    if not os.getenv("UGI_TEST_REDIS_URL"):
        pytest.skip("Requires actual FalkorDB")
    cfg = settings().model_copy(update={"backend": "falkordb", "redis_url": os.environ["UGI_TEST_REDIS_URL"],
                                       "graph_prefix": "ugi_f_"+uuid4().hex[:10]})
    store, other = Store(cfg), Store(cfg, dataset="other")
    try:
        a = source(store, "Acme Corporation", "123")
        b = source(store, "Acme Corp.", "123")
        observe(store, a, "123")
        observe(store, b, "123")
        reader = Store(cfg)
        resolver = IdentityResolver(reader)
        assert resolver.compare(a["id"], b["id"])["decision"] == "SAME_ENTITY"
        assert a["id"] in resolver.candidates(b["id"])["candidate_ids"]
        params = "CYPHER keys="+literal(resolver.blocks(b["id"], {}))+" limit=22 "
        plan = reader.client.execute_command("GRAPH.EXPLAIN", reader.graph, params+POSTING_QUERY)
        assert any("index scan" in line.lower() for line in plan), plan
        assert not other.list("IdentityPosting")
        before = reader.query("MATCH(n:Record) RETURN n.id,n.payload ORDER BY n.id")
        with pytest.raises(ValueError):
            observe(reader, a, "unsupported")
        assert reader.query("MATCH(n:Record) RETURN n.id,n.payload ORDER BY n.id") == before
    finally:
        for target in (store, other):
            assert target.graph.startswith(cfg.graph_prefix+"_")
            target.client.execute_command("GRAPH.DELETE", target.graph)
