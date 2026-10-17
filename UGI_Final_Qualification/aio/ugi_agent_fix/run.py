"""Compare unchanged UGI and patched-copy UGI on same pinned real GitHub configs.

This script operates on fresh graph namespaces and never modifies the source repo.
"""
from __future__ import annotations
import argparse
import json
import os
import time
from pathlib import Path

from ugi_real_track1.real_suite import (prepare, benchmark_queries, action_test, mcp_test,
                                        official_mcp_test, safety_agent_test, note, summarize)
from ugi_krish_validation_v2.full_audit import MCPStdio, ollama_model_available
from ugi_agent_fix.agent import make_goals, workflow


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--mode',choices=['baseline','patched'],required=True)
    ap.add_argument('--model',default='qwen3:4b-instruct')
    ap.add_argument('--ollama-url',default='http://host.docker.internal:11434')
    ap.add_argument('--output',required=True)
    ap.add_argument('--max-calls',type=int,default=13)
    ap.add_argument('--skip-ai',action='store_true')
    args=ap.parse_args()
    output={'version':'ugi-agent-fix-trial-v1','mode':args.mode,
            'source_commit':'30f4b7f6a6c3b0c0ecf4d4efb0de203c48d11562',
            'date':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()), 'results':[],
            'guarantees':['Existing datasets unchanged','Only new UUID-prefixed graphs written',
                          'No external actions','No paid models','Model arguments never corrected silently']}
    try:
        prepared, config, prefix, owner=prepare(output,None)
        if len(prepared)!=5: raise RuntimeError('Incomplete pinned source imports')
    except Exception as exc:
        note(output,'Real-source graph preparation','FAIL',{'error':repr(exc)})
        prepared={}
    if prepared:
        for label, fn in [
            ('Graph reasoning/explanation',lambda:benchmark_queries(output,prepared)),
            ('Authorized persistent action with no duplicates',lambda:action_test(output,prepared)),
            ('Actual MCP subprocess protocol',lambda:mcp_test(output,prepared,prefix,owner,config)),
        ]:
            try:fn()
            except Exception as exc:note(output,label,'FAIL',{'error':repr(exc)})
        if args.mode=='patched':
            # The SDK was already verified in previous runs; this one tests it
            # again only when available without modifying the app environment.
            try:official_mcp_test(output,prepared,prefix,owner,config)
            except Exception as exc:note(output,'Official MCP SDK','INCONCLUSIVE',{'error':repr(exc)})
            if args.skip_ai:
                note(output,'Model-selected multi-step MCP investigation','NOT_RUN',note='AI disabled by operator',category='AI')
            else:
                try:
                    available=ollama_model_available(args.ollama_url,args.model)
                except Exception as exc:
                    available=False;why=repr(exc)
                else:why='Ollama model not present: '+args.model
                if not available:
                    note(output,'Model-selected multi-step MCP investigation','INCONCLUSIVE',
                         {'reason':why},category='AI')
                else:
                    goals=make_goals(prepared);results=[]
                    for i,g in enumerate(goals):
                        print(f'  AI workflow {i+1}/{len(goals)}: {g["source"]} {g["split"]}',flush=True)
                        client=MCPStdio(prefix,g['source'],owner,config.redis_url)
                        try:
                            r=client.request('initialize',{'protocolVersion':'2025-11-25',
                                                          'capabilities':{},
                                                          'clientInfo':{'name':'ugi-agent-fix-trial','version':'1.0'}})
                            if not r.get('result'): raise ValueError('MCP initialize unsuccessful')
                            result=workflow(g,client,args.ollama_url,args.model,args.max_calls)
                        except Exception as exc:
                            result={'source':g['source'],'split':g['split'],'strict_pass':False,
                                    'completed':False,'error':repr(exc)}
                        finally:client.close()
                        results.append(result)
                    good=sum(bool(r.get('strict_pass')) for r in results)
                    note(output,'Model-selected multi-step MCP investigation',
                         'PASS' if good==len(results) else 'FAIL',
                         {'strict_pass':good,'total':len(results),
                          'regression_strict':sum(r.get('strict_pass',False) for r in results if r.get('split')=='regression'),
                          'alternate_strict':sum(r.get('strict_pass',False) for r in results if r.get('split')=='alternate_prompt'),
                          'workflows':results},
                         'Fresh model outputs on five real Compose source graphs, 10 task formulations. '
                         'No production incidents, no argument substitution; a constrained local-model planner.', 'AI')
                    try:safety_agent_test(output,args.ollama_url,args.model)
                    except Exception as exc:note(output,'Unsafe tool refusal','FAIL',{'error':repr(exc)},category='AI')
    summarize(output)
    output['scope_warning']='A PASS does not establish general real-world reasoning, NLP extraction, or production causation.'
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(output,indent=2,ensure_ascii=False,default=str)+'\n',encoding='utf-8')
    print('RESULT',args.mode,output['counts'],'VERDICT',output['verdict'],path,flush=True)
    return 1 if output['counts']['FAIL'] else 0

if __name__=='__main__':raise SystemExit(main())
