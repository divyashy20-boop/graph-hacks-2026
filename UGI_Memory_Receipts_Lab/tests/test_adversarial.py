import concurrent.futures,random,tempfile,threading,time,unittest
from pathlib import Path
from p5memory import Memory,PolicyError
D='2026-10-17'
class AdversarialTests(unittest.TestCase):
 def setUp(self):self.t=tempfile.TemporaryDirectory();self.m=Memory(Path(self.t.name)/'d.sqlite');self.s='tenant/private'
 def tearDown(self):self.t.cleanup()
 def _r(self,k,f):
  r=self.m.open_read(self.s,D);r.read(k,f);return r.seal('plan')
 def test_untrusted_sql_names_literal(self):
  k="thing'); DROP TABLE facts; --";self.m.publish(self.s,k,'f',1,valid_from=D);r=self._r(k,'f');self.assertEqual(r['status'],'VALID')
  self.assertEqual(self.m.stats(self.s)['events'],1)
 def test_unicode_entity_and_field(self):
  self.m.publish(self.s,'मुंबई','अवधि','अभी',valid_from=D);self.assertEqual(self.m.state_as_known(self.s,'मुंबई','अवधि',D)['value'],'अभी')
 def test_malformed_scope_refused(self):
  with self.assertRaises(PolicyError):self.m.publish(' ','a','b',1,valid_from=D)
 def test_unknown_parent_refused_no_incomplete_child(self):
  r=self.m.open_read(self.s,D);r.read('a','b')
  with self.assertRaises(PolicyError):r.seal('bad',parents=['invented'])
  self.assertEqual(sum(self.m.stats(self.s)['receipts'].values()),0)
 def test_protect_action_from_absence_disallowed_after_insertion(self):
  rec=self._r('user','disabled');self.m.publish(self.s,'user','disabled',False,valid_from=D)
  with self.assertRaisesRegex(PolicyError,'BLOCKED_STALE'):self.m.protected_action(rec['rid'],self.s,'do',1,valid_at=D)
 def test_explicit_conflict_marked_unknown_for_prefix(self):
  self.m.publish(self.s,'service:foo','owner','A',source='one',valid_from=D)
  self.m.publish(self.s,'service:foo','owner','B',source='two',valid_from=D)
  r=self.m.open_read(self.s,D);r.scan('service:');self.assertEqual(r.seal('list')['status'],'UNKNOWN')
 def test_snapshot_seal_unknown_if_conflicted_read(self):
  self.m.publish(self.s,'x','a',1,source='s1',valid_from=D)
  self.m.publish(self.s,'x','a',2,source='s2',valid_from=D)
  r=self.m.open_read(self.s,D);r.read('x','a');self.assertEqual(r.seal('ambiguous')['status'],'UNKNOWN')
 def test_two_concurrent_actions_same_key_effect_once(self):
  self.m.publish(self.s,'x','a',1,valid_from=D);r=self._r('x','a')
  def act(_):return self.m.protected_action(r['rid'],self.s,'single',{'run':True},valid_at=D)
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(act,range(8)))
  self.assertEqual(self.m.effect_count(self.s),1);self.assertEqual(sum(not x['duplicate'] for x in rows),1)
 def test_receipt_dependencies_never_cross_scope_on_invalidations(self):
  self.m.publish(self.s,'x','a',1,valid_from=D);r=self._r('x','a')
  self.m.publish('tenant/other','x','a',2,valid_from=D)
  self.assertEqual(self.m.receipt(r['rid'])['status'],'VALID')
 def test_consistent_fact_not_auto_certified_external_truth(self):
  self.m.publish(self.s,'x','a',1,valid_from=D);st=self.m.state_as_known(self.s,'x','a',D)
  self.assertEqual(st['verdict'],'CLEAR');self.assertIn('sources',st);self.assertNotIn('verified_in_world',st)
 def test_prefix_empty_guard(self):
  r=self.m.open_read(self.s,D)
  with self.assertRaisesRegex(PolicyError,'EMPTY_PREFIX'):r.scan('')
 def test_timestamp_late_fact_changes_receipt(self):
  self.m.publish(self.s,'contract','expiry','2027-12-31',source='a',valid_from='2026-02-01');r=self._r('contract','expiry')
  self.m.publish(self.s,'contract','expiry','2026-12-31',source='a',valid_from='2026-03-01');self.assertEqual(self.m.receipt(r['rid'])['status'],'STALE')
 def test_retraction_of_absent_source_no_change(self):
  r=self._r('x','a');self.m.publish(self.s,'x','a',None,source='missing',valid_from=D,retract=True)
  self.assertEqual(self.m.receipt(r['rid'])['status'],'VALID')
 def test_complex_nested_json_output_serialization(self):
  self.m.publish(self.s,'x','a',{'b':[1,2]},valid_from=D);r=self.m.open_read(self.s,D);r.read('x','a')
  receipt=r.seal({'source':'test','nested':{'hello':[True,42]}})
  self.assertEqual(self.m.receipt(receipt['rid'])['output']['nested']['hello'],[True,42])
 def test_fanout_350_receipts(self):
  self.m.publish(self.s,'hot','version',1,valid_from=D)
  ids=[self._r('hot','version')['rid'] for _ in range(350)]
  result=self.m.publish(self.s,'hot','version',2,valid_from=D)
  self.assertEqual(result['affected'],350)
  self.assertEqual(self.m.stats(self.s)['receipts'].get('STALE'),350)
 def test_bad_replay_rolls_back_batch(self):
  self.m.publish(self.s,'a','b',1,event_id='replay',valid_from=D)
  with self.assertRaisesRegex(PolicyError,'IDEMPOTENCY_KEY'):
   self.m.batch_publish(self.s,[{'key':'fresh','field':'x','value':2,'valid_from':D},
                                  {'key':'a','field':'b','value':3,'valid_from':D,'event_id':'replay'}])
  self.assertEqual(self.m.state_as_known(self.s,'fresh','x',D)['verdict'],'ABSENT')
if __name__=='__main__':unittest.main()
