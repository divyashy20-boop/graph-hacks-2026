"""Small frozen evaluation; no network/provider calls. Writes only explicit report paths."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from hashlib import sha256
from pathlib import Path
from time import perf_counter

from .engine import Engine
from .models import RelationQuery, Settings, now
from .store import Store


def scores(predicted, gold):
    tp = len(predicted & gold)
    precision = tp / len(predicted) if predicted else 0.0
    recall = tp / len(gold) if gold else 0.0
    return dict(tp=tp, predicted=len(predicted), gold=len(gold), precision=precision,
                recall=recall, f1=2 * precision * recall / (precision + recall)
                if precision + recall else 0.0)


def evaluate(root):
    fixture = root / "evaluation/heldout.json"
    dataset = json.loads(fixture.read_text())
    reports = {}
    # C and D run the same hybrid architecture offline. No learned-model score is implied.
    for variant, semantic in [("B_deterministic", False), ("C_hybrid_offline", False),
                              ("D_hybrid_offline_verified", True)]:
        predicted, gold, strict_predicted, strict_gold, pe, ge, rows = (
            set(), set(), set(), set(), set(), set(), []
        )
        qualifier_correct = qualifier_total = temporal_correct = temporal_total = 0
        support_correct = support_total = 0
        started = perf_counter()
        for sample in dataset["samples"]:
            engine = Engine(Store(Settings(backend="memory")))
            result = engine.ingest(sample["id"] + ".txt", sample["text"].encode(),
                                   semantic_verification=semantic)
            claims = engine.store.claims()
            sid = sample["id"]
            sample_gold = {tuple(g) for g in sample["gold"]}
            sample_pred = {(c["subject"], c["predicate"], c["object"], c["polarity"], c["modality"])
                           for c in claims}
            predicted |= {(sid, *v[:3]) for v in sample_pred}
            gold |= {(sid, *v[:3]) for v in sample_gold}
            strict_predicted |= {(sid, *v) for v in sample_pred}
            strict_gold |= {(sid, *v) for v in sample_gold}
            pe |= {(sid, name) for c in sample_pred for name in (c[0], c[2])}
            ge |= {(sid, name) for c in sample_gold for name in (c[0], c[2])}
            for c in claims:
                triple = (c["subject"], c["predicate"], c["object"])
                corresponding = [g for g in sample_gold if g[:3] == triple]
                support_total += 1
                support_correct += bool(corresponding and tuple([*triple, c["polarity"], c["modality"]])
                                        in sample_gold)
                if corresponding:
                    qualifier_total += 1
                    qualifier_correct += (c["polarity"], c["modality"]) == corresponding[0][3:]
                for field in ("historical", "event_time", "valid_from", "valid_to"):
                    if field in sample:
                        temporal_total += 1
                        temporal_correct += c.get(field) == sample[field]
            rows.append(dict(id=sid, domain=sample["domain"], predicted=[list(p) for p in sample_pred],
                             gold=sample["gold"], elapsed_ms=result["elapsed_ms"]))
        reports[variant] = dict(
            relation=scores(predicted, gold), strict_relation=scores(strict_predicted, strict_gold),
            entity_surface=scores(pe, ge), samples=len(rows),
            qualifier_accuracy=dict(correct=qualifier_correct, total=qualifier_total),
            temporal_accuracy=dict(correct=temporal_correct, total=temporal_total),
            evidence_semantic_precision=support_correct / support_total if support_total else 0,
            unsupported_relationship_rate=1 - support_correct / support_total if support_total else 0,
            elapsed_ms=round((perf_counter() - started) * 1000, 3), model_calls=0,
            estimated_usd=0, per_sample=rows,
        )
    try:
        from universal_graph.config import Settings as OldSettings
        from universal_graph.extraction import RuleExtractor
        from universal_graph.ingestion import IngestionService

        predicted, gold = set(), set()
        for sample in dataset["samples"]:
            source, chunks = IngestionService(OldSettings(_env_file=None)).parse(
                sample["id"] + ".txt", sample["text"].encode())
            result = RuleExtractor().extract(chunks)
            names = {e.id: e.name for e in result.entities}
            predicted |= {(sample["id"], names[c.subject_id], c.predicate, names.get(c.object_id, ""))
                          for c in result.claims}
            gold |= {(sample["id"], *g[:3]) for g in sample["gold"]}
        reports["A_historical_rules"] = dict(relation=scores(predicted, gold), samples=20,
                                               note="Historical four-predicate rules; not baseline LLM")
    except ImportError:
        reports["A_historical_rules"] = {"state": "unavailable", "reason": "Historical package not on path"}
    engine = Engine(Store(Settings(backend="memory")))
    engine.ingest("incident.json", (root / "demo/incident.json").read_bytes())
    questions = json.loads((root / "evaluation/questions.json").read_text())["questions"]
    answers, confusion = [], Counter()
    for row in questions:
        query = RelationQuery(**{k: v for k, v in row.items() if k != "expected"})
        answer = engine.relationship(query)
        answers.append(dict(query=row, actual=answer["status"], correct=answer["status"] == row["expected"]))
        confusion[row["expected"] + "->" + answer["status"]] += 1
    return dict(
        recorded_at=now(), fixture_sha256=sha256(fixture.read_bytes()).hexdigest(),
        scope="20 synthetic held-out passages across two domains; not independent external accuracy",
        variants=reports,
        unknown=dict(correct=sum(a["correct"] for a in answers), total=len(answers),
                     confusion=dict(confusion), results=answers,
                     llm_comparison="Not run: live paid model calls not authorised"),
        limitations=["B/C/D share offline candidates; no learned extraction comparison measured",
                     "Entity metric is surface-set F1, not strict span NER F1",
                     "Gold authored with AI assistance, no independent human adjudication",
                     "Small synthetic set has wide uncertainty and limited language coverage"],
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = evaluate(Path(__file__).parents[1])
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(json.dumps({"variants": {k: v.get("relation", v) for k, v in report["variants"].items()},
                      "unknown": {k: v for k, v in report["unknown"].items() if k != "results"}}, indent=2))


if __name__ == "__main__":
    main()
