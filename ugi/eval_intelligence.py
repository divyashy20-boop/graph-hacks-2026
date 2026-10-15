"""Reproducible relation/event assessment with explicit annotation scope and splits."""
from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
from time import perf_counter

from pydantic import Field, model_validator

from .engine import Engine
from .evaluate import scores
from .models import Settings, Strict, key, now, predicate
from .provider import Ollama
from .store import Store


class AnnotationCase(Strict):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")
    domain: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=4000)
    entities: list[str] = Field(default_factory=list)
    binary: list[dict] = Field(default_factory=list, max_length=60)
    events: list[dict] = Field(default_factory=list, max_length=12)
    complete: bool = True
    annotation_status: str = "provisional"
    reviewers: list[str] = Field(default_factory=list)
    notes: str = ""

    @model_validator(mode="after")
    def labels(self):
        if self.annotation_status not in {"unreviewed", "provisional", "human_reviewed"}:
            raise ValueError("Invalid annotation status")
        if self.annotation_status == "human_reviewed" and (
                not self.reviewers or any(not name.strip() for name in self.reviewers)):
            raise ValueError("Human-reviewed labels need named reviewer metadata")
        for label in self.binary:
            if not all(label.get(k) for k in ("subject", "predicate", "object")):
                raise ValueError("Binary gold needs subject/predicate/object")
        for label in self.events:
            if not label.get("relation_type") or len(label.get("participants", [])) < 3:
                raise ValueError("Event gold needs 3+ role-labelled participants")
            if not all(p.get("role") and p.get("name") for p in label["participants"]):
                raise ValueError("Gold participant needs role and name")
        return self


class Suite(Strict):
    version: str
    split: str
    licence: str
    provenance: str
    cases: list[AnnotationCase] = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def identities(self):
        if self.split not in {"development", "evaluation", "annotation_queue"}:
            raise ValueError("Invalid split")
        if len({c.id for c in self.cases}) != len(self.cases):
            raise ValueError("Duplicate case IDs")
        hashes = [sha256(key(c.text).encode()).hexdigest() for c in self.cases]
        if len(set(hashes)) != len(hashes):
            raise ValueError("Duplicate source text within split")
        return self


def binary_signature(record, temporal=False):
    value = (key(record["subject"]), predicate(record["predicate"]), key(record["object"]),
             record.get("polarity", "positive"), record.get("modality", "asserted"))
    if temporal:
        value += tuple(record.get(f) for f in ("event_time", "valid_from", "valid_to"))
        value += (record.get("historical", False),)
    return value


def event_signature(record, temporal=False):
    from .nary import event_type

    value = (event_type(record["relation_type"]), tuple(sorted(
        (p["role"], key(p["name"])) for p in record["participants"])),
        record.get("polarity", "positive"), record.get("modality", "asserted"))
    if temporal:
        value += tuple(record.get(f) for f in ("event_time", "valid_from", "valid_to"))
        value += (record.get("historical", False),)
    return value


def load_suite(path, development=None):
    raw = path.read_bytes()
    suite = Suite.model_validate_json(raw)
    if development:
        dev = Suite.model_validate_json(development.read_bytes())
        if dev.split != "development" or suite.split != "evaluation":
            raise ValueError("Expected separate development and evaluation splits")
        overlap = {key(c.text) for c in dev.cases} & {key(c.text) for c in suite.cases}
        if overlap or {c.id for c in dev.cases} & {c.id for c in suite.cases}:
            raise ValueError("Development/evaluation source or case-ID leakage")
    canonical = sha256(json.dumps(json.loads(raw), sort_keys=True, ensure_ascii=False,
                                   separators=(",", ":")).encode()).hexdigest()
    return suite, canonical


def run(path, development=None, model=None, limit=None):
    suite, digest = load_suite(path, development)
    if model and (limit is None or not 1 <= limit <= 6):
        raise ValueError("Local inference requires explicit --limit 1..6")
    if limit is not None and not 1 <= limit <= len(suite.cases):
        raise ValueError("Invalid case limit")
    cases = suite.cases[:limit] if limit else suite.cases
    gold, predicted = defaultdict(set), defaultdict(set)
    domains = defaultdict(list)
    rows, durations = [], []
    exact = cited = review_documents = model_calls = input_tokens = output_tokens = failures = 0
    empty = abstentions = unassessed = 0
    for case in cases:
        settings = Settings(backend="memory", provider="ollama" if model else "offline",
                            model_id=model or "", ollama_url=__import__("os").environ.get(
                                "UGI_OLLAMA_URL", "http://127.0.0.1:11434"),
                            max_model_calls=4, max_output_tokens=1800)
        store = Store(settings)
        provider = Ollama(settings, store) if model else None
        engine = Engine(store, provider_factory=(lambda: provider) if provider else None)
        started = perf_counter()
        report = engine.ingest(case.id + ".txt", case.text.encode(), use_ai=bool(model))
        durations.append((perf_counter() - started) * 1000)
        failures += bool(report["warnings"])
        claims, events = store.claims(), store.events()
        observed = {
            "binary": {binary_signature(c) for c in claims},
            "binary_temporal": {binary_signature(c, True) for c in claims},
            "event": {event_signature(e) for e in events},
            "event_temporal": {event_signature(e, True) for e in events},
            "entities": {key(e["name"]) for e in store.list("Entity")},
            "pair": {(key(c["subject"]), key(c["object"])) for c in claims},
            "participant_roles": {(e["relation_type"], p["role"], key(p["name"]))
                                  for e in events for p in e["participants"]},
        }
        expected = {
            "binary": {binary_signature(c) for c in case.binary},
            "binary_temporal": {binary_signature(c, True) for c in case.binary},
            "event": {event_signature(e) for e in case.events},
            "event_temporal": {event_signature(e, True) for e in case.events},
            "entities": {key(e) for e in case.entities},
            "pair": {(key(c["subject"]), key(c["object"])) for c in case.binary},
            "participant_roles": {(e["relation_type"], p["role"], key(p["name"]))
                                  for e in case.events for p in e["participants"]},
        }
        assessable = case.annotation_status != "unreviewed" and case.complete
        if assessable:
            for metric in observed:
                gold[metric] |= {(case.id, item) for item in expected[metric]}
                predicted[metric] |= {(case.id, item) for item in observed[metric]}
            if not case.binary and not case.events:
                empty += 1
                abstentions += not claims and not events
        else:
            unassessed += len(claims) + len(events)
        review_documents += report["review_tasks"] > 0
        model_calls += report["usage"].get("calls", 0)
        input_tokens += report["usage"].get("input_tokens", 0)
        output_tokens += report["usage"].get("output_tokens", 0)
        for item in claims + events:
            evidence = store.get(item["evidence_id"])
            chunk = store.get(item["chunk_id"])
            cited += 1
            exact += bool(evidence and chunk and evidence["start"] >= 0
                          and chunk["text"][evidence["start"]:evidence["end"]] == evidence["quote"])
        row = dict(id=case.id, domain=case.domain, annotation_status=case.annotation_status,
                   assessable=assessable, binary=[{k: c.get(k) for k in (
                       "subject", "predicate", "object", "polarity", "modality", "event_time",
                       "valid_from", "valid_to", "historical")} for c in claims],
                   events=[{k: e.get(k) for k in ("relation_type", "participants", "polarity",
                           "modality", "event_time", "valid_from", "valid_to", "historical")}
                           for e in events], warnings=report["warnings"],
                   review_reasons=[r.get("reason") for r in store.list("ReviewTask")],
                   elapsed_ms=round(durations[-1], 2), usage=report["usage"],
                   exact_binary_matches=len(observed["binary"] & expected["binary"]),
                   expected_binary=len(expected["binary"]), predicted_binary=len(claims),
                   exact_event_matches=len(observed["event"] & expected["event"]),
                   expected_events=len(expected["event"]), predicted_events=len(events))
        rows.append(row)
        domains[case.domain].append(row)
    metrics = {name: scores(predicted[name], gold[name]) for name in gold}
    total_predictions = sum(metrics.get(name, {}).get("predicted", 0) for name in ("binary", "event"))
    unsupported = sum(metrics.get(name, {}).get("predicted", 0)
                      - metrics.get(name, {}).get("tp", 0) for name in ("binary", "event"))
    by_domain = {}
    for domain, values in domains.items():
        eligible = [r for r in values if r["assessable"]]
        tp = sum(r["exact_binary_matches"] + r["exact_event_matches"] for r in eligible)
        pg = sum(r["predicted_binary"] + r["predicted_events"] for r in eligible)
        gg = sum(r["expected_binary"] + r["expected_events"] for r in eligible)
        by_domain[domain] = {"cases": len(values), "tp": tp, "predicted": pg, "gold": gg,
                             "f1": 2 * tp / (pg + gg) if pg + gg else None}
    return dict(version=suite.version, split=suite.split, fixture_sha256=digest,
                recorded_at=now(), provenance=suite.provenance, licence=suite.licence,
                cases=len(cases), provider="ollama" if model else "offline", model=model,
                annotation_counts=dict(__import__("collections").Counter(c.annotation_status for c in cases)),
                metrics=metrics, by_domain=by_domain,
                macro_domain_f1=statistics.mean(v["f1"] for v in by_domain.values()
                                               if v["f1"] is not None) if any(
                                                   v["f1"] is not None for v in by_domain.values()) else None,
                unsupported_against_complete_labels={"count": unsupported, "checked": total_predictions,
                     "rate": unsupported / total_predictions if total_predictions else None},
                unassessed_predictions=unassessed, evidence={"exact": exact, "checked": cited},
                abstention={"correct": abstentions, "controls": empty},
                review_document_rate=review_documents / len(cases), failed_documents=failures,
                latency_ms={"median": statistics.median(durations), "max": max(durations)},
                model_usage={"calls": model_calls, "calls_per_document": model_calls / len(cases),
                             "input_tokens": input_tokens, "output_tokens": output_tokens,
                             "cloud_api_charge_usd": 0, "local_compute_cost": "not measured"},
                per_case=rows, limitations=[
                    "Provisional annotations are AI-authored, not independent human ground truth",
                    "Human review metadata is self-reported, not independently certified",
                    "Entity metric is exact surface-set coverage/F1, not span-level NER",
                    "Unsupported rate is label disagreement, not independently adjudicated hallucination",
                    "Only complete, reviewed/provisional cases contribute precision/recall; unreviewed excluded",
                    "Predicate aliases are fixed before evaluation; exact canonical matching may undercount synonyms",
                    "In-memory extraction evaluation; real graph/workflow checks run separately",
                ])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--development", type=Path)
    parser.add_argument("--local-model")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.fixture, args.development, args.local_model, args.limit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("cases", "split", "metrics", "by_domain",
          "abstention", "evidence", "model_usage", "failed_documents")}, indent=2))


if __name__ == "__main__":
    main()
