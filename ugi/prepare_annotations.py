"""Public FewRel annotation queue. Human PID labels are not exhaustive source entailment labels."""
from __future__ import annotations

import argparse
import json
import random
import urllib.request
from hashlib import sha256
from pathlib import Path

from .eval_fewrel import VALIDATION_URL, _name


def select(raw, count=24, seed=20261015):
    data = json.loads(raw)
    old_random = random.Random(17)
    old_groups = {}
    for pid, entries in sorted(data.items()):
        shuffled = list(entries)
        old_random.shuffle(shuffled)
        old_groups[pid] = shuffled
    # Exclude every source in the previously inspected 128-example diagnostic.
    old = {sha256(" ".join(item["tokens"]).encode()).hexdigest()
           for offset in range(8) for entries in old_groups.values()
           for item in entries[offset:offset + 1]}
    eligible = []
    seen = set(old)
    for pid, entries in sorted(data.items()):
        for index, item in enumerate(entries):
            text = " ".join(item["tokens"])
            digest = sha256(text.encode()).hexdigest()
            if digest not in seen:
                eligible.append((pid, index, item, digest))
                seen.add(digest)
    random.Random(seed).shuffle(eligible)
    chosen = eligible[:count]
    if len(chosen) != count:
        raise ValueError("Insufficient distinct new examples")
    cases = []
    for pid, index, item, digest in chosen:
        cases.append(dict(
            id="fewrel_" + digest[:16], domain="public_wikipedia", text=" ".join(item["tokens"]),
            entities=[], binary=[], events=[], complete=False, annotation_status="unreviewed",
            reviewers=[], notes="Upstream human relation-class annotation: " + pid + "; head="
            + _name(item["h"]) + "; tail=" + _name(item["t"])
            + f"; original index={index}. Review ALL source-supported relations/events; "
            "do not assume that every Wikidata relation is directly evidenced by this sentence.",
        ))
    return dict(version="fewrel-annotation-queue-v1", split="annotation_queue", licence="CC-BY-SA-4.0",
                provenance="THUNLP FewRel (Han et al., EMNLP 2018), " + VALIDATION_URL
                + "; original data SHA256=" + sha256(raw).hexdigest()
                + "; seed=" + str(seed) + "; excludes seed-17 128 diagnostic sentences. "
                "Human upstream PID labels retained as notes; source-entailment annotations pending.",
                cases=cases)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--count", type=int, default=24, choices=range(6, 101))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.download == bool(args.input):
        parser.error("Choose --download or --input")
    if args.download:
        with urllib.request.urlopen(VALIDATION_URL, timeout=30) as response:
            raw = response.read(15 * 1024 * 1024 + 1)
    else:
        raw = args.input.read_bytes()
    if len(raw) > 15 * 1024 * 1024:
        raise ValueError("Dataset exceeds download limit")
    queue = select(raw, args.count)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"cases": len(queue["cases"]), "status": "human annotation required",
                      "fixture_sha256": sha256(args.output.read_bytes()).hexdigest(),
                      "provenance": queue["provenance"]}, indent=2))


if __name__ == "__main__":
    main()
