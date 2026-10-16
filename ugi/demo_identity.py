"""Persistent, synthetic ledger/reversal/freshness demonstration, no model calls."""
import argparse
import json
from pathlib import Path

from .engine import Engine
from .identity import ArtifactRequest, IdentityChange, IdentityLedger
from .models import RelationQuery, Settings, now, uid
from .store import Store


def run(settings, dataset="showcase-e-identity"):
    store = Store(settings, dataset=dataset)
    engine, ledger = Engine(store), IdentityLedger(store)
    base = dict(subject="Rahul Sharma", subject_type="Person", predicate="WORKS_AT",
                object="Willow", object_type="Organisation")
    engine.ingest("people.json", json.dumps([{**base, "subject_id": "synthetic:person:1"},
                                            {**base, "subject_id": "synthetic:person:2"},
                                            {**base, "subject": "Noor", "subject_id": "synthetic:person:3"}]).encode())
    engine.ingest("renamed.json", json.dumps([
        {**base, "subject": "Rahul S", "subject_id": "synthetic:person:1"}]).encode())
    snapshots = store.list("MentionSnapshot")
    mids = sorted(m["id"] for m in snapshots if m["text"] == "Rahul Sharma")
    unaffected = next(m["id"] for m in snapshots if m["text"] == "Noor")
    assert len(mids) == 2
    original = [ledger.assignment(mid) for mid in mids]
    assert len({a["cluster_id"] for a in original}) == 2
    card = ledger.card(original[0]["mention"]["entity_id"])
    renamed_eid = next(m["entity_id"] for m in snapshots if m["text"] == "Rahul S")
    assert len(ledger.card(renamed_eid)["versions"]) == 2
    run_id = uid([a["revision_id"] for a in original])
    artifact = ledger.artifact(ArtifactRequest(mention_snapshot_ids=mids,
        output="Synthetic unverified plan consuming two distinct identity assignments",
        idempotency_key=uid(run_id, "plan"), authorise_action=True))
    other = ledger.artifact(ArtifactRequest(mention_snapshot_ids=[unaffected],
        output="Unrelated synthetic output", idempotency_key=uid(run_id, "other"), authorise_action=True))
    request = IdentityChange(operation="provisional_merge", mention_snapshot_ids=mids,
        reason="Deliberately mistaken provisional union for reversible-history demonstration only",
        idempotency_key=uid(run_id, "merge"), authorise_action=True)
    revision = ledger.revise(request, "synthetic_demo")
    merged = [ledger.assignment(mid) for mid in mids]
    assert len({a["cluster_id"] for a in merged}) == 1
    assert ledger.freshness(artifact["id"])["state"] == "stale"
    assert ledger.freshness(other["id"])["state"] == "current_inputs_only"
    undo = ledger.revise(IdentityChange(operation="revert", revision_id=revision["id"],
        reason="Undo deliberately mistaken provisional demo union; preserve all sources",
        idempotency_key=uid(run_id, "undo"), authorise_action=True), "synthetic_demo")
    restored = [ledger.assignment(mid) for mid in mids]
    assert [a["cluster_id"] for a in restored] == [a["cluster_id"] for a in original]
    reader = Store(settings, dataset=dataset)
    assert reader.get(revision["id"]) == revision and reader.get(undo["id"]) == undo
    assert engine.relationship(RelationQuery(subject="Rahul Sharma", object="Willow",
                                            predicate="WORKS_AT"))["status"] == "UNKNOWN"
    return dict(recorded_at=now(), backend=settings.backend, graph=store.graph, dataset=dataset,
                data_provenance="Synthetic CC0 controlled demonstration, not entity-linking accuracy",
                model_calls=0, cloud_api_charge_usd=0,
                renamed_typed_id_card_versions=2, before=original, provisional_merge=revision,
                merged=merged, undo=undo, restored=restored,
                artifact_freshness=ledger.freshness(artifact["id"]),
                unrelated_freshness=ledger.freshness(other["id"]),
                sample_card_versions=len(card["versions"]), reconnect_equal=True,
                limitations=["Explicitly authorized simulated wrong merge, not automatic mistake detection",
                             "Projection never rewires or participates in definitive Claim inference",
                             "Stale notices do not perform semantic re-evaluation",
                             "Opt-in ledger, bounded200 mentions/upload and per card; no legacy backfill"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=["memory", "falkordb"], default="falkordb")
    parser.add_argument("--dataset", default="showcase-e-identity")
    parser.add_argument("--execute", action="store_true", help="Authorize synthetic provisional revisions and artifacts")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute required: this demonstration persists synthetic revisions")
    result = run(Settings(backend=args.backend, identity_ledger=True, provider="offline",
                          allow_paid_calls=False), args.dataset)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(dict(backend=result["backend"], reconnect_equal=True,
                         mistaken_projection_reversed=True, unrelated_artifact_unchanged=True,
                         affected_artifact="stale", model_calls=0), indent=2))


if __name__ == "__main__":
    main()
