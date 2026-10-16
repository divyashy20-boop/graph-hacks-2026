"""Increasing bounded source/candidate overhead; not enterprise throughput."""
import argparse
import json
import os
import tracemalloc
from pathlib import Path
from time import perf_counter, process_time
from uuid import uuid4

from .engine import Engine
from .identity import IdentityLedger
from .identity_policy import IdentityPolicy
from .models import Settings, now
from .profile_ingestion import MeasuredRedis, ProfileStore, verify_graph
from .resolution import IdentityResolver
from .store import Store


def run():
    results = []
    for size in (10, 30, 80):
        cfg = Settings(identity_ledger=True, identity_resolution="dry_run", provider="offline",
                       allow_paid_calls=False, graph_prefix="ugi_fperf_"+uuid4().hex[:8],
                       redis_url=os.getenv("UGI_TEST_REDIS_URL", "redis://127.0.0.1:6380/0"))
        client = MeasuredRedis.from_url(cfg.redis_url, decode_responses=True)
        store = ProfileStore(cfg, client=client)
        try:
            rows = [dict(subject="Name "+str(i), predicate="USES", object="Shared Tool") for i in range(size)]
            client.reset_measurements()
            tracemalloc.start()
            wall, cpu = perf_counter(), process_time()
            report = Engine(store).ingest("records.json", json.dumps(rows).encode())
            result = dict(rows=size, mentions=2*size, ingestion_ms=round((perf_counter()-wall)*1000, 3),
                          write_ms=round(store.write_ms, 3), client_cpu_ms=round((process_time()-cpu)*1000, 3),
                          python_allocation_peak_bytes=tracemalloc.get_traced_memory()[1],
                          ingestion_measurements=client.measurements(), model_calls=report["usage"]["calls"])
            tracemalloc.stop()
            result["exact_graph"] = verify_graph(store, Store(cfg))
            mid = next(m["id"] for m in store.list("MentionSnapshot") if m["text"] == "Shared Tool")
            client.reset_measurements()
            started = perf_counter()
            retrieval = IdentityResolver(store).candidates(mid)
            result["candidate_wall_ms"] = round((perf_counter()-started)*1000, 3)
            result["candidate_count"] = retrieval["candidate_count"]
            result["candidate_complete"] = retrieval["complete"]
            result["candidate_measurements"] = client.measurements()
            start = perf_counter()
            cluster = IdentityPolicy(store).inspect(mid)
            result["cluster_ms"] = round((perf_counter()-start)*1000, 3)
            result["cluster_pair_checks"] = cluster["analysis"]["pair_checks"]
            start = perf_counter()
            eid = store.get(mid)["entity_id"]
            card = IdentityLedger(store).card(eid)
            result["card_reconstruction_ms"] = round((perf_counter()-start)*1000, 3)
            assert len(card["mentions"]) == size and retrieval["candidate_count"] == min(size-1, 20)
            results.append(result)
        finally:
            if tracemalloc.is_tracing():
                tracemalloc.stop()
            assert store.graph.startswith(cfg.graph_prefix+"_")
            client.execute_command("GRAPH.DELETE", store.graph)
    return dict(recorded_at=now(), backend="actual FalkorDB", results=results, model_calls=0,
                limitations=["One local traced observation per size, no p95/production claim",
                             "Shared-name candidate pressure intentionally overflows20-candidate budget at30/80 rows",
                             "Singleton unresolved clusters: no claim of large-cluster matching throughput",
                             "Memory/CPU are Python client only; no server RSS/CPU",
                             "Correction and invalidation separately verified by real policy tests/demos"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run()
    args.output.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps([{k: r[k] for k in ("rows", "ingestion_ms", "write_ms", "candidate_count",
                                       "candidate_complete", "candidate_wall_ms")} for r in result["results"]], indent=2))


if __name__ == "__main__":
    main()
