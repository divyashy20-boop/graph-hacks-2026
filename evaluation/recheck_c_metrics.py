"""Independent arithmetic check of recorded C outputs; does not certify labels.

Intentionally does not import UGI scoring/signature helpers or invoke a model.
"""
import json
import math
import re
from pathlib import Path


def signature(item):
    canonical = re.sub(r"[^\w]+", "_", item["predicate"].strip()).upper()
    canonical = {"OWN": "OWNS", "USE": "USES"}.get(canonical, canonical)
    return (item["subject"].strip().casefold(), canonical,
            item["object"].strip().casefold(), item.get("polarity", "positive"),
            item.get("modality", "asserted"))


def recheck():
    root = Path(__file__).parent
    fixture = json.loads((root / "c_development.json").read_text(encoding="utf-8"))
    labels = {c["id"]: c for c in fixture["cases"]}
    output = {}
    for name in ("c_baseline", "c_development_final", "c_qwen_baseline", "c_qwen_final"):
        report = json.loads((root / (name + ".json")).read_text(encoding="utf-8"))
        subsets = {}
        for subset in ("all_complete", "public_complete"):
            gold, predicted = set(), set()
            for row in report["per_case"]:
                case = labels[row["id"]]
                if not case["complete"] or case["annotation_status"] == "unreviewed":
                    continue
                if subset == "public_complete" and not case["source_url"].startswith("https://"):
                    continue
                gold.update((case["id"], signature(c)) for c in case.get("binary", []))
                predicted.update((case["id"], signature(c)) for c in row["claims"])
            tp = len(gold & predicted)
            subsets[subset] = dict(tp=tp, predicted=len(predicted), gold=len(gold),
                                   f1=2*tp/(len(gold)+len(predicted)) if gold or predicted else 0)
        actual = subsets["all_complete"]
        expected = report["metrics"]["binary"]
        assert all(actual[k] == expected[k] for k in ("tp", "predicted", "gold")), (name, actual, expected)
        assert math.isclose(actual["f1"], expected["f1"], abs_tol=1e-12), (name, actual, expected)
        output[name] = subsets
    return dict(scope="Arithmetic only; provisional AI labels, not independent human accuracy",
                results=output)


if __name__ == "__main__":
    print(json.dumps(recheck(), indent=2))
