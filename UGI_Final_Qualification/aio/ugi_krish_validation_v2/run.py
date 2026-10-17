"""Read-only UGI adapter comparison: `python -m ugi_krish_validation_v2.run --mode offline`.

Live mode imports *your existing UGI checkout*, no modifications or extra deps.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from uuid import uuid4
from .analytics import projection, pagerank, components, shortest_path, MAX_NODES, MAX_CLAIMS
from .freshness import classify_freshness, inspect_ugi_artifact
from .planner import plan_readonly, actual_mcp_handler_probe


def fixture():
    ents = [{'id': x, 'kind': 'Entity', 'name': x} for x in ['Checkout', 'Gateway', 'Cache', 'Redis', 'Other']]
    def c(ident, s, p, o, **kw):
        return {'id': ident, 'kind': 'Claim', 'subject_id': s, 'predicate': p,
                'object_id': o, 'polarity': 'positive', 'modality': 'asserted', **kw}
    claims = [c('c1','Checkout','DEPENDS_ON','Gateway'),
              c('c2','Gateway','DEPENDS_ON','Cache'),
              c('c3','Cache','USES','Redis'),
              c('c4','Cache','USES','Redis',polarity='negative'),
              c('c5','Checkout','DEPENDS_ON','Other',modality='possible'),
              c('c6','Other','DEPENDS_ON','Cache',valid_from='2020-01-01',valid_to='2022-12-31')]
    return ents, claims


def report_for(entities, claims, start, end, as_of=None, allow_predicates=('DEPENDS_ON',), blocked_assertion_ids=()):
    view = projection(entities,claims,as_of,allow_predicates,blocked_assertion_ids)
    lookup={e['name']:e['id'] for e in entities}
    path = shortest_path(view, lookup.get(start,start), lookup.get(end,end))
    return {'view': {'included_count':view['included_count'], 'excluded':view['excluded'],
                     'max_nodes':MAX_NODES, 'max_claims':MAX_CLAIMS, 'allow_predicates':view['allow_predicates']},
            'shortest_path': path, 'pagerank':pagerank(view), 'weak_components':components(view),
            'meaning': 'Read-only analysis of selected assertions. Never proof of actual outages.'}


def offline():
    entities,claims = fixture()
    res = report_for(entities,claims,'Checkout','Cache')
    res['mode'] = 'offline_synthetic'
    res['tool_plan'] = plan_readonly('Cache','Checkout','Cache')
    res['stale_guard_demo'] = {
        'stale': classify_freshness({'kind':'DerivedArtifact'}, {'state':'stale','changed_mention_snapshot_ids':['ms1']}),
        'unchanged_identity':classify_freshness({'kind':'DerivedArtifact'}, {'state':'current_inputs_only'}),
        'unknown':classify_freshness(None)
    }
    return res


def live(dataset, start, end, target, artifact_id=None):
    from ugi.models import Settings
    from ugi.engine import Engine
    from .read_only_store import read_only_store
    settings = Settings()
    if settings.backend != 'falkordb':
        raise ValueError('Live mode requires existing FalkorDB backend; no in-memory substitution')
    store = read_only_store(settings, dataset=dataset)
    if not store.client:
        raise RuntimeError('FalkorDB not reachable')
    entity_rows=store.list('Entity', MAX_NODES+1)
    claim_rows=store.list('Claim', MAX_CLAIMS+1)
    if not entity_rows and not claim_rows:
        raise ValueError('Dataset empty. Seed ONLY your synthetic demo with `python -m ugi.demo --execute ...`, or select an existing dataset.')
    binding_rows=store.list('SchemaBinding',20000)
    if len(binding_rows)>=20000:
        raise ValueError('Schema binding read truncated; refusing unsafe analysis')
    blocked_ids={r.get('assertion_id') for r in binding_rows}
    result=report_for(entity_rows,claim_rows,start,end,blocked_assertion_ids=blocked_ids)
    result['excluded_schema_bound_assertion_ids']=len(blocked_ids)
    engine=Engine(store)
    before={'investigations':len(store.list('Investigation', 2000)),
            'tasks':len(store.list('ReviewTask',2000))}
    result['mcp_probe']=actual_mcp_handler_probe(engine,target,start,end)
    # Baseline is always the existing UGI preview. NO authorise_action.
    from ugi.models import InvestigationRequest
    result['ugi_baseline_preview']=engine.investigate(InvestigationRequest(target=target,idempotency_key='lab-readonly-'+uuid4().hex[:16],authorise_action=False),'integration-lab')
    after={'investigations':len(store.list('Investigation',2000)),
           'tasks':len(store.list('ReviewTask',2000))}
    result['db_action_counts_before']=before
    result['db_action_counts_after']=after
    result['no_agent_action_written']= before==after
    if before!=after:
        raise AssertionError('Read-only trial unexpectedly changed action counts')
    if artifact_id:
        result['freshness_guard']=inspect_ugi_artifact(store, artifact_id)
    else:
        result['freshness_guard']='not_tested: pass --artifact-id for an existing DerivedArtifact'
    result['mode']='live_read_only'
    result['graph_write_permission']='blocked_at_store_query_commit'
    result['snapshot_limit']='not transactionally isolated from concurrent writers'
    result['dataset']=dataset
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description='UGI / project1 / Track2 read-only integration comparison')
    p.add_argument('--mode', choices=['offline','live'],default='offline')
    p.add_argument('--dataset',default='showcase-b-incident')
    p.add_argument('--start',default='Checkout')
    p.add_argument('--end',default='Cache')
    p.add_argument('--target',default='Cache')
    p.add_argument('--artifact-id')
    p.add_argument('--output',default='ugi_krish_validation_v2/results/latest.json')
    a=p.parse_args(argv)
    r=offline() if a.mode=='offline' else live(a.dataset,a.start,a.end,a.target,a.artifact_id)
    dest=Path(a.output)
    if not dest.resolve().is_relative_to(Path.cwd().resolve()):
        raise ValueError('Report must be written inside the selected working directory')
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(r,indent=2,default=str,sort_keys=True),encoding='utf-8')
    print('RESULT:', 'PASS' if r['shortest_path'].get('found') else 'CHECK', '| mode:',r['mode'])
    print('eligible claims:',r['view']['included_count'],'| shortest path:',r['shortest_path'])
    print('report:',dest)
    return r


if __name__=='__main__':
    main()
