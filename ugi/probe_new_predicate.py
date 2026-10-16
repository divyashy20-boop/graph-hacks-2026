"""Source-selected exact clause probe; never an independent accuracy benchmark."""
import argparse
import json
from pathlib import Path

from .engine import Engine
from .models import Settings, now
from .schema import SchemaRuntime
from .store import Store


def run(fixture,dataset):
    cfg=Settings(open_predicates=True,provider="offline",allow_paid_calls=False)
    graph=Store(cfg,dataset=dataset)
    attribution={k:fixture[k] for k in ("source_url","title","locator","licence")}
    attribution["note"]=fixture["context"]+"\n"+fixture["limits"]
    report=Engine(graph).ingest("public-exact-clause.txt",fixture["text"].encode(),source_attribution=attribution)
    reader=Store(cfg,dataset=dataset)
    claims=[c for c in reader.claims() if c["source_id"]==report["source_id"]]
    matching=[c for c in claims if (c["subject"],c["original_predicate"],c["object"])==
              (fixture["expected_subject"],fixture["expected_phrase"],fixture["expected_object"])]
    assert len(matching)==1
    claim=matching[0]
    binding=reader.get(claim["schema_binding_id"])
    definition=reader.get(binding["predicate_definition_id"])
    assert definition["semantic_state"]=="PROVISIONAL" and binding["state"]=="PROVISIONAL_NEW"
    assert SchemaRuntime(reader).assertions(definition["id"])["items"]
    assert reader.get(claim["evidence_id"])["quote"]==fixture["text"]
    full=Engine(graph).ingest("public-full-context.txt",fixture["context"].encode(),source_attribution=attribution)
    return dict(recorded_at=now(),dataset=dataset,backend="actual FalkorDB",source=attribution,
                report=report,claim=claim,binding=binding,definition=definition,reconnected=True,
                full_context_report=full,model_calls=0,annotation=fixture["annotation"],
                limitations=[fixture["limits"],"This is an independently sourced expression, not independently adjudicated accuracy",
                             "No predicate-specific code was added for this phrase; no tuning to full-context output"])


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute",action="store_true",required=True)
    parser.add_argument("--fixture",type=Path,default=Path("evaluation/g_novel_public_clause.json"))
    parser.add_argument("--dataset",default="showcase-g-public-clause")
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if len(args.dataset)>60 or not args.dataset.replace("-","").replace("_","").isalnum():
        raise ValueError("Invalid dataset")
    result=run(json.loads(args.fixture.read_text(encoding="utf-8")),args.dataset)
    args.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(dict(exact_clause_claims=result["report"]["claims"],
                         full_context_claims=result["full_context_report"]["claims"],
                         state=result["binding"]["state"],reconnected=result["reconnected"])))
