"""Explicit, no-LLM seeding of bundled FalkorDB demonstration datasets.

This is an operator command, not a startup hook or public API route.
It never seeds a populated dataset or invokes a paid provider.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from .engine import Engine
from .models import Settings, uid
from .store import Store

DEMOS = {
    "showcase-b-incident": ("incident.json",),
    "showcase-b-supply": ("supply_network.json",),
    "showcase-b-research": ("research_network.json", "research_identity.json"),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed an explicit graph demo without AI")
    parser.add_argument("--dataset", choices=sorted(DEMOS), required=True)
    parser.add_argument("--key-index", type=int, default=0,
                        help="Index within UGI_API_KEYS (never prints the key)")
    parser.add_argument("--confirm-falkordb", action="store_true",
                        help="Explicitly authorize writes to the configured FalkorDB")
    args = parser.parse_args()
    if not args.confirm_falkordb:
        parser.error("Pass --confirm-falkordb after verifying the target database")
    settings = Settings()
    if settings.backend != "falkordb":
        parser.error("This operator utility requires the FalkorDB backend")
    keys = [k.strip() for k in settings.api_keys.split(",") if k.strip()]
    if args.key_index < 0 or (keys and args.key_index >= len(keys)) or (
        not keys and args.key_index != 0
    ):
        parser.error("Invalid --key-index for configured owner keys")
    owner = uid(keys[args.key_index])[:24] if keys else "local"
    store = Store(settings, owner=owner, dataset=args.dataset)
    if store.list("Source", 1):
        print("DATASET_NOT_EMPTY_SKIPPED", args.dataset)
        return
    root = Path(__file__).resolve().parent.parent / "demo"
    engine = Engine(store)
    for filename in DEMOS[args.dataset]:
        report = engine.ingest(filename, (root / filename).read_bytes(), use_ai=False)
        print("SEEDED", args.dataset, filename,
              "CLAIMS", report.get("claims", 0),
              "EVENTS", report.get("relation_events", 0))
    counts = store.counts()
    if counts.get("Entity", 0) == 0:
        raise RuntimeError("DEMO_HAS_NO_ENTITIES")
    print("DEMO_READY", args.dataset, "ENTITIES", counts["Entity"], "AI_CALLS", 0)


if __name__ == "__main__":
    main()
