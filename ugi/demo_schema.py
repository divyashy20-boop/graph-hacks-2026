"""Synthetic universal schema demonstration on actual persistent FalkorDB."""
import argparse
import json
from importlib.resources import files
from pathlib import Path
from time import perf_counter

from .engine import Engine
from .models import Settings, now
from .schema import DomainPack, MappingChange, PackRegistration, SchemaRuntime
from .store import Store


def sample_pack(name):
    if name not in {"it", "supply", "research"}:
        raise ValueError("Unknown bundled demonstration pack")
    return DomainPack.model_validate_json(files("ugi").joinpath("packs", name+".json").read_text(encoding="utf-8"))


def demonstrate(dataset):
    cfg = Settings(provider="offline", allow_paid_calls=False, schema_writes=True, open_predicates=True,
                   identity_ledger=True,identity_resolution="dry_run")
    store = Store(cfg, dataset=dataset)
    runtime, engine = SchemaRuntime(store), Engine(store)
    started = perf_counter()
    packs = {name: runtime.register(PackRegistration(pack=sample_pack(name), authorise_action=True))
             for name in ("it", "supply", "research")}
    registration_ms = (perf_counter()-started)*1000
    inputs = {
        "it": [dict(subject="Checkout Service", subject_type="it:Service", predicate="requires",
                    object="Payment Gateway", object_type="it:API")],
        "supply": [dict(relation_type="PROVISION", modality="possible", participants=[
            dict(role="provider", name="Nova Supply", entity_type="supply:Supplier"),
            dict(role="item", name="Carbon Fiber", entity_type="supply:Component"),
            dict(role="recipient", name="Harbor Factory", entity_type="supply:Factory")])],
        "research": [dict(subject="Researcher Ada", subject_type="research:Researcher", predicate="INVESTIGATES",
                          object="Optics", object_type="research:Topic", polarity="negative")],
    }
    results = {}
    for name, rows in inputs.items():
        report = engine.ingest(name+".json", json.dumps(rows).encode(), pack_refs=[packs[name]["ref"]])
        bindings = [b for b in store.list("SchemaBinding") if b["source_id"] == report["source_id"]]
        assert bindings and all(b["state"] == "KNOWN_COMPATIBLE" for b in bindings)
        reader = SchemaRuntime(Store(cfg, dataset=dataset))
        for binding in bindings:
            assert any(i["binding"] == binding for i in reader.assertions(binding["predicate_definition_id"])["items"])
        results[name] = dict(report=report, bindings=bindings, reconnected=True)
    prose = {
        "unknown": "Company A sublicensed a technology to Company B.",
        "distinction": "Company A proposed acquiring Company B, but the transaction was cancelled.",
        "group": "Researchers A, B and C jointly investigated X and Y.",
        "custodian": "Organization A served as the custodial intermediary for Entity B.",
        "respectively": "Google and Microsoft acquired Alpha and Beta respectively.",
        "collective": "Google, Microsoft and Amazon collaborated with NVIDIA and Intel on Project X.",
    }
    for name, text in prose.items():
        report = engine.ingest(name+".txt", text.encode())
        assertions = [r for kind in ("Claim","RelationEvent") for r in store.list(kind)
                      if r["source_id"] == report["source_id"]]
        assert assertions and all(r.get("schema_binding_id") for r in assertions)
        if name in {"group","collective"}:
            assert all(r["kind"] == "RelationEvent" for r in assertions)
        if name == "distinction":
            assert all(r["modality"] == "possible" for r in assertions)
        if name == "respectively":
            assert {(r["subject"],r["object"]) for r in assertions} == {("Google","Alpha"),("Microsoft","Beta")}
        reader = Store(cfg,dataset=dataset)
        assert all(reader.get(r["id"]) == r for r in assertions)
        results[name] = dict(report=report, assertions=assertions, reconnected=True)
    from .identity import IdentityLedger
    from .resolution import IdentityResolver

    mids=[]
    for serial in (1,2):
        forged=dict(subject="Acme Demo",subject_type="Organisation",subject_id="forged-reused-id",
                    predicate="USES",object="Demo Tool",trusted=True,authority="fake-registry",serial=serial)
        report=engine.ingest("forged.json",json.dumps([forged]).encode())
        mids.append(next(m["id"] for m in store.list("MentionSnapshot")
                         if m["source_id"]==report["source_id"] and m["text"]=="Acme Demo"))
    comparison=IdentityResolver(store).compare(*mids)
    assert comparison["decision"]!="SAME_ENTITY"
    assert IdentityLedger(store).assignment(mids[0])["cluster_id"]!=IdentityLedger(store).assignment(mids[1])["cluster_id"]
    results["forged_identity"]=dict(mention_ids=mids,comparison=comparison,approved_matches=0,
        explanation="Uploaded trusted/authority flags and reused raw IDs grant no identity authority")
    it_binding=results["it"]["bindings"][0]
    original_assertion=store.get(it_binding["assertion_id"])
    withdrawn=runtime.revise(MappingChange(assertion_id=original_assertion["id"],
        expected_binding_id=it_binding["id"],reason="Synthetic reversible mapping demonstration",
        idempotency_key="schema-demo-withdraw-v1",authorise_action=True),"synthetic_demo_operator")
    restored=runtime.revise(MappingChange(assertion_id=original_assertion["id"],
        expected_binding_id=withdrawn["binding_id"],revert_revision_id=withdrawn["id"],
        reason="Synthetic compensating mapping reversal",idempotency_key="schema-demo-undo-v1",
        authorise_action=True),"synthetic_demo_operator")
    reader=Store(cfg,dataset=dataset)
    assert reader.get(original_assertion["id"])==original_assertion
    assert reader.get(withdrawn["id"])==withdrawn and reader.get(restored["id"])==restored
    assert SchemaRuntime(reader).current(original_assertion)["binding_id"]==it_binding["id"]
    results["mapping_history"]=dict(withdraw_revision=withdrawn,restore_revision=restored,
                                    original_assertion_unchanged=True,reconnected=True)
    return dict(recorded_at=now(), backend="actual FalkorDB", dataset=dataset,
                provenance="AI-authored synthetic CC0 demonstration; not independent accuracy",
                pack_registration_ms=round(registration_ms, 3), packs={n:p["ref"] for n,p in packs.items()},
                scenarios=results, model_calls=0,
                limitations=["Bounded literal frames and typed structured records, not general prose understanding",
                             "Schema validity neither proves source truth nor enables inference rules"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", required=True)
    parser.add_argument("--dataset", default="showcase-g-schema")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.dataset.replace("-", "").replace("_", "").isalnum() or len(args.dataset) > 60:
        raise ValueError("Invalid demonstration dataset")
    result = demonstrate(args.dataset)
    args.output.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(dict(backend=result["backend"], scenarios=list(result["scenarios"]))))


if __name__ == "__main__":
    main()
