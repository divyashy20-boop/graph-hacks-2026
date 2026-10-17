import unittest
from unittest.mock import patch
from ugi_krish_validation_v2.full_audit import (test_llm_choices as run_model_trial,
                                             ollama_model_available, digest, check,
                                             offline_tests, MCPStdio)

class FakeMCP:
    def __init__(self):
        self.calls=[]
    def tool(self,name,args):
        self.calls.append((name,dict(args)))
        return {'isError':False}

class CombinedAuditTests(unittest.TestCase):
    def test_offline_check(self):
        self.assertEqual(offline_tests()['status'],'PASS')

    def test_model_actual_arguments_used(self):
        valid=[
            {'tool':'search_entities','arguments':{'name':'Cache'}},
            {'tool':'evaluate_relationship','arguments':{'subject':'Checkout','object':'Cache','predicate':'TRANSITIVELY_DEPENDS_ON'}},
            {'tool':'get_claim_evidence','arguments':{'claim_id':'c1'}},
            {'tool':'investigate_dependency_incident','arguments':{'target':'Cache','idempotency_key':'trial','authorise_action':False}},
            {'tool':'search_entities','arguments':{'name':'Ghost-Not-Present'}},
            {'tool':'ABSTAIN','arguments':{}},
        ]
        mcp=FakeMCP()
        with patch('ugi_krish_validation_v2.full_audit.ollama_model_available',return_value=True), \
             patch('ugi_krish_validation_v2.full_audit.ollama_generate',side_effect=[(v,'mock',1) for v in valid]):
            out=run_model_trial(mcp,'c1','http://fake','fake')
        self.assertEqual(out['status'],'PASS')
        self.assertEqual(out['evidence']['correct'],6)
        self.assertEqual(len(mcp.calls),5)
        self.assertEqual(mcp.calls[3][1]['idempotency_key'],'trial')

    def test_wrong_model_arguments_not_overridden(self):
        bad=[{'tool':'search_entities','arguments':{'name':'WRONG'}}]*6
        mcp=FakeMCP()
        with patch('ugi_krish_validation_v2.full_audit.ollama_model_available',return_value=True), \
             patch('ugi_krish_validation_v2.full_audit.ollama_generate',side_effect=[(v,'mock',1) for v in bad]):
            out=run_model_trial(mcp,'c1','http://fake','fake')
        self.assertEqual(out['status'],'FAIL')
        self.assertEqual(len(mcp.calls),0)

    def test_missing_model_is_inconclusive(self):
        with patch('ugi_krish_validation_v2.full_audit.ollama_model_available',return_value=False):
            self.assertEqual(run_model_trial(FakeMCP(),'c1','http://fake','missing')['status'],'INCONCLUSIVE')

    def test_digests_are_stable(self):
        self.assertEqual(digest({'a':1,'b':2}),digest({'b':2,'a':1}))
        self.assertNotEqual(digest({'b':2}),digest({'b':3}))

if __name__=='__main__': unittest.main()
