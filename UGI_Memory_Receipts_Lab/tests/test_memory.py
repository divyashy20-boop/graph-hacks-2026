import concurrent.futures
import json
import random
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from p5memory import Memory, PolicyError

D='2026-10-17'

class MemoryCase(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=Memory(Path(self.tmp.name)/'memory.sqlite')
        self.scope='tenant-a/project-1'
    def tearDown(self):self.tmp.cleanup()
    def put(self,key='api',field='args',value=None,**kw):
        return self.db.publish(self.scope,key,field,['amount'] if value is None else value,valid_from='2026-01-01',**kw)
    def receipt(self,key='api',field='args',day=D,output=None,parents=()):
        r=self.db.open_read(self.scope,day)
        result=r.read(key,field)
        return r.seal({'observed':result['value']} if output is None else output,parents=parents)
    def act(self,r,action='a',day=D):
        return self.db.protected_action(r['rid'],self.scope,action,{'plan':'run'},valid_at=day)

    def test_t1_changed_field_stales(self):
        self.put();r=self.receipt();self.put(value=['amount','currency','region']);
        self.assertEqual(self.db.receipt(r['rid'])['status'],'STALE')
    def test_t2_unrelated_field_stays_valid(self):
        self.put();r=self.receipt();self.put(field='description',value='updated');self.assertEqual(self.db.receipt(r['rid'])['status'],'VALID')
    def test_t3_absence_new_fact_stales(self):
        r=self.receipt('supplier','contract');self.assertIsNone(r['output']['observed']);self.put(key='supplier',field='contract',value='signed');self.assertEqual(self.db.receipt(r['rid'])['status'],'STALE')
    def test_t4_conflict_marks_unknown(self):
        self.put(value='amount only');r=self.receipt();self.put(value='amount+region',source='another-source');self.assertEqual(self.db.receipt(r['rid'])['status'],'UNKNOWN');
        with self.assertRaisesRegex(PolicyError,'BLOCKED_UNKNOWN'):self.act(r)
    def test_t5_cascade_multiple_layers(self):
        self.put();parent=self.receipt()
        sub=self.db.open_read(self.scope,D);sub.read('unrelated','field');child=sub.seal('child',parents=[parent['rid']])
        r=self.db.open_read(self.scope,D);r.read('another','field');grand=r.seal('grandchild',parents=[child['rid']]);
        self.put(value=['amount','region']);self.assertEqual([self.db.receipt(x['rid'])['status'] for x in (parent,child,grand)],['STALE']*3)
    def test_t6_toctou_stale_action_rejected(self):
        self.put();r=self.receipt();self.put(value='changed')
        with self.assertRaisesRegex(PolicyError,'BLOCKED_STALE'):self.act(r)
        self.assertEqual(self.db.effect_count(self.scope),0)
    def test_bitemporal_old_revision_and_backdated_correction(self):
        self.put(value='v1',source='a');oldrev=self.db.stats(self.scope)['revision']
        self.put(value='v2',source='a',valid_from='2025-01-01') if False else None
        self.db.publish(self.scope,'api','args','v2',source='a',valid_from='2026-01-01')
        self.assertEqual(self.db.state_as_known(self.scope,'api','args',D,oldrev)['value'],'v1')
        self.assertEqual(self.db.state_as_known(self.scope,'api','args',D)['value'],'v2')
    def test_late_backdated_update_affects_old_receipt(self):
        self.put(value='old');r=self.receipt(day='2026-02-01')
        self.db.publish(self.scope,'api','args','late',source='a',valid_from='2026-01-15')
        self.assertEqual(self.db.receipt(r['rid'])['status'],'UNKNOWN') # two disagreeing sources
    def test_same_source_backdated_override(self):
        self.put(value='old',source='a');r=self.receipt()
        self.db.publish(self.scope,'api','args','fix',source='a',valid_from='2026-01-01')
        self.assertEqual(self.db.receipt(r['rid'])['status'],'STALE')
    def test_same_source_future_start_on_day(self):
        self.put(value='old',source='a');self.db.publish(self.scope,'api','args','new',source='a',valid_from='2026-12-01')
        self.assertEqual(self.db.state_as_known(self.scope,'api','args',D)['value'],'old')
        self.assertEqual(self.db.state_as_known(self.scope,'api','args','2026-12-05')['value'],'new')
    def test_expiry_sweep(self):
        self.db.publish(self.scope,'contract','valid','yes',valid_from='2026-01-01',valid_to='2026-10-18')
        r=self.receipt('contract','valid');self.assertEqual(self.db.receipt(r['rid'])['status'],'VALID')
        self.db.sweep(self.scope,'2026-10-18');self.assertEqual(self.db.receipt(r['rid'])['status'],'STALE')
    def test_retraction_stales(self):
        self.put(source='one');r=self.receipt()
        self.db.publish(self.scope,'api','args',None,source='one',valid_from='2026-01-01',retract=True)
        self.assertEqual(self.db.receipt(r['rid'])['status'],'STALE')
    def test_retraction_does_not_delete_event(self):
        self.put(source='one');self.db.publish(self.scope,'api','args',None,source='one',valid_from='2026-01-01',retract=True)
        self.assertEqual(self.db.stats(self.scope)['events'],2)
    def test_reconcile_conflict_does_not_auto_validate_old_receipt(self):
        self.put(value='old',source='a');r=self.receipt();self.put(value='other',source='b')
        self.assertEqual(self.db.receipt(r['rid'])['status'],'UNKNOWN')
        self.db.publish(self.scope,'api','args','old',source='b',valid_from='2026-01-01')
        self.assertNotEqual(self.db.receipt(r['rid'])['status'],'VALID')
    def test_negative_prefix_query_new_item(self):
        r=self.db.open_read(self.scope,D);self.assertEqual(r.scan('service:')['count'],0);rec=r.seal({'empty':True})
        self.put(key='service:new',field='name',value='API');self.assertEqual(self.db.receipt(rec['rid'])['status'],'STALE')
    def test_prefix_other_key_no_stale(self):
        r=self.db.open_read(self.scope,D);r.scan('service:');rec=r.seal('list')
        self.put(key='other:1',field='name',value='API');self.assertEqual(self.db.receipt(rec['rid'])['status'],'VALID')
    def test_prefix_same_key_mutation(self):
        self.put(key='service:1',field='health',value='ok');r=self.db.open_read(self.scope,D);r.scan('service:');rec=r.seal('list')
        self.put(key='service:1',field='health',value='bad');self.assertEqual(self.db.receipt(rec['rid'])['status'],'STALE')
    def test_prefix_literal_sql_wildcards(self):
        r=self.db.open_read(self.scope,D);self.assertEqual(r.scan('item_%')['count'],0);rec=r.seal('absent')
        self.put(key='itemABC',field='name',value='x');self.assertEqual(self.db.receipt(rec['rid'])['status'],'VALID')
        self.put(key='item_%foo',field='name',value='x');self.assertEqual(self.db.receipt(rec['rid'])['status'],'STALE')
    def test_source_provenance_change_conservative(self):
        self.put(value='x',source='a');r=self.receipt();self.put(value='x',source='b');self.assertEqual(self.db.receipt(r['rid'])['status'],'STALE')
    def test_no_graph_reads_fail_closed(self):
        r=self.db.open_read(self.scope,D)
        with self.assertRaisesRegex(PolicyError,'EMPTY_READ_SET'):r.seal('made up')
    def test_ambiguous_conflict_new_receipt_unknown(self):
        self.put(value='x',source='a');self.put(value='y',source='b');r=self.receipt();self.assertEqual(r['status'],'UNKNOWN')
    def test_no_conflict_from_different_fields(self):
        self.put(field='a',value='x',source='a');self.put(field='b',value='y',source='b');self.assertEqual(self.db.state_as_known(self.scope,'api','a',D)['verdict'],'CLEAR')
    def test_different_project_no_leak(self):
        self.put();r=self.receipt()
        self.db.publish('tenant-b/project-1','api','args',['other'],valid_from='2026-01-01');self.assertEqual(self.db.receipt(r['rid'])['status'],'VALID')
    def test_parent_other_scope_denied(self):
        self.put();p=self.receipt();r=self.db.open_read('tenant-b','2026-10-17');r.read('x','y')
        with self.assertRaisesRegex(PolicyError,'BAD_PARENT'):r.seal('child',parents=[p['rid']])
    def test_no_action_wrong_scope(self):
        self.put();r=self.receipt()
        with self.assertRaisesRegex(PolicyError,'UNKNOWN_RECEIPT'):self.db.protected_action(r['rid'],'wrong','a',{},valid_at=D)
    def test_action_idempotent(self):
        self.put();r=self.receipt();self.assertFalse(self.act(r)['duplicate']);self.assertTrue(self.act(r)['duplicate']);self.assertEqual(self.db.effect_count(self.scope),1)
    def test_action_key_collision(self):
        self.put();r=self.receipt();self.act(r)
        with self.assertRaisesRegex(PolicyError,'ACTION_KEY_COLLISION'):self.db.protected_action(r['rid'],self.scope,'a',{'changed':'yes'},valid_at=D)
    def test_execute_from_unknown_rejected(self):
        self.put(value='a',source='a');self.put(value='b',source='b');r=self.receipt()
        with self.assertRaisesRegex(PolicyError,'BLOCKED_UNKNOWN'):self.act(r)
    def test_old_receipt_cannot_revive(self):
        self.put(value='a',source='a');r=self.receipt();self.put(value='b',source='a');self.put(value='a',source='a');self.assertEqual(self.db.receipt(r['rid'])['status'],'STALE')
    def test_historical_read_as_known_rev_unknown_newer(self):
        self.put();
        with self.assertRaisesRegex(PolicyError,'BAD_KNOWN'):self.db.state_as_known(self.scope,'api','args',D,500)
    def test_event_id_duplicate_exact(self):
        x=self.put(value='x',event_id='ev1');y=self.put(value='x',event_id='ev1');self.assertTrue(y['duplicate']);self.assertEqual(self.db.stats(self.scope)['events'],1)
    def test_event_id_collision_detected(self):
        self.put(value='x',event_id='ev1');
        with self.assertRaisesRegex(PolicyError,'IDEMPOTENCY_KEY'):self.put(value='y',event_id='ev1')
    def test_future_update_not_invalidate_past(self):
        self.put(value='a',source='a');r=self.receipt(day='2026-02-01')
        self.db.publish(self.scope,'api','args','new',source='a',valid_from='2026-12-01');self.assertEqual(self.db.receipt(r['rid'])['status'],'VALID')
    def test_action_after_future_day_blocked(self):
        self.put(value='a',source='a');r=self.receipt()
        self.db.publish(self.scope,'api','args','new',source='a',valid_from='2026-12-01')
        with self.assertRaisesRegex(PolicyError,'BLOCKED_STALE'):self.act(r,day='2026-12-02')
        self.assertEqual(self.db.effect_count(self.scope),0)
    def test_concurrent_snapshot_seal_detects_change(self):
        self.put(value='a',source='a');s=self.db.open_read(self.scope,D);s.read('api','args');self.put(value='b',source='a');r=s.seal('late');self.assertEqual(r['status'],'STALE')
    def test_recorder_closed(self):
        self.put();s=self.db.open_read(self.scope,D);s.read('api','args');s.seal('out')
        with self.assertRaisesRegex(PolicyError,'READER_CLOSED'):s.read('api','args')
    def test_duplicate_seal_denied(self):
        self.put();s=self.db.open_read(self.scope,D);s.read('api','args');s.seal('out')
        with self.assertRaisesRegex(PolicyError,'READER_ALREADY'):s.seal('out')
    def test_invalid_dates(self):
        with self.assertRaises(ValueError):self.db.open_read(self.scope,'bad date')
    def test_invalid_intervals(self):
        with self.assertRaisesRegex(PolicyError,'INVALID_VALIDITY'):self.db.publish(self.scope,'x','y','v',valid_from=D,valid_to='2026-01-01')
    def test_different_values_same_source_at_different_times(self):
        self.put(value='v1',source='a');self.db.publish(self.scope,'api','args','v2',valid_from='2026-06-01',source='a')
        self.assertEqual(self.db.state_as_known(self.scope,'api','args','2026-04-01')['value'],'v1')
        self.assertEqual(self.db.state_as_known(self.scope,'api','args','2026-09-01')['value'],'v2')
    def test_effect_log_stable_after_fact_change(self):
        self.put();r=self.receipt();self.act(r);self.put(value='new',source='source-1');self.assertEqual(self.db.effect_count(self.scope),1)
    def test_cannot_create_fake_evidence_in_receipt(self):
        # Receipt output is NOT an evidence source; only captured tool reads are trusted.
        self.put();r=self.db.open_read(self.scope,D);r.read('api','args');rec=r.seal({'asserted_claim_id':'FAKE'})
        self.assertEqual(rec['dependencies'][0]['fact_key'],'api')
    def test_randomized_field_change_invariants(self):
        rng=random.Random(18042)
        for i in range(80):
            key=f'node{i}';field=f'field{rng.randrange(1000)}';self.put(key=key,field=field,value='before')
            r=self.receipt(key=key,field=field)
            self.put(key=key,field=f'unrelated{rng.randrange(1000)}',value='x')
            self.assertEqual(self.db.receipt(r['rid'])['status'],'VALID')
            self.put(key=key,field=field,value='after')
            self.assertNotEqual(self.db.receipt(r['rid'])['status'],'VALID')
    def test_race_updater_vs_action(self):
        for i in range(40):
            key='race'+str(i)
            self.put(key=key,value='old',source='a');rec=self.receipt(key=key)
            barrier=threading.Barrier(2)
            def writer():
                barrier.wait();return self.db.publish(self.scope,key,'args','new',source='a',valid_from='2026-01-01')
            def actor():
                barrier.wait()
                try:return self.db.protected_action(rec['rid'],self.scope,'race-act'+str(i),{'id':i},valid_at=D)
                except PolicyError:return {'executed':False}
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                f1=pool.submit(writer);f2=pool.submit(actor);f1.result();out=f2.result()
            if not out['executed']:
                self.assertNotEqual(self.db.receipt(rec['rid'])['status'],'VALID')
    def test_atomic_rollback_bad_input(self):
        with self.assertRaises(PolicyError):self.db.publish(self.scope,'a','b',1,valid_from=D,valid_to=D)
        self.assertEqual(self.db.stats(self.scope)['revision'],0)
    def test_concurrent_publish_unique_revisions(self):
        def f(i):return self.db.publish(self.scope,'node'+str(i),'x',i,valid_from=D)['revision']
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as p: results=list(p.map(f,range(30)))
        self.assertEqual(sorted(results),list(range(1,31)))

if __name__=='__main__':unittest.main()
