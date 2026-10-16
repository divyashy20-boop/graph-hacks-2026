"""Actual persisted correction after later trusted evidence; all data synthetic."""
import argparse
import json
from pathlib import Path

from .engine import Engine
from .identity import ArtifactRequest, IdentityLedger
from .identity_policy import IdentityPolicy
from .models import Settings, now, uid
from .resolution import AuthorityObservation, IdentityResolver
from .store import Store


def run(backend="falkordb", apply=False):
    cfg = Settings(backend=backend, identity_ledger=True, identity_resolution="dry_run",
                   identity_auto_apply=apply, provider="offline", allow_paid_calls=False,
                   identity_authorities={"synthetic_connector": ["fixture:legacy", "fixture:registry"]})
    dataset = "showcase-f-identity" if apply else "showcase-f-dryrun"
    store = Store(cfg, dataset=dataset)
    # Each invocation appends a fresh synthetic source batch, not reset/deletion.
    invocation = now()
    mentions = []
    for name, registry in [("Mira", "one"), ("Mira", "two"), ("Noor", "other")]:
        row = dict(subject=name, subject_type="Person", predicate="WORKS_AT", object="Willow",
                   invocation=invocation, identity=[dict(name=name, entity_type="Person", namespace=ns, value=value)
                   for ns, value in [("fixture:legacy", "shared" if name == "Mira" else "other"),
                                     ("fixture:registry", registry)]])
        report = Engine(store).ingest("identity-demo.json", json.dumps([row]).encode())
        mentions.append(next(m for m in store.list("MentionSnapshot")
                             if m["source_id"] == report["source_id"] and m["text"] == name))
    ledger, resolver = IdentityLedger(store), IdentityResolver(store)
    def observe(mention, pairs):
        return resolver.observe(AuthorityObservation(mention_snapshot_id=mention["id"],
            authority="synthetic_connector", identifiers=[dict(namespace=ns, value=v) for ns, v in pairs],
            idempotency_key=uid(invocation, mention["id"], pairs), authorise_action=True), "synthetic_demo")
    for mention in mentions[:2]:
        observe(mention, [("fixture:legacy", "shared")])
    mids = [m["id"] for m in mentions]
    if not apply:
        from .identity import IdentityChange

        ledger.revise(IdentityChange(operation="provisional_merge", mention_snapshot_ids=mids[:2],
            reason="Synthetic pre-existing mistaken cluster for detection-only demo",
            idempotency_key=uid(invocation, "prior"), authorise_action=True), "synthetic_demo")
    assert ledger.assignment(mids[0])["cluster_id"] == ledger.assignment(mids[1])["cluster_id"]
    artifact = ledger.artifact(ArtifactRequest(mention_snapshot_ids=mids[:2], output="Synthetic dependent plan",
        idempotency_key=uid(invocation, "plan"), authorise_action=True))
    other = ledger.artifact(ArtifactRequest(mention_snapshot_ids=mids[2:], output="Unrelated synthetic plan",
        idempotency_key=uid(invocation, "other"), authorise_action=True))
    facts = {r["id"]: r for kind in ("Claim", "RelationEvent", "Mention", "MentionSnapshot", "EntityCard", "Evidence")
             for r in store.list(kind, 20000)}
    observe(mentions[0], [("fixture:legacy", "shared"), ("fixture:registry", "one")])
    evidence = observe(mentions[1], [("fixture:legacy", "shared"), ("fixture:registry", "two")])
    policy_run = store.get(evidence["automation_run_id"])
    assert policy_run["inspected"]["analysis"]["state"] == "INCONSISTENT"
    assert bool(policy_run["applied_revision_id"]) == apply
    reader = Store(cfg, dataset=dataset)
    assert all(reader.get(ident) == payload for ident, payload in facts.items())
    assert ledger.freshness(other["id"])["state"] == "current_inputs_only"
    assert ledger.freshness(artifact["id"])["state"] == ("stale" if apply else "current_inputs_only")
    return dict(recorded_at=now(), backend=backend, dataset=dataset, graph=store.graph,
                data_provenance="Synthetic CC0; deliberately bad legacy-namespace authority assertion, corrected by later exclusive evidence",
                authority_assumptions="Connector assertions, not real registry lookups; identifiers present in original source, learned in later attestations",
                mode="apply" if apply else "dry_run", policy_run=policy_run,
                final_cluster=IdentityPolicy(store).inspect(mids[0]),
                original_payloads_unchanged=len(facts), reconnect_equal=True,
                dependent_freshness=ledger.freshness(artifact["id"])["state"],
                unrelated_freshness=ledger.freshness(other["id"])["state"], model_calls=0,
                limitations=["No independent real-world accuracy or external authority authentication",
                             "Only registered per-assignment dependencies are invalidated",
                             "Detection/staleness are not semantic re-evaluation"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--apply", action="store_true", help="Explicitly authorize policy overlay corrections in synthetic demo")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute required to persist synthetic evidence and revisions")
    result = run(apply=args.apply)
    args.output.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("backend", "mode", "original_payloads_unchanged",
                                           "reconnect_equal", "dependent_freshness", "unrelated_freshness")}, indent=2))


if __name__ == "__main__":
    main()
