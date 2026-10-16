"""Synthetic bounded cluster detection/partition/reversal metrics, actual graph."""
import argparse
import json
import os
import tracemalloc
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from .engine import Engine
from .identity import ArtifactRequest, IdentityChange, IdentityLedger
from .identity_policy import IdentityPolicy
from .models import Settings, now, uid
from .resolution import AuthorityObservation, IdentityResolver
from .store import Store

FIXTURE = Path(__file__).parents[1]/"evaluation/identity_clusters_v1.json"


def evaluate():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    cfg = Settings(identity_ledger=True, identity_resolution="dry_run", identity_auto_apply=False,
                   identity_authorities={"fixture-registry": ["fixture:registry", "fixture:legacy", "fixture:other"]},
                   provider="offline", allow_paid_calls=False, graph_prefix="ugi_fc_"+uuid4().hex[:10],
                   redis_url=os.getenv("UGI_TEST_REDIS_URL", "redis://127.0.0.1:6380/0"))
    results = []
    tracemalloc.start()
    began = perf_counter()
    for case in fixture["cases"]:
        store = Store(cfg, dataset=case["id"])
        ledger, resolver = IdentityLedger(store), IdentityResolver(store)
        try:
            mids = []
            for i, identifiers in enumerate([*case["members"], {}]):
                name = "Name "+str(i)
                record = dict(subject=name, subject_type="Person", predicate="WORKS_AT", object="Willow",
                              identity=[dict(name=name, entity_type="Person", namespace=ns, value=v)
                                        for ns, v in identifiers.items()])
                source = Engine(store).ingest("cluster.json", json.dumps([record]).encode())
                mid = next(m["id"] for m in store.list("MentionSnapshot")
                           if m["text"] == name and m["source_id"] == source["source_id"])
                mids.append(mid)
                if identifiers:
                    resolver.observe(AuthorityObservation(mention_snapshot_id=mid, authority="fixture-registry",
                        identifiers=[dict(namespace=ns, value=v) for ns, v in identifiers.items()],
                        idempotency_key=str(i), authorise_action=True), "synthetic_connector")
            selected, unrelated = mids[:-1], mids[-1]
            ledger.revise(IdentityChange(operation="provisional_merge", mention_snapshot_ids=selected,
                reason="Authored cluster evaluation setup (may deliberately be incorrect)",
                idempotency_key="setup", authorise_action=True), "synthetic_fixture")
            before = [ledger.assignment(m)["cluster_id"] for m in selected]
            artifact = ledger.artifact(ArtifactRequest(mention_snapshot_ids=selected, output="Registered test output",
                                                       idempotency_key="plan", authorise_action=True))
            other = ledger.artifact(ArtifactRequest(mention_snapshot_ids=[unrelated], output="Unrelated test output",
                                                    idempotency_key="other", authorise_action=True))
            frozen = {r["id"]: r for kind in ("Claim", "RelationEvent", "Evidence", "Mention", "MentionSnapshot", "EntityCard")
                      for r in store.list(kind, 20000)}
            store.settings = cfg.model_copy(update={"identity_auto_apply": True})
            started = perf_counter()
            with store.transaction():
                records, run = IdentityPolicy(store).plan(selected[0], {})
                ledger._commit_bounded([*records, run])
            analysis = run["inspected"]["analysis"]
            expected = (sorted(sorted(selected[i] for i in g) for g in case["partition"])
                        if case["partition"] else None)
            matched_partition = run["proposed_groups"] == expected
            # A consistent cluster requires no correction even when it has one safe group.
            applied = bool(run["applied_revision_id"])
            dependent_correct = ledger.freshness(artifact["id"])["state"] == ("stale" if applied else "current_inputs_only")
            unrelated_correct = ledger.freshness(other["id"])["state"] == "current_inputs_only"
            reversal_ok = None
            if applied:
                ledger.revise(IdentityChange(operation="revert", revision_id=run["applied_revision_id"],
                    reason="Controlled reversal integrity check", idempotency_key="undo", authorise_action=True), "fixture")
                reversal_ok = [ledger.assignment(m)["cluster_id"] for m in selected] == before
            preserved = all(store.get(ident) == value for ident, value in frozen.items())
            results.append(dict(id=case["id"], expected_inconsistent=case["inconsistent"],
                                mention_ids=selected, proposed_groups=run["proposed_groups"],
                                detected=analysis["state"] == "INCONSISTENT", state=analysis["state"],
                                expected_defensible_split=expected is not None, partition_correct=matched_partition,
                                applied=applied, reversal_integrity=reversal_ok, original_payloads_preserved=preserved,
                                invalidation_correct=dependent_correct and unrelated_correct,
                                pair_checks=analysis["pair_checks"], correction_and_checks_ms=round((perf_counter()-started)*1000, 3)))
        finally:
            assert store.graph.startswith(cfg.graph_prefix+"_")
            store.client.execute_command("GRAPH.DELETE", store.graph)
    tp = sum(r["detected"] and r["expected_inconsistent"] for r in results)
    fp = sum(r["detected"] and not r["expected_inconsistent"] for r in results)
    gold = sum(r["expected_inconsistent"] for r in results)
    splits = [r for r in results if r["expected_defensible_split"]]
    result = dict(recorded_at=now(), fixture_hash=uid(fixture), backend="actual FalkorDB",
                  annotation_status=fixture["annotation_status"], split="development", results=results,
                  metrics=dict(detection_tp=tp, detection_fp=fp, detection_gold=gold,
                               detection_precision=tp/(tp+fp) if tp+fp else None, detection_recall=tp/gold,
                               defensible_split_cases=len(splits), correct_splits=sum(r["partition_correct"] and r["applied"] for r in splits),
                               false_splits=sum(r["applied"] and not r["expected_defensible_split"] for r in results),
                               non_split_cases=sum(not r["expected_defensible_split"] for r in results),
                               false_split_rate=sum(r["applied"] and not r["expected_defensible_split"] for r in results)
                                                /sum(not r["expected_defensible_split"] for r in results),
                               reversals_passed=sum(r["reversal_integrity"] is True for r in results),
                               invalidation_cases_passed=sum(r["invalidation_correct"] for r in results),
                               preservation_cases_passed=sum(r["original_payloads_preserved"] for r in results)),
                  elapsed_ms=round((perf_counter()-began)*1000, 3),
                  python_allocation_peak_bytes=tracemalloc.get_traced_memory()[1], model_calls=0,
                  limitations=[fixture["scope"], "No independent real-world detection/split accuracy",
                               "Unknown/ABC members intentionally flagged without forcing a partition",
                               "Policy assumptions depend on truthful authorized connector/namespace configuration"])
    tracemalloc.stop()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate()
    args.output.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result["metrics"], indent=2))


if __name__ == "__main__":
    main()
