"""Read-only payload/edge fingerprints for explicitly selected synthetic demos.

This command never restarts services or deletes graphs. Run the actual Docker
restart separately between --snapshot and --compare.
"""
import argparse
import json
from hashlib import sha256
from pathlib import Path

from .models import Settings, now
from .store import Store


def fingerprint(include_identity=False, include_policy=False, include_schema=False):
    results = {}
    datasets = ["showcase-b-" + domain for domain in ("incident", "supply", "research")]
    if include_identity:
        datasets.append("showcase-e-identity")
    if include_policy:
        datasets.extend(["showcase-f-identity", "showcase-f-dryrun"])
    if include_schema:
        datasets.extend(["showcase-g-schema", "showcase-g-public-clause"])
    for dataset in datasets:
        store = Store(Settings(provider="offline", allow_paid_calls=False), dataset=dataset)
        records = [json.loads(row[0]) for row in store.query(
            "MATCH (n:Record) RETURN n.payload ORDER BY n.id")]
        edges = store.query("MATCH (a:Record)-[r]->(b:Record) RETURN a.id,b.id,type(r),r.claim_id,r.role")
        assert records and any(r["kind"] == "Source" for r in records), "Seed demo before restart check"
        def digest(value):
            return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        results[dataset] = dict(records=len(records), edges=len(edges),
                                payload_sha256=digest(records),
                                incidence_sha256=digest(sorted(edges, key=lambda e: json.dumps(e))),
                                counts=store.counts(),
                                investigation_ids=sorted(r["id"] for r in records if r["kind"] == "Investigation"))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--snapshot", type=Path)
    mode.add_argument("--compare", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--include-identity", action="store_true", help="Also fingerprint the seeded E ledger demo")
    parser.add_argument("--include-policy", action="store_true", help="Also fingerprint the seeded F dry-run/apply demos")
    parser.add_argument("--include-schema", action="store_true", help="Also fingerprint G registry/revision and public-clause demos")
    args = parser.parse_args()
    observed = fingerprint(args.include_identity, args.include_policy, args.include_schema)
    if args.snapshot:
        args.snapshot.write_text(json.dumps(observed, indent=2)+"\n", encoding="utf-8")
        print("Captured exact persistent demo record/edge fingerprints; no data changed.")
    else:
        expected = json.loads(args.compare.read_text(encoding="utf-8"))
        assert observed == expected, "Persistent demo state changed across restart"
        result = dict(recorded_at=now(), unchanged=True, datasets=observed,
                      limitations="Controlled restart/read smoke, not backup, crash recovery or production durability")
        if args.output:
            args.output.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
        print(json.dumps(dict(unchanged=True, datasets=list(observed)), indent=2))


if __name__ == "__main__":
    main()
