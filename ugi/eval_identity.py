"""Reproducible synthetic identity policy evaluation, not independent accuracy."""
import argparse
import json
import os
import tracemalloc
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from .engine import Engine
from .models import Settings, now, uid
from .profile_ingestion import MeasuredRedis
from .resolution import AuthorityObservation, IdentityResolver
from .store import Store

FIXTURE = Path(__file__).parents[1]/"evaluation/identity_cases_v1.json"


def evaluate(backend="falkordb", auto_apply=False):
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    cfg = Settings(backend=backend, identity_ledger=True, identity_resolution="dry_run",
                   identity_auto_apply=auto_apply,
                   identity_authorities={"fixture-registry": ["fixture:org", "fixture:other"]},
                   graph_prefix="ugi_feval_"+uuid4().hex[:10], provider="offline", allow_paid_calls=False,
                   redis_url=os.getenv("UGI_TEST_REDIS_URL", "redis://127.0.0.1:6380/0"))
    results = []
    tracemalloc.start()
    started = perf_counter()
    for case in raw["cases"]:
        client = MeasuredRedis.from_url(cfg.redis_url, decode_responses=True) if backend == "falkordb" else None
        store = Store(cfg, dataset=case["id"], client=client)
        resolver = IdentityResolver(store)
        try:
            if client:
                client.reset_measurements()
            mentions = []
            for side, name in enumerate((case["a"], case["b"])):
                entity_type = case.get("types", ["Organisation"]*2)[side]
                namespace = case.get("namespaces", ["fixture:org"]*2)[side]
                value = case.get("ids", [None, None])[side]
                row = dict(subject=name, subject_type=entity_type, predicate="USES", object="Tool",
                           fixture_side=side, context=case.get("context", ["", ""])[side])
                if value:
                    row["subject_id"] = value  # Untrusted legacy anchor; not accepted as match evidence.
                    row["identity"] = [dict(name=name, entity_type=entity_type, namespace=namespace, value=value)]
                source = Engine(store).ingest("case.json", json.dumps([row]).encode())
                mention = next(m for m in store.list("MentionSnapshot")
                               if m["source_id"] == source["source_id"] and m["text"] == name)
                mentions.append(mention["id"])
                if value and case.get("attest", True):
                    resolver.observe(AuthorityObservation(mention_snapshot_id=mention["id"],
                        authority="fixture-registry", identifiers=[dict(namespace=namespace, value=value)],
                        idempotency_key=uid(case["id"], side), authorise_action=True), "synthetic_connector")
            retrieval = resolver.candidates(mentions[1])
            result = resolver.compare(*mentions)
            from .identity import IdentityLedger

            ledger = IdentityLedger(store)
            same_overlay = ledger.assignment(mentions[0])["cluster_id"] == ledger.assignment(mentions[1])["cluster_id"]
            results.append(dict(id=case["id"], expected=case["expected"], decision=result["decision"],
                                matching_candidate_retrieved=mentions[0] in retrieval["candidate_ids"],
                                retrieval=retrieval, features=result["features"],
                                same_overlay=same_overlay,
                                measurements=client.measurements() if client else {}))
        finally:
            if client:
                assert store.graph.startswith(cfg.graph_prefix+"_")
                client.execute_command("GRAPH.DELETE", store.graph)
                client.close()
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    positives = [r for r in results if r["expected"] == "SAME_ENTITY"]
    negatives = [r for r in results if r["expected"] != "SAME_ENTITY"]
    tp = sum(r["decision"] == "SAME_ENTITY" for r in positives)
    fp = sum(r["decision"] == "SAME_ENTITY" for r in negatives)
    predicted = tp+fp
    return dict(recorded_at=now(), backend=backend, fixture_hash=uid(raw), auto_apply=auto_apply,
                annotation_status=raw["annotation_status"], split=raw["split"], cases=len(results),
                metrics=dict(tp=tp, predicted=predicted, gold=len(positives),
                             precision=tp/predicted if predicted else None, recall=tp/len(positives),
                             f1=2*tp/(predicted+len(positives)), false_merges=fp,
                             false_merge_rate=fp/len(negatives), missed_match_rate=(len(positives)-tp)/len(positives),
                             candidate_recall=sum(r["matching_candidate_retrieved"] for r in positives)/len(positives),
                             overlay_matches=sum(r["same_overlay"] for r in positives),
                             overlay_false_merges=sum(r["same_overlay"] for r in negatives),
                             expected_abstentions=sum(r["expected"] in {"POSSIBLY_SAME", "UNRESOLVED"} for r in results),
                             correct_abstentions=sum(r["expected"] in {"POSSIBLY_SAME", "UNRESOLVED"}
                                                      and r["decision"] in {"POSSIBLY_SAME", "UNRESOLVED"} for r in results),
                             exact_categories=sum(r["decision"] == r["expected"] for r in results)),
                elapsed_ms=round((perf_counter()-started)*1000, 3), python_allocation_peak_bytes=peak,
                model_calls=0, results=results,
                limitations=[raw["scope"], "Rules and synthetic labels share the same specification, not an independent benchmark",
                             "Trusted evidence is explicitly supplied by a synthetic connector, not verified registry data",
                             "No labelled public identity accuracy or broad lexical linking claim",
                             "Automatic overlays enabled only by the explicit auto_apply evaluation option"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=["memory", "falkordb"], default="falkordb")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--auto-apply", action="store_true", help="Authorize automatic synthetic overlay revisions under policy")
    args = parser.parse_args()
    result = evaluate(args.backend, args.auto_apply)
    args.output.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("backend", "cases", "metrics", "elapsed_ms")}, indent=2))


if __name__ == "__main__":
    main()
