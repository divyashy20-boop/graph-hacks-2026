import json
from pathlib import Path

import pytest

from ugi.engine import Engine
from ugi.eval_intelligence import Suite, load_suite, run
from ugi.extract import discover, verify
from ugi.models import Candidate, CompactExtraction, Settings
from ugi.prepare_annotations import select
from ugi.store import Store

ROOT = Path(__file__).parents[1]


def test_evaluation_temporal_event_metrics_and_split_guard():
    report = run(ROOT / "evaluation/intelligence_dev.json")
    assert report["cases"] == 6
    assert report["metrics"]["event"]["tp"] == 1
    assert report["metrics"]["binary_temporal"]["tp"] == 3
    assert report["evidence"]["checked"] == report["evidence"]["exact"]
    assert report["model_usage"]["calls"] == 0
    assert report["annotation_counts"] == {"provisional": 6}
    with pytest.raises(ValueError):
        load_suite(ROOT / "evaluation/intelligence_dev.json", ROOT / "evaluation/intelligence_dev.json")


def test_unreviewed_incomplete_annotations_never_become_false_positive_labels(tmp_path):
    data = json.loads((ROOT / "evaluation/intelligence_dev.json").read_text())
    data["cases"] = [data["cases"][0]]
    data["cases"][0].update(annotation_status="unreviewed", complete=False, binary=[])
    path = tmp_path / "unreviewed.json"
    path.write_text(json.dumps(data))
    report = run(path)
    assert report["metrics"] == {}
    assert report["unassessed_predictions"] == 1
    assert report["unsupported_against_complete_labels"]["rate"] is None


def test_label_validation_requires_review_metadata():
    data = json.loads((ROOT / "evaluation/intelligence_dev.json").read_text())
    data["cases"][0]["annotation_status"] = "human_reviewed"
    with pytest.raises(ValueError, match="reviewer"):
        Suite.model_validate(data)


def test_local_probe_requires_explicit_small_limit():
    with pytest.raises(ValueError, match="explicit"):
        run(ROOT / "evaluation/intelligence_dev.json", model="fake")


def test_compact_dates_preserved_and_duplicate_model_claim_removed():
    text = "Mara works at Nacre from 2018 until 2020."

    class Local:
        is_local = True
        usage = {"calls": 0}

        def request(self, prompt, schema):
            self.usage["calls"] += 1
            assert schema is CompactExtraction
            return CompactExtraction(relations=[{
                "subject": "Mara", "predicate": "WORKS_AT", "object": "Nacre", "evidence": text,
            }])

    store = Store(Settings(backend="memory"))
    local = Local()
    result = Engine(store, provider_factory=lambda: local).ingest("time.txt", text.encode(), use_ai=True)
    assert result["claims"] == 1 and result["review_tasks"] == 0
    assert store.claims()[0]["valid_from"] == "2018-01-01"
    assert store.claims()[0]["valid_to"] == "2020-12-31"
    assert local.usage["calls"] == 1


def test_fresh_public_queue_reproducible_and_unreviewed():
    raw = json.dumps({"P1": [dict(tokens=["Entity" + str(i), "owns", "Object" + str(i)],
                                      h=["Entity" + str(i)], t=["Object" + str(i)])
                               for i in range(30)]}).encode()
    first = select(raw, 6)
    second = select(raw, 6)
    assert first == second
    assert all(not c["complete"] and c["annotation_status"] == "unreviewed" for c in first["cases"])
    Suite.model_validate(first)


def test_compact_date_recovery_is_bound_to_the_matching_relation():
    text = "Ada works at Boreal from 2010 until 2012. Cora works at Delta from 2020 until 2022."

    class Local:
        is_local = True

        def request(self, prompt, schema):
            return CompactExtraction(relations=[{
                "subject": "Cora", "predicate": "WORKS_AT", "object": "Delta", "evidence": text,
            }])

    candidates, _ = discover({"text": text, "record": None}, Local())
    model = next(c for c in candidates if c.subject == "Cora" and c.evidence == text)
    assert (model.valid_from, model.valid_to) == ("2020-01-01", "2022-12-31")


@pytest.mark.parametrize("updates", [{"event_time": "2025-01-02"}, {"historical": True}])
def test_grammar_vetoes_wrong_event_date_and_historical_flag(updates):
    text = "Ada meets Boreal on 2025-01-01."
    candidate = Candidate(subject="Ada", predicate="MEETS", object="Boreal",
                          evidence=text, event_time="2025-01-01").model_copy(update=updates)
    assert not verify(candidate, {"text": text, "record": None})[0]


def test_fixture_hash_is_independent_of_windows_line_endings(tmp_path):
    source = ROOT / "evaluation/intelligence_eval.json"
    windows = tmp_path / "windows.json"
    windows.write_bytes(source.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    assert load_suite(windows)[1] == load_suite(source)[1]
    assert load_suite(source)[1] == "b534b5d70492d113f0400d308bfe00458c28cf7b0ba5bda5f2453075e33e8b73"
