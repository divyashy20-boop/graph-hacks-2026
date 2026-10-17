import json,tempfile,unittest
from pathlib import Path
from ugi_final.report_builder import make
from ugi_final.focused_report import EXPECTED

class ReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();p=Path(self.tmp.name)
        self.f=[str(p/x) for x in ('v5.json','p5.json','combo.json')]
        v5={'results':[{'category':'Real GitHub','title':'Source','status':'PASS'},
             {'category':'AI','title':'Real local LLM next-tool advisory agreement','status':'FAIL'},
             {'category':'Comparison','title':'Legacy LLM-selected strict baseline','status':'FAIL'}],
             'workflows':[{'benchmark_pass':True}]*10,
             'extended_workflows':[{'passed':True}]*39}
        p5={'pass':17,'total':17}
        co={'status':'PASS','passed':11,'total':11,'production_external_actions':False,
            'cases':[{'name':name,'pass':True} for name in EXPECTED]}
        for file,obj in zip(self.f,[v5,p5,co]):Path(file).write_text(json.dumps(obj))
    def tearDown(self):self.tmp.cleanup()
    def test_expected_legacy_qwen_failure_is_reported_not_hidden_or_blocker(self):
        r=make(*self.f,unit_ok=True,patch_ok=True,app_test_status='NOT_RUN')
        self.assertEqual(r['decision'],'QUALIFIED_FOR_FEATURE_FLAGGED_INTEGRATION')
        self.assertEqual(r['llm_baseline']['status'],'FAIL')
        self.assertEqual(r['llm_advice']['status'],'FAIL')
    def test_missing_combined_is_hard_blocker(self):
        Path(self.f[2]).unlink()
        r=make(*self.f,unit_ok=True,patch_ok=True,app_test_status='NOT_RUN')
        self.assertIn('combined_UGI_MCP_P5',r['hard_blockers'])
    def test_missing_combined_case_blocks_even_if_report_claims_pass(self):
        obj=json.loads(Path(self.f[2]).read_text())
        obj['cases'].pop()
        Path(self.f[2]).write_text(json.dumps(obj))
        r=make(*self.f,unit_ok=True,patch_ok=True,app_test_status='NOT_RUN')
        self.assertIn('combined_UGI_MCP_P5',r['hard_blockers'])
    def test_incomplete_live_suite_blocks(self):
        o=json.loads(Path(self.f[0]).read_text());o['extended_workflows'][0]['passed']=False
        Path(self.f[0]).write_text(json.dumps(o))
        r=make(*self.f,unit_ok=True,patch_ok=True,app_test_status='NOT_RUN')
        self.assertIn('rulebook_extended_live',r['hard_blockers'])
    def test_native_UGI_memory_test_fail_when_requested_is_blocker(self):
        r=make(*self.f,unit_ok=True,patch_ok=True,app_test_status='FAIL')
        self.assertIn('optional_UGI_native_offline',r['hard_blockers'])
    def test_unit_regression_blocks_even_all_other_green(self):
        r=make(*self.f,unit_ok=False,patch_ok=True,app_test_status='NOT_RUN')
        self.assertIn('offline_test_suite',r['hard_blockers'])

if __name__=='__main__':unittest.main()
