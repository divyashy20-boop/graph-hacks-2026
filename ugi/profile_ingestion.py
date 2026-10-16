"""Actual isolated graph profiling; GRAPH.PROFILE executes writes, never a dry run."""
from __future__ import annotations

import argparse
import json
import os
import re
import tracemalloc
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from time import perf_counter, process_time
from uuid import uuid4

from redis import Redis
from redis.exceptions import RedisError

from .benchmark_conversion import TimedStore, payload
from .conversion_audit import incidence
from .engine import Engine
from .models import RelationQuery, Settings, now
from .store import Store


class MeasuredRedis(Redis):
    def reset_measurements(self):
        self.commands = Counter()
        self.roundtrip_ms = 0.0
        self.graph_response_ms = 0.0
        self.graph_internal_ms = 0.0
        self.failed_commands = 0
        self.last_write = None

    def execute_command(self, *args, **kwargs):
        if not hasattr(self, "commands"):
            self.reset_measurements()
        command = str(args[0]).upper()
        self.commands[command] += 1
        if command == "GRAPH.QUERY" and "MERGE" in str(args[2]):
            self.last_write = args
        start = perf_counter()
        try:
            result = super().execute_command(*args, **kwargs)
            if command == "GRAPH.QUERY" and isinstance(result, list):
                for item in result[-1] if result and isinstance(result[-1], list) else []:
                    match = re.search(r"Query internal execution time: ([\d.]+)", str(item))
                    if match:
                        self.graph_internal_ms += float(match[1])
            return result
        except RedisError:
            self.failed_commands += 1
            raise
        finally:
            elapsed = (perf_counter() - start) * 1000
            self.roundtrip_ms += elapsed
            if command == "GRAPH.QUERY":
                self.graph_response_ms += elapsed

    def measurements(self):
        return dict(redis_commands=dict(self.commands), network_roundtrips=sum(self.commands.values()),
                    cypher_queries=self.commands["GRAPH.QUERY"],
                    client_command_wall_ms=round(self.roundtrip_ms, 3),
                    graph_response_wall_ms=round(self.graph_response_ms, 3),
                    successful_graph_internal_ms=round(self.graph_internal_ms, 3),
                    failed_commands=self.failed_commands)


class ProfileStore(TimedStore):
    def __init__(self, *args, **kwargs):
        self.transaction_ms = 0
        self.expected = {}
        super().__init__(*args, **kwargs)

    @contextmanager
    def transaction(self):
        nested = bool(getattr(getattr(self, "_transaction_state", None), "depth", 0))
        start = perf_counter()
        try:
            with super().transaction():
                yield
        finally:
            if not nested:
                self.transaction_ms += (perf_counter() - start) * 1000

    def commit(self, records, links=()):
        records = list(records)
        self.expected.update({r["id"]: r for r in records})
        return super().commit(records, links)


def verify_graph(store, reader):
    rows = reader.query("MATCH (n:Record) RETURN n.id,labels(n),n.payload")
    actual = {}
    for ident, labels, raw in rows:
        record = json.loads(raw)
        # Existing Store uses the non-compact Redis protocol: arrays render as
        # '[Record, Claim]', unlike native client/compact decoded label lists.
        if isinstance(labels, str):
            labels = re.findall(r"[A-Za-z_]+", labels)
        assert set(labels) == {"Record", record["kind"]}, "Kind label/payload mismatch"
        assert ident == record["id"] and ident not in actual, "Duplicate/stale record ID"
        actual[ident] = record
    assert actual == store.expected, "Reconnected payload differs from intended staged records"
    edges = {tuple(row) for row in reader.query(
        "MATCH (a:Record)-[r]->(b:Record) RETURN a.id,b.id,type(r),r.claim_id,r.role")}
    assert edges == incidence(actual), "Exact graph incidence mismatch"
    return dict(exact_records=len(actual), exact_edges=len(edges), kind_labels_consistent=True,
                payloads_consistent=True, incidence_consistent=True)


def profile(sizes=(100, 1000, 2000)):
    if not sizes or any(n not in {100, 1000, 2000} for n in sizes):
        raise ValueError("Profile only quota-sized 100/1000/2000 synthetic records")
    settings = Settings(provider="offline", allow_paid_calls=False,
                        graph_prefix="ugi_dprof_" + uuid4().hex[:10],
                        redis_url=os.environ.get("UGI_TEST_REDIS_URL", "redis://127.0.0.1:6380/0"))
    results = []
    for extension in ("csv", "json"):
        for size in sizes:
            dataset = extension + str(size)
            client = MeasuredRedis.from_url(settings.redis_url, decode_responses=True,
                                            socket_connect_timeout=3, socket_timeout=15)
            store = ProfileStore(settings, dataset=dataset, client=client)
            row = dict(format=extension, records=size, success=False)
            try:
                client.reset_measurements()
                content = payload(size, extension)
                tracemalloc.start()
                wall, cpu = perf_counter(), process_time()
                try:
                    Engine(store).ingest("chain." + extension, content)
                    row["success"] = True
                except (RedisError, ValueError) as exc:
                    row.update(error=str(exc), error_type=type(exc).__name__)
                row.update(ingestion_ms=round((perf_counter()-wall)*1000, 3),
                           graph_write_ms=round(store.write_ms, 3),
                           transaction_ms=round(store.transaction_ms, 3),
                           client_cpu_ms=round((process_time()-cpu)*1000, 3),
                           python_allocation_peak_bytes=tracemalloc.get_traced_memory()[1],
                           input_bytes=len(content), model_calls=0,
                           **client.measurements())
                tracemalloc.stop()
                row["client_cpu_ms_per_record"] = round(row["client_cpu_ms"]/size, 4)
                row["writer_strategy"] = getattr(store, "last_write_strategy", "legacy_c_baseline")
                row["non_command_wall_ms"] = round(row["ingestion_ms"]-row["client_command_wall_ms"], 3)
                write = client.last_write
                row["counts"] = store.counts()
                if row["success"]:
                    reader = Store(settings, dataset=dataset)
                    row["retrieval"] = verify_graph(store, reader)
                    before = store.counts()
                    repeated = Engine(store).ingest("chain."+extension, content)
                    assert repeated["duplicate"] and store.counts() == before
                    row["duplicate_no_new_records"] = True
                    started = perf_counter()
                    answer = Engine(reader).relationship(RelationQuery(
                        subject="Node0", object="Node2", predicate="TRANSITIVELY_DEPENDS_ON"))
                    row["two_hop_query_ms"] = round((perf_counter()-started)*1000, 3)
                    assert answer["status"] == "RULE_DERIVED"
                else:
                    assert not row["counts"], "Failed fresh upload left partial records"
                if write:
                    row["write_command_bytes"] = len(write[2].encode())
                    row["write_plan"] = client.execute_command("GRAPH.EXPLAIN", store.graph, write[2])
                    if size == 100 and row["success"]:
                        fresh = Store(settings, dataset="operators-"+dataset)
                        try:
                            row["write_profile_on_fresh_graph"] = client.execute_command(
                                "GRAPH.PROFILE", fresh.graph, write[2], "TIMEOUT", 5000)
                            verify_graph(store, fresh)
                        finally:
                            assert fresh.graph.startswith(settings.graph_prefix + "_")
                            fresh.client.execute_command("GRAPH.DELETE", fresh.graph)
                results.append(row)
            finally:
                if tracemalloc.is_tracing():
                    tracemalloc.stop()
                assert store.graph.startswith(settings.graph_prefix + "_")
                client.execute_command("GRAPH.DELETE", store.graph)
                client.close()
    return dict(recorded_at=now(), results=results, backend="actual FalkorDB", model_calls=0,
                timeout_ms=5000,
                limitations=["Single-machine traced synthetic observations, not p95/throughput",
                             "Graph internal time excludes failed-query server time, which is unavailable",
                             "Client command wall includes network/server/client decode, not pure network time",
                             "Non-command wall includes serialization/processing/wait, not pure CPU",
                             "GRAPH.PROFILE executes the captured fresh-upload write on another owned empty graph",
                             "Counters include Redis lock calls but not TCP handshake packets or connect PING",
                             "Python allocation peak/client CPU are not server RSS/GPU/host CPU"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", nargs="+", type=int, default=[100, 1000, 2000])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = profile(args.sizes)
    args.output.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps([{k: r.get(k) for k in ("format", "records", "success", "ingestion_ms",
                     "graph_write_ms", "cypher_queries", "network_roundtrips", "error")}
                      for r in result["results"]], indent=2))


if __name__ == "__main__":
    main()
