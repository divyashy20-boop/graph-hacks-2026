"""Adversarial policy/correction logic; authored synthetic labels, not real accuracy."""
import json
import os
from copy import deepcopy
from uuid import uuid4

import pytest

from ugi.engine import Engine
from ugi.identity import ArtifactRequest, IdentityChange, IdentityLedger
from ugi.identity_policy import CLUSTER_QUERY, IdentityPolicy
from ugi.models import Settings
from ugi.resolution import AuthorityObservation, IdentityResolver
from ugi.store import Store, literal


def config(apply=False):
    return Settings(backend="memory", identity_ledger=True, identity_resolution="dry_run",
                    identity_auto_apply=apply,
                    identity_authorities={"fixture-registry": ["fixture:legacy", "fixture:registry", "fixture:other"]})


def seed(store, records):
    for i, identifiers in enumerate(records):
        name = "Person " + str(i)
        row = dict(subject=name, subject_type="Person", predicate="WORKS_AT", object="Willow",
                   context="Address/employment changes are not exclusive identifying evidence",
                   identity=[dict(name=name, entity_type="Person", namespace=ns, value=value)
                             for ns, value in identifiers.items()])
        Engine(store).ingest("people.json", json.dumps([row]).encode())
    return [next(m for m in store.list("MentionSnapshot") if m["text"] == "Person "+str(i))
            for i in range(len(records))]


def observation(store, mention, identifiers):
    return IdentityResolver(store).observe(AuthorityObservation(mention_snapshot_id=mention["id"],
        authority="fixture-registry", identifiers=[dict(namespace=ns, value=value) for ns, value in identifiers.items()],
        idempotency_key=uuid4().hex, authorise_action=True), "fixture_connector")


def manual_merge(store, mids):
    return IdentityLedger(store).revise(IdentityChange(operation="provisional_merge",
        mention_snapshot_ids=mids, reason="Controlled deliberately mistaken provisional cluster",
        idempotency_key=uuid4().hex, authorise_action=True), "test")


def check_correction(store):
    mentions = seed(store, [{"fixture:legacy": "shared", "fixture:registry": "one"},
                            {"fixture:legacy": "shared", "fixture:registry": "two"},
                            {"fixture:registry": "unrelated"}])
    mids = [m["id"] for m in mentions]
    ledger, policy = IdentityLedger(store), IdentityPolicy(store)
    for mention in mentions[:2]:
        observation(store, mention, {"fixture:legacy": "shared"})
    # Strict dry-run does not change assignments, even with SAME evidence.
    if not store.settings.identity_auto_apply:
        manual_merge(store, mids[:2])
    assert ledger.assignment(mids[0])["cluster_id"] == ledger.assignment(mids[1])["cluster_id"]
    artifact = ledger.artifact(ArtifactRequest(mention_snapshot_ids=mids[:2], output="Registered test plan",
                                               idempotency_key="plan", authorise_action=True))
    unrelated = ledger.artifact(ArtifactRequest(mention_snapshot_ids=mids[2:], output="Unrelated plan",
                                                idempotency_key="other", authorise_action=True))
    before = {kind: deepcopy(store.list(kind, 20000)) for kind in
              ("Claim", "RelationEvent", "Mention", "MentionSnapshot", "EntityCard", "Evidence", "Chunk", "Source")}
    observation(store, mentions[0], {"fixture:legacy": "shared", "fixture:registry": "one"})
    result = observation(store, mentions[1], {"fixture:legacy": "shared", "fixture:registry": "two"})
    run = store.get(result["automation_run_id"])
    assert run["inspected"]["analysis"]["state"] == "INCONSISTENT"
    assert len(run["proposed_groups"]) == 2
    if store.settings.identity_auto_apply:
        revision = store.get(run["applied_revision_id"])
        assert revision["operation"] == "automatic_partition" and not revision["eligible_for_inference"]
        assert ledger.assignment(mids[0])["cluster_id"] != ledger.assignment(mids[1])["cluster_id"]
        assert ledger.freshness(artifact["id"])["state"] == "stale"
        assert ledger.freshness(unrelated["id"])["state"] == "current_inputs_only"
        assert set(revision["affected_record_ids"]) == {m["dependent_record_id"] for m in mentions[:2]}
        undo = ledger.revise(IdentityChange(operation="revert", revision_id=revision["id"],
            reason="Audit compensating undo of synthetic correction", idempotency_key="undo",
            authorise_action=True), "test")
        assert undo["reverts_id"] == revision["id"]
        assert ledger.assignment(mids[0])["cluster_id"] == ledger.assignment(mids[1])["cluster_id"]
        # A subsequent observation rechecks negative evidence and repairs again.
        observation(store, mentions[1], {"fixture:legacy": "shared", "fixture:registry": "two"})
        assert ledger.assignment(mids[0])["cluster_id"] != ledger.assignment(mids[1])["cluster_id"]
    else:
        assert run["applied_revision_id"] is None
        assert ledger.freshness(artifact["id"])["state"] == "current_inputs_only"
        assert policy.inspect(mids[0])["analysis"]["state"] == "INCONSISTENT"
    for kind, old in before.items():
        assert store.list(kind, 20000) == old
    return run


@pytest.mark.parametrize("apply", [False, True])
def test_dry_run_first_and_optin_automatic_correction_selective_staleness_and_undo(apply):
    check_correction(Store(config(apply)))


def test_abc_negative_constraint_vetoes_transitive_identity():
    store = Store(config())
    mentions = seed(store, [{"fixture:legacy": "a", "fixture:registry": "one"},
                            {"fixture:legacy": "a", "fixture:other": "b"},
                            {"fixture:other": "b", "fixture:registry": "two"}])
    for mention, ids in zip(mentions, [{"fixture:legacy": "a", "fixture:registry": "one"},
                                     {"fixture:legacy": "a", "fixture:other": "b"},
                                     {"fixture:other": "b", "fixture:registry": "two"}], strict=True):
        observation(store, mention, ids)
    mids = [m["id"] for m in mentions]
    manual_merge(store, mids)
    inspected = IdentityPolicy(store).inspect(mids[0])
    assert inspected["analysis"]["state"] == "INCONSISTENT"
    assert inspected["analysis"]["groups"] is None  # No arbitrary split of ambiguous middle B.


def test_unknown_member_and_ordinary_changes_do_not_cause_a_false_split():
    store = Store(config(True))
    mentions = seed(store, [{"fixture:registry": "one"}, {"fixture:registry": "two"}, {}])
    mids = [m["id"] for m in mentions]
    manual_merge(store, mids)
    observation(store, mentions[0], {"fixture:registry": "one"})
    result = observation(store, mentions[1], {"fixture:registry": "two"})
    run = store.get(result["automation_run_id"])
    assert run["inspected"]["analysis"]["state"] == "INCONSISTENT"
    assert run["proposed_groups"] is None and run["applied_revision_id"] is None
    empty = Store(config(True))
    other = seed(empty, [{}, {}])
    manual_merge(empty, [m["id"] for m in other])
    assert IdentityPolicy(empty).inspect(other[0]["id"])["analysis"]["state"] == "UNRESOLVED"


def test_declared_type_difference_alone_does_not_authorize_auto_split():
    store = Store(config(True))
    person = seed(store, [{}])[0]
    Engine(store).ingest("org.json", json.dumps([dict(subject="Some Org", subject_type="Organisation",
                                                     predicate="USES", object="Tool")]).encode())
    org = next(m for m in store.list("MentionSnapshot") if m["text"] == "Some Org")
    result = IdentityPolicy(store).analyze([person["id"], org["id"]])
    assert result["state"] == "INCONSISTENT" and result["groups"] is None


def test_incomplete_legacy_cluster_and_candidate_limit_cannot_auto_merge():
    store = Store(config(True).model_copy(update={"identity_candidate_limit": 1}))
    mentions = seed(store, [{"fixture:registry": "same"}]*3)
    for mention in mentions:
        observation(store, mention, {"fixture:registry": "same"})
    # Depending on arrival, an earlier complete pair may join. No final truncated
    # retrieval can prove a complete three-member match or silently grow it.
    run = store.list("IdentityRun")[-1]
    assert not run["candidate_complete"] and run["applied_revision_id"] is None
    legacy = Store(Settings(backend="memory", identity_ledger=True))
    Engine(legacy).ingest("x.txt", b"Vega uses Willow.")
    mid = legacy.list("MentionSnapshot")[0]["id"]
    assert IdentityPolicy(legacy).inspect(mid)["analysis"]["state"] == "INCOMPLETE"


@pytest.mark.integration
def test_real_atomic_policy_correction_index_reconnect_and_runtime_rollback():
    if not os.getenv("UGI_TEST_REDIS_URL"):
        pytest.skip("Requires actual FalkorDB")
    cfg = config(True).model_copy(update={"backend": "falkordb", "redis_url": os.environ["UGI_TEST_REDIS_URL"],
                                        "graph_prefix": "ugi_fpolicy_"+uuid4().hex[:8]})
    store = Store(cfg)
    try:
        run = check_correction(store)
        assert Store(cfg).get(run["id"]) == run
        cluster = store.list("IdentityAssignment")[0]["cluster_id"]
        plan = store.client.execute_command("GRAPH.EXPLAIN", store.graph,
                                             "CYPHER cluster="+literal(cluster)+" "+CLUSTER_QUERY)
        assert any("index scan" in line.lower() for line in plan), plan
        # Genuine server runtime failure while evidence, assignment, notices and
        # revision are in the same mutating query must roll back everything.
        people = [m for m in store.list("MentionSnapshot") if m["text"] in {"Person 0", "Person 1"}]
        manual_merge(store, [m["id"] for m in people])
        IdentityLedger(store).artifact(ArtifactRequest(mention_snapshot_ids=[m["id"] for m in people],
            output="Plan before rollback probe", idempotency_key="rollback-plan", authorise_action=True))
        before = store.query("MATCH(n:Record) RETURN n.id,n.payload ORDER BY n.id")
        original = store.commit
        def fail(records, links=()):
            records = list(records)
            if any(r["kind"] == "IdentityRun" for r in records):
                assert any(r["kind"] == "IdentityRevision" and r["operation"] == "automatic_partition" for r in records)
                assert any(r["kind"] == "KnowledgeRevision" for r in records)
                # Usage sorts after evidence, heads, revision and notices: error
                # occurs late in the one mutating query, not during preflight.
                records.append(dict(id="injected-invalid-runtime-map", kind="Usage", name_key={"invalid": "map"}))
            return original(records, links)
        store.commit = fail
        mention = next(m for m in store.list("MentionSnapshot") if m["text"] == "Person 1")
        from redis.exceptions import ResponseError

        with pytest.raises(ResponseError):
            observation(store, mention, {"fixture:legacy": "shared", "fixture:registry": "two"})
        assert Store(cfg).query("MATCH(n:Record) RETURN n.id,n.payload ORDER BY n.id") == before
        store.commit = original
        # Automatic correction may touch an event participant's projection, not
        # any event role, qualifier, source evidence or base participant endpoint.
        event_row = dict(relation_type="COLLABORATION", participants=[
            dict(role="researcher", name="Event Person", entity_type="Person"),
            dict(role="researcher", name="Other Researcher", entity_type="Person"),
            dict(role="project", name="Project", entity_type="Project")],
            identity=[dict(name="Event Person", entity_type="Person", namespace="fixture:registry", value="event-one")])
        Engine(store).ingest("event.json", json.dumps([event_row]).encode())
        event = store.events()[0]
        evidence = store.get(event["evidence_id"])
        participant = next(m for m in store.list("MentionSnapshot") if m["text"] == "Event Person")
        manual_merge(store, [participant["id"], mention["id"]])
        observed = observation(store, participant, {"fixture:registry": "event-one"})
        run = store.get(observed["automation_run_id"])
        assert run["applied_revision_id"]
        assert event["id"] in store.get(run["applied_revision_id"])["affected_record_ids"]
        assert Store(cfg).get(event["id"]) == event
        assert Store(cfg).get(event["evidence_id"]) == evidence
    finally:
        assert store.graph.startswith(cfg.graph_prefix+"_")
        store.client.execute_command("GRAPH.DELETE", store.graph)
