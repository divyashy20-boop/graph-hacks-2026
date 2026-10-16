"""Authored schema/shape tests, not independently annotated language accuracy."""
import json
import os
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from redis.exceptions import ResponseError

from ugi.api import create_app
from ugi.engine import Engine
from ugi.models import RelationQuery, Settings, uid
from ugi.schema import DomainPack, PackRegistration, SchemaRuntime
from ugi.store import Store


def pack(name="it"):
    return DomainPack.model_validate_json((Path(__file__).parents[1]/"ugi/packs"/(name+".json")).read_text())


def register(store, value=None):
    return SchemaRuntime(store).register(PackRegistration(pack=value or pack(), authorise_action=True))


def config(**kwargs):
    return Settings(backend="memory", schema_writes=True, **kwargs)


def row(**kwargs):
    return dict(subject="Checkout", subject_type="it:Service", predicate="requires",
                object="Payments", object_type="it:API", **kwargs)


@pytest.mark.parametrize("mutation", [
    {"version":"01.0.0"}, {"version":"1.0"}, {"schema_version":2},
    {"namespace":"../bad"}, {"python":"import os"}, {"cypher":"MATCH (n) DELETE n"},
    {"url":"http://localhost/private"}, {"entity_types":["foreign:Service"]},
])
def test_pack_rejects_unsafe_or_invalid_configuration(mutation):
    with pytest.raises(ValueError):
        DomainPack.model_validate({**pack().model_dump(), **mutation})


def test_role_alias_conflict_and_immutable_versioning():
    data = pack().model_dump()
    data["predicates"][1]["aliases"] = ["requires"]
    with pytest.raises(ValueError, match="alias"):
        DomainPack.model_validate(data)
    data = pack().model_dump()
    data["predicates"][0]["roles"][0]["maximum"] = 2
    with pytest.raises(ValueError):
        DomainPack.model_validate(data)
    store = Store(config())
    first = register(store)
    assert first == register(store) and first["content_hash"] == pack().content_hash
    changed = pack().model_dump()
    changed["predicates"][0]["definition"] += " Updated meaning."
    with pytest.raises(ValueError, match="conflict"):
        register(store, DomainPack.model_validate(changed))
    changed["version"] = "2.0.0"
    second = register(store, DomainPack.model_validate(changed))
    assert second["id"] != first["id"] and store.get(first["id"]) == first
    assert len(store.list("DomainPack")) == 2


def test_three_packs_role_validation_exact_evidence_and_no_rule_leakage():
    store = Store(config())
    for name in ("it", "supply", "research"):
        register(store, pack(name))
    refs = [pack().ref]
    content = json.dumps([row()]).encode()
    report = Engine(store).ingest("it.json", content, pack_refs=refs)
    binding = store.list("SchemaBinding")[0]
    claim = store.claims()[0]
    assert binding["state"] == "KNOWN_COMPATIBLE"
    items = SchemaRuntime(store).assertions(binding["predicate_definition_id"])["items"]
    assert items[0]["evidence"]["quote"] == store.get(claim["chunk_id"])["text"]
    assert not Engine(store).usable(claim)
    assert Engine(store).relationship(RelationQuery(subject="Checkout", object="Payments", predicate="DEPENDS_ON"))["status"] == "UNKNOWN"
    assert Engine(store).ingest("it.json", content, pack_refs=refs)["duplicate"]
    with pytest.raises(ValueError, match="already pinned"):
        Engine(store).ingest("it.json", content)
    assert store.get(report["source_id"])["pack_refs"] == [pack().ref.model_dump()]
    wrong = row()
    wrong["subject_type"] = "it:Database"
    Engine(store).ingest("wrong.json", json.dumps([wrong]).encode(), pack_refs=refs)
    assert store.list("SchemaBinding")[-1]["state"] == "INCOMPATIBLE"
    event = dict(relation_type="PROVISION", participants=[
        dict(role="provider", name="Nova", entity_type="supply:Supplier"),
        dict(role="item", name="Fiber", entity_type="supply:Component"),
        dict(role="recipient", name="Harbor", entity_type="supply:Factory")], modality="possible")
    Engine(store).ingest("supply.json", json.dumps([event]).encode(), pack_refs=[pack("supply").ref])
    assert store.list("SchemaBinding")[-1]["state"] == "KNOWN_COMPATIBLE"
    assert len(store.claims()) == 2 and len(store.events()) == 1
    assert not store.events()[0]["eligible_for_inference"]
    research = dict(subject="Ada", subject_type="research:Researcher", predicate="INVESTIGATES",
                    object="Optics", object_type="research:Topic")
    Engine(store).ingest("research.json", json.dumps([research]).encode(), pack_refs=[pack("research").ref])
    assert store.list("SchemaBinding")[-1]["namespace"] == "research"


def test_dependency_pins_namespace_ambiguity_and_isolation():
    store = Store(config())
    data = pack("supply").model_dump()
    data["dependencies"] = [pack().ref.model_dump()]
    data["predicates"][0]["roles"][1]["types"] = ["it:Component"]
    bridge = DomainPack.model_validate(data)
    with pytest.raises(ValueError, match="missing"):
        register(store, bridge)
    register(store)
    register(store, bridge)
    assert SchemaRuntime(store).load([bridge.ref])
    with pytest.raises(ValueError):
        SchemaRuntime(Store(config(), owner="other")).load([bridge.ref])
    changed = pack().model_dump()
    changed["namespace"] = "other"
    changed["entity_types"] = [t.replace("it:", "other:") for t in changed["entity_types"]]
    for p in changed["predicates"]:
        for r in p["roles"]:
            r["types"] = [t.replace("it:", "other:") for t in r["types"]]
    other = DomainPack.model_validate(changed)
    register(store, other)
    Engine(store).ingest("ambiguous.json", json.dumps([row()]).encode(), pack_refs=[pack().ref, other.ref])
    assert store.list("SchemaBinding")[0]["state"] == "UNRESOLVED"


def test_pack_api_dual_gate_and_tenant_scope():
    app = create_app(config(api_keys="alice,bob"))
    with TestClient(app) as client:
        request = dict(pack=pack().model_dump(), authorise_action=False)
        assert client.post("/api/schema/packs", json=request, headers={"x-api-key":"alice"}).status_code == 422
        request["authorise_action"] = True
        assert client.post("/api/schema/packs", json=request, headers={"x-api-key":"alice"}).status_code == 200
        assert client.get("/api/schema/packs", headers={"x-api-key":"bob"}).json() == []
        assert client.get("/api/schema/packs").status_code == 401
    with pytest.raises(ValueError):
        register(Store(Settings(backend="memory")))


@pytest.mark.integration
def test_real_schema_index_reconnect_and_late_rollback():
    if not os.getenv("UGI_TEST_REDIS_URL"):
        pytest.skip("Requires actual FalkorDB")
    settings = Settings(schema_writes=True, redis_url=os.environ["UGI_TEST_REDIS_URL"],
                        graph_prefix="ugi_gschema_"+uuid4().hex[:8])
    store = Store(settings)
    try:
        original = register(store)
        Engine(store).ingest("it.json", json.dumps([row()]).encode(), pack_refs=[pack().ref])
        binding = store.list("SchemaBinding")[0]
        reader = Store(settings)
        assert SchemaRuntime(reader).assertions(binding["predicate_definition_id"])["items"][0]["binding"] == binding
        plan = store.client.execute_command("GRAPH.EXPLAIN", store.graph,
            "CYPHER key='x' MATCH (b:SchemaBinding) WHERE b.block_key=$key RETURN b.payload LIMIT 101")
        assert "Index Scan" in str(plan)
        before = {r[0]:r[1] for r in store.query("MATCH(n:Record) RETURN n.id,n.payload")}
        changed = pack().model_dump()
        changed["version"] = "1.0.1"
        second = DomainPack.model_validate(changed)
        record = dict(id=uid("rollback-pack"), kind="DomainPack", pack=second.model_dump())
        with pytest.raises(ResponseError):
            store.commit([record, dict(id=uid("bad-g"), kind="Usage", name_key={"map":"invalid"})])
        assert before == {r[0]:r[1] for r in store.query("MATCH(n:Record) RETURN n.id,n.payload")}
        assert reader.get(original["id"]) == original
        with pytest.raises(ValueError, match="Immutable"):
            store.commit([{**deepcopy(original), "content_hash":"0"*64}])
    finally:
        store.client.execute_command("GRAPH.DELETE", store.graph)
