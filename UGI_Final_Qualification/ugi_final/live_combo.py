"""Disposable actual UGI FalkorDB + MCP ↔ P5 sidecar qualification.

Run only inside the user's existing UGI Docker api container, with graph URL
pointing to its existing FalkorDB. Creates NEW graph names; never alters prior
UGI namespaces. The sidecar is an isolated SQLite file under /tmp.
"""
from __future__ import annotations
import argparse
import json
import os
import tempfile
import time
import uuid
from datetime import date
from pathlib import Path
from p5memory.core import Memory, PolicyError
from ugi_krish_validation_v2.full_audit import MCPStdio
from ugi_real_track1.real_suite import prepare
from .bridge import track_and_register, refresh_receipt, BridgeError

DAY='2026-10-17'


def main(output: str) -> int:
    report={'version':'ugi-final-qualification-v1','backend':'UGI FalkorDB + MCP stdio + SQLite P5 sidecar',
            'graph_data':'SHA256-pinned Docker Compose source assertions transformed to structured JSON',
            'production_external_actions':False,'graph_mutations':'disposable namespaces only',
            'cases':[], 'limits':[
            'Not a production integration or atomic distributed graph+receipt transaction',
            'Graph writes outside the instrumented gateway are only detected on required fresh MCP reread',
            'No real external side effects; internal SQLite protected effects only',
            'No guarantee against a graph change AFTER reread without a coordinated lock/fence',
            'Receipts from MCP tool outputs; production restart durable registry still requires implementation',
            'Unstructured-language ingestion and actual incident causality not established']}
    def check(name,ok,detail=None):
        report['cases'].append({'name':name,'pass':bool(ok),'detail':detail or {}})
        print(('PASS' if ok else 'FAIL')+' COMBO: '+name,flush=True)
    try:
        synthetic={'results':[]}
        prepared,cfg,root,owner=prepare(synthetic,None)
        report['isolated_prefix']=root
        if len(prepared)!=5:raise RuntimeError('NOT_ALL_FIVE_GRAPHS_INGESTED')
        f=tempfile.NamedTemporaryFile(suffix='.sqlite3',prefix='ugi_final_receipts_',delete=False)
        f.close()
        memory=Memory(f.name)
        report['sidecar_store']=f.name
        source='flask-redis'; item=prepared[source]
        scope=f'{root}::{owner}::{source}'
        cli=MCPStdio(root,source,owner,cfg.redis_url)
        try:
            cli.request('initialize',{'protocolVersion':'2025-11-25','capabilities':{},
                        'clientInfo':{'name':'ugi-final-receipt-lab','version':'1'}})
            def track(query):
                return track_and_register(memory,cli,scope=scope,dataset=source,query=query,
                     entities=item['services'],day=DAY,
                     allowed_source_ids={item['source_id']})
            positive=track('Does web directly depend on redis?')
            neg=track('Does redis directly depend on web?')
            check('positive and negative real MCP investigations complete',
                  positive['outcome'].get('status')=='COMPLETE' and positive['outcome'].get('verdict')=='SOURCE_ASSERTED'
                  and neg['outcome'].get('status')=='COMPLETE' and neg['outcome'].get('verdict') in {'UNKNOWN','CONNECTED_ONLY'},
                  {'positive':positive['outcome'].get('verdict'),'negative':neg['outcome'].get('verdict')})
            check('automatic all-read capture and valid receipts',
                  positive['receipt'] is not None and neg['receipt'] is not None and
                  len(positive['observations'])>=4 and len(neg['observations'])>=3 and
                  memory.receipt(positive['receipt']['rid'])['status']=='VALID',
                  {'captured_positive_tools':len(positive['observations']),'captured_negative_tools':len(neg['observations'])})
            # A new source assertion fills previously absent reverse dependency.
            rows=[{'subject':'redis','subject_type':'Service','subject_id':'github:docker/awesome-compose:flask-redis:redis',
                    'predicate':'depends on','object':'web','object_type':'Service',
                    'object_id':'github:docker/awesome-compose:flask-redis:web',
                    'source_url':'urn:ugi-final-disposable-reverse-edge-test'}]
            ing=item['engine'].ingest('FINAL_QUAL_REVERSE_'+uuid.uuid4().hex+'.json',json.dumps(rows).encode())
            new_src=ing.get('source_id')
            check('new directed edge ingested into actual isolated UGI graph',
                  ing.get('claims',0)>=1 and new_src and new_src!=item['source_id'],
                  {'new_claims':ing.get('claims'), 'source_id':new_src})
            change=refresh_receipt(memory,cli,scope=scope,receipt={**neg['receipt'],
                                    'observations':neg['observations']},day=DAY)
            check('new graph edge invalidates old negative conclusion',
                  change['changed']>=1 and memory.receipt(neg['receipt']['rid'])['status']=='STALE',change)
            try:
                memory.protected_action(neg['receipt']['rid'],scope,'stale-negative-action',{'task':'consume old missing-dependency answer'},valid_at=DAY)
                blocked=False
            except PolicyError as exc:
                blocked='BLOCKED_' in str(exc)
            check('stale real-graph answer denied by internal action gate',blocked,
                  {'effects':memory.effect_count(scope)})
            pcheck=refresh_receipt(memory,cli,scope=scope,receipt={**positive['receipt'],
                                   'observations':positive['observations']},day=DAY)
            # IMPORTANT: `changed` is the number of new events written by THIS
            # refresh, NOT the number of original receipt reads that differ.
            # The negative answer's earlier refresh can update shared entity
            # lookups and invalidate this positive receipt before we reread it.
            # Read-set fingerprints are compared to the ORIGINAL sealed snapshot.
            positive_status=memory.receipt(positive['receipt']['rid'])['status']
            diff=pcheck['original_read_difference_count']
            check('unrelated receipt status matches observed read-set changes',
                  (diff==0 and positive_status=='VALID') or
                  (diff>0 and positive_status in {'STALE','UNKNOWN'}),
                  {'status':positive_status,'new_events_in_this_refresh':pcheck['changed'],
                   'original_read_difference_count':diff,
                   'original_read_difference_keys':pcheck['original_read_difference_keys']})
            # Real UGI contradiction: an explicit opposing declaration, not merely
            # a synthetic SQLite conflict. It must invalidate the existing receipt
            # as UNKNOWN, and the internal-action gate must refuse it.
            negative_row=[{'subject':'web','subject_type':'Service',
                'subject_id':'github:docker/awesome-compose:flask-redis:web',
                'predicate':'depends on','object':'redis','object_type':'Service',
                'object_id':'github:docker/awesome-compose:flask-redis:redis',
                'polarity':'negative','source_url':'urn:ugi-final-disposable-contradiction'}]
            conf=item['engine'].ingest('FINAL_QUAL_OPPOSING_'+uuid.uuid4().hex+'.json',
                                         json.dumps(negative_row).encode())
            check('actual UGI opposing source assertion ingested',
                  conf.get('claims',0)>=1,{'claims':conf.get('claims')})
            conflict_change=refresh_receipt(memory,cli,scope=scope,
                receipt={**positive['receipt'],'observations':positive['observations']},day=DAY)
            check('actual UGI CONTRADICTED verdict becomes UNKNOWN receipt',
                  memory.receipt(positive['receipt']['rid'])['status']=='UNKNOWN',conflict_change)
            try:
                memory.protected_action(positive['receipt']['rid'],scope,'unknown-conflict-action',
                     {'test':'must block'},valid_at=DAY)
                conflict_blocked=False
            except PolicyError as exc:
                conflict_blocked='BLOCKED_' in str(exc)
            check('conflicted real-graph conclusion blocked at internal gate',conflict_blocked,
                  {'effect_count':memory.effect_count(scope)})
            # Existing VALID receipts can feed dependent agents. Track propagation after change.
            source2='nginx-flask-mysql'; item2=prepared[source2]
            scope2=f'{root}::{owner}::{source2}'
            cli2=MCPStdio(root,source2,owner,cfg.redis_url)
            try:
                cli2.request('initialize',{'protocolVersion':'2025-11-25',
                    'capabilities':{},'clientInfo':{'name':'ugi-final','version':'1'}})
                initial=track_and_register(memory,cli2,scope=scope2,dataset=source2,
                     query='Does proxy indirectly depend on db?',entities=item2['services'],
                     day=DAY,allowed_source_ids={item2['source_id']})
                parent=initial['receipt']['rid']
                rd=memory.open_read(scope2,DAY)
                child=rd.seal({'downstream':'agent-B'},parents=(parent,))
                rd=memory.open_read(scope2,DAY)
                grand=rd.seal({'downstream':'agent-C'},parents=(child['rid'],))
                # Alter a tool-observed supporting claim (new positive reverse edge may change
                # a result, but for guaranteed path change add a contradictory assertion).
                # Sidecar mutation here exercises cross-agent invalidation independently
                # of UGI's own historical claim-reconciliation semantics.
                one=next(iter(initial['observations'].items()))
                memory.publish(scope2,one[0],'/result',{'changed':'deliberate upstream observed data'},
                               source='ugi-mcp-observed',valid_from=DAY)
                check('real-MCP-derived receipt cascades through two agent outputs',
                    [memory.receipt(x)['status'] for x in (parent,child['rid'],grand['rid'])]==['STALE']*3,
                    {'dependent_count':len(memory.dependents(parent))})
            finally:cli2.close()
            check('no external actions and all preview/write gates disabled',
                  memory.effect_count(scope)==0 and memory.effect_count(scope2)==0)
        finally:cli.close()
    except Exception as exc:
        report['fatal_error']=type(exc).__name__+': '+str(exc)[:350]
        check('live-combined-experiment-infrastructure',False,{'error':report['fatal_error']})
    report['passed']=sum(int(c['pass']) for c in report['cases'])
    report['total']=len(report['cases'])
    report['status']='PASS' if report['cases'] and report['passed']==report['total'] else 'FAIL'
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    Path(output).write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print('LIVE COMBINED',report['status'],report['passed'],'/',report['total'],'REPORT',output,flush=True)
    return 0 if report['status']=='PASS' else 1

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True)
    a=p.parse_args();raise SystemExit(main(a.output))
