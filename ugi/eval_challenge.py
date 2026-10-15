"""Reproducible strict extraction diagnostic on independent input fixtures.

The bundled challenge is NEW but AI-assisted SYNTHETIC, not an external
independently-annotated corpus. Scores are diagnostic only. Offline by default.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from hashlib import sha256
from pathlib import Path

from .engine import Engine
from .evaluate import scores
from .models import Settings, now, predicate
from .store import Store


def run(fixture: Path) -> dict:
    raw = fixture.read_bytes()
    data = json.loads(raw)
    samples = data.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ValueError("Expected nonempty samples list")
    rows = []
    predicted, gold, strict_predicted, strict_gold = set(), set(), set(), set()
    domain_counts = defaultdict(lambda: {"gold": set(), "predicted": set(),
                                         "strict_gold": set(), "strict_predicted": set(),
                                         "negative": 0, "false_alarm": 0})
    empty = false_alarm = evidence_total = evidence_exact = reviews = 0
    ids = set()
    for case in samples:
        ident = case["id"]
        if not isinstance(ident, str) or not ident or ident in ids or "/" in ident:
            raise ValueError("Sample IDs must be distinct safe strings")
        ids.add(ident)
        text = case["text"]
        domain = case["domain"]
        annotations = case["gold"]
        if not isinstance(text, str) or not isinstance(domain, str) or not isinstance(annotations, list):
            raise ValueError("Invalid text/domain/gold record")
        if any(not isinstance(r, list) or len(r) != 5 or not all(isinstance(v, str) for v in r)
               for r in annotations):
            raise ValueError("Gold rows must be 5 strings: subject,predicate,object,polarity,modality")
        engine = Engine(Store(Settings(backend="memory", provider="offline",
                                       allow_paid_calls=False)))
        result = engine.ingest(ident + ".txt", text.encode("utf-8"))
        claims = engine.store.claims()
        observations = {(c["subject"], c["predicate"], c["object"],
                         c["polarity"], c["modality"]) for c in claims}
        expected = {(r[0], predicate(r[1]), *r[2:]) for r in annotations}
        observed3 = {(ident, *v[:3]) for v in observations}
        expected3 = {(ident, *v[:3]) for v in expected}
        observed5 = {(ident, *v) for v in observations}
        expected5 = {(ident, *v) for v in expected}
        predicted |= observed3
        gold |= expected3
        strict_predicted |= observed5
        strict_gold |= expected5
        group = domain_counts[domain]
        group["predicted"].update(observed3)
        group["gold"].update(expected3)
        group["strict_predicted"].update(observed5)
        group["strict_gold"].update(expected5)
        if not expected:
            empty += 1
            group["negative"] += 1
            if observations:
                false_alarm += 1
                group["false_alarm"] += 1
        for claim in claims:
            evidence_total += 1
            quote = engine.store.get(claim["evidence_id"])
            chunk = engine.store.get(claim["chunk_id"])
            if (quote and chunk and quote["start"] >= 0
                    and chunk["text"][quote["start"]:quote["end"]] == quote["quote"]):
                evidence_exact += 1
        reviews += result["review_tasks"]
        rows.append({
            "id": ident, "domain": domain, "text": text,
            "expected": [list(x) for x in sorted(expected)],
            "predicted": [list(x) for x in sorted(observations)],
            "false_positive": [list(x) for x in sorted(observations - expected)],
            "false_negative": [list(x) for x in sorted(expected - observations)],
            "review_tasks": result["review_tasks"],
            "correct_abstention": not expected and not observations,
        })
    grouped = {k: {
        "relation": scores(v["predicted"], v["gold"]),
        "strict_relation": scores(v["strict_predicted"], v["strict_gold"]),
        "negative_cases": v["negative"],
        "false_alarm_cases": v["false_alarm"],
    } for k, v in sorted(domain_counts.items())}
    return {
        "recorded_at": now(), "fixture_sha256": sha256(raw).hexdigest(),
        "fixture_version": data.get("version"),
        "scope": data.get("provenance", "External fixture; verify its annotation protocol"),
        "cases": len(samples), "relation": scores(predicted, gold),
        "strict_relation": scores(strict_predicted, strict_gold),
        "abstention": {"gold_empty": empty, "correct": empty - false_alarm,
                       "false_alarm": false_alarm,
                       "correct_abstention_rate": (empty - false_alarm) / empty if empty else None},
        "evidence_span": {"correct": evidence_exact, "checked": evidence_total,
                          "accuracy": evidence_exact / evidence_total if evidence_total else None},
        "review_tasks": reviews, "by_domain": grouped, "per_sample": rows,
        "model_calls": 0, "paid_api_calls": 0,
        "limitations": [
            "Exact surface/predicate match after the same fixed alias policy on predictions and labels",
            "Evidence span equality is provenance correctness, not entailment correctness",
            "No independent real-world benchmark is implied by bundled synthetic fixture",
            "Predicted relations rejected into review are not counted as extracted",
            "Unannotated relations in an external fixture may appear as false positives",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=Path(__file__).parents[1]
                        / "evaluation/challenge_v1.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run(args.fixture)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                               encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("cases", "fixture_sha256", "relation",
          "strict_relation", "abstention", "evidence_span", "review_tasks", "by_domain",
          "model_calls")}, indent=2))


if __name__ == "__main__":
    main()
