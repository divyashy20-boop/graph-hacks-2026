import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--baseline',required=True);p.add_argument('--patched',required=True);p.add_argument('--output',required=True);a=p.parse_args()
b=json.loads(Path(a.baseline).read_text());f=json.loads(Path(a.patched).read_text())
def item(o,n):return next((x for x in o['results'] if x['title']==n),{})
key='UGI answer versus explanation agreement'
x=item(b,key);y=item(f,key)
agent=item(f,'Model-selected multi-step MCP investigation')
summary={'version':'ugi-agent-fix-comparison-v1','baseline_explanation':x.get('status','NOT_RUN'),
         'patched_explanation':y.get('status','NOT_RUN'),
         'baseline_disagreements':x.get('evidence',{}).get('disagreements'),
         'patched_disagreements':y.get('evidence',{}).get('disagreements'),
         'model_strict_completed':agent.get('evidence',{}).get('strict_pass'),
         'model_tasks':agent.get('evidence',{}).get('total'),
         'agent_status':agent.get('status','NOT_RUN'),
         'baseline_counts':b.get('counts'), 'patched_counts':f.get('counts'),
         'gaps':['Results depend on real local Qwen performance and test configuration',
                 'Source is five public GitHub Compose examples converted to structured input',
                 'Do not confuse rule proofs with observed incidents',
                 'Agent still experimental; no code installed in UGI by default'],
         'pass_criteria':'zero explanation disagreements AND strict completion for all agent workflows AND no MCP safety failures'}
Path(a.output).write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
