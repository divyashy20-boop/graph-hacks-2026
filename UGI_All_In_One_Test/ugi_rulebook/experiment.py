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
from ugi_real_track1.manifest import generate_questions
from ugi_agent_fix.agent import make_goals, workflow as legacy_workflow
from .controller import run_controller
from .preflight import validate_prepared_sources, import_origins, assert_runtime_module_origins, PreflightError


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
         'source_repo':'docker/awesome-compose', 'results':[], 'workflows':[], 'extended_workflows':[],
         'baseline_workflows':[], 'ai_advisor_available':False,
         'safety':{'no_paid_calls':True,'no_old_graph_modification':True,
                   'disposable_graphs_preserved':True,'production_actions':False}}
    # Protect direct CLI usage as well as the PowerShell runner: never import
    # old modules from /tmp before starting a graph run.
    try:
        out['import_origins'] = assert_runtime_module_origins(Path(__file__).resolve().parents[1])
    except PreflightError as exc:
        note(out,'Runtime Python module origin verification','FAIL',{'error':str(exc)},category='Infrastructure')
        summarize(out)
        Path(output).write_text(json.dumps(out,indent=2)+'\n')
        return 1
    try:
        prepared, cfg, root, owner=prepare(out,None)
        if len(prepared)!=5:
            raise RuntimeError('Five GitHub Compose source graphs were not fully prepared')
        validate_prepared_sources(prepared)
        out['import_origins'] = import_origins()
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
                   client,advisor=advisory_client(url,model) if use_advisor and present else None,
                   allowed_source_ids={prepared[goal['source']]['source_id']})
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
    # NEW: additional real-MCP task formulations generated from human-annotated
    # source declarations. Unlike the original 10, these include unsupported reverse
    # dependency (UNKNOWN/CONNECTED_ONLY), new synonyms and reversed grammar.
    # Expected verdicts only score results; they are NEVER sent to the controller.
    extended=[]
    for source, item in prepared.items():
        for q in generate_questions(item['source']):
            if q['predicate']=='CAUSED':
                continue  # Outage causation intentionally outside dependency-rule scope
            a,b=q['subject'],q['object']
            words='indirectly' if q['predicate']=='TRANSITIVELY_DEPENDS_ON' else 'directly'
            extended.append((source, f'Does {a} {words} depend on {b}?', q['expected'], 'graph_negative_or_positive'))
        for a,b in sorted(item['edges']):
            extended.append((source,f'Does {a} rely on {b}?','SOURCE_ASSERTED','synonym_rely'))
            extended.append((source,f'Is {b} required by {a}?','SOURCE_ASSERTED','reverse_required_by'))
    for i,(source,query,expected,split) in enumerate(extended,1):
        client=MCPStdio(root,source,owner,cfg.redis_url)
        try:
            client.request('initialize',{'protocolVersion':'2025-11-25',
                    'capabilities':{},'clientInfo':{'name':'ugi-v3-extended','version':'1.0'}})
            row=run_controller(query,source,prepared[source]['services'],client,
                 allowed_source_ids={prepared[source]['source_id']})
        except Exception as exc:
            row={'status':'ERROR','reason':repr(exc),'trace':[]}
        finally:
            client.close()
        value=row.get('verdict')
        correct=(value==expected if expected in ('SOURCE_ASSERTED','RULE_DERIVED')
                 else value in ('UNKNOWN','CONNECTED_ONLY'))
        passed=bool(row.get('status')=='COMPLETE' and correct
                    and row.get('writes_attempted')==0
                    and (bool(row.get('verified_claim_ids')) if expected in ('SOURCE_ASSERTED','RULE_DERIVED') else True)
                    and not row.get('preview_done'))
        out['extended_workflows'].append({'source':source,'query':query,'split':split,
             'expected':expected,'actual':value,'status':row.get('status'),
             'passed':passed,'reason':row.get('reason'),'steps':len(row.get('trace',[])),
             'claim_count':len(row.get('verified_claim_ids',[]))})
        if not passed:
            print('  EXTENDED FAIL:',source,query,row.get('reason'),value,flush=True)
    extras_good=sum(x['passed'] for x in out['extended_workflows'])
    note(out,'Extended real MCP robustness and negative-claim tests',
         'PASS' if extras_good==len(extended) and extended else 'FAIL',
         {'passed':extras_good,'total':len(extended),'splits':{
            k:sum(x['passed'] for x in out['extended_workflows'] if x['split']==k)
            for k in sorted({x['split'] for x in out['extended_workflows']})},
            'failed_queries':[x for x in out['extended_workflows'] if not x['passed']][:12]},
         'Additional directed, reversed, unknown, indirect and synonym questions against live MCP. '
         'Compose dependencies are source assertions, not incident outcomes.','Agent')

    if use_advisor and present:
        n=sum(w.get('model_advice_count',0) for w in out['workflows'])
        good=sum(w.get('model_advice_agreements',0) for w in out['workflows'])
        note(out,'Real local LLM next-tool advisory agreement', ('INCONCLUSIVE' if n==0 else ('PASS' if good==n else 'FAIL')),
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
        'Bounded explicit service-dependency questions handled; arbitrary language and new intents remain unproven.',
        'Rulebook interpretation uses entity inventory from source graph, not arbitrary NLP extraction.',
        'No real incident causality, business impact ground truth, semantic recomputation or external actions tested.',
        'Snapshot consistency and concurrency guarantees beyond earlier labs are not established.',
    ]
    dest=Path(output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(out,indent=2,ensure_ascii=False,default=str)+'\n',encoding='utf-8')
    print('GUIDED RESULT:',passed,'/',len(goals),' | summary:',out['counts'],' | file:',str(dest),flush=True)
    return 1 if passed!=len(goals) or extras_good!=len(extended) or any(x['status']=='FAIL' for x in out['results'] if x['category'] not in ('Comparison','AI')) else 0


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
