"""Optional read-only query using a prior isolated test graph (not existing user graphs)."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from ugi_krish_validation_v2.full_audit import MCPStdio
from ugi_real_track1.manifest import SOURCES,load_manifest,extract_explicit_dependencies
from .controller import run_controller


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--report',type=Path,required=True)
    p.add_argument('--dataset',required=True)
    p.add_argument('--query',required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    rep=json.loads(a.report.read_text(encoding='utf-8'))
    root=rep['isolation']['graph_prefix']
    if not root.startswith('ugi_real_') or len(root)>70:
        p.error('Only isolated ugi_real_* graph prefix from a test report is permitted')
    src=next((x for x in SOURCES['sources'] if x['name']==a.dataset),None)
    if src is None:p.error('Dataset must match one of the pinned GitHub source examples')
    entities,_=extract_explicit_dependencies(load_manifest(src))
    import os
    client=MCPStdio(root,a.dataset,'ugi-audit',os.environ.get('UGI_REDIS_URL','redis://graph:6379/0'))
    try:
        client.request('initialize',{'protocolVersion':'2025-11-25','capabilities':{},
                                     'clientInfo':{'name':'ugi-rulebook-query','version':'1.0'}})
        result=run_controller(a.query,a.dataset,entities,client)
    finally:client.close()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':result['status'],'verdict':result.get('verdict'),
                      'reason':result.get('reason'),'trace_steps':len(result['trace'])}))
    return 0 if result['status']=='COMPLETE' else 1

if __name__=='__main__':raise SystemExit(main())
