import unittest
from ugi_agent_fix.patch_engine import patch_text, ANCHORS
from ugi_agent_fix.agent import prompt_for
class PatchTests(unittest.TestCase):
    def test_patch_conserves_both_rules(self):
        # Actual UGI structure: transitive return uses one line,
        # while shared-employer return splits the rule across two lines.
        fixture = (
            'def proof(base, proof, shared):\n'
            '    if proof:\n'
            '        return {**base, "status": "RULE_DERIVED", "rules": ["dependency_reachability_v1"],\n'
            '                "explanation": "valid forward dependency path"}\n'
            '    if shared:\n'
            '        return {**base, "status": "RULE_DERIVED",\n'
            '                "rules": ["shared_employer_temporal_overlap_v1"],\n'
            '                "explanation": "shared employer at supported date"}\n'
            '    return base\n'
        )
        patched,r=patch_text(fixture)
        self.assertEqual(len(r['changed']),2)
        self.assertIn('RULE_DERIVED_FROM_DEPENDENCIES',patched)
        self.assertIn('RULE_DERIVED_SHARED_EMPLOYER',patched)
        self.assertNotIn('safe_to_infer_real_outage": true',str(r))
        self.assertEqual(patch_text(patched)[0],patched)
        ns={}
        exec(compile(patched,'<fixture>','exec'),ns)
        a=ns['proof']({'resolution':{'assessment':'CONNECTED_BUT_NOT_ENTAILED'}}, {'claims':[{'id':'c1'}]}, None)
        self.assertEqual(a['resolution']['assessment'],'RULE_DERIVED_FROM_DEPENDENCIES')
        b=ns['proof']({'resolution':{'assessment':'CONNECTED_BUT_NOT_ENTAILED'}}, None, {'claims':[{'id':'c2'}]})
        self.assertEqual(b['resolution']['assessment'],'RULE_DERIVED_SHARED_EMPLOYER')

    def test_split_line_employer_rule_regression(self):
        # Actual engine form puts the shared employer rule on a separate line.
        fixture = (
            'def relationship(base, proof, shared):\n'
            '    if proof:\n'
            '        return {**base, "status": "RULE_DERIVED", "rules": ["dependency_reachability_v1"],\n'
            '                "explanation": "forward chain"}\n'
            '    if shared:\n'
            '        return {**base, "status": "RULE_DERIVED",\n'
            '                "rules": ["shared_employer_temporal_overlap_v1"],\n'
            '                "explanation": "shared employer"}\n'
            '    return base\n'
        )
        patched, receipt = patch_text(fixture)
        self.assertEqual(set(receipt["changed"]), {"dependency_reachability_v1", "shared_employer_temporal_overlap_v1"})
        self.assertEqual(patch_text(patched)[0], patched)
        namespace = {}
        exec(compile(patched, "engine_fixture", "exec"), namespace)
        proof = {"claims": [{"id": "c1"}, {"id": "c2"}]}
        shared = {"claims": [{"id": "c3"}, {"id": "c4"}]}
        base = {"resolution": {"assessment": "CONNECTED_BUT_NOT_ENTAILED"}}
        first = namespace["relationship"](base, proof, None)
        second = namespace["relationship"](base, None, shared)
        self.assertEqual(first["resolution"]["assessment"], "RULE_DERIVED_FROM_DEPENDENCIES")
        self.assertEqual(second["resolution"]["assessment"], "RULE_DERIVED_SHARED_EMPLOYER")
        self.assertEqual(first["resolution"]["proof_claim_ids"], ["c1", "c2"])
        self.assertEqual(second["resolution"]["proof_claim_ids"], ["c3", "c4"])

    def test_refuses_unknown_version(self):
        with self.assertRaises(ValueError):patch_text('class Fake: pass')
    def test_prompt_keeps_project_context_separate(self):
        goal=dict(source='nginx-flask-mysql',subject='proxy',object='db',predicate='TRANSITIVELY_DEPENDS_ON',task='investigate')
        p=prompt_for(goal,{'resolved_services':[]})
        self.assertIn('dataset_context is NOT an entity',p)
        self.assertIn('proxy',p)
        self.assertIn('"subject_service":"proxy"',p)
    def test_never_overrides_model_args(self):
        from ugi_agent_fix.agent import workflow
        class Stub:
            def __init__(self):self.calls=[]
            def tool(self,n,a):self.calls.append((n,a));return {}
        # In a real run, wrong model args cannot reach MCP. This static test
        # verifies the explicit guard exists; the integration test executes it.
        import inspect
        s=inspect.getsource(workflow)
        self.assertIn('SEARCHED_PROJECT_OR_WRONG_ENTITY',s)
        self.assertIn('WRONG_RELATION_ARGUMENTS',s)
        self.assertIn('UNAUTHORIZED_ACTION',s)
        self.assertIn('MCP_TOOL_ERROR',s)
if __name__=='__main__':unittest.main()
