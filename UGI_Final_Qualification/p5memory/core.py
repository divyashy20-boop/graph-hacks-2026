"""UGI P5 isolated reference implementation. stdlib SQLite, no UGI source edits.

Safety semantics: every read is captured; all updates and protected INTERNAL test
operations are single SQLite write transactions; an external side-effect adapter is
intentionally NOT provided (atomicity cannot be promised outside SQLite).
"""
from __future__ import annotations
import contextlib
import hashlib
import json
import sqlite3
import threading
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

VALID = "VALID"
STALE = "STALE"
UNKNOWN = "UNKNOWN"


def stable(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def iso_day(s: str) -> str:
    date.fromisoformat(s)
    return s


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


class PolicyError(RuntimeError):
    pass


class Memory:
    def __init__(self, path: str | Path):
        self.path = str(path)
        if self.path == ':memory:':
            raise PolicyError('IN_MEMORY_CONNECTIONS_ARE_NOT_SHARED_USE_FILE_PATH')
        if self.path != ':memory:':
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        # Every method starts a new connection so threads cannot share transaction state.
        with self._connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS revisions(scope TEXT PRIMARY KEY, rev INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS facts (
               event_id TEXT PRIMARY KEY, scope TEXT NOT NULL, fact_key TEXT NOT NULL,
               field_path TEXT NOT NULL, source_id TEXT NOT NULL, payload TEXT,
               valid_from TEXT NOT NULL, valid_to TEXT, record_seq INTEGER NOT NULL,
               recorded_at TEXT NOT NULL, kind TEXT NOT NULL,
               UNIQUE(scope, record_seq));
            CREATE INDEX IF NOT EXISTS facts_lookup ON facts(scope,fact_key,field_path,record_seq);
            CREATE TABLE IF NOT EXISTS receipts (
               rid TEXT PRIMARY KEY, scope TEXT NOT NULL, output TEXT NOT NULL,
               status TEXT NOT NULL, valid_at TEXT NOT NULL, snapshot_rev INTEGER NOT NULL,
               created_at TEXT NOT NULL, reason TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS reads (
               rid TEXT NOT NULL, kind TEXT NOT NULL, fact_key TEXT NOT NULL,
               field_path TEXT NOT NULL, fingerprint TEXT NOT NULL,
               PRIMARY KEY(rid,kind,fact_key,field_path),
               FOREIGN KEY(rid) REFERENCES receipts(rid));
            CREATE INDEX IF NOT EXISTS reads_reverse ON reads(kind,fact_key,field_path,rid);
            CREATE TABLE IF NOT EXISTS receipt_links (
               parent TEXT NOT NULL, child TEXT NOT NULL, PRIMARY KEY(parent,child));
            CREATE INDEX IF NOT EXISTS receipt_links_reverse ON receipt_links(parent,child);
            CREATE TABLE IF NOT EXISTS invalidations (
               idx INTEGER PRIMARY KEY AUTOINCREMENT, rid TEXT NOT NULL, old_status TEXT NOT NULL,
               new_status TEXT NOT NULL, rev INTEGER NOT NULL, reason TEXT NOT NULL, at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS protected_effects (
               scope TEXT NOT NULL, action_id TEXT NOT NULL, rid TEXT NOT NULL,
               payload TEXT NOT NULL, executed_at TEXT NOT NULL,
               PRIMARY KEY(scope,action_id));
            ''')

    @contextlib.contextmanager
    def _connect(self):
        con = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        con.row_factory = sqlite3.Row
        con.execute('PRAGMA busy_timeout=15000')
        con.execute('PRAGMA foreign_keys=ON')
        if self.path != ':memory:':
            con.execute('PRAGMA journal_mode=WAL')
        try:
            yield con
        finally:
            con.close()

    @contextlib.contextmanager
    def _transaction(self):
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            try:
                yield db
                db.execute('COMMIT')
            except BaseException:
                db.execute('ROLLBACK')
                raise

    @staticmethod
    def _rev(db, scope):
        row = db.execute('SELECT rev FROM revisions WHERE scope=?', (scope,)).fetchone()
        return row['rev'] if row else 0

    @staticmethod
    def _state(db, scope, key, field, day, revision):
        # One active assertion per source: latest effective valid start, then recorded revision.
        rows = db.execute('''SELECT source_id,payload,kind,valid_from,record_seq FROM facts
           WHERE scope=? AND fact_key=? AND field_path=? AND record_seq<=?
             AND valid_from<=? AND (valid_to IS NULL OR valid_to>?)
           ORDER BY source_id, valid_from DESC,record_seq DESC''',
           (scope,key,field,revision,day,day)).fetchall()
        per_source = {}
        for r in rows:
            if r['source_id'] not in per_source:
                per_source[r['source_id']] = r
        active = {s:json.loads(r['payload']) for s,r in per_source.items() if r['kind']=='ASSERT'}
        distinct = {stable(v) for v in active.values()}
        verdict = 'ABSENT' if not active else ('CONFLICT' if len(distinct)>1 else 'CLEAR')
        value = next(iter(active.values())) if verdict=='CLEAR' else None
        # fingerprint captures observed source membership, intentionally conservative.
        fingerprint = stable({'verdict':verdict,'sources':[(k, active[k]) for k in sorted(active)]})
        return {'verdict':verdict,'value':value,'sources':sorted(active),'fingerprint':fingerprint}

    @classmethod
    def _prefix(cls, db, scope, prefix, day, revision):
        keys = db.execute('''SELECT DISTINCT fact_key,field_path FROM facts
            WHERE scope=? AND record_seq<=? AND fact_key LIKE ? ESCAPE '\\'
            ORDER BY fact_key,field_path''',
            (scope,revision,prefix.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%')).fetchall()
        items=[]
        conflicting=False
        for row in keys:
            state=cls._state(db,scope,row['fact_key'],row['field_path'],day,revision)
            if state['verdict']!='ABSENT':
                if state['verdict']=='CONFLICT': conflicting=True
                items.append((row['fact_key'],row['field_path'],state['fingerprint']))
        return {'fingerprint':stable(items),'count':len(items),'matches':items,'verdict':'CONFLICT' if conflicting else 'CLEAR'}

    def open_read(self, scope, valid_at):
        if not scope or not scope.strip(): raise PolicyError('EMPTY_SCOPE')
        iso_day(valid_at)
        with self._connect() as db: rev=self._rev(db,scope)
        return Reader(self,scope,valid_at,rev)

    def state_as_known(self, scope, key, field, valid_at, known_rev=None):
        iso_day(valid_at)
        with self._connect() as db:
            rev=self._rev(db,scope)
            if known_rev is not None:
                if not isinstance(known_rev,int) or known_rev<0 or known_rev>rev: raise PolicyError('BAD_KNOWN_REVISION')
                rev=known_rev
            return self._state(db,scope,key,field,valid_at,rev)

    def _status(self, db, rid, newstatus, rev, reason):
        row=db.execute('SELECT status FROM receipts WHERE rid=?',(rid,)).fetchone()
        if not row: return False
        old=row['status']
        # Monotone safety lattice for ORIGINAL, unreplanned receipts:
        # VALID < STALE < UNKNOWN. A later contradiction is more restrictive
        # than a prior stale read; the receipt must be allowed to escalate
        # STALE -> UNKNOWN. A resolved conflict never revives it; generating a
        # new VALID receipt requires an independent fully-captured reread.
        safety_rank={VALID:0, STALE:1, UNKNOWN:2}
        if newstatus not in safety_rank:
            raise PolicyError('INVALID_RECEIPT_STATUS')
        if safety_rank[newstatus] <= safety_rank[old]:
            return False
        db.execute('UPDATE receipts SET status=?,reason=? WHERE rid=?',(newstatus,reason,rid))
        db.execute('INSERT INTO invalidations(rid,old_status,new_status,rev,reason,at) VALUES(?,?,?,?,?,?)',
                   (rid,old,newstatus,rev,reason,utc()))
        return True

    def _cascade(self, db, changed, rev):
        queue=list(changed); visited=set()
        while queue:
            parent=queue.pop(0)
            if parent in visited: continue
            visited.add(parent)
            for row in db.execute('SELECT child FROM receipt_links WHERE parent=?',(parent,)).fetchall():
                child=row['child']
                if self._status(db,child,STALE,rev,'UPSTREAM_RECEIPT_CHANGED:'+parent): queue.append(child)

    @staticmethod
    def _validate_event(e):
        scope,key,field,source=e['scope'],e['key'],e['field'],e.get('source','source-1')
        if not all(isinstance(v,str) and v.strip() for v in (scope,key,field,source)):
            raise PolicyError('INVALID_FACT_ADDRESS')
        frm=iso_day(e.get('valid_from','2026-01-01'))
        to=e.get('valid_to')
        if to is not None:
            iso_day(to)
            if to<=frm:raise PolicyError('INVALID_VALIDITY_INTERVAL')
        retract=bool(e.get('retract',False))
        payload=None if retract else json.dumps(e.get('value'),sort_keys=True,allow_nan=False)
        eid=e.get('event_id') or uuid.uuid4().hex
        return eid,scope,key,field,source,payload,frm,to,'RETRACT' if retract else 'ASSERT'

    def batch_publish(self, scope, events):
        """Atomically publish multiple source field events and invalidate final snapshot."""
        if not events:raise PolicyError('EMPTY_EVENT_BATCH')
        validated=[self._validate_event({**e,'scope':scope}) for e in events]
        ids=[e[0] for e in validated]
        if len(set(ids))!=len(ids):raise PolicyError('DUPLICATE_IDS_IN_BATCH')
        inserted=[];duplicates=[];affected=set()
        with self._transaction() as db:
            rev=self._rev(db,scope)
            changed_addresses=set()
            for ev in validated:
                eid,escope,key,field,source,payload,frm,to,kind=ev
                old=db.execute('SELECT * FROM facts WHERE event_id=?',(eid,)).fetchone()
                if old:
                    prev=(old['event_id'],old['scope'],old['fact_key'],old['field_path'],old['source_id'],old['payload'],old['valid_from'],old['valid_to'],old['kind'])
                    if prev!=ev:raise PolicyError('IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_FACT')
                    duplicates.append({'event_id':eid,'revision':old['record_seq']})
                    continue
                rev+=1
                db.execute('''INSERT INTO facts(event_id,scope,fact_key,field_path,source_id,payload,valid_from,valid_to,record_seq,recorded_at,kind)
                     VALUES(?,?,?,?,?,?,?,?,?,?,?)''',(eid,scope,key,field,source,payload,frm,to,rev,utc(),kind))
                changed_addresses.add((key,field))
                inserted.append({'event_id':eid,'revision':rev})
            if inserted:
                db.execute('INSERT INTO revisions(scope,rev) VALUES(?,?) ON CONFLICT(scope) DO UPDATE SET rev=excluded.rev',(scope,rev))
                candidates=db.execute('''SELECT DISTINCT r.rid,r.valid_at,d.kind,d.fact_key,d.field_path,d.fingerprint
                    FROM receipts r JOIN reads d ON d.rid=r.rid WHERE r.scope=?''',(scope,)).fetchall()
                for c in candidates:
                    relevant = ((c['kind']=='FIELD' and (c['fact_key'],c['field_path']) in changed_addresses) or
                                (c['kind']=='PREFIX' and any(k.startswith(c['fact_key']) for k,_ in changed_addresses)))
                    if not relevant:continue
                    state=(self._state(db,scope,c['fact_key'],c['field_path'],c['valid_at'],rev)
                         if c['kind']=='FIELD' else self._prefix(db,scope,c['fact_key'],c['valid_at'],rev))
                    if state['fingerprint']==c['fingerprint']:continue
                    new=UNKNOWN if state.get('verdict')=='CONFLICT' else STALE
                    if self._status(db,c['rid'],new,rev,'DEPENDENCY_CHANGED_BATCH'):
                        affected.add(c['rid'])
                self._cascade(db,affected,rev)
        return {'revision':rev,'inserted':inserted,'duplicates':duplicates,'affected':len(affected),'atomic':True}

    def publish(self, scope, key, field, value, *, source='source-1', valid_from='2026-01-01', valid_to=None, event_id=None, retract=False):
        e={'key':key,'field':field,'value':value,'source':source,'valid_from':valid_from,'valid_to':valid_to,
           'retract':retract}
        if event_id is not None:e['event_id']=event_id
        r=self.batch_publish(scope,[e])
        first=(r['inserted'] or r['duplicates'])[0]
        return {'event_id':first['event_id'],'revision':first['revision'], 'duplicate':not bool(r['inserted']), 'affected':r['affected']}

    def seal(self, reader, output, *, parents=()):
        if reader.closed:raise PolicyError('READER_ALREADY_SEALED')
        if not reader.observations and not parents:raise PolicyError('EMPTY_READ_SET')
        jsonout=json.dumps(output,sort_keys=True,allow_nan=False)
        rid=uuid.uuid4().hex
        with self._transaction() as db:
            live_rev=self._rev(db,reader.scope)
            status=VALID if live_rev==reader.rev else STALE
            reason='CAPTURED_GRAPH_READS' if status==VALID else 'SNAPSHOT_CHANGED_BEFORE_SEAL'
            if any(x['verdict']=='CONFLICT' for x in reader.observations.values()):
                if status==VALID: status,reason=UNKNOWN,'CONFLICTING_FACTS'
            for parent in parents:
                p=db.execute('SELECT status,scope FROM receipts WHERE rid=?',(parent,)).fetchone()
                if not p or p['scope']!=reader.scope:raise PolicyError('BAD_PARENT_SCOPE_OR_ID')
                if p['status']!=VALID:status,reason=STALE,'UPSTREAM_NOT_VALID'
            db.execute('INSERT INTO receipts(rid,scope,output,status,valid_at,snapshot_rev,created_at,reason) VALUES(?,?,?,?,?,?,?,?)',
                       (rid,reader.scope,jsonout,status,reader.valid_at,reader.rev,utc(),reason))
            for (kind,key,field),obs in reader.observations.items():
                db.execute('INSERT INTO reads(rid,kind,fact_key,field_path,fingerprint) VALUES(?,?,?,?,?)',
                           (rid,kind,key,field,obs['fingerprint']))
            for parent in parents:
                # Detect cycle naturally: parent must preexist and child is newly created.
                db.execute('INSERT INTO receipt_links(parent,child) VALUES(?,?)',(parent,rid))
        reader.closed=True
        return self.receipt(rid)

    def receipt(self,rid):
        with self._connect() as db:
            r=db.execute('SELECT * FROM receipts WHERE rid=?',(rid,)).fetchone()
            if not r:raise PolicyError('UNKNOWN_RECEIPT')
            deps=db.execute('SELECT kind,fact_key,field_path,fingerprint FROM reads WHERE rid=? ORDER BY kind,fact_key,field_path',(rid,)).fetchall()
            return {**dict(r),'output':json.loads(r['output']),'dependencies':[dict(x) for x in deps]}

    def dependents(self, rid):
        with self._connect() as db:
            q=[rid];visited={rid}; found=[]
            while q:
                par=q.pop(0)
                for row in db.execute('SELECT child FROM receipt_links WHERE parent=?',(par,)).fetchall():
                    ch=row['child']
                    if ch not in visited:visited.add(ch);found.append(ch);q.append(ch)
            return found

    def _recheck(self,db,row,day,rev):
        if row['status']!=VALID: return False,row['status'],'PREVIOUSLY_INVALIDATED'
        for dep in db.execute('SELECT * FROM reads WHERE rid=?',(row['rid'],)).fetchall():
            state=(self._state(db,row['scope'],dep['fact_key'],dep['field_path'],day,rev)
                   if dep['kind']=='FIELD' else self._prefix(db,row['scope'],dep['fact_key'],day,rev))
            if state.get('verdict')=='CONFLICT':return False,UNKNOWN,'CONFLICT_AT_ACTION_TIME'
            if state['fingerprint']!=dep['fingerprint']:return False,STALE,'READ_SET_CHANGED_AT_ACTION_TIME'
        for p in db.execute('SELECT r.status FROM receipt_links l JOIN receipts r ON r.rid=l.parent WHERE l.child=?',(row['rid'],)).fetchall():
            if p['status']!=VALID:return False,STALE,'UPSTREAM_NOT_VALID'
        return True,VALID,'REVALIDATED'

    def protected_action(self, rid, scope, action_id, payload, *, valid_at):
        """Atomic idempotent INTERNAL test effect, with gate held in same transaction.

        This method DOES NOT invoke external services, where atomicity would not hold.
        """
        iso_day(valid_at)
        result=None
        blocked=None
        content=json.dumps(payload,sort_keys=True,allow_nan=False)
        with self._transaction() as db:
            prior=db.execute('SELECT * FROM protected_effects WHERE scope=? AND action_id=?',(scope,action_id)).fetchone()
            if prior:
                if prior['rid']!=rid or prior['payload']!=content:
                    raise PolicyError('ACTION_KEY_COLLISION')
                return {'executed':True,'duplicate':True,'action_id':action_id}
            row=db.execute('SELECT * FROM receipts WHERE rid=? AND scope=?',(rid,scope)).fetchone()
            if row is None:raise PolicyError('UNKNOWN_RECEIPT_OR_SCOPE')
            current=self._rev(db,scope)
            ok,status,reason=self._recheck(db,row,valid_at,current)
            if not ok:
                if self._status(db,rid,status,current,reason):self._cascade(db,{rid},current)
                blocked='BLOCKED_'+status+':'+reason
            else:
                db.execute('INSERT INTO protected_effects(scope,action_id,rid,payload,executed_at) VALUES(?,?,?,?,?)',
                           (scope,action_id,rid,content,utc()))
                result={'executed':True,'duplicate':False,'action_id':action_id}
        if blocked:raise PolicyError(blocked)
        return result

    def effect_count(self,scope):
        with self._connect() as db:
            return db.execute('SELECT count(*) FROM protected_effects WHERE scope=?',(scope,)).fetchone()[0]

    def sweep(self,scope,valid_at):
        """Recheck receipt read sets after clock advances, independently of new events."""
        iso_day(valid_at)
        with self._transaction() as db:
            rev=self._rev(db,scope);changed=set()
            for row in db.execute('SELECT * FROM receipts WHERE scope=? AND status=?',(scope,VALID)).fetchall():
                ok,status,reason=self._recheck(db,row,valid_at,rev)
                if not ok and self._status(db,row['rid'],status,rev,reason):changed.add(row['rid'])
            self._cascade(db,changed,rev)
            return {'changed':len(changed),'revision':rev}

    def stats(self,scope):
        with self._connect() as db:
            return {'revision':self._rev(db,scope), 'events':db.execute('SELECT count(*) FROM facts WHERE scope=?',(scope,)).fetchone()[0],
                    'receipts':{r['status']:r['n'] for r in db.execute('SELECT status,count(*) n FROM receipts WHERE scope=? GROUP BY status',(scope,))},
                    'effects':self.effect_count(scope)}


class Reader:
    def __init__(self,memory,scope,valid_at,rev):
        self.memory=memory;self.scope=scope;self.valid_at=valid_at;self.rev=rev
        self.observations={};self.closed=False

    def read(self,key,field):
        if self.closed:raise PolicyError('READER_CLOSED')
        with self.memory._connect() as db:
            state=self.memory._state(db,self.scope,key,field,self.valid_at,self.rev)
        self.observations[('FIELD',key,field)]=state
        return {k:v for k,v in state.items() if k!='fingerprint'}

    def scan(self,prefix):
        if self.closed:raise PolicyError('READER_CLOSED')
        if prefix=='':raise PolicyError('EMPTY_PREFIX_REJECTED')
        with self.memory._connect() as db:
            state=self.memory._prefix(db,self.scope,prefix,self.valid_at,self.rev)
        self.observations[('PREFIX',prefix,'*')]=state
        return {'count':state['count'],'matches':state['matches']}

    def seal(self,output,*,parents=()):
        return self.memory.seal(self,output,parents=parents)
