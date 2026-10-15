"""External benchmark adapter tests without network or AWS calls."""
import json

import pytest

from ugi.eval_fewrel import run


def tiny():
    return json.dumps({
        "P1": [
            {"tokens": ["Alice", "owns", "Acme", "."],
             "h": ["Alice", "Q1", [[0]]], "t": ["Acme", "Q2", [[2]]]},
            {"tokens": ["Iris", "owns", "Juniper", "."],
             "h": ["Iris", "Q3", [[0]]], "t": ["Juniper", "Q4", [[2]]]}
        ],
        "P2": [
            {"tokens": ["Orion", "depends", "on", "Pegasus", "."],
             "h": ["Orion", "Q5", [[0]]], "t": ["Pegasus", "Q6", [[3]]]}
        ]
    }).encode()


def test_external_benchmark_pair_not_relation_label():
    r = run(tiny(), limit=3, seed=17)
    assert r["sampled"] == 3 and r["available_pids"] == 2
    assert r["head_tail_directed_pair_hits"] == 3
    assert r["directed_pair_rate"] == 1.0
    assert r["samples_with_any_claim"] == 3
    assert r["surface_present"] == 3
    assert r["reverse_pair_hits"] == 0
    assert r["evidence_span"]["correct"] == r["evidence_span"]["checked"]
    assert r["model_calls"] == r["external_paid_calls"] == 0
    assert not any(k in r for k in ("precision", "recall", "f1"))


def test_external_benchmark_reproducible_fixed_seed():
    a = run(tiny(), limit=2, seed=17)
    b = run(tiny(), limit=2, seed=17)
    assert a["samples"] == b["samples"]
    assert a["sha256"] == b["sha256"]


def test_external_benchmark_direction_matters():
    wrong = {"P2": [{
        "tokens": ["Acme", "owns", "Alice", "."],
        "h": ["Alice", "Q1", [[2]]], "t": ["Acme", "Q2", [[0]]]
    }]}
    r = run(json.dumps(wrong).encode(), limit=1)
    assert r["head_tail_directed_pair_hits"] == 0
    assert r["reverse_pair_hits"] == 1


def test_external_benchmark_rejects_bad_samples():
    with pytest.raises(ValueError, match="Limit"):
        run(tiny(), limit=0)
    with pytest.raises(ValueError, match="tokens"):
        run(json.dumps({"P1": [{"tokens": 42, "h": ["Alice"], "t": ["Acme"]}]}).encode())
    with pytest.raises(ValueError, match="head/tail"):
        run(json.dumps({"P1": [{"tokens": ["Alice", "owns", "Acme"], "h": [],
                                "t": ["Acme"]}]}).encode())
