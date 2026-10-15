import json
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from ugi.api import create_app
from ugi.engine import Engine
from ugi.extract import grounded, text_candidates, verify
from ugi.models import Candidate, RelationQuery, Settings
from ugi.store import Store


@pytest.mark.parametrize("text", [
    "Vega uses Willow from 2019 but does not use Willow now.",
    "Vega uses Willow since 2019 if Cygnus approves.",
    "Vega uses Willow on 2020-01-01 according to an anonymous source.",
])
def test_temporal_tail_never_discards_qualification(text):
    assert not text_candidates(text)


@pytest.mark.parametrize("text,polarity,modality", [
    ("Vega might not own Willow.", "negative", "possible"),
    ("Vega does not own Willow.", "negative", "asserted"),
    ("Vega may own Willow.", "positive", "possible"),
    ("Vega owns Willow.", "positive", "asserted"),
])
def test_modal_negation_and_existing_polarity_preserved(text, polarity, modality):
    candidate = text_candidates(text)[0]
    assert candidate.polarity == polarity and candidate.modality == modality
    assert "not" not in candidate.predicate


def test_bounded_appositive_main_clause_and_negative_control():
    result = text_candidates("Talia, a former Vega engineer, led Gemini 9 investigation.")
    assert len(result) == 1 and result[0].subject == "Talia"
    assert result[0].object == "Gemini 9 investigation" and result[0].historical
    assert not text_candidates("Talia, who might not lead the team, led Gemini 9 investigation.")
    present = text_candidates("Talia, a former Vega engineer, owns Willow.")[0]
    assert not present.historical  # Former modifies affiliation, not present ownership.
    assert text_candidates("Talia owns Willow.")[0].object == "Willow"


def test_object_determiners_are_not_predicate_tokens():
    candidate = text_candidates("Talia led the Gemini 9 investigation.")[0]
    assert candidate.predicate == "led" and candidate.object == "Gemini 9 investigation"
    assert not text_candidates("Talia is a fictional researcher at Willow.")
    assert text_candidates("Talia works at Willow.")[0].predicate == "works at"


def test_empty_extraction_discloses_unassessed_coverage_without_inventing_facts():
    engine = Engine(Store(Settings(backend="memory")))
    empty = engine.ingest("complex.txt", b"An unstructured description without a named directed claim.")
    assert len(empty["candidate_free_text_chunks"]) == 1
    assert "does not prove" in empty["coverage_note"]
    assert not engine.store.claims() and not engine.store.events()
    positive = engine.ingest("simple.txt", b"Vega owns Willow.")
    assert not positive["candidate_free_text_chunks"] and positive["claims"] == 1


@pytest.mark.parametrize("name,quote", [("Ann", "Joanne owns Cygnus."),
                                        ("Cygnus", "Ann owns Cygnusville.")])
def test_entity_substrings_are_not_grounded_mentions(name, quote):
    candidate = Candidate(subject="Ann", predicate="OWNS", object="Cygnus", evidence=quote)
    assert not grounded(candidate, {"text": quote, "record": None})[0]
    true = "Ann owns Cygnus."
    assert grounded(candidate.model_copy(update={"evidence": true}), {"text": true, "record": None})[0]


def test_date_precision_rejects_invented_month_day():
    quote = "Vega met Willow in 2020."
    candidate = Candidate(subject="Vega", predicate="MET", object="Willow", evidence=quote,
                          event_time="2020-09-17", time_precision="day")
    assert not grounded(candidate, {"text": quote, "record": None})[0]
    assert grounded(candidate.model_copy(update={"event_time": "2020-01-01", "time_precision": "year"}),
                    {"text": quote, "record": None})[0]
    assert grounded(Candidate(subject="Vega", predicate="MET", object="Willow",
                              evidence="Vega met Willow on 2020-09-17.",
                              event_time="2020-09-17", time_precision="day"),
                    {"text": "Vega met Willow on 2020-09-17.", "record": None})[0]


def test_attributed_statement_does_not_become_unqualified_fact():
    quote = "Council claims Vega owns Willow."
    candidate = Candidate(subject="Vega", predicate="OWNS", object="Willow", evidence=quote)
    chunk = {"text": quote, "record": None}
    class Approver:
        def request(self, *args):
            from ugi.models import Verdict
            return Verdict(supported=True, reason="Test-only reviewer accepts literal attribution")
    assert not verify(candidate, chunk, Approver())[0]
    assert verify(candidate.model_copy(update={"attribution": "Council"}), chunk, Approver())[0]
    assert not verify(candidate.model_copy(update={"attribution": "Invented Council"}), chunk, Approver())[0]
    simple = "Vega owns Willow."
    assert verify(candidate.model_copy(update={"evidence": simple}), {"text": simple, "record": None})[0]


def test_speculation_does_not_prove_current_direct_relationship():
    engine = Engine(Store(Settings(backend="memory")))
    engine.ingest("maybe.txt", b"Vega allegedly owns Willow.")
    assert engine.store.claims()[0]["modality"] == "alleged"
    assert engine.relationship(RelationQuery(subject="Vega", object="Willow", predicate="OWNS"))["status"] == "UNKNOWN"


@pytest.mark.parametrize("verb,base", [("owns", "own"), ("uses", "use")])
def test_inflection_does_not_hide_a_source_contradiction_and_legacy_still_queries(verb, base):
    engine = Engine(Store(Settings(backend="memory")))
    engine.ingest("both.txt", f"Vega {verb} Willow. Vega does not {base} Willow.".encode())
    query = RelationQuery(subject="Vega", predicate=verb, object="Willow")
    assert engine.relationship(query)["status"] == "CONTRADICTED"
    # Simulate already-stored Milestone B canonical base-form payloads: no migration/write.
    negative = next(c for c in engine.store.claims() if c["polarity"] == "negative")
    negative["predicate"] = base.upper()
    assert engine.relationship(query)["status"] == "CONTRADICTED"
    positive = Engine(Store(Settings(backend="memory")))
    positive.ingest("yes.txt", f"Vega {verb} Willow.".encode())
    assert positive.relationship(query)["status"] == "SOURCE_ASSERTED"
    assert positive.relationship(RelationQuery(subject="Willow", predicate=verb, object="Vega"))["status"] != "SOURCE_ASSERTED"


BAD_INPUTS = [
    ("partial.json", b'[{"subject":"A","predicate":"owns","object":"B"},{"subject":"C","predicate":"owns"}]'),
    ("scalar.json", b'[3]'),
    ("missing.csv", b'subject,predicate,object\nA,owns,B\nC,owns,\n'),
    ("repeat.json", b'{"subject":"A","predicate":"owns","predicate":"never_owns","object":"B"}'),
    ("nonfinite.json", b'{"name":"Vega","value":NaN}'),
    ("blank.json", b'{"subject":" ","predicate":"owns","object":"B"}'),
    ("event.json", b'[{"relation_type":"PROVISION","participants":[]}]'),
    ("corrupt.pdf", b'%PDF-1.4\ngarbage'),
]


@pytest.mark.parametrize("filename,content", BAD_INPUTS)
def test_malformed_document_is_atomic_and_existing_data_unchanged(filename, content):
    client = TestClient(create_app(Settings(backend="memory", requests_per_minute=500)))
    assert client.post("/api/uploads", files={"file": ("ok.txt", b"Vega owns Willow.")}).status_code == 200
    before = client.get("/api/graph").json()
    response = client.post("/api/uploads", files={"file": (filename, content)})
    assert response.status_code == 422, response.text
    assert client.get("/api/graph").json() == before
    # Recovery and idempotency still work after a rejected upload.
    assert client.post("/api/uploads", files={"file": ("ok.txt", b"Vega owns Willow.")}).json()["duplicate"]


def exercise_identity(store):
    engine = Engine(store)
    def upload(name, rows):
        return engine.ingest(name, json.dumps(rows).encode())
    base = dict(subject="Alex", subject_id="same", subject_type="Person", predicate="WORKS_AT",
                object="Vega", object_id="same", object_type="Organization",
                valid_from="2018-01-01", valid_to="2021-12-31")
    upload("old.json", [base])
    assert len(store.list("Entity")) == 2
    assert store.entities("Alex")[0]["id"] != store.entities("Vega")[0]["id"]
    assert engine.relationship(RelationQuery(subject="Alex", object="Vega", predicate="WORKS_AT",
                                              as_of="2020-01-01"))["status"] == "SOURCE_ASSERTED"
    negative = {**base, "polarity": "negative"}
    upload("contradiction.json", [negative])
    assert len(store.list("Entity")) == 2  # Explicit cross-document IDs link, not name guesses.
    assert engine.relationship(RelationQuery(subject="Alex", object="Vega", predicate="WORKS_AT",
                                              as_of="2020-01-01"))["status"] == "CONTRADICTED"
    assert engine.relationship(RelationQuery(subject="Alex", object="Vega", predicate="WORKS_AT",
                                              as_of="2024-01-01"))["status"] == "UNKNOWN"
    upload("other.json", [{**base, "subject_id": "other"}])
    assert engine.resolve("Alex") is None and len(store.entities("Alex")) == 2
    assert store.list("MergeDecision")
    return engine


def test_adversarial_cross_document_identity_and_temporal_conflicts():
    exercise_identity(Store(Settings(backend="memory")))


def test_graph_timeout_has_an_actionable_safe_response():
    from redis.exceptions import ResponseError

    client = TestClient(create_app(Settings(backend="memory")))
    client.post("/api/uploads", files={"file": ("ok.txt", b"Vega owns Willow.")})
    store = client.app.state.store_for("local", "demo")
    def timeout(*args, **kwargs):
        raise ResponseError("Query timed out")
    store.commit = timeout
    result = client.post("/api/uploads", files={"file": ("new.txt", b"Orion owns Maple.")})
    assert result.status_code == 503
    assert "reduce upload size" in result.json()["detail"]
    assert len(store.claims()) == 1


@pytest.mark.integration
def test_actual_write_budget_does_not_partially_overwrite_existing_dataset():
    from redis.exceptions import ResponseError

    from ugi.benchmark_conversion import payload

    if not os.getenv("UGI_TEST_REDIS_URL"):
        pytest.skip("Requires actual FalkorDB")
    settings = Settings(redis_url=os.environ["UGI_TEST_REDIS_URL"], graph_prefix="ugi_budget_"+uuid4().hex[:10])
    store = Store(settings)
    try:
        engine = Engine(store)
        engine.ingest("seed.txt", b"Vega owns Willow.")
        before = {r["id"]: r for kind in ("Entity", "Claim", "Source", "Chunk", "Evidence", "Mention")
                  for r in store.list(kind)}
        try:
            engine.ingest("large.json", payload(1000, "json"))
        except ResponseError as exc:
            assert "timed out" in str(exc).lower()
            after = {r["id"]: r for kind in ("Entity", "Claim", "Source", "Chunk", "Evidence", "Mention")
                     for r in store.list(kind, 20000)}
            assert after == before
        else:
            # Faster CI hardware may finish under the same bounded write budget.
            assert len(store.claims()) == 1001
            assert all(store.get(rid) == record for rid, record in before.items())
    finally:
        assert store.graph.startswith(settings.graph_prefix+"_")
        store.client.execute_command("GRAPH.DELETE", store.graph)


@pytest.mark.integration
def test_real_invalid_upload_does_not_corrupt_existing_graph_and_identity():
    if not os.getenv("UGI_TEST_REDIS_URL"):
        pytest.skip("Requires actual FalkorDB")
    settings = Settings(redis_url=os.environ["UGI_TEST_REDIS_URL"], graph_prefix="ugi_robust_"+uuid4().hex[:10])
    store = Store(settings)
    try:
        engine = exercise_identity(store)
        before = store.counts()
        for filename, content in BAD_INPUTS:
            with pytest.raises(ValueError):
                engine.ingest(filename, content)
            assert store.counts() == before
        other = Store(settings, dataset="separate")
        assert not other.claims()
        assert Store(settings).counts() == before
    finally:
        for dataset in ("demo", "separate"):
            isolated = Store(settings, dataset=dataset)
            assert isolated.graph.startswith(settings.graph_prefix+"_")
            isolated.client.execute_command("GRAPH.DELETE", isolated.graph)
