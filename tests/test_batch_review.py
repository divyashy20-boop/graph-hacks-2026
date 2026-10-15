"""Semantic batch verification must lower cost without inventing new graph facts."""
import json

from ugi.engine import Engine
from ugi.extract import verify, verify_local_batch
from ugi.models import BatchVerdicts, Candidate, CompactExtraction, Settings
from ugi.store import Store


def candidate(s, p, o, quote):
    return Candidate(subject=s, predicate=p, object=o, evidence=quote)


def test_local_batch_preserves_source_and_group_guards():
    text = "Atlas lies near Beacon and south of Cape, between Dune and Elm."
    data = [
        candidate("Atlas", "LOCATED_NEAR", "Beacon", text),
        candidate("Atlas", "SOUTH_OF", "Cape", text),
        candidate("Atlas", "SITUATED_BETWEEN", "Dune", text),
        candidate("Atlas", "LOCATED_NEAR", "Beacon", text.replace("Beacon", "Bea-con")),
        candidate("Atlas", "FRIENDS_WITH", "Elm", text),
    ]

    class Reviewer:
        is_local = True

        def __init__(self):
            self.calls = 0

        def request(self, instruction, schema):
            self.calls += 1
            assert schema is BatchVerdicts
            assert "CANDIDATES:" in instruction
            asked = json.loads(instruction.split("CANDIDATES:\n")[1])
            assert [item["index"] for item in asked] == [0, 1, 4]
            return BatchVerdicts(decisions=[
                {"index": 0, "supported": True, "reason": "Explicit spatial statement"},
                {"index": 1, "supported": True, "reason": "Explicit orientation"},
                {"index": 4, "supported": False, "reason": "No friendship assertion"},
            ])

    provider = Reviewer()
    outcome = verify_local_batch(data, {"text": text, "record": None}, provider)
    assert provider.calls == 1
    assert [o[0] for o in outcome] == [True, True, False, False, False]
    assert "multiple anchors" in outcome[2][1]
    assert "exact source span" in outcome[3][1]
    assert not outcome[4][0]


def test_ambiguous_participial_actor_not_promoted_even_with_provider():
    sentence = ("Coastal Road ends by Stone Bridge and where Railway Route crosses "
                "Birch River, entering into East District.")
    relation = candidate("Coastal Road", "ENTERS", "East District", sentence)
    accepted, reason = verify(relation, {"text": sentence, "record": None}, None)
    assert not accepted
    assert "Ambiguous participial" in reason


def test_batch_missing_or_duplicate_index_abstains():
    sentence = "Atlas lies near Beacon and south of Cape."
    data = [candidate("Atlas", "LOCATED_NEAR", "Beacon", sentence),
            candidate("Atlas", "SOUTH_OF", "Cape", sentence)]

    class BadReviewer:
        def request(self, *_):
            return BatchVerdicts(decisions=[
                {"index": 0, "supported": True, "reason": "yes"},
                {"index": 0, "supported": True, "reason": "again"},
            ])

    outcome = verify_local_batch(data, {"text": sentence, "record": None}, BadReviewer())
    assert not outcome[0][0] and not outcome[1][0]
    assert "duplicate" in outcome[0][1]
    assert "missing" in outcome[1][1]


def test_batch_review_failure_does_not_drop_deterministic_grammar():
    sentence = "Alice owns Acme. Delta lies near Echo."
    data = [candidate("Alice", "owns", "Acme", "Alice owns Acme."),
            candidate("Delta", "LOCATED_NEAR", "Echo", "Delta lies near Echo.")]

    class Failure:
        def request(self, *_):
            raise ValueError("Model call budget exhausted")

    outcome = verify_local_batch(data, {"text": sentence, "record": None}, Failure())
    assert outcome[0][0] is True
    assert outcome[1][0] is False
    assert "budget" in outcome[1][1]


def test_engine_multi_candidate_uses_two_calls_not_one_per_candidate():
    text = "Atlas lies near Beacon and south of Cape, between Dune and Elm."

    class Provider:
        is_local = True

        def __init__(self):
            self.calls = 0
            self.usage = {"calls": 0, "estimated_usd": 0}

        def request(self, instruction, schema):
            self.calls += 1
            self.usage["calls"] += 1
            if schema is CompactExtraction:
                return CompactExtraction(relations=[
                    {"subject": "Atlas", "predicate": "LOCATED_NEAR",
                     "object": "Beacon", "evidence": text},
                    {"subject": "Atlas", "predicate": "SOUTH_OF",
                     "object": "Cape", "evidence": text},
                    {"subject": "Atlas", "predicate": "SITUATED_BETWEEN",
                     "object": "Dune", "evidence": text},
                    {"subject": "Atlas", "predicate": "FRIENDS_WITH",
                     "object": "Elm", "evidence": text},
                ])
            assert schema is BatchVerdicts
            return BatchVerdicts(decisions=[
                {"index": 0, "supported": True, "reason": "Near relationship explicit"},
                {"index": 1, "supported": True, "reason": "South of Cape explicit"},
                {"index": 3, "supported": False, "reason": "No friendship assertion"},
            ])

    settings = Settings(backend="memory", provider="ollama",
                        model_id="fake-local", max_model_calls=4)
    provider = Provider()
    store = Store(settings)
    engine = Engine(store, provider_factory=lambda: provider)
    result = engine.ingest("batch.txt", text.encode(), use_ai=True)
    assert provider.calls == 2
    assert result["usage"]["calls"] == 2
    assert result["claims"] == 2 and result["review_tasks"] == 2
    assert store.counts()["Claim"] == 2
    predicates = {c["predicate"] for c in store.claims()}
    assert predicates == {"LOCATED_NEAR", "SOUTH_OF"}
