"""Reproducible multi-domain backend demo; writes only when --execute is supplied."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import Engine
from .models import InvestigationRequest, RelationQuery, Settings, now
from .store import Store

ROOT = Path(__file__).parents[1]


def showcase(settings, prefix="showcase-v1", execute=False):
    output = {}
    for domain, filename, target in [("incident", "incident.json", "Cache"),
                                     ("supply", "supply_network.json", "Nova Supply"),
                                     ("research", "research_network.json", None)]:
        store = Store(settings, dataset=prefix + "-" + domain)
        engine = Engine(store)
        ingested = engine.ingest(filename, (ROOT / "demo" / filename).read_bytes())
        if domain == "research":
            lina_id = next(e["id"] for e in store.entities("Lina")
                           if e.get("external_id") == "lina-main")
            before = engine.relationship(RelationQuery(
                subject=lina_id, object="Noor", predicate="SHARES_EMPLOYER", as_of="2021-06-01"))
            later = engine.relationship(RelationQuery(
                subject=lina_id, object="Noor", predicate="SHARES_EMPLOYER", as_of="2023-06-01"))
            assert before["status"] == "RULE_DERIVED" and later["status"] == "UNKNOWN"
            engine.ingest("research_identity.json", (ROOT / "demo/research_identity.json").read_bytes())
            uncertain = engine.relationship(RelationQuery(
                subject="Lina", object="Noor", predicate="SHARES_EMPLOYER", as_of="2021-06-01"))
            assert uncertain["status"] == "UNKNOWN" and len(store.entities("Lina")) == 2
            output[domain] = dict(ingestion=ingested, historical_status=before["status"],
                                  later_status=later["status"], after_collision=uncertain,
                                  events=store.events(), identity_candidates=store.entities("Lina"),
                                  merge_reviews=store.list("MergeDecision"), graph=store.graph)
        else:
            request = InvestigationRequest(target=target, idempotency_key="showcase-v1",
                                           authorise_action=execute)
            preview = engine.investigate(request.model_copy(update={"authorise_action": False}), "demo")
            case = engine.investigate(request, "demo")
            if execute:
                assert case["executed"] and store.get(case["id"])
            assert len(case["affected_entity_ids"]) == 2
            subject, obj = ("Checkout", "Cache") if domain == "incident" else ("Harbor Factory", "Nova Supply")
            derived = engine.relationship(RelationQuery(subject=subject, object=obj,
                                                        predicate="TRANSITIVELY_DEPENDS_ON"))
            assert derived["status"] == "RULE_DERIVED"
            output[domain] = dict(ingestion=ingested, preview=preview, action=case,
                                  derived=derived, tasks=store.list("ReviewTask"), graph=store.graph)
    return dict(recorded_at=now(), backend=settings.backend, executed=execute, domains=output,
                data_provenance="Synthetic CC0 demo records; dependencies explicitly supplied, "
                                "not inferred by flattening provision events", model_calls=0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["memory", "falkordb"], default="falkordb")
    parser.add_argument("--dataset-prefix", default="showcase-v1")
    parser.add_argument("--execute", action="store_true", help="Authorise local persistent cases/review tasks")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = showcase(Settings(backend=args.backend), args.dataset_prefix, args.execute)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"backend": report["backend"], "executed": report["executed"],
                      "domains": list(report["domains"]), "model_calls": 0}, indent=2))


if __name__ == "__main__":
    main()
