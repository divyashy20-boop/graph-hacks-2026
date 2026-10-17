"""Regression cases grounded in real UGI + MCP handler and P5 sidecar.

These run with UGI's in-memory graph implementation, not FalkorDB. The Windows
focused runner separately executes the eleven actual FalkorDB/MCP test cases.
"""
import sys
import tempfile
import unittest
from pathlib import Path

from p5memory.core import Memory, PolicyError
from ugi_final.bridge import receipt_read_differences, BridgeError
from test_ugi_memory_integration import ActualUGIEngineCombo


class PrecedenceAndReadSetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.mem=Memory(Path(self.tmp.name)/'case.sqlite3')
        self.scope='isolated::tenant::dataset'
        self.day='2026-10-17'
    def tearDown(self):
        self.tmp.cleanup()

    def test_stale_receipt_escalates_unknown_if_another_read_conflicts(self):
        self.mem.publish(self.scope,'a','/v','old',valid_from=self.day)
        self.mem.publish(self.scope,'b','/v','stable',valid_from=self.day)
        reader=self.mem.open_read(self.scope,self.day)
        reader.read('a','/v');reader.read('b','/v')
        receipt=reader.seal({'answer':'old'})
        self.mem.publish(self.scope,'a','/v','new',valid_from=self.day)
        self.assertEqual(self.mem.receipt(receipt['rid'])['status'],'STALE')
        self.mem.publish(self.scope,'b','/v','opposing',source='different-source',valid_from=self.day)
        self.assertEqual(self.mem.receipt(receipt['rid'])['status'],'UNKNOWN')
        with self.assertRaises(PolicyError):
            self.mem.protected_action(receipt['rid'],self.scope,'no-effect',{'x':1},valid_at=self.day)
        self.assertEqual(self.mem.effect_count(self.scope),0)

    def test_unknown_never_downgrades_to_stale_or_valid_after_conflict_ends(self):
        self.mem.publish(self.scope,'a','/v','yes',valid_from=self.day)
        rd=self.mem.open_read(self.scope,self.day);rd.read('a','/v')
        receipt=rd.seal({'answer':'yes'})
        self.mem.publish(self.scope,'a','/v','no',source='opponent',valid_from=self.day)
        self.assertEqual(self.mem.receipt(receipt['rid'])['status'],'UNKNOWN')
        self.mem.publish(self.scope,'a','/v',None,source='opponent',retract=True,valid_from=self.day)
        self.mem.publish(self.scope,'a','/v','third',valid_from=self.day)
        self.assertEqual(self.mem.receipt(receipt['rid'])['status'],'UNKNOWN')
        with self.assertRaises(PolicyError):
            self.mem.protected_action(receipt['rid'],self.scope,'never-effect',{},valid_at=self.day)

    def test_unrelated_field_change_keeps_original_receipt_valid(self):
        self.mem.publish(self.scope,'a','/v',10,valid_from=self.day)
        rd=self.mem.open_read(self.scope,self.day);rd.read('a','/v')
        receipt=rd.seal({'answer':10})
        self.mem.publish(self.scope,'b','/v',20,valid_from=self.day)
        self.assertEqual(self.mem.receipt(receipt['rid'])['status'],'VALID')
        self.assertEqual(receipt_read_differences(self.mem,receipt['rid'],scope=self.scope),[])

    def test_read_diff_refuses_other_tenant_scope(self):
        self.mem.publish(self.scope,'a','/v',10,valid_from=self.day)
        rd=self.mem.open_read(self.scope,self.day);rd.read('a','/v')
        receipt=rd.seal({'answer':10})
        with self.assertRaises(BridgeError):
            receipt_read_differences(self.mem,receipt['rid'],scope='other::tenant::dataset')

    def test_change_then_reversal_never_revives_original_receipt(self):
        self.mem.publish(self.scope,'a','/v','v1',valid_from=self.day)
        rd=self.mem.open_read(self.scope,self.day);rd.read('a','/v')
        receipt=rd.seal({'answer':'v1'})
        self.mem.publish(self.scope,'a','/v','v2',valid_from=self.day)
        self.mem.publish(self.scope,'a','/v','v1',valid_from=self.day)
        self.assertEqual(self.mem.receipt(receipt['rid'])['status'],'STALE')
        self.assertEqual(receipt_read_differences(self.mem,receipt['rid'],scope=self.scope),[])
        with self.assertRaises(PolicyError):
            self.mem.protected_action(receipt['rid'],self.scope,'no-revive',{},valid_at=self.day)


class ActualUGICombinedRegression(ActualUGIEngineCombo):
    # unittest discovers inherited cases as well; acceptable and useful:
    # repeat source evidence, negative edge, conflict and action safety checks.

    def test_refresh_by_other_receipt_counts_zero_but_original_dependency_changed(self):
        p=self.track('Does web directly depend on redis?')
        n=self.track('Does redis directly depend on web?')
        self.ingest('new-opposite-edge',[('redis','web','positive')])
        n_refresh=self.refresh(n)
        self.assertGreater(n_refresh['changed'],0)
        self.assertEqual(self.memory.receipt(p['receipt']['rid'])['status'],'STALE')
        # Shared entity search observations were synchronized by n_refresh.
        p_refresh=self.refresh(p)
        self.assertEqual(p_refresh['changed'],0)
        self.assertGreater(p_refresh['original_read_difference_count'],0)
        self.assertEqual(p_refresh['receipt_status'],'STALE')
        self.assertEqual(self.memory.effect_count(self.scope),0)

    def test_real_ugi_stale_receipt_then_opposing_assertion_escalates_unknown(self):
        p=self.track('Does web directly depend on redis?')
        n=self.track('Does redis directly depend on web?')
        self.ingest('reverse-edge',[('redis','web','positive')])
        self.refresh(n)
        self.assertEqual(self.memory.receipt(p['receipt']['rid'])['status'],'STALE')
        self.ingest('contradicting-edge',[('web','redis','negative')])
        conflict_refresh=self.refresh(p)
        self.assertEqual(conflict_refresh['receipt_status'],'UNKNOWN')
        self.assertGreater(conflict_refresh['original_read_difference_count'],0)
        with self.assertRaises(PolicyError):
            self.memory.protected_action(p['receipt']['rid'],self.scope,'conflict-no-exec',{},valid_at='2026-10-17')
        self.assertEqual(self.memory.effect_count(self.scope),0)

    def test_unrelated_real_ugi_relationship_does_not_invalidate(self):
        p=self.track('Does web directly depend on redis?')
        self.ingest('completely-unrelated',[('service-x','service-y','positive')])
        refreshed=self.refresh(p)
        self.assertEqual(refreshed['changed'],0)
        self.assertEqual(refreshed['original_read_difference_count'],0)
        self.assertEqual(refreshed['receipt_status'],'VALID')

class FocusedReportGuardTests(unittest.TestCase):
    def test_missing_case_cannot_be_silently_qualified(self):
        from ugi_final.focused_report import make_report,EXPECTED
        incomplete={'cases':[{'name':name,'pass':True} for name in EXPECTED[:-1]],
                    'passed':10,'total':10,'status':'PASS','production_external_actions':False}
        self.assertEqual(make_report(incomplete,'PASS','PASS')['decision'],'NOT_QUALIFIED_FIX_FAILURES')

    def test_duplicate_case_cannot_be_silently_qualified(self):
        from ugi_final.focused_report import make_report,EXPECTED
        duplicate={'cases':[{'name':name,'pass':True} for name in EXPECTED[:-1]]
                    +[{'name':EXPECTED[0],'pass':True}],
                    'passed':11,'total':11,'status':'PASS','production_external_actions':False}
        self.assertEqual(make_report(duplicate,'PASS','PASS')['decision'],'NOT_QUALIFIED_FIX_FAILURES')

    def test_only_all_eleven_safe_checks_qualify_for_next_stage(self):
        from ugi_final.focused_report import make_report,EXPECTED
        full={'cases':[{'name':name,'pass':True} for name in EXPECTED],
              'passed':11,'total':11,'status':'PASS','production_external_actions':False}
        self.assertEqual(make_report(full,'PASS','PASS')['decision'],'READY_FOR_FEATURE_FLAGGED_INTEGRATION_TEST')
        full['production_external_actions']=True
        self.assertEqual(make_report(full,'PASS','PASS')['decision'],'NOT_QUALIFIED_FIX_FAILURES')


if __name__=='__main__':
    unittest.main()
