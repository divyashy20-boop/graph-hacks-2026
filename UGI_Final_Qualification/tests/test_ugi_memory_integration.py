"""REAL UGI Engine + real UGI MCP JSON-RPC handler (in-memory graph backend).
No FalkorDB here: the separate live_combo covers that on user's Windows Docker.
"""
import tempfile,unittest,json,sys,types
from pathlib import Path
# The UGI Store imports redis even when using its in-memory backend. When
# redis is absent ONLY in this isolated test runtime, install a nonfunctional
# import shim. In Windows Docker the real redis dependency is used.
try:
    import redis  # noqa
except ImportError:
    mod=types.ModuleType('redis')
    mod.Redis=type('Redis',(),{})
    ex=types.ModuleType('redis.exceptions')
    ex.ResponseError=type('ResponseError',(Exception,),{})
    mod.exceptions=ex
    sys.modules['redis']=mod
    sys.modules['redis.exceptions']=ex
from ugi.engine import Engine
from ugi.store import Store
from ugi.models import Settings
from ugi.mcp_server import handle_message
from p5memory.core import Memory,PolicyError
from ugi_final.bridge import track_and_register,refresh_receipt,CapturingMCP,BridgeError

class ActualMCP:
    def __init__(self,eng):self.eng=eng;self.n=0
    def request(self,method,params=None,**kwargs):
        self.n+=1
        return handle_message({'jsonrpc':'2.0','id':self.n,'method':method,'params':params or {}},self.eng,allow_writes=False)
    def tool(self,name,args):
        return self.request('tools/call',{'name':name,'arguments':args})['result']

class ActualUGIEngineCombo(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.memory=Memory(Path(self.t.name)/'receipts.sqlite')
        self.engine=Engine(Store(Settings(backend='memory',provider='offline',allow_paid_calls=False)))
        self.mcp=ActualMCP(self.engine)
        self.scope='isolated-runtime::tenant-a::demo'
        self.src1=self.ingest('before',[('web','redis','positive')])
    def tearDown(self):self.t.cleanup()
    def ingest(self,filename,relations):
        rows=[{'subject':u,'subject_type':'Service','subject_id':'svc:'+u,
               'predicate':'depends on','object':v,'object_type':'Service','object_id':'svc:'+v,
               'polarity':pol} for u,v,pol in relations]
        return self.engine.ingest(filename+'.json',json.dumps(rows).encode())['source_id']
    def track(self,query):
        return track_and_register(self.memory,self.mcp,scope=self.scope,dataset='demo',
             query=query,entities=['web','redis'],day='2026-10-17',allowed_source_ids={self.src1})
    def refresh(self,x):
        return refresh_receipt(self.memory,self.mcp,scope=self.scope,
               receipt={**x['receipt'],'observations':x['observations']},day='2026-10-17')
    def test_actual_ugi_negative_to_positive_invalidates_receipt(self):
        result=self.track('Does redis directly depend on web?')
        self.assertIn(result['outcome']['verdict'],{'UNKNOWN','CONNECTED_ONLY'})
        self.assertEqual(result['receipt']['status'],'VALID')
        self.ingest('added-reverse-edge',[('redis','web','positive')])
        info=self.refresh(result)
        self.assertGreater(info['changed'],0)
        self.assertEqual(self.memory.receipt(result['receipt']['rid'])['status'],'STALE')
        with self.assertRaises(PolicyError):
            self.memory.protected_action(result['receipt']['rid'],self.scope,'stale',{'payload':True},valid_at='2026-10-17')
        self.assertEqual(self.memory.effect_count(self.scope),0)
    def test_actual_ugi_positive_source_evidence_capture(self):
        result=self.track('Does web directly depend on redis?')
        self.assertEqual(result['outcome']['verdict'],'SOURCE_ASSERTED')
        self.assertTrue(result['outcome']['verified_claim_ids'])
        self.assertGreaterEqual(len(result['observations']),4)
        self.assertEqual(self.refresh(result)['changed'],0)
        self.assertEqual(self.memory.receipt(result['receipt']['rid'])['status'],'VALID')
    def test_actual_ugi_conflict_marks_existing_receipt_unknown(self):
        r=self.track('Does web directly depend on redis?')
        self.assertEqual(r['receipt']['status'],'VALID')
        self.ingest('opposing',[('web','redis','negative')])
        change=self.refresh(r)
        self.assertGreater(change['changed'],0)
        self.assertEqual(self.memory.receipt(r['receipt']['rid'])['status'],'UNKNOWN')
        with self.assertRaises(PolicyError):
            self.memory.protected_action(r['receipt']['rid'],self.scope,'conflicted',{'x':1},valid_at='2026-10-17')
        self.assertEqual(self.memory.effect_count(self.scope),0)
    def test_durable_registry_after_new_memory_connection(self):
        r=self.track('Does web directly depend on redis?')
        second=Memory(Path(self.t.name)/'receipts.sqlite')
        check=refresh_receipt(second,self.mcp,scope=self.scope,receipt={'rid':r['receipt']['rid']},day='2026-10-17')
        self.assertEqual(check['changed'],0)
    def test_underlying_mcp_denies_persistent_action(self):
        proxy=CapturingMCP(self.mcp)
        with self.assertRaises(BridgeError):
            proxy.tool('investigate_dependency_incident',{'target':'redis','idempotency_key':'x','authorise_action':True})
        self.assertFalse(self.engine.store.list('Investigation'))
        # Even bypassing proxy, actual MCP server requires explicit allow_writes.
        result=self.mcp.tool('investigate_dependency_incident',{'target':'redis','idempotency_key':'x','authorise_action':True})
        self.assertTrue(result.get('isError'))
        self.assertFalse(self.engine.store.list('Investigation'))

if __name__=='__main__':unittest.main()
