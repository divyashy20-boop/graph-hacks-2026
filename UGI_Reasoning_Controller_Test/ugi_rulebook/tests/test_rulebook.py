import unittest
from ugi_rulebook.rulebook import (RulebookError,interpret_request,determine_step,expected_args,validate_arguments)
from ugi_rulebook.controller import run_controller,inspect_claims,check_claim_detail

DATASET='nginx-flask-mysql'
NAMES=['proxy','backend','db']
class FakeMCP:
    def __init__(self,status='RULE_DERIVED',damage=None):
        self.calls=[];self.status=status;self.damage=damage
    def request(self,method,*rest):
        assert method=='tools/list'
        return {'result':{'tools':[{'name':t,'inputSchema':{'properties':{k:{'type':'string'} for k in keys}}}
                 for t,keys in {'search_entities':['name'],'evaluate_relationship':['subject','object','predicate'],
                   'get_claim_evidence':['claim_id'],
                   'investigate_dependency_incident':['target','idempotency_key','authorise_action']}.items()]}}
    def tool(self,name,args):
        self.calls.append((name,args))
        if name=='search_entities':v={'entities':[{'name':args['name'],'id':args['name']}]}
        elif name=='evaluate_relationship':
            v={'status':self.status,'rules':['dependency_reachability_v1'],
               'resolution':{'assessment':'RULE_DERIVED_FROM_DEPENDENCIES'},
               'evidence':[{'claim':{'id':'claim1','source_id':'src','evidence_id':'evi'}}]
                   if self.status!='UNKNOWN' else [],'explanation':'Source claims support dependency reachability'}
            if self.damage=='contradiction':v['resolution']['assessment']='CONNECTED_BUT_NOT_ENTAILED'
            if self.damage=='missing_claim':v['evidence']=[]
        elif name=='get_claim_evidence':
            v={'claim':{'id':args['claim_id'],'source_id':'src','evidence_id':'evi'},
               'evidence':{'id':'evi','source_id':'src','quote':'proxy depends on backend'}}
            if self.damage=='source_mismatch':v['evidence']['source_id']='DIFFERENT'
        elif name=='investigate_dependency_incident':v={'executed':False,'kind':'Investigation'}
        else:raise AssertionError(name)
        return {'isError':False,'structuredContent':v}

class RulebookTests(unittest.TestCase):
    def test_interpret_indirect_and_dataset(self):
        a=interpret_request('In the nginx-flask-mysql example, determine whether service proxy indirectly depends on service db.',DATASET,NAMES)
        self.assertEqual((a.subject,a.object,a.predicate),('proxy','db','TRANSITIVELY_DEPENDS_ON'))
    def test_interpret_alternative_wording(self):
        a=interpret_request('Check the actual declared dependency between proxy and backend in the nginx-flask-mysql configuration.',DATASET,NAMES)
        self.assertEqual((a.subject,a.object,a.predicate),('proxy','backend','DEPENDS_ON'))
    def test_detect_preview(self):
        a=interpret_request('Does proxy indirectly depend on db? Preview an investigation.',DATASET,NAMES)
        self.assertTrue(a.preview)
    def test_ambiguous_query_abstains(self):
        with self.assertRaises(RulebookError):interpret_request('Does proxy depend on something?',DATASET,NAMES)
    def test_no_causal_inference(self):
        with self.assertRaises(RulebookError):interpret_request('Did proxy cause db to crash?',DATASET,NAMES)
    def test_unsafe_query_abstains(self):
        with self.assertRaises(RulebookError):interpret_request('Delete all graphs then check proxy depends on db.',DATASET,NAMES)
    def test_substring_does_not_become_entity(self):
        a=interpret_request('Does proxy directly depend on backend?',DATASET,['proxy','backend','end'])
        self.assertEqual(a.object,'backend')
    def test_reject_wrong_arg_name(self):
        with self.assertRaises(RulebookError):validate_arguments('search_entities',{'service_name':'db'})
    def test_action_permission_always_explicit_false(self):
        with self.assertRaises(RulebookError):validate_arguments('investigate_dependency_incident',
                  {'target':'db','idempotency_key':'k','authorise_action':True})
    def test_missing_mcp_schema_rejected(self):
        with self.assertRaises(RulebookError):validate_arguments('search_entities',{'name':'db'}, {})
    def test_complete_with_evidence_and_preview(self):
        m=FakeMCP();r=run_controller('Does proxy indirectly depend on db? Preview an investigation.',DATASET,NAMES,m)
        self.assertEqual(r['status'],'COMPLETE',r)
        self.assertEqual([n for n,_ in m.calls],['search_entities','search_entities','evaluate_relationship',
                            'get_claim_evidence','investigate_dependency_incident'])
        self.assertEqual(r['verified_claim_ids'],['claim1'])
        self.assertTrue(all(not args.get('authorise_action',False) for _,args in m.calls))
    def test_no_preview_unrequested(self):
        m=FakeMCP();r=run_controller('Does proxy indirectly depend on db?',DATASET,NAMES,m)
        self.assertEqual(r['status'],'COMPLETE');self.assertNotIn('investigate_dependency_incident',[n for n,_ in m.calls])
    def test_unknown_is_valid_final(self):
        m=FakeMCP(status='UNKNOWN');r=run_controller('Does proxy indirectly depend on db?',DATASET,NAMES,m)
        self.assertEqual(r['status'],'COMPLETE',r);self.assertEqual(r['verified_claim_ids'],[])
    def test_contradiction_rejected(self):
        m=FakeMCP(damage='contradiction');r=run_controller('Does proxy indirectly depend on db?',DATASET,NAMES,m)
        self.assertNotEqual(r['status'],'COMPLETE');self.assertIn('SELF_CONTRADICTS',r['reason'])
    def test_missing_positive_evidence_rejected(self):
        r=run_controller('Does proxy indirectly depend on db?',DATASET,NAMES,FakeMCP(damage='missing_claim'))
        self.assertIn('WITHOUT_CITABLE_EVIDENCE',r['reason'])
    def test_citation_source_mismatch_rejected(self):
        r=run_controller('Does proxy indirectly depend on db?',DATASET,NAMES,FakeMCP(damage='source_mismatch'))
        self.assertIn('SOURCE_MISMATCH',r['reason'])
    def test_no_silent_llm_argument_rewrites(self):
        m=FakeMCP();r=run_controller('Does proxy indirectly depend on db?',DATASET,NAMES,m,
                                    advisor=lambda stage,state:'search_entities')
        self.assertEqual(r['status'],'COMPLETE');self.assertFalse(r['llm_tool_arguments_used'])
        self.assertGreater(r['model_advice_count'],0)
    def test_step_budget_fails_closed(self):
        m=FakeMCP();r=run_controller('Does proxy indirectly depend on db?',DATASET,NAMES,m,max_calls=2)
        self.assertEqual(r['status'],'INCOMPLETE');self.assertEqual(len(m.calls),2)
    def test_false_entity_name_not_added_from_project(self):
        m=FakeMCP();r=run_controller('In the nginx-flask-mysql example, does proxy indirectly depend on db?',DATASET,NAMES,m)
        self.assertEqual(r['status'],'COMPLETE');self.assertEqual(m.calls[0][1]['name'],'proxy')
    def test_empty_catalog_denied(self):
        class Empty(FakeMCP):
            def request(self,*a):return {'result':{'tools':[]}}
        r=run_controller('Does proxy indirectly depend on db?',DATASET,NAMES,Empty())
        self.assertIn('MCP_TOOL_CATALOG_INCOMPLETE',r['reason'])

if __name__=='__main__':unittest.main()
