from __future__ import annotations

import json

from benchmarks.groq_tournament import (
    EXPECTED_BASELINE,
    MODEL,
    GroqTournamentMeter,
    duration_seconds,
    quality_gate,
    verify_baseline,
)


def test_duration_parser_accepts_groq_reset_formats():
    assert duration_seconds("250ms") == 0.25
    assert duration_seconds("7.5s") == 7.5
    assert duration_seconds("2m") == 120
    assert duration_seconds("bad") is None


def test_saved_baseline_values_are_strictly_verified(tmp_path):
    whole = {
        "setting": "whole_compact", "extraction_score": 54.515,
        "accepted_total": 6, "evidence_exact": 6, "reference_pair_hits": 3,
        "query_visible": 5, "claim_queries": 6,
    }
    split = {"setting": "split_context", "extraction_score": 52.015}
    report = {"results": [
        {"name": "Qwen3 32B", "extraction": [whole, split],
         "qa_reference": {"correct": 12}, "qa_own_graph": {"correct": 7}},
        {"name": "Claude Haiku 4.5",
         "extraction": [{"setting": "whole_compact", "extraction_score": 55.23}]},
    ]}
    path = tmp_path / "original.json"
    path.write_text(json.dumps(report))
    assert verify_baseline(path) == EXPECTED_BASELINE


def test_checkpoint_cache_replays_without_network(tmp_path):
    prompt = "frozen prompt"
    key = GroqTournamentMeter.cache_key(prompt, 2250, "graph_creation")
    checkpoint = tmp_path / "checkpoint.json"
    checkpoint.write_text(json.dumps({
        "version": 1, "model": MODEL["id"], "attempts": [],
        "responses": {key: {
            "status": "COMPLETE", "output": '{"relations":[],"events":[]}',
            "finish_reason": "stop", "usage": {"prompt_tokens": 5, "completion_tokens": 7},
            "latency_s": 1.25,
        }},
    }))
    meter = GroqTournamentMeter("not-used", checkpoint)
    output, finish = meter.call(MODEL, prompt, 2250, "graph_creation")
    assert json.loads(output) == {"relations": [], "events": []}
    assert finish == "stop" and meter.events[0]["status"] == "CACHED_COMPLETE"


def test_quality_gate_requires_all_safety_and_accuracy_controls():
    variant = {
        "setting": "whole_compact", "status": "COMPLETE", "extraction_score": 54.515,
        "accepted_total": 6, "evidence_exact": 6, "reference_pair_hits": 3,
    }
    cases = [{"citations_valid": True}] * 12
    report = {
        "groq": {
            "extraction": [variant, {"setting": "split_context", "status": "COMPLETE"}],
            "qa_reference": {"correct": 12, "total": 12, "negative_correct": 4,
                             "cases": cases},
            "qa_own_graph": {"correct": 7, "total": 12, "negative_correct": 4,
                             "cases": cases},
        },
        "controls": {"question_count": 28, "passed": 28, "p5": {
            "passes": True, "unsafe_abstained": True,
            "negative_receipt_reuse_blocked": True,
        }},
    }
    assert quality_gate(report)["verdict"] == "PASS"
    report["groq"]["qa_own_graph"]["negative_correct"] = 3
    assert quality_gate(report)["verdict"] == "FAIL"
