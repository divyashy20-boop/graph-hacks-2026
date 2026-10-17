import tempfile,unittest
from pathlib import Path
from p5memory import Memory,PolicyError,ingest_json,ingest_python,flatten_json,python_signatures
D='2026-10-17'
class IngestTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.db=Memory(Path(self.temp.name)/'m.sqlite');self.s='team/system'
 def tearDown(self):self.temp.cleanup()
 def test_python_add_required_args_invalidates_receipt(self):
  ingest_python(self.db,self.s,'pay','def process_payment(amount):\n return amount',valid_from=D)
  r=self.db.open_read(self.s,D);v=r.read('code:pay','function:process_payment');self.assertEqual(len(v['value']['params']),1);rec=r.seal({'plan':'invoke(amount)'})
  ingest_python(self.db,self.s,'pay','def process_payment(amount, currency, region):\n return amount',valid_from=D)
  self.assertEqual(self.db.receipt(rec['rid'])['status'],'STALE')
  self.assertEqual(len(self.db.state_as_known(self.s,'code:pay','function:process_payment',D)['value']['params']),3)
 def test_python_unrelated_function_doesnt_invalidate(self):
  ingest_python(self.db,self.s,'pay','def charge(x): pass\ndef inspect(y): pass',valid_from=D)
  r=self.db.open_read(self.s,D);r.read('code:pay','function:charge');rec=r.seal('call charge')
  ingest_python(self.db,self.s,'pay','def charge(x): pass\ndef inspect(y,z): pass',valid_from=D)
  self.assertEqual(self.db.receipt(rec['rid'])['status'],'VALID')
 def test_remove_function_retracts(self):
  ingest_python(self.db,self.s,'a','def old(x):pass',valid_from=D)
  r=self.db.open_read(self.s,D);r.read('code:a','function:old');rec=r.seal('old func')
  ingest_python(self.db,self.s,'a','def new(x):pass',valid_from=D)
  self.assertEqual(self.db.state_as_known(self.s,'code:a','function:old',D)['verdict'],'ABSENT')
  self.assertEqual(self.db.receipt(rec['rid'])['status'],'STALE')
 def test_async_and_class_methods(self):
  sig=python_signatures('class App:\n async def f(self, x:int, *, region="US") -> bool: pass')
  self.assertIn('class:App.f',sig)
  self.assertTrue(sig['class:App.f']['async']);self.assertEqual(sig['class:App.f']['returns'],'bool')
 def test_positional_keyword_and_varargs(self):
  sig=python_signatures('def f(x, /, y=1, *args, k, **kw): pass')['function:f']['params']
  self.assertEqual([x['kind'] for x in sig],['POSITIONAL_ONLY','POSITIONAL_OR_KEYWORD','VAR_POSITIONAL','KEYWORD_ONLY','VAR_KEYWORD'])
 def test_no_execute_python(self):
  python_signatures('raise Exception("not executed")\ndef f():pass')
 def test_python_syntax_error(self):
  with self.assertRaises(SyntaxError):ingest_python(self.db,self.s,'broken','def f(:',valid_from=D)
  self.assertEqual(self.db.stats(self.s)['events'],0)
 def test_json_contract_date_change(self):
  ingest_json(self.db,self.s,'supplier',{'supplier':'Acme','expires':'2026-12-31'},valid_from=D)
  r=self.db.open_read(self.s,D);r.read('json:supplier','/expires');rec=r.seal('renew later')
  ingest_json(self.db,self.s,'supplier',{'supplier':'Acme','expires':'2026-11-01'},valid_from=D)
  self.assertEqual(self.db.receipt(rec['rid'])['status'],'STALE')
 def test_json_unrelated_field(self):
  ingest_json(self.db,self.s,'contract',{'expiry':'2027-01-01','note':'hello'},valid_from=D)
  r=self.db.open_read(self.s,D);r.read('json:contract','/expiry');rec=r.seal('plan')
  ingest_json(self.db,self.s,'contract',{'expiry':'2027-01-01','note':'updated'},valid_from=D)
  self.assertEqual(self.db.receipt(rec['rid'])['status'],'VALID')
 def test_json_removed_field(self):
  ingest_json(self.db,self.s,'doc',{'expires':'tomorrow'},valid_from=D)
  r=self.db.open_read(self.s,D);r.read('json:doc','/expires');rec=r.seal('ok')
  ingest_json(self.db,self.s,'doc',{},valid_from=D)
  self.assertEqual(self.db.receipt(rec['rid'])['status'],'STALE')
 def test_json_pointer_escape(self):
  self.assertEqual(flatten_json({'a/b':{'~c':1}}),{'/a~1b/~0c':1})
 def test_arrays_atomic(self):
  self.assertEqual(flatten_json({'lines':[1,2]}),{'/lines':[1,2]})
 def test_empty_document(self):
  self.assertEqual(flatten_json({}),{'/':{}})
 def test_json_snapshot_noop(self):
  ingest_json(self.db,self.s,'x',{'a':1},valid_from=D);rev=self.db.stats(self.s)['revision'];ret=ingest_json(self.db,self.s,'x',{'a':1},valid_from=D)
  self.assertTrue(ret['unchanged']);self.assertEqual(self.db.stats(self.s)['revision'],rev)
 def test_bulk_update_atomic_rollback(self):
  self.db.publish(self.s,'a','x',1,valid_from=D)
  with self.assertRaises(PolicyError):self.db.batch_publish(self.s,[{'key':'b','field':'x','value':2,'valid_from':D},{'key':'a','field':'x','value':3,'valid_from':D,'event_id':'bad'} ,{'key':'a','field':'x','value':4,'valid_from':D,'event_id':'bad'}])
  self.assertEqual(self.db.stats(self.s)['revision'],1)
 def test_batch_multi_field_both_changed_once(self):
  self.db.batch_publish(self.s,[{'key':'x','field':'a','value':1,'valid_from':D},{'key':'x','field':'b','value':2,'valid_from':D}]);self.assertEqual(self.db.stats(self.s)['revision'],2)
  r=self.db.open_read(self.s,D);r.read('x','a');r.read('x','b');rec=r.seal('plan')
  self.db.batch_publish(self.s,[{'key':'x','field':'a','value':2,'valid_from':D},{'key':'x','field':'b','value':3,'valid_from':D}])
  self.assertEqual(self.db.receipt(rec['rid'])['status'],'STALE')
 def test_batch_idempotency(self):
  e={'key':'x','field':'y','value':1,'valid_from':D,'event_id':'1'}
  self.db.batch_publish(self.s,[e]);ret=self.db.batch_publish(self.s,[e]);self.assertEqual(len(ret['duplicates']),1)
 def test_batch_atomic_concurrent_reader(self):
  self.db.batch_publish(self.s,[{'key':'x','field':'a','value':1,'valid_from':D},{'key':'x','field':'b','value':1,'valid_from':D}])
  self.db.batch_publish(self.s,[{'key':'x','field':'a','value':2,'valid_from':D},{'key':'x','field':'b','value':2,'valid_from':D}])
  r=self.db.open_read(self.s,D);self.assertEqual(r.read('x','a')['value'],2);self.assertEqual(r.read('x','b')['value'],2)

if __name__=='__main__':unittest.main()
