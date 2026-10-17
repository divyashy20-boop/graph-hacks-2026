"""Executable state machine atop UGI MCP stdio, with evidence-linked reasoning trace."""
from __future__ import annotations

import hashlib
import json
from time import monotonic
from .rulebook import (ALLOWED_STATUS, Intent, RulebookError, determine_step,
                       expected_args, interpret_request, validate_arguments)

MAX_CALLS=12


def _unwrap(result: dict) -> dict:
    if not isinstance(result, dict) or result.get('isError') is True:
        raise RulebookError('MCP_REPORTED_ERROR:'+str(result.get('content',[]))[:140])
    value = result.get('structuredContent')
    if not isinstance(value, dict):
        raise RulebookError('MCP_STRUCTURED_CONTENT_MISSING')
    return value


def inspect_claims(relation: dict) -> set[str]:
    ids = set()
    evs = relation.get('evidence', [])
    if not isinstance(evs, list) or len(evs) > 100:
        raise RulebookError('EVIDENCE_LIST_OVER_LIMIT')
    for e in evs:
        claim = (e or {}).get('claim') or {}
        cid = claim.get('id')
        if not isinstance(cid, str) or not 1 <= len(cid) <= 160:
            raise RulebookError('EVIDENCE_CLAIM_ID_INVALID')
        if not claim.get('source_id') or not claim.get('evidence_id'):
            raise RulebookError('EVIDENCE_PROVENANCE_INCOMPLETE')
        ids.add(cid)
    if relation.get('status') in {'SOURCE_ASSERTED', 'RULE_DERIVED'} and not ids:
        raise RulebookError('POSITIVE_RELATION_WITHOUT_CITABLE_EVIDENCE')
    if relation.get('status') == 'RULE_DERIVED':
        resolution = relation.get('resolution') or {}
        if resolution.get('assessment') == 'CONNECTED_BUT_NOT_ENTAILED':
            raise RulebookError('RULE_DERIVED_RESPONSE_SELF_CONTRADICTS')
        if not relation.get('rules'):
            raise RulebookError('DERIVATION_RULE_ID_MISSING')
    return ids


def check_claim_detail(claim_id: str, record: dict) -> str:
    claim = record.get('claim') or {}
    ev = record.get('evidence') or {}
    if claim.get('id') != claim_id or claim.get('evidence_id') != ev.get('id'):
        raise RulebookError('CLAIM_EVIDENCE_ID_MISMATCH')
    if claim.get('source_id') != ev.get('source_id'):
        raise RulebookError('CLAIM_EVIDENCE_SOURCE_MISMATCH')
    if not isinstance(ev.get('quote'), str) or not ev['quote'].strip():
        raise RulebookError('CLAIM_SOURCE_QUOTE_MISSING')
    # Hash for logs: avoid copying entire original source text into result logs.
    return hashlib.sha256(ev['quote'].encode()).hexdigest()


def run_controller(query: str, dataset: str, known_entities: list[str], mcp,
                   *, max_calls: int=MAX_CALLS, advisor=None) -> dict:
    """Return structured result even for abstentions. Calls always come from rulebook.

    LLM advisor (optional) can recommend the next phase, but cannot supply args,
    override the policy controller, fabricate evidence, or authorize writes.
    Its agreement is separately measured; policy remains authoritative.
    """
    result={'query':query, 'dataset':dataset,'status':'INCOMPLETE','reason':None,
            'controller_type':'policy_state_machine', 'llm_tool_arguments_used':False,
            'model_advice_count':0,'model_advice_agreements':0,'model_advice_errors':[],
            'trace':[],'verified_claim_ids':[],'source_quote_sha256':{},
            'unverified_incident_impact':True,'writes_attempted':0}
    try:
        intent=interpret_request(query,dataset,known_entities)
        result['interpreted']={'subject':intent.subject,'object':intent.object,
                               'predicate':intent.predicate,'preview':intent.preview,'method':intent.method}
        listing=mcp.request('tools/list')
        definitions=(listing.get('result') or {}).get('tools',[])
        schemas={d['name']:d for d in definitions if isinstance(d, dict) and 'name' in d}
        if len(schemas) < 4:
            raise RulebookError('MCP_TOOL_CATALOG_INCOMPLETE')
        state={'resolved':set(),'relation':None,'evidence_ids':set(), 'checked_ids':set(), 'preview_done':False}
        for step_idx in range(max_calls):
            stage=determine_step(state,intent)
            if stage=='DONE':
                relation=state['relation']
                result['status']='COMPLETE'
                result['verdict']=relation['status']
                result['rule_ids']=relation.get('rules',[])
                result['verified_claim_ids']=sorted(state['checked_ids'])
                result['preview_done']=state['preview_done']
                result['explanation']=relation.get('explanation','')
                result['resolution']=relation.get('resolution')
                result['causality_proven']=False
                break
            tool_name,args=expected_args(stage,intent)
            validate_arguments(tool_name,args,schemas)
            advice=None
            if advisor is not None:
                try:
                    advice=advisor(stage, {'completed_phases':[e['phase'] for e in result['trace']],
                                           'pending_evidence': sorted(state['evidence_ids']-state['checked_ids']),
                                           'allowed_tool_names': list(sorted(schemas)),
                                           'user_request':query,
                                           'selected_dataset':dataset,
                                           'schema':schemas[tool_name]['inputSchema']})
                    if advice is not None:
                        result['model_advice_count']+=1
                        if advice==tool_name:
                            result['model_advice_agreements']+=1
                except Exception as exc:
                    result['model_advice_errors'].append(type(exc).__name__ + ': ' + str(exc)[:160])
            started=monotonic()
            response=_unwrap(mcp.tool(tool_name,args))
            entry={'phase':stage,'tool':tool_name,'argument_keys':sorted(args),
                   'target':args.get('name',args.get('target',args.get('claim_id'))),
                   'source':'rulebook_derived_from_verified_state',
                   'model_advice':advice,'read_only':True,'elapsed_ms':round(1000*(monotonic()-started),2)}
            if tool_name=='search_entities':
                hits=response.get('entities') or []
                if len(hits)!=1 or hits[0].get('name')!=args['name']:
                    raise RulebookError('MISSING_OR_AMBIGUOUS_ENTITY:'+args['name'])
                state['resolved'].add(args['name'])
                entry['resolved_entity_id']=hits[0].get('id')
            elif tool_name=='evaluate_relationship':
                if response.get('status') not in ALLOWED_STATUS:
                    raise RulebookError('UNKNOWN_RELATION_VERDICT')
                state['relation']=response
                state['evidence_ids']=inspect_claims(response)
                entry['verdict']=response['status']
                entry['supporting_claims']=len(state['evidence_ids'])
            elif tool_name=='get_claim_evidence':
                sha=check_claim_detail(args['claim_id'],response)
                if args['claim_id'] not in state['evidence_ids']:
                    raise RulebookError('UNSOLICITED_CLAIM_REFERENCE')
                state['checked_ids'].add(args['claim_id'])
                result['source_quote_sha256'][args['claim_id']]=sha
                entry['quote_sha256']=sha
            elif tool_name=='investigate_dependency_incident':
                if response.get('executed') is not False:
                    raise RulebookError('UNAUTHORIZED_OR_DUPLICATE_INVESTIGATION_ACTION')
                state['preview_done']=True
                entry['preview_only']=True
            result['trace'].append(entry)
        else:
            raise RulebookError('TOOL_STEP_BUDGET_EXCEEDED')
    except (RulebookError, ValueError, KeyError) as exc:
        result['status']='ABSTAIN' if not result['trace'] else 'INCOMPLETE'
        result['reason']=str(exc)[:300]
    except Exception as exc:
        result['status']='ERROR'
        result['reason']=type(exc).__name__+': '+str(exc)[:220]
    return result
