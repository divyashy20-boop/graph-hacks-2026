"""Bounded ledger-off/on overhead observation on two isolated actual graphs."""
import argparse
import json
import os
import tracemalloc
from pathlib import Path
from time import perf_counter, process_time
from uuid import uuid4

from .benchmark_conversion import payload
from .engine import Engine
from .models import Settings, now
from .profile_ingestion import MeasuredRedis, ProfileStore, verify_graph
from .store import Store


def run():
    results = []
    for enabled in (False, True):
        settings = Settings(identity_ledger=enabled, provider="offline", allow_paid_calls=False,
                            graph_prefix="ugi_eperf_"+uuid4().hex[:10],
                            redis_url=os.getenv("UGI_TEST_REDIS_URL", "redis://127.0.0.1:6380/0"))
        client = MeasuredRedis.from_url(settings.redis_url, decode_responses=True,
                                       socket_connect_timeout=3, socket_timeout=15)
        store = ProfileStore(settings, client=client)
        try:
            client.reset_measurements()
            tracemalloc.start()
            started, cpu = perf_counter(), process_time()
            Engine(store).ingest("chain.csv", payload(100, "csv"))
            observation = dict(identity_ledger=enabled, rows=100,
                               ingestion_ms=round((perf_counter()-started)*1000, 3),
                               graph_write_ms=round(store.write_ms, 3),
                               client_cpu_ms=round((process_time()-cpu)*1000, 3),
                               python_allocation_peak_bytes=tracemalloc.get_traced_memory()[1],
                               **client.measurements())
            tracemalloc.stop()
            reader = Store(settings)
            observation["retrieval"] = verify_graph(store, reader)
            observation["counts"] = reader.counts()
            assert observation["counts"].get("MentionSnapshot", 0) == (200 if enabled else 0)
            assert observation["counts"]["Claim"] == 100
            before = reader.counts()
            assert Engine(store).ingest("chain.csv", payload(100, "csv"))["duplicate"]
            assert reader.counts() == before
            results.append(observation)
        finally:
            if tracemalloc.is_tracing():
                tracemalloc.stop()
            assert store.graph.startswith(settings.graph_prefix+"_")
            store.client.execute_command("GRAPH.DELETE", store.graph)
            client.close()
    return dict(recorded_at=now(), backend="actual FalkorDB", results=results, model_calls=0,
                limitations=["One traced100-row chain per mode, not a controlled throughput/p95 estimate",
                             "Opt-in ledger rejects over200 mentions/upload or per card; not2000-row ledger capacity",
                             "Client CPU/allocation measurements exclude server CPU/RSS",
                             "Fresh independent nodes only; mixed-upsert limit remains"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps([{k: r[k] for k in ("identity_ledger", "ingestion_ms", "graph_write_ms",
                                       "cypher_queries", "retrieval")} for r in result["results"]], indent=2))


if __name__ == "__main__":
    main()
