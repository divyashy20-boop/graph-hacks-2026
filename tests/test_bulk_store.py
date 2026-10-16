import json
import os
from contextlib import nullcontext
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from redis.exceptions import ResponseError

from ugi.benchmark_conversion import payload
from ugi.engine import Engine
from ugi.models import Settings
from ugi.profile_ingestion import ProfileStore, verify_graph
from ugi.store import Store


def test_one_atomic_write_after_readonly_classification_with_unique_aliases():
    store = Store(Settings(backend="memory"))
    store.client = object()
    captured = []
    def query(text, params):
        captured.append((text, params))
        return []
    store.query = query
    store.transaction = nullcontext
    store.commit([dict(id="s", kind="Source"), dict(id="c", kind="Chunk", source_id="s")],
                 iter([("s", "c", "HAS_CHUNK", "c")]))
    assert len(captured) == 2
    assert captured[0][0].startswith("UNWIND $ids")  # Read only, not a partial commit.
    query, params = captured[1]
    assert "CREATE (created:Record)" in query
    assert "WITH collect(bound) AS nodes" in query
    assert "SET typed_Source:Source" in query and "SET typed_Chunk:Chunk" in query
    assert "source_HAS_CHUNK" in query and "target_HAS_CHUNK" in query
    assert params["HAS_CHUNK"] == [dict(ai=1, bi=0, claim_id="c", role="")]
    store.commit([])
    assert len(captured) == 2  # Empty action is an explicit no-op.
    with pytest.raises(ValueError):
        store.commit([dict(id="x", kind="DROP")])
    assert len(captured) == 2


def real_settings():
    if not os.getenv("UGI_TEST_REDIS_URL"):
        pytest.skip("Requires actual FalkorDB")
    return Settings(redis_url=os.environ["UGI_TEST_REDIS_URL"], graph_prefix="ugi_bulk_"+uuid4().hex[:10])


def test_document_read_cache_never_survives_a_new_upload():
    from collections import Counter

    class CountingStore(Store):
        def __init__(self):
            self.reads = Counter()
            super().__init__(Settings(backend="memory"))

        def get(self, ident):
            self.reads[ident] += 1
            return super().get(ident)

    store = CountingStore()
    engine = Engine(store)
    base = dict(subject="Vega", subject_id="v", object="Willow", object_id="w", predicate="OWNS")
    engine.ingest("one.json", json.dumps([base, {**base, "predicate": "USES"}]).encode())
    eid = next(e["id"] for e in store.list("Entity") if e["name"] == "Vega")
    assert store.reads[eid] == 1
    store.reads.clear()
    engine.ingest("two.json", json.dumps([{**base, "subject": "Nova", "predicate": "USES"}]).encode())
    assert store.reads[eid] >= 1
    assert store.get(eid)["name"] == "Nova" and "Vega" in store.get(eid)["aliases"]
    assert len(store.list("Entity")) == 2


@pytest.mark.integration
def test_real_bulk_mixed_payload_labels_roles_rewrite_and_reconnect():
    settings = real_settings()
    store = ProfileStore(settings)
    try:
        engine = Engine(store)
        text = (Path(__file__).parents[1]/"demo/relation_events.txt").read_bytes()
        engine.ingest("events.txt", text)
        engine.ingest("chain.csv", payload(100, "csv"))
        expected = dict(store.expected)
        reader = Store(settings)
        verification = verify_graph(store, reader)
        assert verification["kind_labels_consistent"] and verification["exact_edges"] > 400
        assert len(reader.events()) == 4 and len(reader.claims()) == 100
        before = store.counts()
        # Direct replay of records/edges, not just Engine's duplicate-source bypass.
        edges = store.query("MATCH (a:Record)-[r]->(b:Record) RETURN a.id,b.id,type(r),r.claim_id,r.role")
        store.commit(list(expected.values()), edges)
        assert store.counts() == before
        verify_graph(store, Store(settings))
    finally:
        assert store.graph.startswith(settings.graph_prefix+"_")
        store.client.execute_command("GRAPH.DELETE", store.graph)


@pytest.mark.integration
def test_real_runtime_error_rolls_back_earlier_updates_and_new_records():
    settings = real_settings()
    store = Store(settings)
    try:
        seed = dict(id="original", kind="Entity", name_key="original", aliases=[])
        store.commit([seed])
        before = store.query("MATCH (n:Record) RETURN n.id,n.payload ORDER BY n.id")
        with pytest.raises(ResponseError):
            # A nested map is valid JSON payload but invalid as a graph property.
            # Trigger a genuine server-side runtime error after an earlier update.
            store.commit([{**seed, "name_key": "changed"},
                          dict(id="new", kind="Entity", name_key={"invalid": "property map"}),
                          dict(id="source", kind="Source", filename="not-committed")])
        assert store.query("MATCH (n:Record) RETURN n.id,n.payload ORDER BY n.id") == before
        assert json.loads(before[0][1]) == seed
        assert Store(settings).get("original") == seed
        assert store.last_write_strategy == "legacy_existing_endpoints"
        with pytest.raises(ResponseError):
            store.commit([dict(id="new-only", kind="Entity", name_key="new-only"),
                          dict(id="invalid-only", kind="Entity", name_key={"invalid": "property map"})])
        assert store.last_write_strategy == "bound_nodes_all_new"
        assert store.query("MATCH (n:Record) RETURN n.id,n.payload ORDER BY n.id") == before
    finally:
        assert store.graph.startswith(settings.graph_prefix+"_")
        store.client.execute_command("GRAPH.DELETE", store.graph)


@pytest.mark.integration
def test_real_concurrent_classification_and_mixed_references_are_serialized():
    from concurrent.futures import ThreadPoolExecutor

    settings = real_settings()
    first, second = Store(settings), Store(settings)
    gate = Barrier(2)
    try:
        def write(store):
            gate.wait(timeout=5)
            store.commit([dict(id="shared", kind="Entity", name_key="shared")])
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(write, s) for s in (first, second)]
            for future in futures:
                future.result(timeout=15)
        assert first.counts() == {"Entity": 1}
        first.commit([dict(id="fresh", kind="Entity", name_key="fresh")],
                     [("fresh", "shared", "RELATES", "test-edge")])
        assert first.query("MATCH (a)-[r:RELATES]->(b) RETURN a.id,b.id,r.claim_id") == [
            ["fresh", "shared", "test-edge"]]
        assert first.last_write_strategy == "legacy_existing_endpoints"
        second.commit([], [("fresh", "shared", "RELATES", "test-edge")])
        assert first.counts() == {"Entity": 2}
        before = first.counts()
        with pytest.raises(ValueError, match="endpoint missing"):
            first.commit([dict(id="not-written", kind="Source")],
                         [("not-written", "absent", "HAS_CHUNK", "bad-edge")])
        assert first.counts() == before
    finally:
        assert first.graph.startswith(settings.graph_prefix+"_")
        first.client.execute_command("GRAPH.DELETE", first.graph)
