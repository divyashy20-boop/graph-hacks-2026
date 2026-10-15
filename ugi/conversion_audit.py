"""Source-aware conversion audit, including a real persisted/reconnected graph.

Labels are never sent to extraction. Unreviewed or incomplete cases are not
silently graded as empty gold. A frozen split requires an explicit checkpoint.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from pydantic import Field, model_validator

from .engine import Engine
from .eval_intelligence import AnnotationCase, binary_signature, event_signature
from .evaluate import scores
from .models import Settings, Strict, key, now, uid
from .provider import Ollama
from .store import Store


def digest(data):
    return sha256(json.dumps(data, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":")).encode()).hexdigest()


class AuditCase(AnnotationCase):
    source_url: str
    source_title: str
    licence: str
    licence_url: str
    source_locator: str
    source_sha256: str
    entity_spans: list[dict] = Field(default_factory=list)

    @model_validator(mode="after")
    def provenance(self):
        if not self.source_url.startswith(("https://", "synthetic://")):
            raise ValueError("Explicit public source URL or synthetic provenance required")
        if sha256(self.text.encode()).hexdigest() != self.source_sha256:
            raise ValueError("Source text hash mismatch")
        for label in self.binary + self.events:
            if "evidence" not in label or label["evidence"] not in self.text:
                raise ValueError("Every gold relationship needs an exact supporting quotation")
            if not all(name in label["evidence"] for name in (
                [label["subject"], label["object"]] if "subject" in label else
                [p["name"] for p in label["participants"]]
            )):
                raise ValueError("Gold participant missing from supporting quote")
        for mention in self.entity_spans:
            if self.text[mention["start"]:mention["end"]] != mention["text"]:
                raise ValueError("Gold entity offsets do not match source text")
        return self


class AuditSuite(Strict):
    version: str = "conversion-audit-v1"
    split: str
    scope: str
    cases: list[AuditCase] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def unique(self):
        if self.split not in {"development", "evaluation"}:
            raise ValueError("Invalid split")
        if len({c.id for c in self.cases}) != len(self.cases):
            raise ValueError("Duplicate case ID")
        if len({key(c.text) for c in self.cases}) != len(self.cases):
            raise ValueError("Duplicate source text")
        return self


def shingles(text):
    words = re.findall(r"\w+", text.casefold())
    return {tuple(words[i:i + 4]) for i in range(max(1, len(words) - 3))}


def check_splits(dev, evaluation):
    """Reject exact text/ID leakage and high four-word-shingle containment.

    Source URL reuse is disallowed too: split by document, not sentence.
    This is a reproducible lexical check, not a semantic duplication oracle.
    """
    if dev.split != "development" or evaluation.split != "evaluation":
        raise ValueError("Expected development/evaluation partitions")
    for a in dev.cases:
        for b in evaluation.cases:
            sa, sb = shingles(a.text), shingles(b.text)
            similarity = len(sa & sb) / max(1, min(len(sa), len(sb)))
            if a.id == b.id or a.source_url == b.source_url or key(a.text) == key(b.text) or similarity >= .65:
                raise ValueError("Split leakage or near duplicate: " + a.id + " / " + b.id)


def review_category(reason):
    reason = reason.lower()
    for category, words in {
        "provenance": ("span", "quote", "absent", "evidence"),
        "identity": ("pronoun", "identity", "identifier"),
        "nary_attachment": ("participant", "anchor", "between", "attachment"),
        "qualifier_or_direction": ("grammar", "polarity", "temporal", "scope"),
        "runtime_or_quota": ("unavailable", "quota", "budget", "invalid"),
    }.items():
        if any(w in reason for w in words):
            return category
    return "semantic_review"


def incidence(records):
    expected = set()
    for record in records.values():
        if record["kind"] == "Chunk":
            expected.add((record["source_id"], record["id"], "HAS_CHUNK", record["id"], ""))
        elif record["kind"] in {"Claim", "RelationEvent"}:
            rid = record["id"]
            expected.add((record["evidence_id"], rid, "SUPPORTS", rid, ""))
            expected.add((record["evidence_id"], record["chunk_id"], "CITES", rid, ""))
            if record["kind"] == "Claim":
                expected.add((record["subject_id"], record["object_id"], "RELATES", rid, ""))
            else:
                expected.update((rid, p["entity_id"], "HAS_PARTICIPANT",
                                 uid(rid, p["role"], p["entity_id"]), p["role"])
                                for p in record["participants"])
    return expected


def audit(path, backend="memory", model=None, limit=None, final=False, development=None):
    raw = json.loads(path.read_text(encoding="utf-8"))
    suite = AuditSuite.model_validate(raw)
    if suite.split == "evaluation" and not final:
        raise ValueError("Frozen evaluation requires explicit --final-checkpoint")
    if suite.split == "evaluation":
        if development is None:
            raise ValueError("Evaluation requires --development for leakage check")
        check_splits(AuditSuite.model_validate_json(development.read_bytes()), suite)
        manifest = json.loads(path.with_name("c_manifest.json").read_text())
        if digest(raw) != manifest["evaluation_sha256"]:
            raise ValueError("Frozen evaluation hash mismatch")
    if model and (limit is None or not 1 <= limit <= 6):
        raise ValueError("Local model requires explicit limit 1..6")
    if limit is not None and not 1 <= limit <= len(suite.cases):
        raise ValueError("Invalid case limit")
    from os import environ

    settings = Settings(backend=backend, graph_prefix="ugi_audit_" + uuid4().hex[:12],
                        redis_url=environ.get("UGI_TEST_REDIS_URL", "redis://127.0.0.1:6380/0"),
                        provider="ollama" if model else "offline", model_id=model or "",
                        ollama_url=environ.get("UGI_OLLAMA_URL", "http://127.0.0.1:11434"),
                        allow_paid_calls=False, max_output_tokens=1800)
    expected, observed = defaultdict(set), defaultdict(set)
    rows, failures, domains = [], Counter(), defaultdict(lambda: [0, 0, 0])
    exact = emitted = calls = reviews = controls = abstentions = unassessed = 0
    for case in suite.cases[:limit] if limit else suite.cases:
        store = Store(settings, dataset=case.id)
        try:
            provider = Ollama(settings, store) if model else None
            engine = Engine(store, provider_factory=(lambda: provider) if model else None)
            started = perf_counter()
            ingestion = engine.ingest(case.id + ".txt", case.text.encode(), use_ai=bool(model))
            elapsed = (perf_counter() - started) * 1000
            records = {r["id"]: r for kind in ("Source", "Entity", "Claim", "RelationEvent", "Evidence", "Chunk", "Mention")
                       for r in store.list(kind, 20000)}
            reader = Store(settings, dataset=case.id) if backend == "falkordb" else store
            retrieved = {rid: reader.get(rid) for rid in records}
            consistent = retrieved == records
            assert consistent, "Persisted/reconnected retrieval differs"
            expected_edges = incidence(records)
            actual_edges = ({tuple(row) for row in reader.query(
                "MATCH (a:Record)-[r]->(b:Record) RETURN a.id,b.id,type(r),r.claim_id,r.role")}
                            if reader.client else
                            {tuple(edge) if len(edge) == 5 else (*edge, "") for edge in reader.links})
            assert actual_edges == expected_edges, "Stored graph incidence differs from payloads"
            claims, events = reader.claims(), reader.events(limit=500)
            scored = case.complete and case.annotation_status != "unreviewed"
            p = {binary_signature(c) for c in claims}
            g = {binary_signature(c) for c in case.binary}
            pe = {event_signature(e) for e in events}
            ge = {event_signature(e) for e in case.events}
            values = {
                "binary": (p, g),
                "qualified_binary": ({binary_signature(c, True) for c in claims},
                                     {binary_signature(c, True) for c in case.binary}),
                "events": (pe, ge),
                "qualified_events": ({event_signature(e, True) for e in events},
                                     {event_signature(e, True) for e in case.events}),
                "participant_roles": ({(e["relation_type"], p["role"], key(p["name"]))
                                       for e in events for p in e["participants"]},
                                      {(e["relation_type"], p["role"], key(p["name"]))
                                       for e in case.events for p in e["participants"]}),
                "entity_surfaces": ({key(e["name"]) for e in reader.list("Entity", 20000)},
                                    {key(n) for n in case.entities}),
                "directed_pairs": ({(c[0], c[2]) for c in p}, {(c[0], c[2]) for c in g}),
            }
            incorrect, missing, rejected_supported = [], [], 0
            tasks = reader.list("ReviewTask")
            if scored:
                for name, (predicted, gold) in values.items():
                    observed[name] |= {(case.id, v) for v in predicted}
                    expected[name] |= {(case.id, v) for v in gold}
                incorrect = [list(s) for s in p - g]
                missing = [list(s) for s in g - p]
                for s in p - g:
                    category = ("wrong_qualifier_or_predicate" if (s[0], s[2]) in
                                {(v[0], v[2]) for v in g} else "unsupported_binary")
                    failures[category] += 1
                failures["missed_binary"] += len(g - p)
                failures["unsupported_event"] += len(pe - ge)
                failures["missed_event"] += len(ge - pe)
                qualified = values["qualified_binary"]
                failures["temporal_or_historical_mismatch"] += len(p & g) - len(qualified[0] & qualified[1])
                rejected_supported = sum(binary_signature(t["candidate"]) in g for t in tasks
                                         if t.get("candidate", {}).get("subject"))
                if not g and not ge:
                    controls += 1
                    abstentions += not claims and not events
                d = domains[case.domain]
                d[0] += len(p & g) + len(pe & ge)
                d[1] += len(p) + len(pe)
                d[2] += len(g) + len(ge)
            else:
                unassessed += len(claims) + len(events)
            for record in claims + events:
                evidence, chunk = reader.get(record["evidence_id"]), reader.get(record["chunk_id"])
                exact += chunk["text"][evidence["start"]:evidence["end"]] == evidence["quote"]
                emitted += 1
            calls += ingestion["usage"]["calls"]
            reviews += len(tasks)
            rows.append(dict(id=case.id, domain=case.domain, source_url=case.source_url,
                             source_title=case.source_title, licence=case.licence,
                             licence_url=case.licence_url, source_locator=case.source_locator,
                             annotation_status=case.annotation_status, scored=scored,
                             claims=claims, events=events, incorrect_binary=incorrect,
                             missed_binary=missing, supported_but_rejected=rejected_supported,
                             reviews=[dict(category=review_category(t["reason"]), **t) for t in tasks],
                             usage=ingestion["usage"], warnings=ingestion["warnings"],
                             attempted_model_calls=provider.calls if provider else 0,
                             candidate_free_text_chunks=ingestion.get("candidate_free_text_chunks", []),
                             ingestion_ms=round(elapsed, 3), persisted_records=len(records),
                             graph_incidence_edges=len(actual_edges), graph_incidence_consistent=True,
                             graph_retrieval_consistent=consistent))
        finally:
            # Only this invocation's exact, random, isolated graph is eligible.
            if store.client:
                assert store.graph.startswith(settings.graph_prefix + "_")
                store.client.execute_command("GRAPH.DELETE", store.graph)
    return dict(version=suite.version, recorded_at=now(), split=suite.split,
                fixture_sha256=digest(raw), backend=backend, model=model,
                actual_model_inference=bool(model), scope=suite.scope, cases=len(rows),
                annotation_counts=dict(Counter(r["annotation_status"] for r in rows)),
                metrics={k: scores(observed[k], expected[k]) for k in expected},
                by_domain={k: dict(tp=v[0], predicted=v[1], gold=v[2],
                                  f1=2*v[0]/(v[1]+v[2]) if v[1]+v[2] else None)
                           for k, v in domains.items()},
                failure_categories=dict(failures), evidence=dict(exact=exact, emitted=emitted),
                abstention=dict(correct=abstentions, controls=controls),
                unassessed_predictions=unassessed, model_calls=calls, review_tasks=reviews,
                attempted_model_calls=sum(r["attempted_model_calls"] for r in rows),
                retrieval_checks=sum(r["persisted_records"] for r in rows),
                retrieval_consistent=all(r["graph_retrieval_consistent"] for r in rows),
                graph_incidence_checks=sum(r["graph_incidence_edges"] for r in rows),
                graph_incidence_consistent=all(r["graph_incidence_consistent"] for r in rows),
                per_case=rows, cloud_api_charge_usd=0,
                limitations=["AI-authored provisional labels are not independent human truth",
                             "Entity surfaces are relation participants, not exhaustive span-level NER",
                             "No semantic F1 for unreviewed/incomplete public documents",
                             "Cross-document identity assessed by separate controlled robustness tests",
                             "Small curated corpus; lexical split guard cannot exclude semantic leakage"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--development", type=Path)
    parser.add_argument("--backend", choices=["memory", "falkordb"], default="falkordb")
    parser.add_argument("--local-model")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--final-checkpoint", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.fixture, args.backend, args.local_model, args.limit,
                   args.final_checkpoint, args.development)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("cases", "backend", "metrics", "failure_categories",
                     "evidence", "model_calls", "retrieval_consistent")}, indent=2))


if __name__ == "__main__":
    main()
