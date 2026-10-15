import json
import os
from pathlib import Path

import pytest

from ugi.benchmark_conversion import payload, run
from ugi.conversion_audit import AuditSuite, audit, check_splits, digest, incidence
from ugi.prepare_conversion_corpus import prepare
from ugi.review_conversion_annotations import promote

ROOT = Path(__file__).parents[1]


def test_audit_checks_real_quotes_and_is_explicitly_provisional():
    report = audit(ROOT / "evaluation/c_development.json")
    assert report["annotation_counts"] == {"provisional": 14}
    assert report["evidence"]["exact"] == report["evidence"]["emitted"]
    assert report["retrieval_consistent"] and report["model_calls"] == 0
    assert report["graph_incidence_consistent"] and report["graph_incidence_checks"] > 0
    assert report["metrics"]["binary"]["gold"] == 15
    assert any(not row["scored"] for row in report["per_case"])


def test_frozen_split_refuses_early_use_and_requires_manifest():
    path = ROOT / "evaluation/c_evaluation.json"
    with pytest.raises(ValueError, match="checkpoint"):
        audit(path)
    # Do not execute or inspect frozen outputs during development.


def test_source_hash_quote_and_annotation_validation():
    data = json.loads((ROOT / "evaluation/c_development.json").read_text(encoding="utf-8"))
    data["cases"][0]["text"] += " altered"
    with pytest.raises(ValueError, match="hash"):
        AuditSuite.model_validate(data)
    data["cases"][0]["source_sha256"] = __import__("hashlib").sha256(
        data["cases"][0]["text"].encode()).hexdigest()
    data["cases"][0]["binary"][0]["evidence"] = "Invented quotation"
    with pytest.raises(ValueError, match="quotation"):
        AuditSuite.model_validate(data)


def test_near_duplicate_and_document_leakage_rejected():
    dev = AuditSuite.model_validate_json((ROOT / "evaluation/c_development.json").read_bytes())
    other = dev.model_copy(update={"split": "evaluation"})
    with pytest.raises(ValueError, match="leakage"):
        check_splits(dev, other)
    a = dev.cases[0]
    b = a.model_copy(update={"id": "other", "source_url": "https://different.example/",
                            "text": a.text + " Additional unrelated words."})
    with pytest.raises(ValueError, match="near duplicate"):
        check_splits(dev.model_copy(update={"cases": [a]}),
                     other.model_copy(update={"cases": [b]}))


def test_freeze_cannot_be_silently_overwritten(tmp_path):
    (tmp_path / "c_manifest.json").write_text("{}")
    with pytest.raises(ValueError, match="overwrite"):
        prepare({}, {}, tmp_path)


def test_development_freeze_checksum_has_not_changed():
    manifest = json.loads((ROOT / "evaluation/c_manifest.json").read_text())
    data = json.loads((ROOT / "evaluation/c_development.json").read_text(encoding="utf-8"))
    assert digest(data) == manifest["development_sha256"]


def test_reviewed_derivative_requires_declarations_and_preserves_original(tmp_path):
    # Mock workflow metadata, NOT a real human annotation of public data.
    devdata = json.loads((ROOT / "evaluation/c_development.json").read_text(encoding="utf-8"))
    case = devdata["cases"][-1]
    source = {**devdata, "split": "evaluation", "cases": [case]}
    source["cases"][0] = {**case, "annotation_status": "unreviewed", "complete": False}
    original = tmp_path / "original.json"
    original.write_text(json.dumps(source))
    edited = tmp_path / "edited.json"
    edited.write_text(json.dumps(source))
    development = tmp_path / "development.json"
    development.write_text(json.dumps({**devdata, "cases": devdata["cases"][:1]}))
    with pytest.raises(ValueError, match="No human"):
        promote(edited, original, development, tmp_path / "reviewed")
    source["cases"][0].update(annotation_status="human_reviewed", reviewers=["TEST-ONLY reviewer metadata"])
    edited.write_text(json.dumps(source))
    promote(edited, original, development, tmp_path / "reviewed")
    assert json.loads(original.read_text())["cases"][0]["annotation_status"] == "unreviewed"
    with pytest.raises(ValueError, match="overwrite"):
        promote(edited, original, development, tmp_path / "reviewed")


def test_benchmark_respects_quotas_and_measures_real_operations():
    report = run(sizes=[5], backend="memory")
    for row in report["results"]:
        assert row["counts"]["Claim"] == 5 and row["counts"]["Entity"] == 6
        assert row["duplicate_no_new_records"] and row["repeated_claim_ids_equal"]
        assert len(row["query_observations_ms"]) == 5 and row["model_calls"] == 0
    assert len(json.loads(payload(2000, "json"))) == 2000
    with pytest.raises(ValueError):
        run(sizes=[2001])


def test_incidence_reconstruction_preserves_event_roles_and_no_binary_projection():
    records = {"e": dict(id="e", kind="RelationEvent", evidence_id="ev", chunk_id="ch",
                         participants=[dict(role="provider", entity_id="a"),
                                       dict(role="item", entity_id="b"),
                                       dict(role="recipient", entity_id="c")])}
    edges = incidence(records)
    assert len(edges) == 5
    assert not any(edge[2] == "RELATES" for edge in edges)
    assert {edge[4] for edge in edges if edge[2] == "HAS_PARTICIPANT"} == {"provider", "item", "recipient"}


@pytest.mark.integration
def test_real_conversion_audit_reconnect_and_evidence():
    if not os.getenv("UGI_TEST_REDIS_URL"):
        pytest.skip("Requires actual FalkorDB")
    report = audit(ROOT / "evaluation/c_development.json", backend="falkordb", limit=2)
    assert report["retrieval_consistent"] and report["retrieval_checks"] > 0
    assert report["evidence"]["exact"] == report["evidence"]["emitted"]
