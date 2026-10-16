"""Standalone fixture arithmetic only; no UGI/scorer import or truth adjudication."""
import json
from pathlib import Path

root=Path(__file__).parent
fixture=json.loads((root/"g_open_development.json").read_text(encoding="utf-8"))
report=json.loads((root/"g2_development_final.json").read_text(encoding="utf-8"))
by_id={c["id"]:c for c in fixture["cases"]}
for result in report["results"]:
    true_positives=0
    event_cases=0
    for case in result["cases"]:
        gold=by_id[case["id"]]
        tp=len({tuple(p) for p in case["binary"]}&{tuple(p) for p in gold["binary"]})
        assert tp==case["binary_tp"]
        true_positives+=tp
        event_cases+=case["events"] == [sorted(e) for e in gold["events"]]
    assert true_positives==result["binary_tp"]
    assert event_cases==result["exact_event_cases"]
    assert sum(len(c["binary"]) for c in result["cases"])==result["predicted_binary"]
    assert sum(len(c["binary"]) for c in fixture["cases"])==result["expected_binary"]
public=json.loads((root/"g2_public_final.json").read_text(encoding="utf-8"))
for result in public["results"]:
    assert sum(c["directed_pair_hit"] for c in result["cases"])==result["directed_pair_hits"]
    assert len(result["cases"])==public["selected_count"]
    assert sum(c["abstained"] for c in result["cases"])==result["abstentions"]
    assert all(all(v is None for v in c["semantic_scores"].values()) for c in result["cases"])
sources=json.loads((root/"g_public_sources_v1.json").read_text(encoding="utf-8"))
assert [c["source_sha256"] for c in sources["cases"]]==[c["source_sha256"] for c in public["results"][0]["cases"]]
assert public["selection_hash"]==json.loads((root/"g2_public.json").read_text(encoding="utf-8"))["selection_hash"]
print("G development and public diagnostic arithmetic verified; not independent semantic truth.")
