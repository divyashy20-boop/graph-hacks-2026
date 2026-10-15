"""Build source-attributed, explicitly provisional/unreviewed audit partitions.

Run once BEFORE extraction changes. Refuse to overwrite a freeze; human edits
belong in a versioned derivative, not silent regeneration of evaluation gold.
"""
import argparse
import json
from hashlib import sha256
from pathlib import Path

from .conversion_audit import AuditSuite, check_splits, digest


def prepare(recipe, queue, output):
    files = [output / name for name in ("c_development.json", "c_evaluation.json", "c_manifest.json")]
    if any(p.exists() for p in files):
        raise ValueError("Refusing to overwrite existing audit freeze; choose a new directory/version")
    def case(raw, reviewed=False):
        row = dict(raw)
        row.setdefault("source_url", "synthetic://ugi/milestone-c/" + row["id"])
        synthetic = row["source_url"].startswith("synthetic://")
        row.setdefault("source_title", "AI-authored synthetic safety regression")
        row.setdefault("licence", "CC0-1.0" if synthetic else "US-Government-work")
        row.setdefault("licence_url", "https://creativecommons.org/publicdomain/zero/1.0/" if synthetic
                       else "https://www.usa.gov/government-copyright")
        row.setdefault("source_locator", "Entire stored excerpt; whitespace normalized from HTML")
        row["source_sha256"] = sha256(row["text"].encode()).hexdigest()
        row["annotation_status"] = "provisional" if reviewed else "unreviewed"
        row.setdefault("complete", reviewed)
        row["reviewers"] = []
        for label in row.get("binary", []) + row.get("events", []):
            label["evidence"] = row["text"]
        row["entity_spans"] = [dict(text=name, start=row["text"].index(name),
                                    end=row["text"].index(name) + len(name))
                               for name in row.get("entities", [])]
        return row
    dev = dict(split="development", scope=recipe["scope"],
               cases=[case(r, True) for r in recipe["development"]])
    reserved = [case(r) for r in recipe["reserved_public"]]
    # First four are already inspected model-development examples in Milestone B.
    for row in queue["cases"][4:]:
        reserved.append(case(dict(row, source_url="https://github.com/thunlp/FewRel/blob/master/data/val_wiki.json#" + row["id"],
                                  source_title="Han et al. (2018), FewRel Wikipedia validation excerpt",
                                  licence="CC-BY-SA-4.0", licence_url="https://thunlp.github.io/1/fewrel1.html",
                                  source_locator=row["notes"])))
    evaluation = dict(split="evaluation", scope=recipe["scope"], cases=reserved)
    check_splits(AuditSuite.model_validate(dev), AuditSuite.model_validate(evaluation))
    output.mkdir(parents=True, exist_ok=True)
    manifest = dict(version="c-freeze-v1", development_sha256=digest(dev),
                    evaluation_sha256=digest(evaluation), queue_provenance=queue["provenance"],
                    queue_cases=24, previously_inspected_queue_cases=4,
                    development_cases=len(dev["cases"]), evaluation_cases=len(reserved),
                    policy="No human-reviewed labels. Evaluation labels not used for development; "
                           "only run frozen split at explicit final checkpoint. Four-token shingle "
                           "containment >=0.65, repeated URLs/IDs/exact text rejected.")
    for path, data in zip(files, (dev, evaluation, manifest)):
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipe", type=Path, default=Path("evaluation/c_source_recipe.json"))
    parser.add_argument("--queue", type=Path, default=Path(".evaluation-local/fewrel_queue.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("evaluation"))
    args = parser.parse_args()
    print(json.dumps(prepare(json.loads(args.recipe.read_text(encoding="utf-8")),
                             json.loads(args.queue.read_text(encoding="utf-8")), args.output_dir), indent=2))


if __name__ == "__main__":
    main()
