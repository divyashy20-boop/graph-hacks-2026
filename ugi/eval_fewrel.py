"""External FewRel validation diagnostic: directed entity-pair coverage, NOT F1.

The upstream FewRel validation set consists of Wikipedia-derived, human-
annotated relation-classification examples. Its Wikidata PID label space
is incompatible with UGI's open predicate vocabulary. We therefore report
only whether UGI produced ANY directed relation for the annotated head/tail
surface names; this is an upper-bound screening diagnostic, not correctness
of the extracted predicate. Fetch is explicit, no provider inference.
"""
from __future__ import annotations

import argparse
import json
import random
import urllib.request
from collections import Counter
from hashlib import sha256
from pathlib import Path

from .engine import Engine
from .models import Settings, key, now
from .store import Store

VALIDATION_URL = ("https://raw.githubusercontent.com/thunlp/FewRel/"
                  "master/data/val_wiki.json")


def _name(value):
    if isinstance(value, dict):
        return value.get("text", "")
    if isinstance(value, list) and value and isinstance(value[0], str):
        return value[0]
    return ""


def run(raw: bytes, limit: int = 128, seed: int = 17) -> dict:
    if not 1 <= limit <= 2000:
        raise ValueError("Limit must be 1..2000")
    dataset = json.loads(raw)
    if not isinstance(dataset, dict) or not dataset:
        raise ValueError("Expected FewRel PID -> annotated examples mapping")
    # Stratify by Wikidata relation, then shuffle within each class with fixed
    # seed. Same data/seed/limit yields the same sample without model fitting.
    randomizer = random.Random(seed)
    grouped = {}
    for pid, entries in sorted(dataset.items()):
        if not isinstance(entries, list):
            raise ValueError("Invalid relation group")
        entries = list(entries)
        randomizer.shuffle(entries)
        grouped[pid] = entries
    chosen = []
    offset = 0
    while len(chosen) < limit and any(len(v) > offset for v in grouped.values()):
        for pid in sorted(grouped):
            if len(chosen) >= limit:
                break
            if offset < len(grouped[pid]):
                chosen.append((pid, grouped[pid][offset]))
        offset += 1

    hit = reverse = any_claim = surface = quote_ok = quote_total = 0
    examples = []
    by_pid = Counter()
    for i, (pid, item) in enumerate(chosen):
        tokens = item.get("tokens")
        if not isinstance(tokens, list) or not all(isinstance(t, str) for t in tokens):
            raise ValueError("FewRel sample has invalid tokens")
        sentence = " ".join(tokens)
        head = _name(item.get("h", item.get("head", "")))
        tail = _name(item.get("t", item.get("tail", "")))
        if not head or not tail:
            raise ValueError("FewRel sample is missing head/tail mention")
        visible = key(head) in key(sentence) and key(tail) in key(sentence)
        surface += int(visible)
        engine = Engine(Store(Settings(backend="memory", provider="offline",
                                       allow_paid_calls=False)))
        engine.ingest(f"fewrel_{i:04d}.txt", sentence.encode())
        claims = engine.store.claims()
        any_claim += bool(claims)
        matched = any(key(c["subject"]) == key(head) and key(c["object"]) == key(tail)
                      for c in claims)
        backwards = any(key(c["subject"]) == key(tail) and key(c["object"]) == key(head)
                        for c in claims)
        hit += int(matched)
        reverse += int(backwards)
        by_pid[pid] += int(matched)
        for c in claims:
            quote = engine.store.get(c["evidence_id"])
            chunk = engine.store.get(c["chunk_id"])
            quote_total += 1
            quote_ok += int(bool(quote and chunk and quote["start"] >= 0 and
                                chunk["text"][quote["start"]:quote["end"]] == quote["quote"]))
        examples.append({"i": i, "pid": pid, "text": sentence,
                         "head": head, "tail": tail, "surfaces_visible": visible,
                         "directed_pair_detected": matched, "reverse_pair_detected": backwards,
                         "predicted": [{"subject": c["subject"], "predicate": c["predicate"],
                                        "object": c["object"]} for c in claims]})
    return {"recorded_at": now(), "source_url": VALIDATION_URL,
            "sha256": sha256(raw).hexdigest(), "seed": seed,
            "sampled": len(chosen), "available_pids": len(grouped),
            "surface_present": surface, "samples_with_any_claim": any_claim,
            "head_tail_directed_pair_hits": hit,
            "directed_pair_rate": hit / len(chosen) if chosen else None,
            "reverse_pair_hits": reverse,
            "evidence_span": {"correct": quote_ok, "checked": quote_total},
            "by_pid_directed_hits": dict(sorted(by_pid.items())),
            "model_calls": 0, "external_paid_calls": 0, "samples": examples,
            "limitations": [
                "Wikipedia-derived public FewRel *validation* dataset, not its hidden test set",
                "No Wikidata relation-label mapping or predicate correctness scored",
                "A head-tail hit may describe the WRONG predicate; NOT relation recall, precision or F1",
                "Entity aliases and token detokenisation can undercount recognized entities",
                "Some DocRED-style multi-sentence inferences are outside FewRel's task",
                "This diagnostic uses source text only; no pre-existing world knowledge",
            ]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, help="Local upstream FewRel val_wiki.json")
    parser.add_argument("--download", action="store_true",
                        help="Explicit network fetch from the upstream public GitHub repository")
    parser.add_argument("--limit", type=int, default=128)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.download == bool(args.input):
        parser.error("Choose exactly one of --download or --input")
    if args.download:
        request = urllib.request.Request(VALIDATION_URL, headers={"User-Agent": "UGI-Research/1.0"})
        with urllib.request.urlopen(request, timeout=45) as response:
            raw = response.read(15 * 1024 * 1024 + 1)
        if len(raw) > 15 * 1024 * 1024:
            raise ValueError("External dataset exceeds 15 MB limit")
    else:
        raw = args.input.read_bytes()
        if len(raw) > 15 * 1024 * 1024:
            raise ValueError("External dataset exceeds 15 MB limit")
    report = run(raw, limit=args.limit, seed=args.seed)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n",
                               encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("source_url", "sha256", "sampled",
          "available_pids", "surface_present", "samples_with_any_claim",
          "head_tail_directed_pair_hits", "directed_pair_rate", "reverse_pair_hits",
          "evidence_span", "model_calls")}, indent=2))


if __name__ == "__main__":
    main()
