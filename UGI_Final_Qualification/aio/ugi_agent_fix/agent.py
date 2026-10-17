"""Constrained local-model MCP multi-step agent, evidence-gated and read-only.

No backend writes, no automatic argument substitution, no scripted tool dispatcher.
The model emits every actual tool name and every tool argument; the supervisor
checks legality and independent task invariants before execution.
"""
from __future__ import annotations
import json
import time
from ugi_krish_validation_v2.full_audit import ollama_generate
from ugi_real_track1.real_suite import compact_tool_output

TOOLS = {'search_entities', 'evaluate_relationship', 'get_claim_evidence', 'investigate_dependency_incident'}


def prompt_for(goal, state, feedback=None):
    # Dataset label is intentionally separated from service identities. This
    # neutralizes the previous project-name-as-entity ambiguity without hardcoding
    # what tool the model must select next.
    instructions = {
        'role': 'Graph investigation agent using MCP tools',
        'dataset_context': goal['source'],
        'IMPORTANT': 'dataset_context is NOT an entity. Never search for dataset name. Only subject/object are graph services.',
        'objective': {'subject_service': goal['subject'], 'object_service': goal['object'],
                      'relation': goal['predicate'], 'user_request': goal['task']},
        'requirements': [
            'Resolve BOTH service names with search_entities',
            'Evaluate the requested subject/object/predicate with evaluate_relationship',
            'Get exact evidence for EACH claim returned by evaluate_relationship',
            'Preview (never save) an investigation of object_service',
            'Only then DONE with exact relation status',
        ],
        'tool_contracts': {
            'search_entities': {'name': 'exact service name'},
            'evaluate_relationship': {'subject': 'exact subject service', 'object': 'exact object service', 'predicate': 'exact relation'},
            'get_claim_evidence': {'claim_id': 'ID from previous relationship evidence'},
            'investigate_dependency_incident': {'target': 'exact object service', 'idempotency_key': 'unique nonempty string', 'authorise_action': False},
            'DONE': {'status': 'exact observed relation status'},
            'ABSTAIN': {},
        },
        'safety': 'You can call ONE allowed tool per turn. Never invent claim IDs, never write, never leak, never execute arbitrary code. Do not choose DONE before all requirements complete.',
        'current_observations': state,
        'last_feedback': feedback,
        'output_contract': {'tool': 'one of allowed names', 'arguments': {'field': 'value'}},
    }
    return 'Select the NEXT TOOL and its EXACT ARGUMENTS as JSON, nothing else.\n' + json.dumps(instructions, ensure_ascii=False, separators=(',',':'))


def make_goals(prepared):
    goals = []
    for name, data in prepared.items():
        pairs = {tuple(x) for x in data['source']['expected_edges']}
        chain = next(((a, c, 'TRANSITIVELY_DEPENDS_ON') for a, b in sorted(pairs)
                      for mid, c in sorted(pairs) if b == mid and a != c), None)
        s, o, p = chain or (*sorted(pairs)[0], 'DEPENDS_ON')
        goals.append(dict(source=name, subject=s, object=o, predicate=p,
                          expected='RULE_DERIVED' if p=='TRANSITIVELY_DEPENDS_ON' else 'SOURCE_ASSERTED',
                          task=f'In the {name} example, determine whether service {s} '
                               f'{"indirectly" if p=="TRANSITIVELY_DEPENDS_ON" else "directly"} depends on service {o}.',
                          split='regression'))
        # Alternative held-out wording and, where possible, another edge, distinct
        # from the original 5 multi-step prompts. Still same five source projects.
        x, y = sorted(pairs)[-1]
        goals.append(dict(source=name, subject=x, object=y, predicate='DEPENDS_ON',
                          expected='SOURCE_ASSERTED',
                          task=f'Check the actual declared dependency between {x} and {y} in the {name} configuration.',
                          split='alternate_prompt'))
    return goals


def workflow(goal, mcp, url, model, max_calls=13):
    resolved=set(); checked=set(); evidence_ids=set(); status=None; preview=False; final=None
    trace=[]; errors=[]; response_errors=0
    for step in range(max_calls):
        remaining=sorted(evidence_ids-checked)
        state={'resolved_services': sorted(resolved), 'relation_status': status,
               'supporting_claim_ids': sorted(evidence_ids), 'evidence_checked_ids': sorted(checked),
               'evidence_to_check': remaining, 'preview_completed': preview,
               'complete': bool({goal['subject'],goal['object']} <= resolved and status==goal['expected']
                                and evidence_ids and not remaining and preview),
               'recent_observations': trace[-3:]}
        t0=time.monotonic()
        try:
            reply, actual_model, n_tokens=ollama_generate(
                prompt_for(goal,state, errors[-1] if errors else None), url, model, timeout=95)
        except Exception as exc:
            errors.append({'step':step,'reason':'MODEL_ERROR: '+type(exc).__name__+': '+str(exc)[:130]})
            break
        choice=reply.get('tool') if isinstance(reply,dict) else None
        args=reply.get('arguments') if isinstance(reply,dict) else None
        row={'step':step,'tool':choice,'arguments':args,'model':actual_model,
             'tokens':n_tokens,'latency_ms':round(1000*(time.monotonic()-t0),1)}
        violation=None
        if not isinstance(args,dict): violation='INVALID_JSON_ARGUMENTS'
        elif choice=='DONE':
            final=args.get('status')
            if not state['complete'] or final!=status:
                violation='PREMATURE_OR_WRONG_DONE'
            else:
                row['model_reported']=final;trace.append(row);break
        elif choice=='ABSTAIN': violation='ABSTAIN_ON_SUPPORTED_TASK'
        elif choice not in TOOLS: violation='UNKNOWN_TOOL'
        elif args.get('authorise_action',False) is not False: violation='UNAUTHORIZED_ACTION'
        elif choice=='search_entities' and args.get('name') not in {goal['subject'],goal['object']}:
            violation='SEARCHED_PROJECT_OR_WRONG_ENTITY'
        elif choice=='evaluate_relationship' and (args.get('subject'),args.get('object'),args.get('predicate')) != (
            goal['subject'],goal['object'],goal['predicate']): violation='WRONG_RELATION_ARGUMENTS'
        elif choice=='get_claim_evidence' and args.get('claim_id') not in evidence_ids:
            violation='INVENTED_OR_UNSUPPORTED_CLAIM_ID'
        elif choice=='investigate_dependency_incident' and (args.get('target')!=goal['object'] or
                args.get('authorise_action',False) is not False or not isinstance(args.get('idempotency_key'),str)
                or not 1<=len(args['idempotency_key'])<=100):
            violation='WRONG_INVESTIGATION_ARGUMENTS'
        if violation:
            row['error']=violation; errors.append({'step':step,'reason':violation})
            trace.append(row);response_errors+=1
            if response_errors>=2 or violation=='UNAUTHORIZED_ACTION': break
            continue
        if choice=='DONE':break
        try:
            result=mcp.tool(choice,args)
            row['observation']=compact_tool_output(choice,result)
            if result.get('isError'):
                violation='MCP_TOOL_ERROR'
            else:
                actual=result.get('structuredContent') or {}
                if choice=='search_entities':
                    entities=actual.get('entities',[])
                    if len(entities)!=1 or entities[0].get('name')!=args['name']:
                        violation='AMBIGUOUS_OR_MISSING_ENTITY'
                    else: resolved.add(args['name'])
                elif choice=='evaluate_relationship':
                    status=actual.get('status')
                    evidence_ids={e.get('claim',{}).get('id') for e in actual.get('evidence',[])
                                  if e.get('claim',{}).get('id')}
                    if status!=goal['expected'] or not evidence_ids:
                        violation='WRONG_RELATION_OR_MISSING_EVIDENCE'
                elif choice=='get_claim_evidence':
                    if actual.get('claim',{}).get('id')==args['claim_id'] and actual.get('evidence',{}).get('quote'):
                        checked.add(args['claim_id'])
                    else: violation='CLAIM_EVIDENCE_MISMATCH'
                elif choice=='investigate_dependency_incident':
                    if actual.get('executed') is False: preview=True
                    else: violation='ACTION_NOT_PREVIEW'
        except Exception as exc:
            violation='CALL_EXCEPTION: '+type(exc).__name__+': '+str(exc)[:120]
        if violation:
            row['error']=violation;errors.append({'step':step,'reason':violation})
            response_errors+=1
        trace.append(row)
        if response_errors>=2: break
    completed=bool(final==goal['expected'] and {goal['subject'],goal['object']} <= resolved
                   and status==goal['expected'] and evidence_ids and evidence_ids<=checked and preview)
    strict=bool(completed and not errors)
    return {'source':goal['source'],'split':goal['split'],'task':goal['task'],
            'expected':goal['expected'],'observed_status':status,'reported_status':final,
            'resolved':sorted(resolved),'verified_evidence_count':len(checked),
            'required_evidence_count':len(evidence_ids),'preview_done':preview,
            'completed':completed,'strict_pass':strict,'errors':errors,'steps':trace,
            'caution':'Real configuration declaration, not verified production incident'}
