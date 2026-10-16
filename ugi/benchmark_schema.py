"""Small real-graph off/on observations, not p95 or enterprise certification."""
import argparse
import json
import os
import tracemalloc
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from .demo_schema import sample_pack
from .engine import Engine
from .models import Settings, now
from .open_relations import extract_open
from .profile_ingestion import MeasuredRedis, ProfileStore, verify_graph
from .schema import DomainPack, PackRegistration, SchemaRuntime
from .store import Store


def run():
    results=[]
    for size in (10,30,80):
        for enabled in (False,True):
            cfg=Settings(schema_writes=True,open_predicates=enabled,provider="offline",allow_paid_calls=False,
                redis_url=os.getenv("UGI_TEST_REDIS_URL","redis://127.0.0.1:6380/0"),graph_prefix="ugi_gperf_"+uuid4().hex[:8])
            client=MeasuredRedis.from_url(cfg.redis_url,decode_responses=True,socket_timeout=15)
            graph=ProfileStore(cfg,client=client)
            try:
                raw=sample_pack("it").model_dump_json()
                start=perf_counter()
                pack=DomainPack.model_validate_json(raw)
                load_ms=(perf_counter()-start)*1000
                start=perf_counter()
                registered=SchemaRuntime(graph).register(PackRegistration(pack=pack,authorise_action=True))
                register_ms=(perf_counter()-start)*1000
                graph.write_ms=0
                client.reset_measurements()
                text="\n".join("S"+str(i)+" intermediated for G"+str(i)+"."
                                 for i in range(size))
                tracemalloc.start()
                start=perf_counter()
                extracted=extract_open(text)
                extraction_ms=(perf_counter()-start)*1000
                start=perf_counter()
                report=Engine(graph).ingest("frames.txt",text.encode(),pack_refs=[registered["ref"]] if enabled else [])
                elapsed=(perf_counter()-start)*1000
                peak=tracemalloc.get_traced_memory()[1]
                tracemalloc.stop()
                queries=client.measurements()
                bindings=graph.list("SchemaBinding")
                lookup_ms=None
                if bindings:
                    start=perf_counter()
                    retrieved=SchemaRuntime(graph).assertions(bindings[0]["predicate_definition_id"])
                    lookup_ms=(perf_counter()-start)*1000
                    assert len(retrieved["items"]) == size
                verified=verify_graph(graph,Store(cfg))
                results.append(dict(rows=size,open_enabled=enabled,pack_load_ms=round(load_ms,3),
                    pack_register_ms=round(register_ms,3),ingest_ms=round(elapsed,3),write_ms=round(graph.write_ms,3),
                    queries=queries,peak_python_bytes=peak,claims=report["claims"],
                    bindings=len(bindings),registry_lookup_ms=round(lookup_ms,3) if lookup_ms is not None else None,
                    literal_extraction_ms=round(extraction_ms,3),literal_candidates=len(extracted[0]),
                    canonicalization_candidate_counts=[len(b["candidate_definition_ids"]) for b in bindings],
                    verification=verified,counts=graph.counts(),model_calls=0))
            finally:
                if tracemalloc.is_tracing():
                    tracemalloc.stop()
                assert graph.graph.startswith(cfg.graph_prefix+"_")
                client.execute_command("GRAPH.DELETE",graph.graph)
    return dict(recorded_at=now(),backend="actual FalkorDB",results=results,
        limitations=["One observation per setting, no p95/server memory/large mixed updates",
                     "Short source frames are already grammar-readable; measures added registry/pinning work, not a speedup",
                     "Registry lookup includes exact per-assertion evidence/head fetches; bounded200",
                     "Source frames deliberately repeat one novel predicate; identity ledger is off"])


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    result=run()
    args.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps([{k:r[k] for k in ("rows","open_enabled","claims","ingest_ms","bindings")} for r in result["results"]]))
