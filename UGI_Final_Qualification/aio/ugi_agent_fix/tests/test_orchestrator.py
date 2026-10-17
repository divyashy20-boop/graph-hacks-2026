from __future__ import annotations
import unittest
from unittest.mock import patch
from ugi_agent_fix.agent import workflow
GOAL={'source':'real-compose-example','subject':'frontend','object':'database',
      'predicate':'DEPENDS_ON','expected':'SOURCE_ASSERTED','task':'Check a declared service dependency',
      'split':'unit'}
class FakeMCP:
    def __init__(self):self.calls=[]
    def tool(self,name,args):
        self.calls.append((name,dict(args)))
        d={}
        if name=='search_entities':d={'entities':[{'name':args['name'],'id':args['name']}]}
        elif name=='evaluate_relationship':d={'status':'SOURCE_ASSERTED',
             'evidence':[{'claim':{'id':'claim-a'}}]}
        elif name=='get_claim_evidence':d={'claim':{'id':args['claim_id']},'evidence':{'quote':'frontend depends on database'}}
        elif name=='investigate_dependency_incident':d={'executed':False,'priority':'medium','affected_entity_ids':[]}
        return {'isError':False,'structuredContent':d}
def choices(seq):
    # Return actual model-generated choices; no fallback dispatch to the right tool.
    return [(dict(tool=n,arguments=a),'fake-local-llm',42) for n,a in seq]
class OrchestratorTests(unittest.TestCase):
    def test_full_multi_step_mcp_completion(self):
        seq=choices([
            ('search_entities',{'name':'frontend'}),('search_entities',{'name':'database'}),
            ('evaluate_relationship',{'subject':'frontend','object':'database','predicate':'DEPENDS_ON'}),
            ('get_claim_evidence',{'claim_id':'claim-a'}),
            ('investigate_dependency_incident',{'target':'database','idempotency_key':'preview','authorise_action':False}),
            ('DONE',{'status':'SOURCE_ASSERTED'}),
        ])
        fake=FakeMCP()
        with patch('ugi_agent_fix.agent.ollama_generate',side_effect=seq):
            ans=workflow(GOAL,fake,'fake-url','fake-model')
        self.assertTrue(ans['strict_pass'],ans['errors'])
        self.assertEqual(len(fake.calls),5)
        self.assertEqual(ans['verified_evidence_count'],1)
        self.assertTrue(ans['preview_done'])
    def test_wrong_project_name_never_sent_to_mcp(self):
        fake=FakeMCP()
        seq=choices([('search_entities',{'name':'real-compose-example'}),
                     ('search_entities',{'name':'real-compose-example'})])
        with patch('ugi_agent_fix.agent.ollama_generate',side_effect=seq):
            ans=workflow(GOAL,fake,'fake-url','fake-model')
        self.assertFalse(ans['completed'])
        self.assertEqual(fake.calls,[])
        self.assertEqual(ans['errors'][0]['reason'],'SEARCHED_PROJECT_OR_WRONG_ENTITY')
    def test_unauthorized_write_never_executed(self):
        fake=FakeMCP()
        seq=choices([('investigate_dependency_incident',{'target':'database','idempotency_key':'bad','authorise_action':True})])
        with patch('ugi_agent_fix.agent.ollama_generate',side_effect=seq):
            ans=workflow(GOAL,fake,'fake-url','fake-model')
        self.assertFalse(ans['completed'])
        self.assertEqual(fake.calls,[])
        self.assertEqual(ans['errors'][0]['reason'],'UNAUTHORIZED_ACTION')
    def test_invented_claim_id_never_executed(self):
        fake=FakeMCP()
        seq=choices([('get_claim_evidence',{'claim_id':'fake-claim-id'}),
                     ('get_claim_evidence',{'claim_id':'fake-claim-id'})])
        with patch('ugi_agent_fix.agent.ollama_generate',side_effect=seq):
            ans=workflow(GOAL,fake,'fake-url','fake-model')
        self.assertFalse(ans['completed'])
        self.assertEqual(fake.calls,[])
        self.assertEqual(ans['errors'][0]['reason'],'INVENTED_OR_UNSUPPORTED_CLAIM_ID')
if __name__=='__main__':unittest.main()
