"""Guarded source patch that fixes contradicting resolution metadata for proven rules.

No data mutation, no production write. Fails closed if UGI branch structure differs.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

PATCH_VERSION = 'ugi-rule-resolution-consistency-v2'
ANCHORS = {
    'dependency_reachability_v1': 'return {**base, "status": "RULE_DERIVED", "rules": ["dependency_reachability_v1"],',
    'shared_employer_temporal_overlap_v1': '"rules": ["shared_employer_temporal_overlap_v1"],',
}
TAGS = {
    'dependency_reachability_v1': '"assessment": "RULE_DERIVED_FROM_DEPENDENCIES"',
    'shared_employer_temporal_overlap_v1': '"assessment": "RULE_DERIVED_SHARED_EMPLOYER"',
}


def digest(s: str) -> str:
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def patch_text(original: str) -> tuple[str, dict]:
    text = original
    changed = []
    already = []
    for name, anchor in ANCHORS.items():
        marker = TAGS[name]
        if text.count(anchor) != 1:
            raise ValueError(f'Refusing patch: expected one {name} branch, saw {text.count(anchor)}')
        pos = text.index(anchor)
        near = text[pos:pos + 1350]
        if marker in near:
            already.append(name)
            continue
        if name == 'dependency_reachability_v1':
            body = '''\n                    "resolution": {**(base.get("resolution") or {}),
                                   "assessment": "RULE_DERIVED_FROM_DEPENDENCIES",
                                   "missing_evidence": [],
                                   "proof_claim_ids": [c["id"] for c in proof["claims"]],
                                   "recommended_action": "Check operational telemetry before claiming an outage",
                                   "safety_note": "Indirect dependency is supported by source claims; no outage or causation is proven"},'''
        else:
            body = '''\n                        "resolution": {**(base.get("resolution") or {}),
                                       "assessment": "RULE_DERIVED_SHARED_EMPLOYER",
                                       "missing_evidence": [],
                                       "proof_claim_ids": [c["id"] for c in shared["claims"]],
                                       "recommended_action": "Require separate direct evidence for personal relationships",
                                       "safety_note": "Overlapping source employment does not establish friendship or collaboration"},'''
        text = text.replace(anchor, anchor + body, 1)
        changed.append(name)
    compile(text, '<patched_ugi_engine>', 'exec')
    return text, {'patch_version': PATCH_VERSION, 'original_sha256': digest(original),
                  'patched_sha256': digest(text), 'changed': changed, 'already_patched': already,
                  'safe_to_infer_real_outage': False}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--receipt', type=Path)
    a = p.parse_args()
    if a.input.resolve() == a.output.resolve():
        raise SystemExit('Refusing in-place patch; source must remain unchanged')
    original = a.input.read_text(encoding='utf-8')
    patched, receipt = patch_text(original)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(patched, encoding='utf-8')
    if a.receipt:
        a.receipt.parent.mkdir(parents=True, exist_ok=True)
        a.receipt.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt))

if __name__ == '__main__':
    main()
