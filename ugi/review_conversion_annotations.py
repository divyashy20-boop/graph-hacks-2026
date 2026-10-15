"""Validate a human-edited evaluation derivative without rewriting its original freeze.

This records reviewer declarations, not independent certification. Never adds
reviewer names or changes unreviewed labels to human-reviewed automatically.
"""
import argparse
import json
from pathlib import Path

from .conversion_audit import AuditSuite, check_splits, digest


def promote(edited, original, development, output):
    reviewed = AuditSuite.model_validate_json(edited.read_bytes())
    reserved = AuditSuite.model_validate_json(original.read_bytes())
    dev = AuditSuite.model_validate_json(development.read_bytes())
    by_id = {c.id: c for c in reserved.cases}
    if set(by_id) != {c.id for c in reviewed.cases}:
        raise ValueError("A derivative must preserve original case IDs")
    if not any(c.annotation_status == "human_reviewed" for c in reviewed.cases):
        raise ValueError("No human review declarations; retain the unreviewed freeze")
    for case in reviewed.cases:
        original_case = by_id[case.id]
        fields = ("text", "source_url", "source_sha256", "licence", "licence_url",
                  "source_title", "source_locator")
        if any(getattr(case, f) != getattr(original_case, f) for f in fields):
            raise ValueError("Reviewed derivative must preserve source text and provenance")
    check_splits(dev, reviewed)
    if any((output / name).exists() for name in ("c_evaluation.json", "c_manifest.json")):
        raise ValueError("Never overwrite an existing freeze")
    output.mkdir(parents=True, exist_ok=True)
    data = json.loads(edited.read_text(encoding="utf-8"))
    manifest = dict(version="c-reviewed-derivative-v1", evaluation_sha256=digest(data),
                    original_evaluation_sha256=digest(json.loads(original.read_text(encoding="utf-8"))),
                    development_sha256=digest(json.loads(development.read_text(encoding="utf-8"))),
                    policy="Human reviewer metadata is self-reported; original source freeze preserved")
    (output / "c_evaluation.json").write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    (output / "c_manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edited", type=Path, required=True)
    parser.add_argument("--original", type=Path, default=Path("evaluation/c_evaluation.json"))
    parser.add_argument("--development", type=Path, default=Path("evaluation/c_development.json"))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(promote(args.edited, args.original, args.development, args.output_dir), indent=2))


if __name__ == "__main__":
    main()
