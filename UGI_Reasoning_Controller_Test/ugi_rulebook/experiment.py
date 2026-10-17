"""Real pinned GitHub graph benchmark for deterministic guided controller.

Runs UGI's *real* FalkorDB store and actual MCP stdio; optional Qwen advisor,
which cannot execute or modify tool calls. Baseline agent is separate.
"""
from __future__ import annotations
import argparse
import json
import time
from pathlib import Path

from ugi_krish_validation_v2.full_audit import MCPStdio, ollama_generate, ollama_model_available
from ugi_real_track1.real_suite import prepare, benchmark_queries, note, summarize
from ugi_agent_fix.agent import make_goals, workflow as legacy_workflow
from .controller import run_controller


def advisory_client(url, model, max_calls=3):
    seen={'calls':0}
    def ask(stage, context):
        if seen['calls']>=max_calls:
            return None
        seen['calls']+=1
        prompt={'role':'UGI next tool ADVISOR. Choose one tool NAME only. '
                       'The controller will independently validate and execute; you cannot send arguments.',
                'current_stage':stage, 'state':context,
                'available':context['allowed_tool_names'],
                'output': {'tool':'exact one permitted tool name'}}
        reply, _, _=ollama_generate(json.dumps(prompt),url,model,timeout=65)
        if not isinstance(reply,dict) or not isinstance(reply.get('tool'),str):
            raise ValueError('MODEL_ADVICE_SCHEMA_INVALID')
        return reply['tool']
    return ask


def make_task(goal):
    # Benchmark protocol explicitly asks for preview. In ordinary questions,
    # rulebook does NOT preview unless requested by the user.
    return goal['task'] + (' Also preview a read-only investigation of the destination service; '
                           'do not save any actions.')


def run(output, *, use_advisor, url, model, run_legacy, max_cases=10):
    out={'version':'ugi-guided-rulebook-v1', 'date':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
         'data_meaning':'SHA256-pinned genuine Docker Compose declarations; NO production incident truth',
         'controller_description':'Deterministic evidence-first state machine with optional nonbinding LLM advisor',
         'source_repo':'docker/awesome-compose', 'results':[], 'workflows':[],
         'baseline_workflows':[], 'ai_advisor_available':False,
         'safety':{'no_paid_calls':True,'no_old_graph_modification':True,
                   'disposable_graphs_preserved':True,'production_actions':False}}
    try:
        prepared, cfg, root, owner=prepare(out,None)
        if len(prepared)!=5:
            raise RuntimeError('Five GitHub Compose source graphs were not fully prepared')
    except Exception as exc:
        note(out,'Source preparation','FAIL',{'error':repr(exc)},category='Infrastructure')
        prepared={}
    if not prepared:
        summarize(out)
        Path(output).write_text(json.dumps(out,indent=2)+'\n')
        return 1
    benchmark_queries(out,prepared)
    goals=make_goals(prepared)[:max_cases]
    present=False
    if use_advisor or run_legacy:
        try:
            present=ollama_model_available(url,model)
        except Exception as exc:
            out['model_probe_error']=repr(exc)
    out['ai_advisor_available']=present
    if use_advisor and not present:
        note(out,'Optional local LLM tool advice','INCONCLUSIVE',{'model':model,'reason':'Ollama model unavailable'},category='AI')
    for i, goal in enumerate(goals, 1):
        print(f'  Guided {i}/{len(goals)}: {goal["source"]} {goal["split"]}',flush=True)
        client=MCPStdio(root,goal['source'],owner,cfg.redis_url)
        try:
            init=client.request('initialize',{'protocolVersion':'2025-11-25',
                       'capabilities':{},'clientInfo':{'name':'ugi-rulebook-test','version':'1.0'}})
            if not init.get('result'):raise RuntimeError('MCP initialization did not succeed')
            outcome=run_controller(make_task(goal),goal['source'],prepared[goal['source']]['services'],
                   client,advisor=advisory_client(url,model) if use_advisor and present else None)
        except Exception as exc:
            outcome={'status':'ERROR','reason':repr(exc),'trace':[]}
        finally:client.close()
        outcome.update(source=goal['source'], split=goal['split'], expected=goal['expected'],
                       rubric='exact graph verdict, complete evidence retrieval, required read-only preview')
        outcome['benchmark_pass']=bool(outcome.get('status')=='COMPLETE' and
                 outcome.get('verdict')==goal['expected'] and
                 outcome.get('preview_done') and outcome.get('verified_claim_ids'))
        out['workflows'].append(outcome)
        print(f'    {outcome["status"]} / {outcome.get("verdict")} / pass={outcome["benchmark_pass"]}',flush=True)
    passed=sum(r['benchmark_pass'] for r in out['workflows'])
    note(out,'Guided rulebook real MCP workflows', 'PASS' if passed==len(goals) else 'FAIL',
         {'passed':passed,'total':len(goals),'fails':[
             {'source':r['source'],'reason':r.get('reason'),'status':r['status']}
             for r in out['workflows'] if not r['benchmark_pass']]},
         'Tool arguments are constructed by rulebook from interpreted user query and observed MCP data. '
         'This does not measure free-form autonomous tool choice.', 'Agent')
    if use_advisor and present:
        n=sum(w.get('model_advice_count',0) for w in out['workflows'])
        good=sum(w.get('model_advice_agreements',0) for w in out['workflows'])
        note(out,'Real local LLM next-tool advisory agreement', 'PASS' if n and good==n else 'FAIL',
             {'model':model,'advisor_agreed':good,'advisor_attempts':n,
              'scope':'nonbinding tool-name suggestions, NOT LLM arguments nor autonomous action'},
             'Wrong advice cannot override rulebook; not counted as controller workflow failures','AI')
    if run_legacy:
        if not present:
            note(out,'Legacy model-selected agent comparison','INCONCLUSIVE',{'model':model},
                 'Model unavailable. Existing historical 0/10 scores are not substituted.', 'Comparison')
        else:
            for i,g in enumerate(goals,1):
                print(f'  Original-agent baseline {i}/{len(goals)}: {g["source"]}',flush=True)
                client=MCPStdio(root,g['source'],owner,cfg.redis_url)
                try:
                    client.request('initialize',{'protocolVersion':'2025-11-25',
                              'capabilities':{},'clientInfo':{'name':'baseline','version':'1.0'}})
                    result=legacy_workflow(g,client,url,model,13)
                except Exception as exc:
                    result={'strict_pass':False,'completed':False,'error':repr(exc)}
                finally:client.close()
                out['baseline_workflows'].append(result)
            c=sum(bool(r.get('strict_pass')) for r in out['baseline_workflows'])
            note(out,'Legacy LLM-selected strict baseline','PASS' if c==len(goals) else 'FAIL',
                 {'strict_pass':c,'total':len(goals)},
                 'Legacy asks LLM to supply tool names and argument keys. '
                 'Guided results are a different policy-controller architecture; do not conflate.',
                 'Comparison')
    summarize(out)
    out['outstanding']=[
        'This is a guided deterministic controller, NOT flexible autonomous open-ended planning.',
        'Only explicit service-dependency questions handled; ambiguous natural-language queries abstain.',
        'Rulebook interpretation uses entity inventory from source graph, not arbitrary NLP extraction.',
        'No real incident causality, business impact ground truth, semantic recomputation or external actions tested.',
        'Snapshot consistency and concurrency guarantees beyond earlier labs are not established.',
    ]
    dest=Path(output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(out,indent=2,ensure_ascii=False,default=str)+'\n',encoding='utf-8')
    print('GUIDED RESULT:',passed,'/',len(goals),' | summary:',out['counts'],' | file:',str(dest),flush=True)
    return 1 if passed!=len(goals) or any(x['status']=='FAIL' for x in out['results'] if x['category']!='Comparison' and x['category']!='AI') else 0


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',default='/tmp/ugi_rulebook_result.json')
    p.add_argument('--model',default='qwen3:4b-instruct')
    p.add_argument('--ollama-url',default='http://host.docker.internal:11434')
    p.add_argument('--no-advisor',action='store_true')
    p.add_argument('--run-legacy-agent',action='store_true')
    p.add_argument('--max-cases',type=int,default=10)
    a=p.parse_args()
    if not 1<=a.max_cases<=10: p.error('max-cases must be 1..10')
    return run(a.output,use_advisor=not a.no_advisor,url=a.ollama_url,model=a.model,
               run_legacy=a.run_legacy_agent,max_cases=a.max_cases)

if __name__=='__main__':raise SystemExit(main())
