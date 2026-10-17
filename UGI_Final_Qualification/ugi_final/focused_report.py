"""Gate the focused surgical live rerun; do not silently accept missing tests."""
from __future__ import annotations
import argparse, json
from pathlib import Path

# Exact original eleven case names. No results or counts can be inferred.
EXPECTED=(
 'positive and negative real MCP investigations complete',
 'automatic all-read capture and valid receipts',
 'new directed edge ingested into actual isolated UGI graph',
 'new graph edge invalidates old negative conclusion',
 'stale real-graph answer denied by internal action gate',
 'unrelated receipt status matches observed read-set changes',
 'actual UGI opposing source assertion ingested',
 'actual UGI CONTRADICTED verdict becomes UNKNOWN receipt',
 'conflicted real-graph conclusion blocked at internal gate',
 'real-MCP-derived receipt cascades through two agent outputs',
 'no external actions and all preview/write gates disabled',
)

def make_report(combo:dict,unit_status:str,live_status:str)->dict:
    records=combo.get('cases',[])
    names=[r.get('name') for r in records]
    completeness=(len(names)==len(EXPECTED) and set(names)==set(EXPECTED) and
                  len(names)==len(set(names)))
    no_ext=(combo.get('production_external_actions') is False)
    clean=(all(isinstance(r.get('pass'),bool) and r['pass'] for r in records))
    complete_count=(combo.get('total')==11 and combo.get('passed')==11)
    good=(completeness and no_ext and clean and complete_count and
          combo.get('status')=='PASS' and unit_status=='PASS' and live_status=='PASS')
    return {'version':'ugi-final-p5-surgical-fix-v1',
        'decision':('READY_FOR_FEATURE_FLAGGED_INTEGRATION_TEST' if good else 'NOT_QUALIFIED_FIX_FAILURES'),
        'isolated_real_falkordb_combo':{'passed':combo.get('passed'),'total':combo.get('total'),
           'status':combo.get('status'),'required_cases_complete':completeness},
        'offline_memory_and_bridge_regressions':unit_status,
        'live_exit_status':live_status,
        'external_actions_enabled':False,
        'original_code_modifications':False,
        'production_ready':False,
        'known_gaps':['full API/UI integration not established','external action fencing not proven',
                      'graph writes outside receipt gateway require mandatory reread',
                      'new unseen graph datasets and H1 NLP still need end-to-end checks']}

def main():
    p=argparse.ArgumentParser();p.add_argument('--combo',required=True)
    p.add_argument('--units',choices=['PASS','FAIL'],required=True)
    p.add_argument('--live',choices=['PASS','FAIL'],required=True)
    p.add_argument('--output',required=True)
    args=p.parse_args()
    try: data=json.loads(Path(args.combo).read_text())
    except Exception as e:data={'status':'FAIL','read_error':str(e)}
    report=make_report(data,args.units,args.live)
    Path(args.output).write_text(json.dumps(report,indent=2)+'\n')
    print('P5 FOCUSED DECISION:',report['decision'],flush=True)
    return 0 if report['decision']=='READY_FOR_FEATURE_FLAGGED_INTEGRATION_TEST' else 1

if __name__=='__main__':raise SystemExit(main())
