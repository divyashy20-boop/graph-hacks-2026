import pytest

from ugi.clauses import anchored_dates, entity_hints
from ugi.engine import Engine
from ugi.extract import text_candidates, verify
from ugi.models import Candidate, RelationQuery, Settings
from ugi.store import Store


def extract(text):
    candidates = text_candidates(text)
    assert all(verify(c, {"text": text, "record": None})[0] for c in candidates)
    return {(c.subject, c.predicate, c.object, c.historical, c.polarity, c.modality) for c in candidates}


def test_appositive_affiliation_and_main_clause_have_separate_historical_scope():
    rows = extract("Talia, a former Vega scientist, owns Willow.")
    assert ("Talia", "FORMER_SCIENTIST_AT", "Vega", True, "positive", "asserted") in rows
    assert ("Talia", "owns", "Willow", False, "positive", "asserted") in rows
    assert len(rows) == 2
    assert not text_candidates("If Talia, a former Vega scientist, owns Willow, notify Orion.")
    assert not text_candidates("Talia, a fictional Vega scientist, owns Willow.")
    assert len(extract("Talia owns Willow.")) == 1


def test_responsibility_lists_preserve_action_purpose_and_full_evidence():
    text = ("Vega was the primary Orion industrial contractor, responsible for designing the sensor, "
            "control bus, and cooling shield, and for preparing the vehicle for inspection.")
    rows = extract(text)
    assert len(rows) == 5 and all(r[3] for r in rows)
    assert {r[1] for r in rows} == {"CONTRACTOR_FOR", "RESPONSIBLE_FOR_DESIGNING",
                                               "RESPONSIBLE_FOR_PREPARING_FOR_INSPECTION"}
    assert {r[2] for r in rows} == {"Orion", "sensor", "control bus", "cooling shield", "vehicle"}
    assert all(c.evidence == text for c in text_candidates(text))
    assert not any("BUILT" in r[1] or "OWNS" in r[1] for r in rows)
    assert len(extract("Vega provides Willow to Orion.")) == 0  # Event, no binary projection.


@pytest.mark.parametrize("tail", [
    "if Orion agrees", "but not testing Cygnus", "or maintaining Cygnus",
    "which may never launch", "according to Council", "for NASA", "from 2020 until 2022",
])
def test_ambiguous_responsibility_tail_is_not_discarded(tail):
    assert not text_candidates("Vega is responsible for building the sensor " + tail + ".")


@pytest.mark.parametrize("aux,polarity,modality,historical", [
    ("is", "positive", "asserted", False), ("was", "positive", "asserted", True),
    ("is not", "negative", "asserted", False), ("might not be", "negative", "possible", False),
])
def test_responsibility_negation_modality_scope(aux, polarity, modality, historical):
    rows = extract(f"Vega {aux} responsible for testing the sensor and control bus.")
    assert len(rows) == 2
    assert all(r[3:] == (historical, polarity, modality) for r in rows)


def test_source_entity_hints_are_exact_bounded_and_never_world_knowledge():
    text = "Vega is responsible for building the optical sensor and control bus."
    hints = entity_hints(text)
    assert {"Vega", "optical sensor", "control bus"} <= {h["text"] for h in hints}
    assert all(text[h["start"]:h["end"]] == h["text"] for h in hints)
    assert len(entity_hints(" ".join('Entity'+str(i) for i in range(60)))) <= 24


def test_responsibility_is_not_completed_work_or_current_historical_fact():
    engine = Engine(Store(Settings(backend="memory")))
    engine.ingest("duties.txt", b"Vega was responsible for building the sensor.")
    assert len(engine.store.claims()) == 1
    assert engine.relationship(RelationQuery(subject="Vega", object="sensor",
                                             predicate="BUILT"))["status"] != "SOURCE_ASSERTED"
    assert engine.relationship(RelationQuery(subject="Vega", object="sensor",
                   predicate="RESPONSIBLE_FOR_BUILDING"))["status"] == "UNKNOWN"


def test_partial_model_quote_cannot_evade_full_sentence_predicate_and_history():
    text = "Vega was the main Orion industrial contractor, responsible for building the sensor."
    partial = "Vega was the main Orion industrial contractor"
    candidate = Candidate(subject="Vega", object="Orion", predicate="IS_CONTRACTOR_FOR", evidence=partial)
    accepted, reason = verify(candidate, {"text": text, "record": None})
    assert not accepted and "grammar" in reason
    proper = next(c for c in text_candidates(text) if c.predicate == "CONTRACTOR_FOR")
    assert verify(proper, {"text": text, "record": None})[0]


def test_pair_anchored_dates_require_scope_and_never_copy_unrelated_dates():
    text = "Talia R. Vega served as a pilot from 2001 to 2005"
    fields = anchored_dates("Talia R. Vega", "pilot", text)
    assert fields["valid_from"] == "2001-01-01" and fields["valid_to"] == "2005-12-31"
    assert fields["historical"] and fields["time_precision"] == "year"
    candidate = Candidate(subject="Talia R. Vega", object="pilot", predicate="SERVED_AS", evidence=text)
    assert not verify(candidate, {"text": text, "record": None})[0]
    class Reviewer:
        def request(self, *args):
            from ugi.models import Verdict
            return Verdict(supported=True, reason="Test-only literal occupational statement")
    assert verify(candidate.model_copy(update=fields), {"text": text, "record": None}, Reviewer())[0]
    assert not anchored_dates("Talia", "Willow", "Orion worked at Cedar from 2001 to 2005. Talia owns Willow.")
    assert not anchored_dates("Talia", "Willow", "Talia met Willow in 2001 before Orion moved in 2005.")
