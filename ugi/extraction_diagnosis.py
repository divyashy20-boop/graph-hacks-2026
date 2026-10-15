"""Local stage diagnosis using existing provisional DEVELOPMENT labels only.

No distinct NER stage existed in C: missing participant surfaces in relation
proposals are recorded as a secondary observation, not falsely attributed to NER.
Optional recorded model reports are inspected without making inference calls.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

from .conversion_audit import AuditSuite
from .eval_intelligence import binary_signature, event_signature
from .extract import discover, verify
from .models import key
from .nary import verify_event

CATEGORIES = ("entity_not_identified", "candidate_never_proposed", "wrong_subject_or_object",
              "wrong_direction", "incorrect_predicate", "lost_qualifiers", "wrong_evidence_span",
              "false_rejection_by_verifier", "unsafe_acceptance", "accepted_not_persisted")


def diagnose(fixture, persisted):
    suite = AuditSuite.model_validate_json(fixture.read_bytes())
    if suite.split != "development":
        raise ValueError("Diagnose DEVELOPMENT only; never tune on frozen evaluation labels")
    recorded = json.loads(persisted.read_text(encoding="utf-8"))
    rows_by_id = {r["id"]: r for r in recorded["per_case"]}
    counts = Counter({c: 0 for c in CATEGORIES})
    examples, absent = [], 0
    for case in suite.cases:
        if not case.complete or case.annotation_status == "unreviewed":
            continue
        events = []
        chunk = {"text": case.text, "record": None}
        candidates, _ = discover(chunk, event_sink=events)
        accepted = {binary_signature(c.model_dump()) for c in candidates if verify(c, chunk)[0]}
        row = rows_by_id[case.id]
        stored = {binary_signature(c) for c in row["claims"]}
        gold = {binary_signature(c) for c in case.binary}
        surfaces = {key(n) for c in candidates for n in (c.subject, c.object)}
        for label in case.binary:
            sig = binary_signature(label)
            if sig in stored:
                if binary_signature(label, True) not in {
                        binary_signature(c, True) for c in row["claims"]}:
                    counts["lost_qualifiers"] += 1
                    examples.append(dict(id=case.id, category="lost_qualifiers", target=label))
                continue
            pair = sig[0], sig[2]
            relevant = [c for c in candidates if
                        {key(c.subject), key(c.object)} == set(pair)]
            absent += int(not set(pair) <= surfaces)
            if sig in accepted:
                category = "accepted_not_persisted"
            elif any(binary_signature(c.model_dump()) == sig for c in relevant):
                exact = next(c for c in relevant if binary_signature(c.model_dump()) == sig)
                reason = verify(exact, chunk)[1]
                category = "wrong_evidence_span" if "exact source span" in reason else "false_rejection_by_verifier"
            elif any((key(c.subject), key(c.object)) == pair[::-1] for c in relevant):
                category = "wrong_direction"
            elif relevant:
                category = "incorrect_predicate"
            else:
                category = "candidate_never_proposed"
            counts[category] += 1
            examples.append(dict(id=case.id, category=category, target=label))
        for label in case.events:
            sig = event_signature(label)
            if sig not in {event_signature(e) for e in row["events"]}:
                proposed = next((e for e in events if event_signature(e.model_dump()) == sig), None)
                category = ("candidate_never_proposed" if proposed is None else
                            "accepted_not_persisted" if verify_event(proposed, chunk)[0] else
                            "false_rejection_by_verifier")
                counts[category] += 1
                examples.append(dict(id=case.id, category=category, target=label))
        for claim in row["claims"]:
            if binary_signature(claim) not in gold:
                counts["unsafe_acceptance"] += 1
                examples.append(dict(id=case.id, category="unsafe_acceptance",
                                     candidate=claim, note="Label disagreement, not adjudicated falsehood"))
    return dict(categories=dict(counts), examples=examples,
                unidentifiable_categories=["entity_not_identified", "wrong_subject_or_object"],
                participant_surface_absent_from_proposals=absent,
                scope="Offline developmental stage diagnosis; zero means not observed, not certified safe",
                limitations=["No independent NER stage: entity failure cannot be isolated from candidate generation",
                             "Existing labels are AI provisional; ontology/completeness can be wrong",
                             "wrong_subject/object vs absent proposal cannot be assigned without candidate trace",
                             "Frozen evaluation deliberately excluded"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=Path("evaluation/c_development.json"))
    parser.add_argument("--persisted-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = diagnose(args.fixture, args.persisted_report)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "examples"}, indent=2))


if __name__ == "__main__":
    main()
