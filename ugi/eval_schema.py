"""Real-graph development specification comparison, not independent accuracy."""
import argparse
import json
import os
from pathlib import Path
from uuid import uuid4

from .engine import Engine
from .models import Settings, now, uid
from .store import Store


def evaluate(fixture):
    results=[]
    for enabled in (False,True):
        cases=[]
        cfg=Settings(open_predicates=enabled,provider="offline",allow_paid_calls=False,
            redis_url=os.getenv("UGI_TEST_REDIS_URL","redis://127.0.0.1:6380/0"),graph_prefix="ugi_geval_"+uuid4().hex[:8])
        for case in fixture["cases"]:
            graph=Store(cfg,dataset=case["id"])
            try:
                report=Engine(graph).ingest("source.txt",case["text"].encode())
                reader=Store(cfg,dataset=case["id"])
                claims=reader.claims()
                events=reader.events()
                predicted=[[c["subject"],c["original_predicate"],c["object"],c["polarity"],c["modality"]] for c in claims]
                roles=[sorted([[p["role"],p["name"]] for p in e["participants"]]) for e in events]
                quote_ok=all(reader.get(r["chunk_id"])["text"][reader.get(r["evidence_id"])["start"]:
                    reader.get(r["evidence_id"])["end"]] == reader.get(r["evidence_id"])["quote"] for r in [*claims,*events])
                cases.append(dict(id=case["id"],binary=predicted,events=roles,
                    binary_tp=len({tuple(p) for p in predicted}&{tuple(p) for p in case["binary"]}),
                    exact_events=roles == [sorted(e) for e in case["events"]],
                    exact_quotes=quote_ok,assertions=len(claims)+len(events),report=report))
            finally:
                assert graph.graph.startswith(cfg.graph_prefix+"_")
                graph.client.execute_command("GRAPH.DELETE",graph.graph)
        results.append(dict(open_enabled=enabled,cases=cases,
            binary_tp=sum(c["binary_tp"] for c in cases),predicted_binary=sum(len(c["binary"]) for c in cases),
            expected_binary=sum(len(c["binary"]) for c in fixture["cases"]),
            exact_event_cases=sum(c["exact_events"] for c in cases),all_quotes=all(c["exact_quotes"] for c in cases)))
    return dict(recorded_at=now(),backend="actual FalkorDB",fixture_hash=uid(fixture),
                provenance=fixture["provenance"],results=results,model_calls=0,
                limitations=["Tuned authored policy/development cases, no independent accuracy or human review",
                             "Whole-role equality checked separately; no binary projection credit",
                             "Temporal/numeric scope checked by regression tests, not pooled into this score"])


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture",type=Path,default=Path("evaluation/g_open_development.json"))
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    result=evaluate(json.loads(args.fixture.read_text(encoding="utf-8")))
    args.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps([{k:r[k] for k in ("open_enabled","binary_tp","predicted_binary","expected_binary","exact_event_cases","all_quotes")} for r in result["results"]]))
