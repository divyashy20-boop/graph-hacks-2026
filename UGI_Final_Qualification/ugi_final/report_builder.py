"""Fail-closed final qualification summary. No score masking or inferred green tests."""
import argparse,json
from pathlib import Path
from .focused_report import make_report as verify_combined_eleven

def load(path):
    try:
        obj=json.loads(Path(path).read_text(encoding='utf-8'))
        return {'found':True,'data':obj}
    except Exception as e:
        return {'found':False,'error':type(e).__name__+': '+str(e)[:160]}

def make(guide,p5,combined,*,unit_ok,patch_ok,app_test_status):
    v5=load(guide); p=load(p5); c=load(combined)
    gd=v5.get('data',{}); pd=p.get('data',{}); cd=c.get('data',{})
    basic=gd.get('results',[])
    must=[x for x in basic if x.get('category') not in {'AI','Comparison'}]
    wc=gd.get('workflows',[]); extended=gd.get('extended_workflows',[])
    phases={
      'offline_test_suite':{'status':'PASS' if unit_ok else 'FAIL','note':'unit tests in copied package'},
      'engine_patch_only_in_temp_copy':{'status':'PASS' if patch_ok else 'FAIL'},
      'UGI_live_store_and_source_checks':{'status':'PASS' if must and all(x.get('status')=='PASS' for x in must) else 'FAIL',
                       'passed':sum(x.get('status')=='PASS' for x in must),'total':len(must)},
      'rulebook_original_live':{'status':'PASS' if len(wc)==10 and all(x.get('benchmark_pass') for x in wc) else 'FAIL',
                       'passed':sum(bool(x.get('benchmark_pass')) for x in wc),'total':len(wc)},
      'rulebook_extended_live':{'status':'PASS' if len(extended)==39 and all(x.get('passed') for x in extended) else 'FAIL',
                       'passed':sum(bool(x.get('passed')) for x in extended),'total':len(extended)},
      'P5_local_reference':{'status':'PASS' if pd.get('pass')==17 and pd.get('total')==17 else 'FAIL',
                       'passed':pd.get('pass',0),'total':pd.get('total',0)},
      'combined_UGI_MCP_P5':{'status':'PASS' if verify_combined_eleven(cd,'PASS','PASS')['decision']=='READY_FOR_FEATURE_FLAGGED_INTEGRATION_TEST' else 'FAIL',
                       'passed':cd.get('passed',0),'total':cd.get('total',0)},
      'optional_UGI_native_offline':{'status':app_test_status},
    }
    blockers=[k for k,v in phases.items() if v['status']=='FAIL']
    decision='QUALIFIED_FOR_FEATURE_FLAGGED_INTEGRATION' if not blockers else 'NOT_QUALIFIED_FIX_FAILURES'
    return {'version':'ugi-final-qualification-v1','decision':decision,
            'what_this_does_not_mean':'NOT production ready, NOT deployed, NOT authorized external action atomicity, NOT general autonomous AI',
            'phase_results':phases,'hard_blockers':blockers,
            'llm_baseline':next((x for x in basic if x.get('title')=='Legacy LLM-selected strict baseline'),None),
            'llm_advice':next((x for x in basic if x.get('title')=='Real local LLM next-tool advisory agreement'),None),
            'known_integration_gaps':[
            'Implement enforced capture for every real API/MCP/agent graph-read path, not just wrapped test clients',
            'Replace ephemeral SQLite registry with a durable tenant-scoped receipt registry, transactional/outbox update pipeline',
            'Enforce a graph revision/lease or coordinated executor for real actions; test TOCTOU on external services',
            'Prove correctness with unseen sources and H1 NLP/identity versions; current data are structured Compose declarations',
            'Complete authorization, network, monitoring, restore/replay, AWS/IAM/secrets/security reviews',
            'No paid calls, no destructive migration, no AWS deployment has been performed'],
            'input_reports':{'v5':guide,'p5':p5,'combined':combined}}

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    for flag in ('v5','p5','combined','out'):ap.add_argument('--'+flag,required=True)
    ap.add_argument('--unit-ok',type=int,required=True)
    ap.add_argument('--patch-ok',type=int,required=True)
    ap.add_argument('--app-tests',default='NOT_RUN')
    a=ap.parse_args()
    obj=make(a.v5,a.p5,a.combined,unit_ok=bool(a.unit_ok),patch_ok=bool(a.patch_ok),app_test_status=a.app_tests)
    Path(a.out).write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
    print('FINAL QUALIFICATION DECISION:',obj['decision'])
    print('HARD BLOCKERS:',obj['hard_blockers'])
    raise SystemExit(0 if not obj['hard_blockers'] else 1)
