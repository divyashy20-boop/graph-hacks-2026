"""Reproducible P5 demonstration and measurable acceptance report.
All data synthetic. Report labels deliberately distinguish internal atomic effects
from external side effects. Does not connect to FalkorDB or production services.
"""
import argparse
import json
import random
import tempfile
import time
from pathlib import Path
from . import Memory,PolicyError,ingest_json,ingest_python
D='2026-10-17'

def execute(report_path):
    cases=[]
    started=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='ugi_p5_') as workspace:
        db=Memory(Path(workspace)/'receipts.sqlite')
        scope='ugi-p5/synthetic-project'
        def add(name, actual, expected=True, details=None):
            cases.append({'case':name,'pass':actual==expected,'actual':actual,'expected':expected,'details':details or {}})
        def read(key,field,output='agent answer'):
            s=db.open_read(scope,D);s.read(key,field);return s.seal(output)
        def act(rid,label,day=D):
            try:
                db.protected_action(rid,scope,label,{'action':'internal_test_only'},valid_at=day)
                return 'EXECUTED'
            except PolicyError as e:
                if str(e).startswith('BLOCKED_'):return 'BLOCKED'
                raise
        # T1 CODE SIGNATURE CHANGED
        ingest_python(db,scope,'payments','def process_payment(amount):\n return amount',valid_from=D)
        rec=read('code:payments','function:process_payment','Call process_payment(amount)')
        ingest_python(db,scope,'payments','def process_payment(amount,currency,region):\n return amount',valid_from=D)
        add('T1 code signature changed => stale+blocked', (db.receipt(rec['rid'])['status'],act(rec['rid'],'t1')),('STALE','BLOCKED'))
        # T2 STRUCTURED JSON UNRELATED FIELD
        ingest_json(db,scope,'contract',{'expiry':'2027-01-01','note':'hello'},valid_from=D)
        rec=read('json:contract','/expiry','renew 2027')
        ingest_json(db,scope,'contract',{'expiry':'2027-01-01','note':'world'},valid_from=D)
        add('T2 unrelated field change => valid', db.receipt(rec['rid'])['status'],'VALID')
        # T3 NEGATIVE DEPENDENCY LOOKUP
        rec=read('edge:checkout->cache','depends_on','No dependency present')
        db.publish(scope,'edge:checkout->cache','depends_on',True,valid_from=D)
        add('T3 new graph edge invalidates old absence', (db.receipt(rec['rid'])['status'],act(rec['rid'],'t3')),('STALE','BLOCKED'))
        # T4 CONTRADICTIONS
        db.publish(scope,'supplier','region','EU',source='partner-1',valid_from=D)
        rec=read('supplier','region','Supplier EU region')
        db.publish(scope,'supplier','region','US',source='partner-2',valid_from=D)
        add('T4 opposing source assertions => unknown+blocked', (db.receipt(rec['rid'])['status'],act(rec['rid'],'t4')),('UNKNOWN','BLOCKED'))
        # T5 MULTIAGENT CASCADE
        db.publish(scope,'researcher','institution','University A',valid_from=D)
        root=read('researcher','institution','A affiliation')
        s=db.open_read(scope,D);s.read('other','field');second=s.seal('Agent B plan',parents=[root['rid']])
        s=db.open_read(scope,D);s.read('another','field');third=s.seal('Agent C downstream memo',parents=[second['rid']])
        db.publish(scope,'researcher','institution','University B',valid_from=D)
        add('T5 multi-agent dependency cascade',
            [db.receipt(r['rid'])['status'] for r in [root,second,third]], ['STALE','STALE','STALE'])
        # T6 TIME OF CHECK -> TIME OF USE
        db.publish(scope,'service','revision',1,valid_from=D)
        rec=read('service','revision','Deploy v1')
        before=db.receipt(rec['rid'])['status']
        db.publish(scope,'service','revision',2,valid_from=D)
        add('T6 stale action cannot reach internal effect', (before,act(rec['rid'],'t6')),('VALID','BLOCKED'))
        # T7 LATE VALID TIME
        db.publish(scope,'contract','expiry','2027-01-01',source='issuer',valid_from='2026-01-01')
        rec=read('contract','expiry','contract valid')
        db.publish(scope,'contract','expiry','2026-08-01',source='issuer',valid_from='2026-07-01')
        add('T7 late backdated correction invalidates',db.receipt(rec['rid'])['status'],'STALE')
        # T8 BITEMPORAL TIME TRAVEL
        old=db.state_as_known(scope,'contract','expiry',D,rec['snapshot_rev'])['value']
        new=db.state_as_known(scope,'contract','expiry',D)['value']
        add('T8 previous knowledge remains queryable', (old,new),('2027-01-01','2026-08-01'))
        # T9 SEARCH ABSENCE
        s=db.open_read(scope,D);s.scan('incident:');rec=s.seal('No incident records')
        db.publish(scope,'incident:007','severity','high',valid_from=D)
        add('T9 scoped empty-list assumption invalidates',db.receipt(rec['rid'])['status'],'STALE')
        # T10 RETRACTION
        db.publish(scope,'acquisition','status','announced',source='filing',valid_from=D)
        rec=read('acquisition','status','Proceed')
        db.publish(scope,'acquisition','status',None,source='filing',valid_from=D,retract=True)
        add('T10 retraction blocks plan',db.receipt(rec['rid'])['status'],'STALE')
        # T11 TEMPORAL EXPIRY
        db.publish(scope,'license','active','yes',valid_from='2026-01-01',valid_to='2026-10-18')
        rec=read('license','active','Use license')
        db.sweep(scope,'2026-10-18')
        add('T11 expiration invalidates without source update',db.receipt(rec['rid'])['status'],'STALE')
        # T12 REPLAY IDEMPOTENCE
        ev=db.publish(scope,'credit','limit',100,valid_from=D,event_id='replay-credit-1')
        replay=db.publish(scope,'credit','limit',100,valid_from=D,event_id='replay-credit-1')
        add('T12 duplicate update does not create new fact',replay['duplicate'],True)
        # T13 VALID INTERNAL ACTION
        rec=read('credit','limit','Check limit')
        outcome=act(rec['rid'],'t13');add('T13 fully revalidated internal action',outcome,'EXECUTED')
        # T14 BULK ATOMIC SCHEMA UPDATE
        db.batch_publish(scope,[{'key':'schema','field':'arg1','value':1,'valid_from':D},
                                {'key':'schema','field':'arg2','value':2,'valid_from':D}])
        s=db.open_read(scope,D);s.read('schema','arg1');s.read('schema','arg2');rec=s.seal('API Plan')
        db.batch_publish(scope,[{'key':'schema','field':'arg1','value':3,'valid_from':D},
                                {'key':'schema','field':'arg2','value':4,'valid_from':D}])
        add('T14 batch transition invalidates both-field receipt',db.receipt(rec['rid'])['status'],'STALE')
        # T15 SOURCE SCOPE ISOLATION
        rec=read('credit','limit','Private tenant A plan')
        db.publish('other-tenant/other-project','credit','limit',-1,valid_from=D)
        add('T15 cross-tenant event leaves receipt intact',db.receipt(rec['rid'])['status'],'VALID')
        # T16 REVALIDATED INTERNAL ACTION AFTER COMMIT
        act_before=db.effect_count(scope)
        rec=read('schema','arg1','Call schema v2')
        out=act(rec['rid'],'t16')
        add('T16 atomic internal effect ledger', (out,db.effect_count(scope)-act_before),('EXECUTED',1))
        # T17 WIDE HOT FACT
        db.publish(scope,'popular','state','v1',source='report',valid_from=D)
        watchers=[read('popular','state','dependent plan')['rid'] for _ in range(250)]
        t0=time.monotonic();changed=db.publish(scope,'popular','state','v2',source='report',valid_from=D)
        fanout_ms=round((time.monotonic()-t0)*1000,2)
        add('T17 fanout 250 receipts invalidated', changed['affected'],250,{'publish_latency_ms':fanout_ms})
        # NOTE arbitrary external effects are deliberately unsupported in this lab.
        stale_internal_effects=sum(1 for c in cases if not c['pass'])
        elapsed=round(time.monotonic()-started,3)
        summary={'version':'ugi-p5-memory-lab-v1','source':'synthetic generated fixtures, NOT real UGI production data',
                 'engine':'SQLite WAL local isolated reference implementation',
                 'pass':sum(x['pass'] for x in cases),'total':len(cases),
                 'fail':sum(not x['pass'] for x in cases),
                 'no_external_actions_available':True,'external_action_atomicity_proven':False,
                 'has_real_falkordb_integration':False,
                 'human_review_required_for_defined_scenarios':False,
                 'receipt_capture':'automatic only for Reader.read/scan; external/uninstrumented channels not captured',
                 'intervals':'half-open [valid_from, valid_to)',
                 'late_update':'valid time + transaction-ordered knowledge revision',
                 'conflicts':'UNKNOWN and blocked (no source-rank winner)',
                 'elapsed_seconds':elapsed,'fanout_250_ms':fanout_ms,
                 'synthetic_effects_executed':db.effect_count(scope),
                 'stats':db.stats(scope),'cases':cases,
                 'acceptance':{'all_scenarios_pass':all(x['pass'] for x in cases),
                  'external_write_prohibited':True,'no_stale_internal_action_executed':all(c['pass'] for c in cases if c['case'].startswith(('T1 ','T3 ','T4 ','T6 ')))},
                 'limitations':['not connected to real UGI store/MCP or FalkorDB',
                  'a connected agent must be forced through Reader to prevent unlogged inputs',
                  'external side effects cannot be made atomic with local SQLite without a coordinated executor',
                  'semantic diffs of prose and automated source credibility are not implemented',
                  'scale and multi-process distribution are not established by this synthetic lab']}
        report_path=Path(report_path);report_path.parent.mkdir(parents=True,exist_ok=True)
        report_path.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        print('P5 MEMORY LAB:',summary['pass'],'/',summary['total'],'| elapsed:',elapsed,'s | fanout 250:',fanout_ms,'ms')
        for c in cases:print(' ', 'PASS' if c['pass'] else 'FAIL',c['case'])
        print('REPORT:',str(report_path))
        return 0 if summary['fail']==0 else 2

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--report',default='results/p5_lab_report.json')
    args=ap.parse_args()
    raise SystemExit(execute(args.report))
