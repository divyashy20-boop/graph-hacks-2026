"""Regression cases introduced after the recovered event ZIP was audited."""
from pathlib import Path

import pytest

from ugi.engine import Engine
from ugi.extract import text_candidates
from ugi.models import RelationQuery, Settings
from ugi.store import Store


def engine():
    return Engine(Store(Settings(backend="memory")))


def test_two_explicit_conjuncts_are_independent_claims():
    relations = text_candidates("Mesa depends on Nora and Onyx.")
    assert {(c.subject, c.object, c.predicate) for c in relations} == {
        ("Mesa", "Nora", "depends on"), ("Mesa", "Onyx", "depends on")}
    assert all(c.evidence == "Mesa depends on Nora and Onyx." for c in relations)


def test_explicit_main_clause_after_causal_prefix():
    relations = text_candidates("After Rill failed, Spruce alerted Tern.")
    assert len(relations) == 1 and relations[0].subject == "Spruce"
    assert relations[0].object == "Tern"
    assert relations[0].evidence.startswith("After Rill failed")


def test_conditional_does_not_become_assertion():
    assert not text_candidates("If Alice owns Acme, Bob manages Acme.")
    assert not text_candidates("Alice owns Bob and Charlie but not Dana.")


def test_negated_source_different_from_contradiction():
    system = engine()
    system.ingest("no.txt", b"Alice does not own Acme.")
    answer = system.relationship(RelationQuery(subject="Alice", predicate="OWN", object="Acme"))
    assert answer["status"] == "SOURCE_NEGATED" and answer["conflicting"] is False
    system.ingest("yes.txt", b"Alice owns Acme.")
    # Two identities share a name but cannot be safely merged across separate sources.
    assert system.resolve("Alice") is None
    merged = engine()
    merged.ingest("pair.json", b'[{"subject":"Alice","subject_id":"p1","predicate":"owns","object":"Acme","object_id":"org1"},{"subject":"Alice","subject_id":"p1","predicate":"owns","object":"Acme","object_id":"org1","polarity":"negative"}]')
    answer = merged.relationship(RelationQuery(subject="Alice", predicate="OWNS", object="Acme"))
    assert answer["status"] == "CONTRADICTED" and answer["conflicting"] is True


def test_transitively_depends_on_requires_two_hops():
    system = engine()
    system.ingest("dep.txt", b"Checkout depends on Gateway.")
    answer = system.relationship(RelationQuery(subject="Checkout", object="Gateway",
                                                predicate="TRANSITIVELY_DEPENDS_ON"))
    assert answer["status"] != "RULE_DERIVED"


def test_updated_fixture_quality_is_measurable():
    from ugi.evaluate import evaluate

    report = evaluate(Path(__file__).parents[1])
    outcome = report["variants"]["D_hybrid_offline_verified"]["relation"]
    assert outcome["gold"] == 24 and outcome["tp"] >= 22
    assert outcome["precision"] > .9
    # These synthetic examples are not evidence of general-domain performance.
    assert "synthetic" in report["scope"]
