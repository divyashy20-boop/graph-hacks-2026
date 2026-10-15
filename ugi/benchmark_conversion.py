"""Bounded CSV/JSON ingestion and persistence measurements, never production claims."""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import statistics
import tracemalloc
from pathlib import Path
from time import perf_counter, process_time
from uuid import uuid4

from redis.exceptions import RedisError

from .engine import Engine
from .models import RelationQuery, Settings, now
from .store import Store


class TimedStore(Store):
    def __init__(self, *args, **kwargs):
        self.write_ms = 0
        super().__init__(*args, **kwargs)

    def commit(self, *args, **kwargs):
        started = perf_counter()
        try:
            return super().commit(*args, **kwargs)
        finally:
            self.write_ms += (perf_counter() - started) * 1000


def payload(size, extension):
    rows = [dict(subject="Node" + str(i), predicate="DEPENDS_ON", object="Node" + str(i+1))
            for i in range(size)]
    if extension == "json":
        return json.dumps(rows, separators=(",", ":")).encode()
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def run(sizes=(100, 1000, 2000), backend="falkordb", formats=("csv", "json")):
    if not sizes or any(not 3 <= size <= 2000 for size in sizes):
        raise ValueError("Benchmark sizes must fit 3..2000 record quota")
    settings = Settings(backend=backend, graph_prefix="ugi_perf_" + uuid4().hex[:12],
                        redis_url=os.environ.get("UGI_TEST_REDIS_URL", "redis://127.0.0.1:6380/0"),
                        provider="offline", allow_paid_calls=False)
    results = []
    for extension in formats:
        if extension not in {"csv", "json"}:
            raise ValueError("Only CSV and JSON benchmark formats")
        for size in sizes:
            stores = []
            try:
                content = payload(size, extension)
                tracemalloc.start()
                wall, cpu = perf_counter(), process_time()
                store = TimedStore(settings, dataset=f"{extension}-{size}")
                stores.append(store)
                initialized = perf_counter()
                engine = Engine(store)
                report = engine.ingest("chain." + extension, content)
                ingest_ms = (perf_counter() - initialized) * 1000
                total_ms, cpu_ms = (perf_counter() - wall)*1000, (process_time()-cpu)*1000
                _, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                counts = store.counts()
                assert counts["Entity"] == size + 1 and counts["Claim"] == size
                before = store.counts()
                duplicate_start = perf_counter()
                duplicate = engine.ingest("chain." + extension, content)
                duplicate_ms = (perf_counter() - duplicate_start) * 1000
                assert duplicate["duplicate"] and before == store.counts()
                durations = []
                for _ in range(5):
                    started = perf_counter()
                    answer = engine.relationship(RelationQuery(subject="Node0", object="Node2",
                                                                predicate="TRANSITIVELY_DEPENDS_ON"))
                    durations.append((perf_counter() - started) * 1000)
                    assert answer["status"] == "RULE_DERIVED"
                reconnect = Store(settings, dataset=f"{extension}-{size}") if backend == "falkordb" else store
                assert reconnect.counts() == counts
                isolated = TimedStore(settings, dataset=f"repeat-{extension}-{size}")
                stores.append(isolated)
                assert not isolated.claims()
                Engine(isolated).ingest("chain." + extension, content)
                assert {c["id"] for c in store.claims()} == {c["id"] for c in isolated.claims()}
                results.append(dict(format=extension, records=size, input_bytes=len(content),
                                    success=True,
                                    initialization_ms=round((initialized-wall)*1000, 3),
                                    ingestion_ms=round(ingest_ms, 3), total_wall_ms=round(total_ms, 3),
                                    graph_write_ms=round(store.write_ms, 3),
                                    client_process_cpu_ms=round(cpu_ms, 3),
                                    python_allocations_peak_bytes=peak, counts=counts,
                                    duplicate_wall_ms=round(duplicate_ms, 3), duplicate_no_new_records=True,
                                    query_observations_ms=[round(t, 3) for t in durations],
                                    query_median_ms=round(statistics.median(durations), 3),
                                    reconnect_counts_equal=True, repeated_claim_ids_equal=True,
                                    model_calls=report["usage"]["calls"]))
            except (RedisError, ValueError) as exc:
                peak = tracemalloc.get_traced_memory()[1] if tracemalloc.is_tracing() else peak
                results.append(dict(format=extension, records=size, success=False,
                                    error_type=type(exc).__name__, error=str(exc),
                                    elapsed_ms=round((perf_counter()-wall)*1000, 3),
                                    input_bytes=len(content), graph_write_ms=round(store.write_ms, 3),
                                    python_allocations_peak_bytes=peak,
                                    client_process_cpu_ms=round((process_time()-cpu)*1000, 3),
                                    counts_after_failure=store.counts() if stores else None,
                                    model_calls=0))
            finally:
                if tracemalloc.is_tracing():
                    tracemalloc.stop()
                for store in stores:
                    if store.client:
                        assert store.graph.startswith(settings.graph_prefix + "_")
                        store.client.execute_command("GRAPH.DELETE", store.graph)
    return dict(recorded_at=now(), backend=backend, results=results, model_calls=0,
                limitations=["Single local machine, one traced ingestion per size/format, not throughput/p95",
                             "Python allocation peak is not process RSS/GPU/server memory",
                             "CPU time covers Python client, not FalkorDB process or Docker host",
                             "Five queries over a bounded synthetic chain; no production scalability claim",
                             "Write time includes client serialization and synchronous graph roundtrip"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", nargs="+", type=int, default=[100, 1000, 2000])
    parser.add_argument("--backend", choices=["memory", "falkordb"], default="falkordb")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.sizes, args.backend)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps([dict(format=r["format"], records=r["records"], success=r["success"],
                           ingestion_ms=r.get("ingestion_ms"), error=r.get("error"),
                           graph_write_ms=r.get("graph_write_ms"), query_median_ms=r.get("query_median_ms"))
                      for r in result["results"]], indent=2))


if __name__ == "__main__":
    main()
