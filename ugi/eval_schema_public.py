"""New fixed public source probe; directed-pair screening is NOT predicate F1."""
import argparse
import json
import os
import random
import urllib.request
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from .engine import Engine
from .eval_fewrel import VALIDATION_URL, _name
from .models import Settings, key, now, uid
from .store import Store

ARCHIVE_HASH="76bb44c2485b6faed358a3ce040eadafcc8a8835245cd7e6afc1bef672d4a0bf"
SELECTION_HASH="c093a5468439a7b9a4aa3c84e694de2f2e88bdc1c52cea5ae2b6525ef2af571c"


def choose(raw, root, count=32):
    if sha256(raw).hexdigest() != ARCHIVE_HASH:
        raise ValueError("Upstream frozen FewRel hash changed")
    data=json.loads(raw)
    excluded=set()
    # Reproduce the earlier seed17 stratified128 selection without executing
    # extraction or seeing any new evaluation prediction.
    rng=random.Random(17)
    groups={}
    for pid,entries in sorted(data.items()):
        entries=list(entries)
        rng.shuffle(entries)
        groups[pid]=entries
    old=[groups[p][i] for i in range(7) for p in sorted(groups)][:128]
    excluded.update(key(" ".join(item["tokens"])) for item in old)
    # Exclude all text fields in previously recorded evaluation JSON, including
    # development/frozen queues. No labels enter the resolver.
    def visit(value):
        if isinstance(value,dict):
            if isinstance(value.get("text"),str):
                excluded.add(key(value["text"]))
            for child in value.values():
                visit(child)
        elif isinstance(value,list):
            for child in value:
                visit(child)
    for path in sorted(root.glob("*.json")):
        visit(json.loads(path.read_text(encoding="utf-8")))
    eligible=[(pid,item) for pid,entries in sorted(data.items()) for item in entries
              if key(" ".join(item["tokens"])) not in excluded]
    selected=random.Random(20261017).sample(eligible,count)
    return selected,len(excluded)


def frozen_sources(raw, root, path):
    if sha256(raw).hexdigest()!=ARCHIVE_HASH:
        raise ValueError("Upstream frozen FewRel hash changed")
    if not path.exists():
        chosen,excluded=choose(raw,root)
        source=dict(version=1,source_url=VALIDATION_URL,upstream_sha256=ARCHIVE_HASH,seed=20261017,
            excluded_texts=excluded,
            attribution="FewRel (Han et al., EMNLP2018), CC BY-SA4.0; token-joined excerpts, selection and UGI metadata added.",
            annotation="Upstream classification notes only; complete source-entailment labels absent. Now inspected; never unseen for future tuning.",
            cases=[dict(pid=pid,text=" ".join(item["tokens"]),head=_name(item["h"]),tail=_name(item["t"]),
                        source_sha256=sha256(" ".join(item["tokens"]).encode()).hexdigest(),
                        annotation_status="unreviewed",complete=False) for pid,item in chosen])
        source["content_hash"]=uid(source["cases"])
        path.write_text(json.dumps(source,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    source=json.loads(path.read_text(encoding="utf-8"))
    if source["upstream_sha256"]!=ARCHIVE_HASH or uid(source["cases"])!=source["content_hash"]:
        raise ValueError("Frozen public source manifest changed")
    if (len(source["cases"])!=32 or uid([c["source_sha256"] for c in source["cases"]])!=SELECTION_HASH
            or any(c["annotation_status"]!="unreviewed" or c["complete"] for c in source["cases"])):
        raise ValueError("Frozen public sample/annotation declaration changed")
    upstream={(pid," ".join(item["tokens"]),_name(item["h"]),_name(item["t"])):item
              for pid,items in json.loads(raw).items() for item in items}
    selected=[]
    for case in source["cases"]:
        if sha256(case["text"].encode()).hexdigest()!=case["source_sha256"]:
            raise ValueError("Public source text hash mismatch")
        selected.append((case["pid"],upstream[(case["pid"],case["text"],case["head"],case["tail"])]))
    return selected,source["excluded_texts"]


def evaluate(raw,root,sources_path=None):
    selected,excluded=frozen_sources(raw,root,sources_path) if sources_path else choose(raw,root)
    results=[]
    for enabled in (False,True):
        cfg=Settings(open_predicates=enabled,provider="offline",allow_paid_calls=False,
            redis_url=os.getenv("UGI_TEST_REDIS_URL","redis://127.0.0.1:6380/0"),graph_prefix="ugi_gpub_"+uuid4().hex[:8])
        cases=[]
        for index,(pid,item) in enumerate(selected):
            text=" ".join(item["tokens"])
            graph=Store(cfg,dataset=str(index))
            try:
                started=perf_counter()
                Engine(graph).ingest("public.txt",text.encode(),source_attribution=dict(
                    source_url=VALIDATION_URL,title="FewRel Wikipedia validation — Han et al., EMNLP2018",
                    locator=pid+"/sha256:"+sha256(text.encode()).hexdigest(),licence="CC-BY-SA-4.0",
                    note="Token-joined upstream source. PID/head/tail annotations are grading notes, not extraction input."))
                elapsed_ms=(perf_counter()-started)*1000
                claims,events=graph.claims(),graph.events()
                head,tail=_name(item["h"]),_name(item["t"])
                hit=any(key(c["subject"])==key(head) and key(c["object"])==key(tail) for c in claims)
                quotes=all(graph.get(r["chunk_id"])["text"][graph.get(r["evidence_id"])["start"]:
                    graph.get(r["evidence_id"])["end"]] == graph.get(r["evidence_id"])["quote"] for r in [*claims,*events])
                cases.append(dict(source_sha256=sha256(text.encode()).hexdigest(),upstream_pid=pid,
                    directed_pair_hit=hit,claims=len(claims),events=len(events),exact_quotes=quotes,
                    quotation_spans_checked=len(claims)+len(events),abstained=not claims and not events,
                    ingest_ms=round(elapsed_ms,3),model_calls=0,
                    semantic_scores=dict(exact_binary_matches=None,whole_event_matches=None,missing_relations=None,
                        unsupported_predictions=None,canonicalization_errors=None,qualifier_errors=None),
                    score_status="UNSCORED: no complete independently reviewed source-entailment annotations"))
            finally:
                assert graph.graph.startswith(cfg.graph_prefix+"_")
                graph.client.execute_command("GRAPH.DELETE",graph.graph)
        results.append(dict(open_enabled=enabled,cases=cases,directed_pair_hits=sum(c["directed_pair_hit"] for c in cases),
                            claims=sum(c["claims"] for c in cases),events=sum(c["events"] for c in cases),
                            abstentions=sum(c["abstained"] for c in cases),
                            quotation_spans_checked=sum(c["quotation_spans_checked"] for c in cases),
                            all_quotes=all(c["exact_quotes"] for c in cases)))
    return dict(recorded_at=now(),source_url=VALIDATION_URL,upstream_sha256=ARCHIVE_HASH,
        seed=20261017,selected_count=len(selected),excluded_texts=excluded,
        selection_hash=uid([sha256(" ".join(item["tokens"]).encode()).hexdigest() for _,item in selected]),
        backend="actual FalkorDB",results=results,model_calls=0,
        limitations=["Fixed new sample excludes prior seed17_128 and recorded text fields; no article-level independence proof",
                     "Upstream human relation classification labels are not exhaustive source-entailment annotations",
                     "Directed-pair hits may have wrong predicates; NOT precision/recall/F1 or semantic accuracy",
                     "No rule tuning to these outputs; now inspected, not unseen for future tuning",
                     "CC BY-SA4.0 FewRel (Han et al., EMNLP2018); report retains hashes/counts not excerpts"])


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--download",action="store_true")
    mode.add_argument("--input",type=Path)
    parser.add_argument("--sources",type=Path,default=Path("evaluation/g_public_sources_v1.json"))
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if args.download:
        with urllib.request.urlopen(VALIDATION_URL,timeout=45) as response:
            raw=response.read(15*1024*1024+1)
    else:
        raw=args.input.read_bytes()
    if len(raw)>15*1024*1024:
        raise ValueError("Public download budget exceeded")
    result=evaluate(raw,Path("evaluation"),args.sources)
    args.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps([{k:r[k] for k in ("open_enabled","directed_pair_hits","claims","events","all_quotes")} for r in result["results"]]))
