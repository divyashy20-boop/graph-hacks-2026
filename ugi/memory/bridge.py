"""UGI MCP → tracked receipt integration, limited to disposable test namespaces.

This bridge captures EVERY permitted tools/call output observed by the controller,
then projects those observed values into the P5 append-only SQLite ledger. It does
not trust an LLM to say what it used. Negative graph answers are tracked too.

Important: refresh is required to notice changes made outside this process.
Do not connect this proof to actual external side effects or claim distributed
atomicity; the P5 gate is atomic ONLY for local SQLite internal effects.
"""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass
from typing import Any
from .core import Memory, PolicyError, stable
from ..agent_policy.controller import run_controller
from .registry import ReceiptRegistry, RegistryError

ALLOWED = frozenset({'search_entities','evaluate_relationship','get_claim_evidence','investigate_dependency_incident'})
MAX_OBSERVATIONS=32

class BridgeError(RuntimeError):
    pass


def key_for(name: str, arguments: dict) -> str:
    if name not in ALLOWED or not isinstance(arguments, dict):
        raise BridgeError('UNSUPPORTED_MCP_TOOL')
    return 'mcp:' + name + ':' + stable({'arguments':arguments})


def _raw_observation(result):
    if not isinstance(result,dict):
        raise BridgeError('MCP_RESPONSE_INVALID')
    if 'error' in result:
        raise BridgeError('MCP_TRANSPORT_ERROR')
    obj=(result.get('result') or {})
    if obj.get('isError') is True:
        raise BridgeError('MCP_TOOL_ERROR')
    value=obj.get('structuredContent')
    if not isinstance(value,dict):
        raise BridgeError('MCP_EVIDENCE_MISSING')
    if len(json.dumps(value,default=str))>250_000:
        raise BridgeError('MCP_RESPONSE_OVER_BUDGET')
    return value


def _normalize(name: str, value: dict) -> dict:
    """Conservative normalized tool output; excludes volatile timing where known.
    A larger-than-needed read set causes false STALE, not false VALID.
    """
    if name=='search_entities':
        return {'entities': sorted([{'id':r.get('id'), 'name':r.get('name'),
                       'identity_key':r.get('identity_key'), 'external_id':r.get('external_id'),
                       'aliases':sorted(r.get('aliases') or [])}
                      for r in value.get('entities',[])],key=lambda e:str(e['id']))}
    if name=='evaluate_relationship':
        evidence=value.get('evidence') or []
        return {'status':value.get('status'), 'rules':value.get('rules') or [],
                'supporting_claims':sorted([{'id':(x.get('claim') or {}).get('id'),
                              'source_id':(x.get('claim') or {}).get('source_id'),
                              'polarity':(x.get('claim') or {}).get('polarity'),
                              'verification_level':(x.get('claim') or {}).get('verification_level')}
                             for x in evidence],key=lambda x:str(x['id'])),
                'resolution':value.get('resolution')}
    if name=='get_claim_evidence':
        claim=value.get('claim') or {};evidence=value.get('evidence') or {}
        return {'claim_id':claim.get('id'), 'claim_source_id':claim.get('source_id'),
                'polarity':claim.get('polarity'), 'review_status':claim.get('review_status'),
                'evidence_id':evidence.get('id'), 'evidence_source_id':evidence.get('source_id'),
                'quote_digest':hashlib.sha256(str(evidence.get('quote','')).encode()).hexdigest()}
    if name=='investigate_dependency_incident':
        if value.get('executed') is not False:
            raise BridgeError('INVESTIGATION_WAS_NOT_READ_ONLY')
        return {'preview_only':True, 'target':value.get('target')}
    raise BridgeError('UNSUPPORTED_MCP_TOOL')


class CapturingMCP:
    """No arbitrary writes: rejects all unrecognized tools and authorized actions."""
    def __init__(self, client):
        self.client=client
        self.observed={}

    def request(self, method, params=None, **kwargs):
        if method not in {'initialize','tools/list','tools/call','ping'}:
            raise BridgeError('NON_ALLOWLISTED_MCP_METHOD')
        if method=='tools/call':
            if not isinstance(params,dict) or params.get('name') not in ALLOWED:
                raise BridgeError('NON_ALLOWLISTED_MCP_TOOL')
            arguments=params.get('arguments')
            if not isinstance(arguments,dict):
                raise BridgeError('MCP_ARGUMENTS_INVALID')
            if params['name']=='investigate_dependency_incident' and arguments.get('authorise_action') is not False:
                raise BridgeError('EXTERNAL_ACTIONS_DISABLED')
            if len(self.observed)>=MAX_OBSERVATIONS and key_for(params['name'],arguments) not in self.observed:
                raise BridgeError('OBSERVATION_BUDGET_EXCEEDED')
            response=self.client.request(method,params,**kwargs)
            # Capture only responses actually returned by MCP; never model-generated values.
            norm=_normalize(params['name'],_raw_observation(response))
            self.observed[key_for(params['name'],arguments)]={'name':params['name'],
                'args':dict(arguments), 'value':norm}
            return response
        return self.client.request(method,params,**kwargs)

    def tool(self, name, arguments):
        return self.request('tools/call',{'name':name,'arguments':arguments}).get('result',{})


def publish_observations(memory: Memory, scope: str, entries: dict, *, day: str) -> dict:
    if not scope or not entries or len(entries)>MAX_OBSERVATIONS:
        raise BridgeError('INVALID_SCOPE_OR_EMPTY_OBSERVATIONS')
    changed=0; untouched=0
    # Process a known UGI CONTRADICTED verdict before secondary lookups.
    # Combined with UNKNOWN precedence in the P5 status lattice, this
    # prevents intermediate STALE from obscuring an observed contradiction.
    ordered=sorted(entries.items(),key=lambda item: 0 if (
             item[1]['name']=='evaluate_relationship' and
             item[1]['value'].get('status')=='CONTRADICTED') else 1)
    for key, entry in ordered:
        if not key.startswith('mcp:'):
            raise BridgeError('NON_MCP_OBSERVATION')
        actual=memory.state_as_known(scope,key,'/result',day)
        data=entry['value']
        contradicted=(entry['name']=='evaluate_relationship' and
                      data.get('status')=='CONTRADICTED')
        # A contradiction in the REAL UGI verdict maps to UNKNOWN, not VALID.
        # Insert a distinct conflicting source within one SQLite transaction,
        # so prior VALID receipts become UNKNOWN without an intermediate STALE.
        if contradicted:
            if actual['verdict']=='CONFLICT':
                untouched+=1;continue
            events=[]
            if actual['verdict']=='ABSENT':
                events.append({'key':key,'field':'/result','source':'ugi-mcp-observed',
                               'value':data,'valid_from':day})
            events.append({'key':key,'field':'/result','source':'ugi-mcp-conflict-signal',
                           'value':{'contradicted':True},'valid_from':day})
            memory.batch_publish(scope,events)
            changed+=1;continue
        # Remove an old contradiction marker when newer graph readings agree;
        # previously invalidated receipts do not magically become VALID.
        if actual['verdict']=='CONFLICT':
            memory.batch_publish(scope,[
               {'key':key,'field':'/result','source':'ugi-mcp-observed','value':data,'valid_from':day},
               {'key':key,'field':'/result','source':'ugi-mcp-conflict-signal','retract':True,'valid_from':day}])
            changed+=1;continue
        if actual['verdict']=='CLEAR' and actual['value']==data:
            untouched+=1;continue
        memory.publish(scope,key,'/result',data,source='ugi-mcp-observed',valid_from=day)
        changed+=1
    return {'changed':changed,'unchanged':untouched}


def track_controller(memory:Memory, client, *, scope:str, dataset:str,
                     query:str, entities:list[str], day:str, allowed_source_ids=None):
    if scope.split('::')[-1]!=dataset:
        raise BridgeError('SCOPE_DATASET_MISMATCH')
    proxy=CapturingMCP(client)
    outcome=run_controller(query,dataset,entities,proxy,allowed_source_ids=allowed_source_ids)
    # Do not issue receipts for incomplete or ungrounded agent runs.
    if outcome['status']!='COMPLETE':
        return {'status':outcome['status'],'reason':outcome.get('reason'),'receipt':None,
                'controller':outcome,'capture_count':len(proxy.observed)}
    if not proxy.observed:
        raise BridgeError('ZERO_TOOL_READS_FOR_COMPLETED_AGENT')
    publish_observations(memory,scope,proxy.observed,day=day)
    reader=memory.open_read(scope,day)
    for key in sorted(proxy.observed):
        state=reader.read(key,'/result')
        if state['verdict']!='CLEAR':
            raise BridgeError('UNEXPECTED_TRACKED_SOURCE_STATE')
    receipt=reader.seal({'query':query,'dataset':dataset,'verdict':outcome.get('verdict'),
             'claim_ids':outcome.get('verified_claim_ids',[]),'tool_calls':len(outcome.get('trace',[]))})
    ReceiptRegistry(memory).save(receipt['rid'],scope,proxy.observed)
    return {'status':outcome['status'],'receipt':receipt,'controller':outcome,
            'capture_count':len(proxy.observed),'observation_keys':sorted(proxy.observed)}


def receipt_read_differences(memory: Memory, receipt_id: str, *, scope: str) -> list[str]:
    """Compare original receipt fingerprints, not per-refresh global write count.

    A different receipt can refresh shared MCP observations first. Its write
    makes this receipt STALE, while our own subsequent refresh publishes zero
    additional events. Comparing original fingerprints prevents interpreting
    that zero as a false claim that this receipt was unaffected.
    """
    recorded=memory.receipt(receipt_id)
    if recorded['scope']!=scope:
        raise BridgeError('RECEIPT_SCOPE_MISMATCH')
    changes=[]
    for dependency in recorded['dependencies']:
        if dependency['kind']!='FIELD':
            # All bridge receipts should be field reads. Unknown dependency
            # kinds must not lead to a false-clean freshness diagnosis.
            raise BridgeError('UNSUPPORTED_RECEIPT_DEPENDENCY_KIND')
        current=memory.state_as_known(
            scope,dependency['fact_key'],dependency['field_path'],recorded['valid_at'])
        if current['fingerprint']!=dependency['fingerprint']:
            changes.append(dependency['fact_key'])
    return sorted(set(changes))


def refresh_receipt(memory:Memory, client, *, scope:str, receipt:dict, day:str) -> dict:
    """Mandatory fresh MCP reread before deciding whether an old answer is reusable.
    The exact tool/args are kept in an explicit provided read-log registry, never
    reconstructed by an LLM. The registry is separate from persisted P5 hashes.
    """
    provided=receipt.get('observations')
    try:
        entries=ReceiptRegistry(memory).load(receipt['rid'],scope)
    except (KeyError,RegistryError) as exc:
        raise BridgeError('OBSERVATION_REGISTRY_MISSING_OR_CORRUPT') from exc
    if provided is not None:
        expected={k:{'name':v['name'],'args':v['args']} for k,v in provided.items()}
        if expected!=entries:
            raise BridgeError('OBSERVATION_REGISTRY_TAMPERING')
    fresh=CapturingMCP(client)
    for key,entry in entries.items():
        if key!=key_for(entry['name'],entry['args']):
            raise BridgeError('READ_LOG_TAMPERING')
        # Fail closed by recording an unavailable state if an MCP read fails.
        try:
            fresh.tool(entry['name'],entry['args'])
        except Exception as exc:
            fresh.observed[key]={'name':entry['name'],'args':entry['args'],
                                 'value':{'unavailable':type(exc).__name__}}
    previous_status=memory.receipt(receipt['rid'])['status']
    result=publish_observations(memory,scope,fresh.observed,day=day)
    differences=receipt_read_differences(memory,receipt['rid'],scope=scope)
    result['receipt_status']=memory.receipt(receipt['rid'])['status']
    result['previous_receipt_status']=previous_status
    result['original_read_difference_count']=len(differences)
    result['original_read_difference_keys']=differences
    # Even when fingerprints later return to a prior value, a receipt that
    # already consumed a changed revision is NEVER auto-revalidated.
    result['sticky_invalidated']=result['receipt_status']!='VALID' and not differences
    return result


def track_and_register(memory, client, *, scope, dataset, query, entities, day, allowed_source_ids=None):
    # Registry is maintained by the caller in the disposable test session.
    # It is NOT a production durable registry; restart/recovery is an open gap.
    if not isinstance(scope,str) or scope.split('::')[-1]!=dataset:
        raise BridgeError('SCOPE_DATASET_MISMATCH')
    wrapped=CapturingMCP(client)
    outcome=run_controller(query,dataset,entities,wrapped,allowed_source_ids=allowed_source_ids)
    if outcome['status']!='COMPLETE':
        return {'outcome':outcome,'receipt':None,'observations':dict(wrapped.observed)}
    if not wrapped.observed:
        raise BridgeError('ZERO_TOOL_READS_FOR_COMPLETED_AGENT')
    publish_observations(memory,scope,wrapped.observed,day=day)
    rd=memory.open_read(scope,day)
    for key in sorted(wrapped.observed):rd.read(key,'/result')
    rec=rd.seal({'query':query,'verdict':outcome.get('verdict'),
                 'verified_claim_ids':outcome.get('verified_claim_ids',[])})
    ReceiptRegistry(memory).save(rec['rid'],scope,wrapped.observed)
    return {'outcome':outcome,'receipt':rec,'observations':dict(wrapped.observed)}
