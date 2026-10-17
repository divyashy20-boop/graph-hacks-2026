"""Durable single-SQLite-file receipt tool read-log for the disposable P5 lab.

This is not a distributed/cryptographically authenticated source of truth.
The digest catches accidental corruption, not a malicious DB administrator.
The enforcing executor must verify tenant scope before using the registry.
"""
import json
from .core import stable

class RegistryError(RuntimeError):pass

class ReceiptRegistry:
    def __init__(self,memory):
        self.memory=memory
        with self.memory._connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS receipt_tool_reads(
                    rid TEXT PRIMARY KEY, scope TEXT NOT NULL, payload TEXT NOT NULL, digest TEXT NOT NULL)''')

    def save(self,rid,scope,observations):
        if not isinstance(observations,dict) or not observations:
            raise RegistryError('EMPTY_TOOL_REGISTRY')
        with self.memory._transaction() as db:
            rec=db.execute('SELECT scope FROM receipts WHERE rid=?',(rid,)).fetchone()
            if rec is None or rec['scope']!=scope:
                raise RegistryError('RECEIPT_SCOPE_MISMATCH')
            values={k:{'name':o['name'],'args':o['args']} for k,o in observations.items()}
            payload=json.dumps(values,sort_keys=True,ensure_ascii=True,separators=(',',':'))
            digest=stable(values)
            prior=db.execute('SELECT scope,payload,digest FROM receipt_tool_reads WHERE rid=?',(rid,)).fetchone()
            if prior:
                if prior['scope']!=scope or prior['payload']!=payload or prior['digest']!=digest:
                    raise RegistryError('REGISTRY_REWRITE_DENIED')
                return
            db.execute('INSERT INTO receipt_tool_reads(rid,scope,payload,digest) VALUES(?,?,?,?)',
                       (rid,scope,payload,digest))

    def load(self,rid,scope):
        with self.memory._connect() as db:
            row=db.execute('SELECT * FROM receipt_tool_reads WHERE rid=? AND scope=?',(rid,scope)).fetchone()
        if not row:raise RegistryError('REGISTRY_MISSING_FAIL_CLOSED')
        try:observations=json.loads(row['payload'])
        except (ValueError,TypeError) as exc:raise RegistryError('REGISTRY_CORRUPT_JSON') from exc
        if not isinstance(observations,dict) or not observations or stable(observations)!=row['digest']:
            raise RegistryError('REGISTRY_CORRUPTED_FAIL_CLOSED')
        return observations
