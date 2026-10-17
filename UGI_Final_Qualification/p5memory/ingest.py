"""Deterministic, conservative field-level change detection (Python AST + JSON).
No semantic guessing, no code execution. Nested Python functions are not indexed.
"""
from __future__ import annotations
import ast
import json
from .core import PolicyError


def flatten_json(value, prefix=''):
    """RFC6901-style JSON-pointer leaf paths. Arrays treated atomically."""
    if isinstance(value,dict) and value:
        ans={}
        for k,v in value.items():
            if not isinstance(k,str):raise PolicyError('JSON_KEYS_MUST_BE_STRINGS')
            esc=k.replace('~','~0').replace('/','~1')
            ans.update(flatten_json(v,prefix+'/'+esc))
        return ans
    return {prefix or '/':value}


def _signature(node):
    a=node.args
    def param(arg,kind,default):
        return {'name':arg.arg,'kind':kind,'default':default,'annotation':ast.unparse(arg.annotation) if arg.annotation else None}
    params=[]
    pos=a.posonlyargs+a.args
    defaulted=max(0,len(pos)-len(a.defaults))
    for i,p in enumerate(pos):params.append(param(p,'POSITIONAL_ONLY' if i<len(a.posonlyargs) else 'POSITIONAL_OR_KEYWORD',i>=defaulted))
    if a.vararg:params.append(param(a.vararg,'VAR_POSITIONAL',False))
    for arg,default in zip(a.kwonlyargs,a.kw_defaults):params.append(param(arg,'KEYWORD_ONLY',default is not None))
    if a.kwarg:params.append(param(a.kwarg,'VAR_KEYWORD',False))
    return {'params':params,'returns':ast.unparse(node.returns) if node.returns else None,'async':isinstance(node,ast.AsyncFunctionDef)}


def python_signatures(text):
    tree=ast.parse(text)
    sig={}
    for node in tree.body:
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
            sig['function:'+node.name]=_signature(node)
        elif isinstance(node,ast.ClassDef):
            for method in node.body:
                if isinstance(method,(ast.FunctionDef,ast.AsyncFunctionDef)):
                    sig['class:'+node.name+'.'+method.name]=_signature(method)
    return sig


def _current_fields(memory,scope,key,source,day):
    with memory._connect() as db:
        rev=memory._rev(db,scope)
        fields=[r[0] for r in db.execute('SELECT DISTINCT field_path FROM facts WHERE scope=? AND fact_key=? AND source_id=?',
                         (scope,key,source)).fetchall()]
        result={}
        for field in fields:
            rows=db.execute('''SELECT payload,kind FROM facts WHERE scope=? AND fact_key=? AND field_path=? AND source_id=?
                AND record_seq<=? AND valid_from<=? AND (valid_to IS NULL OR valid_to>?)
                ORDER BY valid_from DESC,record_seq DESC LIMIT 1''', (scope,key,field,source,rev,day,day)).fetchone()
            if rows and rows['kind']=='ASSERT':result[field]=json.loads(rows['payload'])
        return result


def publish_snapshot(memory,scope,key,source,field_map,*,valid_from):
    """Atomic snapshot replacement for a single source+fact key.
    Emits source-scoped retractions on deleted fields. Same-value leaves do not churn.
    """
    if not isinstance(field_map,dict) or not all(isinstance(k,str) and k for k in field_map):
        raise PolicyError('INVALID_SNAPSHOT')
    before=_current_fields(memory,scope,key,source,valid_from)
    actions=[]
    for field in sorted(set(before)|set(field_map)):
        if field in before and field not in field_map:
            actions.append({'key':key,'field':field,'source':source,'retract':True,'valid_from':valid_from})
        elif field in field_map and (field not in before or before[field]!=field_map[field]):
            actions.append({'key':key,'field':field,'source':source,'value':field_map[field],'valid_from':valid_from})
    if not actions:return {'unchanged':True,'fields_changed':0}
    result=memory.batch_publish(scope,actions)
    return {'unchanged':False,'fields_changed':len(actions),**result}


def ingest_python(memory,scope,module_name,content,*,source='repository',valid_from):
    if not isinstance(content,str):raise PolicyError('INVALID_CODE_INPUT')
    return publish_snapshot(memory,scope,'code:'+module_name,source,python_signatures(content),valid_from=valid_from)


def ingest_json(memory,scope,doc_name,payload,*,source='document',valid_from):
    if isinstance(payload,str):payload=json.loads(payload)
    return publish_snapshot(memory,scope,'json:'+doc_name,source,flatten_json(payload),valid_from=valid_from)
