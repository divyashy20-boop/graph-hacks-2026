"""Synthetic universal schema demonstration on actual persistent FalkorDB."""
import argparse
import json
from importlib.resources import files
from pathlib import Path
from time import perf_counter

from .engine import Engine
from .models import Settings, now
from .schema import DomainPack, PackRegistration, SchemaRuntime
from .store import Store


def sample_pack(name):
    if name not in {"it", "supply", "research"}:
        raise ValueError("Unknown bundled demonstration pack")
    return DomainPack.model_validate_json(files("ugi").joinpath("packs", name+".json").read_text(encoding="utf-8"))


def demonstrate(dataset):
    cfg = Settings(provider="offline", allow_paid_calls=False, schema_writes=True)
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
    return dict(recorded_at=now(), backend="actual FalkorDB", dataset=dataset,
                provenance="AI-authored synthetic CC0 demonstration; not independent accuracy",
                pack_registration_ms=round(registration_ms, 3), packs={n:p["ref"] for n,p in packs.items()},
                scenarios=results, model_calls=0,
                limitations=["Literal aliases and typed structured records, not general prose discovery at G1",
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
