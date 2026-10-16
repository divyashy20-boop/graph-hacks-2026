"""External T2D correspondence-label probe. Gold URIs NEVER enter the resolver."""
import argparse
import csv
import io
import json
import os
import random
import tarfile
import tracemalloc
import urllib.request
from collections import defaultdict
from hashlib import sha256
from itertools import combinations
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from .engine import Engine
from .models import Settings, now, uid
from .resolution import IdentityResolver
from .store import Store

URL = "https://webdatacommons.org/webtables/entities_instance.tar.gz"
SOURCE = "https://webdatacommons.org/webtables/goldstandard.html"
EXCLUDED_PREVIEW_TABLE = "68779923_2_1000046510804975562.csv"
ARCHIVE_SHA256 = "1a1c64113d0eb6054bc567a73af89947165cb2a1085290ad3eed20ead3c2cbfa"


def sample(data, count=12, seed=20261016):
    if not 1 <= count <= 20:
        raise ValueError("Public probe capped at20 pairs per class")
    groups = defaultdict(list)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        if sum(m.size for m in archive.getmembers()) > 20_000_000:
            raise ValueError("Archive expansion budget exceeded")
        for member in sorted(archive.getmembers(), key=lambda m: m.name):
            if not member.isfile() or member.name == EXCLUDED_PREVIEW_TABLE:
                continue
            for row in csv.reader(io.StringIO(archive.extractfile(member).read().decode("utf-8-sig"))):
                if len(row) != 3 or not row[0].startswith("http://dbpedia.org/resource/"):
                    continue
                if row[1].strip() and len(row[1]) <= 160:
                    groups[row[0]].append(dict(id=uid(member.name, row[2]), text=row[1], table=member.name))
    rng = random.Random(seed)
    eligible = [(uri, sorted(records, key=lambda r: r["id"])) for uri, records in sorted(groups.items())
                if len({r["table"] for r in records}) >= 2]
    selected = rng.sample(eligible, count)
    positives = []
    for uri, records in selected:
        a, b = next((a, b) for a, b in combinations(records, 2) if a["table"] != b["table"])
        positives.append((a, b, True))
    # Ring pairs have different upstream URI labels, with no label in the input.
    negatives = [(positives[i][0], positives[(i+1) % count][1], False) for i in range(count)]
    if count == 1:
        raise ValueError("At least2 classes needed for non-match ring")
    return positives+negatives


def evaluate(cache, count=12):
    data = cache.read_bytes()
    if sha256(data).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("Frozen external archive hash changed; do not silently replace evaluation inputs")
    pairs = sample(data, count)
    rows = {r["id"]: r for a, b, _ in pairs for r in (a, b)}
    cfg = Settings(identity_ledger=True, identity_resolution="dry_run", identity_authorities={},
                   provider="offline", allow_paid_calls=False, graph_prefix="ugi_fpublic_"+uuid4().hex[:8],
                   redis_url=os.getenv("UGI_TEST_REDIS_URL", "redis://127.0.0.1:6380/0"))
    store, resolver = Store(cfg), None
    tracemalloc.start()
    started = perf_counter()
    try:
        mids = {}
        for record in rows.values():
            # Only the row surface and opaque row ID go into the converter.
            row = dict(subject=record["text"], subject_type="Entity", predicate="MENTIONED_IN",
                       object=record["table"], object_type="Table", source_record_id=record["id"])
            report = Engine(store).ingest("public-row.json", json.dumps([row]).encode())
            mids[record["id"]] = next(m["id"] for m in store.list("MentionSnapshot")
                                      if m["source_id"] == report["source_id"] and m["text"] == record["text"])
        resolver = IdentityResolver(store)
        outputs = []
        for a, b, label in pairs:
            result = resolver.compare(mids[a["id"]], mids[b["id"]])
            retrieval = resolver.candidates(mids[b["id"]])
            outputs.append(dict(left_record=a["id"], right_record=b["id"], gold_match=label,
                                decision=result["decision"], candidate_retrieved=mids[a["id"]] in retrieval["candidate_ids"],
                                candidate_complete=retrieval["complete"]))
        tp = sum(r["gold_match"] and r["decision"] == "SAME_ENTITY" for r in outputs)
        fp = sum(not r["gold_match"] and r["decision"] == "SAME_ENTITY" for r in outputs)
        result = dict(recorded_at=now(), source_url=SOURCE, download_url=URL,
                      archive_sha256=sha256(data).hexdigest(), license="Apache-2.0 correspondences (not Web tables/DBpedia dump)",
                      upstream_annotation="Human-generated row-to-DBpedia correspondences; derived row-pair identity labels",
                      seed=20261016, pairs=len(outputs), records=len(rows), backend="actual FalkorDB",
                      selection_hash=uid([(a["id"], b["id"], label) for a, b, label in pairs]),
                      predicted_matches=tp+fp, tp=tp, fp=fp, gold_matches=count,
                      precision=tp/(tp+fp) if tp+fp else None, recall=tp/count, f1=2*tp/(tp+fp+count),
                      false_merge_rate=fp/count, missed_match_rate=(count-tp)/count,
                      candidate_recall=sum(r["candidate_retrieved"] for r in outputs if r["gold_match"])/count,
                      abstentions=sum(r["decision"] in {"UNRESOLVED", "POSSIBLY_SAME"} for r in outputs),
                      elapsed_ms=round((perf_counter()-started)*1000, 3),
                      python_allocation_peak_bytes=tracemalloc.get_traced_memory()[1], outputs=outputs, model_calls=0,
                      limitations=["Small label-derived public diagnostic, not full T2D entity-linking leaderboard",
                                   "Gold DBpedia URIs excluded from source records, blocking and evidence",
                                   "Name-only features; no approved authority evidence, so positive matching deliberately abstains",
                                   "Candidate recall is within the sampled pool, not all26124 correspondences",
                                   "Excluded inspected first-table preview, names over160 chars and non-URI mappings",
                                   "No tuning after evaluating this checkpoint; future tuning makes it development",
                                   "Zero false merges does not imply good recall; undefined precision when no matches"])
        # Keep labels/row hashes, not redistribute source surfaces or DBpedia URIs.
        return result
    finally:
        tracemalloc.stop()
        assert store.graph.startswith(cfg.graph_prefix+"_")
        store.client.execute_command("GRAPH.DELETE", store.graph)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--cache", type=Path, default=Path(".evaluation-local/t2d_entities.tar.gz"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.download:
        with urllib.request.urlopen(URL, timeout=30) as response:
            content = response.read(4_000_001)
        if len(content) > 4_000_000:
            raise ValueError("Download exceeds4MB budget")
        args.cache.parent.mkdir(parents=True, exist_ok=True)
        args.cache.write_bytes(content)
    result = evaluate(args.cache)
    args.output.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("pairs", "records", "predicted_matches", "precision", "recall", "f1", "candidate_recall")}, indent=2))


if __name__ == "__main__":
    main()
