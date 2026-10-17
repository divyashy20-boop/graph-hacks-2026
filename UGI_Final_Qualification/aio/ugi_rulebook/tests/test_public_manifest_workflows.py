"""Offline mock MCP sanity check, NOT the real FalkorDB integration test."""
import unittest
from ugi_real_track1.manifest import SOURCES,load_manifest,extract_explicit_dependencies,directed_reachable
from ugi_agent_fix.agent import make_goals
from ugi_rulebook.experiment import make_task
from ugi_rulebook.controller import run_controller

class ManifestMCP:
    def __init__(self,links,names):
        self.calls=[];self.names=names
        self.edges={(l['subject'],l['object']) for l in links}
        self.claims={f'claim-{u}-{v}':(u,v) for u,v in self.edges}
    def request(self,method,*args):
        return {'result':{'tools':[{'name':n,'inputSchema':{'properties':{k:{'type':('boolean' if k=='authorise_action' else 'string')} for k in keys},'required':(['target','idempotency_key'] if n=='investigate_dependency_incident' else keys),'additionalProperties':False}}
          for n,keys in {
             'search_entities':['name'], 'evaluate_relationship':['subject','object','predicate'],
             'get_claim_evidence':['claim_id'],
             'investigate_dependency_incident':['target','idempotency_key','authorise_action']}.items()]}}
    def tool(self,name,args):
        self.calls.append((name,args))
        if name=='search_entities':val={'entities':[{'id':args['name'],'name':args['name']}] if args['name'] in self.names else []}
        elif name=='evaluate_relationship':
            a,b,p=args['subject'],args['object'],args['predicate']
            if p=='DEPENDS_ON' and (a,b) in self.edges:
                claim_ids=[f'claim-{a}-{b}'];status='SOURCE_ASSERTED'
            elif p=='TRANSITIVELY_DEPENDS_ON' and directed_reachable(self.edges,a,b) and directed_reachable(self.edges,a,b)>1:
                path=next(((a,mid,b) for x,mid in self.edges for y,z in self.edges
                           if x==a and mid==y and z==b),None)
                claim_ids=[f'claim-{path[0]}-{path[1]}',f'claim-{path[1]}-{path[2]}'] if path else []
                status='RULE_DERIVED' if claim_ids else 'UNKNOWN'
            else:status='UNKNOWN';claim_ids=[]
            val={'status':status,'rules':['dependency_reachability_v1'] if status=='RULE_DERIVED' else [],
                 'resolution':{'assessment':'RULE_DERIVED_FROM_DEPENDENCIES'} if status=='RULE_DERIVED' else {},
                 'evidence':[{'claim':{'id':c,'source_id':'src','evidence_id':'evi-'+c}} for c in claim_ids],
                 'explanation':'graph source assertions only'}
        elif name=='get_claim_evidence':
            ident=args['claim_id'];val={'claim':{'id':ident,'source_id':'src','evidence_id':'evi-'+ident},
                                        'evidence':{'id':'evi-'+ident,'source_id':'src','quote':self.claims[ident][0]+' depends on '+self.claims[ident][1]}}
        else:val={'executed':False,'kind':'Investigation'}
        return {'isError':False,'structuredContent':val}

class PublicCases(unittest.TestCase):
    def test_all_10_pinned_questions_complete_against_fake_graph(self):
        # No UGI live graph or model here. It independently sanity-checks rulebook's
        # graph-assertion flow using developer-authored Compose declarations.
        prepared={}
        for s in SOURCES['sources']:
            names,links=extract_explicit_dependencies(load_manifest(s))
            prepared[s['name']]={'source':s,'services':names,'links':links}
        cases=make_goals(prepared)
        self.assertEqual(len(cases),10)
        for goal in cases:
            with self.subTest(task=goal['task']):
                item=prepared[goal['source']]
                mcp=ManifestMCP(item['links'],item['services'])
                outcome=run_controller(make_task(goal),goal['source'],item['services'],mcp)
                self.assertEqual(outcome['status'],'COMPLETE',outcome)
                self.assertEqual(outcome['verdict'],goal['expected'],outcome)
                self.assertTrue(outcome['preview_done'])
                self.assertTrue(outcome['verified_claim_ids'])
                self.assertEqual([x['tool'] for x in outcome['trace']].count('evaluate_relationship'),1)
                self.assertTrue(all(not args.get('authorise_action',False) for _,args in mcp.calls))

if __name__=='__main__':unittest.main()
