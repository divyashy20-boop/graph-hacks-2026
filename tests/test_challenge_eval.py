"""Second-milestone audit regression tests (offline and graph-independent)."""
import json
from pathlib import Path

import pytest

from ugi.engine import Engine
from ugi.eval_challenge import run
from ugi.models import RelationQuery, Settings
from ugi.store import Store

ROOT = Path(__file__).parents[1]


def test_new_challenge_fixture_is_separate_and_nonempty():
    data = json.loads((ROOT / "evaluation/challenge_v1.json").read_text())
    previous = json.loads((ROOT / "evaluation/heldout.json").read_text())
    assert len(data["samples"]) == 26
    assert set(row["id"] for row in data["samples"]).isdisjoint(
        row["id"] for row in previous["samples"])
    assert sum(not row["gold"] for row in data["samples"]) >= 4
    assert "synthetic" in data["provenance"].lower()


def test_challenge_report_has_strict_scores_and_abstention():
    report = run(ROOT / "evaluation/challenge_v1.json")
    assert report["cases"] == 26
    assert report["relation"]["gold"] >= 20
    assert report["strict_relation"]["gold"] == report["relation"]["gold"]
    assert report["abstention"]["gold_empty"] >= 4
    assert report["evidence_span"]["correct"] == report["evidence_span"]["checked"]
    assert report["model_calls"] == report["paid_api_calls"] == 0
    assert report["fixture_sha256"] and len(report["per_sample"]) == 26
    assert "operations" in report["by_domain"] and "finance" in report["by_domain"]


def test_challenge_detects_false_alarms_and_exact_errors(tmp_path):
    path = tmp_path / "negative.json"
    path.write_text(json.dumps({"samples": [
        {"id": "x", "domain": "control", "text": "Alpha owns Beta.", "gold": []},
        {"id": "y", "domain": "control", "text": "If Alpha owns Beta, Gamma manages Delta.",
         "gold": []}
    ]}))
    outcome = run(path)
    assert outcome["abstention"]["gold_empty"] == 2
    assert outcome["abstention"]["false_alarm"] == 1
    assert outcome["relation"]["predicted"] == 1
    assert outcome["per_sample"][0]["false_positive"]
    assert outcome["per_sample"][1]["correct_abstention"]


def test_challenge_rejects_invalid_gold_and_duplicate_ids(tmp_path):
    invalid = tmp_path / "invalid.json"
    invalid.write_text(json.dumps({"samples": [{
        "id": "x", "domain": "test", "text": "Alpha owns Beta.", "gold": ["bad"]
    }]}))
    with pytest.raises(ValueError, match="Gold rows"):
        run(invalid)
    invalid.write_text(json.dumps({"samples": [
        {"id": "x", "domain": "test", "text": "Alpha owns Beta.", "gold": []},
        {"id": "x", "domain": "test", "text": "Beta owns Alpha.", "gold": []}
    ]}))
    with pytest.raises(ValueError, match="distinct"):
        run(invalid)


def test_unknown_resolver_explains_non_entailing_path_without_mutation():
    e = Engine(Store(Settings(backend="memory")))
    e.ingest("people.txt", b"Alice works at Acme. Bob works at Acme.")
    before = e.store.counts()
    result = e.relationship(RelationQuery(subject="Alice", object="Bob",
                                          predicate="FRIENDS_WITH", allow_hypothesis=False))
    assert result["status"] == "CONNECTED_ONLY"
    assert result["resolution"]["assessment"] == "CONNECTED_BUT_NOT_ENTAILED"
    assert "social ties" in result["resolution"]["missing_evidence"][0]
    assert len(result["resolution"]["path_summaries"]) > 0
    assert result["hypotheses"] == []
    assert e.store.counts() == before


def test_unknown_resolver_reports_identity_and_temporal_gap():
    e = Engine(Store(Settings(backend="memory")))
    e.ingest("links.txt", b"Alpha depends on Beta.")
    missing = e.relationship(RelationQuery(subject="Ghost", object="Beta",
                                           predicate="DEPENDS_ON"))
    assert missing["status"] == "UNKNOWN"
    assert missing["resolution"]["assessment"] == "MISSING_OR_AMBIGUOUS_IDENTITY"
    no_date = e.relationship(RelationQuery(subject="Alpha", object="Beta",
                                           predicate="TRANSITIVELY_DEPENDS_ON",
                                           as_of="2020-01-01"))
    assert no_date["status"] == "UNKNOWN"
    assert no_date["resolution"]["assessment"] == "NO_APPLICABLE_GRAPH_PATH"
    assert any("2020-01-01" in r for r in no_date["resolution"]["missing_evidence"])


def test_unknown_resolver_does_not_promote_generic_path_to_employment():
    e = Engine(Store(Settings(backend="memory")))
    e.ingest("people.txt", b"Alice works at Acme. Bob works at Acme.")
    r = e.relationship(RelationQuery(subject="Alice", object="Bob",
                                     predicate="SHARES_EMPLOYER"))
    assert r["status"] == "CONNECTED_ONLY"
    assert r["resolution"]["assessment"] == "CONNECTED_BUT_NOT_ENTAILED"
    assert any("dated" in s for s in r["resolution"]["missing_evidence"])
    assert e.store.list("Hypothesis") == []
