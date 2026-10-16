"""Independent arithmetic only: no engine, resolver or evaluator imports."""
import json
from pathlib import Path

ROOT = Path(__file__).parent


def read(name):
    return json.loads((ROOT/name).read_text(encoding="utf-8"))


def main():
    fixture = {c["id"]: c for c in read("identity_cases_v1.json")["cases"]}
    report = read("f_policy_identity_final.json")
    positive = [r for r in report["results"] if fixture[r["id"]]["expected"] == "SAME_ENTITY"]
    negative = [r for r in report["results"] if fixture[r["id"]]["expected"] != "SAME_ENTITY"]
    tp = sum(r["decision"] == "SAME_ENTITY" for r in positive)
    fp = sum(r["decision"] == "SAME_ENTITY" for r in negative)
    assert (tp, tp+fp, len(positive)) == tuple(report["metrics"][k] for k in ("tp", "predicted", "gold"))
    assert report["metrics"]["f1"] == 2*tp/(tp+fp+len(positive))
    clusters = {c["id"]: c for c in read("identity_clusters_v1.json")["cases"]}
    observed = read("f_cluster_evaluation_final.json")
    detected_tp = detected_fp = splits = false_splits = 0
    for row in observed["results"]:
        label = clusters[row["id"]]
        detected_tp += row["detected"] and label["inconsistent"]
        detected_fp += row["detected"] and not label["inconsistent"]
        expected = sorted(sorted(row["mention_ids"][i] for i in g) for g in label["partition"]) if label["partition"] else None
        assert row["partition_correct"] == (row["proposed_groups"] == expected)
        splits += row["applied"] and expected is not None and row["proposed_groups"] == expected
        false_splits += row["applied"] and expected is None
    assert (detected_tp, detected_fp, splits, false_splits) == tuple(observed["metrics"][k] for k in
        ("detection_tp", "detection_fp", "correct_splits", "false_splits"))
    public = read("f_public_t2d_frozen.json")
    gold = sum(r["gold_match"] for r in public["outputs"])
    public_tp = sum(r["gold_match"] and r["decision"] == "SAME_ENTITY" for r in public["outputs"])
    public_fp = sum(not r["gold_match"] and r["decision"] == "SAME_ENTITY" for r in public["outputs"])
    assert (gold, public_tp, public_fp) == (public["gold_matches"], public["tp"], public["fp"])
    assert public["precision"] is None and public_tp+public_fp == 0
    print(json.dumps(dict(scope="Arithmetic/fixture consistency only, not independent annotation or identity truth",
                         synthetic_matches=dict(tp=tp, fp=fp, gold=len(positive)),
                         synthetic_clusters=dict(tp=detected_tp, fp=detected_fp, splits=splits, false_splits=false_splits),
                         public=dict(tp=public_tp, fp=public_fp, gold=gold, precision=None)), indent=2))


if __name__ == "__main__":
    main()
