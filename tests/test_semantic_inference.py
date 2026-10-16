"""Typed multi-hop inference, evidence/temporal abstention and verifier guards."""
import json

from ugi.engine import Engine
from ugi.extract import verify
from ugi.models import Candidate, RelationQuery, Settings, Verdict
from ugi.store import Store


def system(rows):
    e = Engine(Store(Settings(backend="memory")))
    e.ingest("relations.json", json.dumps(rows).encode())
    return e


def answer(e, relation="SHARES_EMPLOYER", as_of=None):
    return e.relationship(RelationQuery(
        subject="Alice", object="Bob", predicate=relation, as_of=as_of))


def test_shared_employer_only_with_overlapping_temporal_evidence():
    e = system([
        {"subject":"Alice","subject_id":"alice","subject_type":"Person",
         "predicate":"works_for","object":"Acme","object_id":"acme",
         "object_type":"Organisation","valid_from":"2020-01-01","valid_to":"2022-12-31"},
        {"subject":"Bob","subject_id":"bob","subject_type":"Person",
         "predicate":"works_at","object":"Acme","object_id":"acme",
         "object_type":"Organisation","valid_from":"2021-01-01","valid_to":"2023-12-31"}
    ])
    result = answer(e, as_of="2021-06-01")
    assert result["status"] == "RULE_DERIVED"
    assert result["rules"] == ["shared_employer_temporal_overlap_v1"]
    assert result["resolution"]["assessment"] == "RULE_DERIVED"
    assert result["resolution"]["supporting_claim_ids"] == result["supporting_claim_ids"]
    assert len(result["evidence"]) == 2
    assert result["paths"]
    assert answer(e, "FRIENDS_WITH", "2021-06-01")["status"] == "CONNECTED_ONLY"
    assert answer(e, as_of="2023-06-01")["status"] == "UNKNOWN"
    assert answer(e)["status"] in {"UNKNOWN", "CONNECTED_ONLY"}


def test_undated_employment_must_not_prove_temporal_overlap():
    e = system([
        {"subject":"Alice","subject_id":"alice","predicate":"works_at",
         "object":"Acme","object_id":"acme"},
        {"subject":"Bob","subject_id":"bob","predicate":"works_at",
         "object":"Acme","object_id":"acme"}
    ])
    assert answer(e)["status"] == "CONNECTED_ONLY"
    assert answer(e, as_of="2021-01-01")["status"] == "UNKNOWN"


def test_dependency_rule_verdict_and_resolution_are_consistent():
    e = system([
        {"subject": "proxy", "subject_id": "proxy", "predicate": "depends_on",
         "object": "backend", "object_id": "backend"},
        {"subject": "backend", "subject_id": "backend", "predicate": "depends_on",
         "object": "db", "object_id": "db"},
    ])

    result = e.relationship(RelationQuery(
        subject="proxy", object="db", predicate="TRANSITIVELY_DEPENDS_ON"))

    assert result["status"] == "RULE_DERIVED"
    assert result["resolution"]["assessment"] == result["status"]
    assert result["rules"] == ["dependency_reachability_v1"]
    assert result["resolution"]["rule_id"] == result["rules"][0]
    assert len(result["supporting_claim_ids"]) == 2
    assert result["resolution"]["supporting_claim_ids"] == result["supporting_claim_ids"]
    assert result["resolution"]["missing_evidence"] == []


def test_shared_event_does_not_prove_same_employer():
    e = system([
        {"subject":"Alice","subject_id":"alice","predicate":"attended",
         "object":"Meetup","object_id":"meetup"},
        {"subject":"Bob","subject_id":"bob","predicate":"attended",
         "object":"Meetup","object_id":"meetup"}
    ])
    assert answer(e)["status"] == "CONNECTED_ONLY"


def test_provider_can_review_distinct_unparsed_clause():
    class Reviewer:
        def request(self, prompt, response_type):
            assert response_type is Verdict
            assert "Bob" in prompt and "leads" in prompt
            return Verdict(supported=True, reason="Explicit second clause")

    text = "Alice owns Acme. Bob, the CTO, leads Delta."
    candidate = Candidate(subject="Bob", object="Delta",
                          predicate="leads", evidence=text)
    accepted, _ = verify(candidate, {"text":text, "record":None}, Reviewer())
    assert accepted


def test_grammar_reversal_is_not_overridden_by_provider():
    class Reviewer:
        def request(self, *_):
            raise AssertionError("Deterministic contradiction must veto model")

    text = "Alice owns Acme."
    candidate = Candidate(subject="Acme", object="Alice",
                          predicate="owns", evidence=text)
    accepted, _ = verify(candidate, {"text":text, "record":None}, Reviewer())
    assert not accepted


def test_same_external_id_different_entity_types_does_not_merge():
    e = system([{
        "subject": "Alice", "subject_id": "shared-123", "subject_type": "Person",
        "predicate": "works_at", "object": "Acme", "object_id": "shared-123",
        "object_type": "Organisation"
    }])
    assert e.store.counts()["Entity"] == 2
    c = e.store.claims()[0]
    assert c["subject_id"] != c["object_id"]
    assert e.relationship(RelationQuery(subject="Alice", object="Acme",
                                        predicate="WORKS_AT"))["status"] == "SOURCE_ASSERTED"


def test_legacy_identifiers_preserved_if_types_match():
    from ugi.models import uid, key
    e = Engine(Store(Settings(backend="memory")))
    old_id = uid("entity", "id:person-legacy")
    e.store.commit([{
        "id": old_id, "kind": "Entity", "identity_key": "id:person-legacy",
        "name": "Alice", "name_key": key("Alice"), "entity_type": "Person",
        "aliases": [], "alias_keys": [], "external_id": "person-legacy"
    }])
    e.ingest("legacy.json", json.dumps([{
        "subject": "Alice", "subject_type": "Person", "subject_id": "person-legacy",
        "predicate": "works_at", "object": "Acme", "object_type": "Organisation",
        "object_id": "organisation-1"
    }]).encode())
    assert e.resolve("Alice")["id"] == old_id
    assert e.store.counts()["Entity"] == 2
