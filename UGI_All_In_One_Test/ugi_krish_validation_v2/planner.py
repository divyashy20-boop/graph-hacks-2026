"""Krish-style observation-based read-only MCP-tool sequencing.

This is a deterministic comparison adapter, NOT a validated autonomous LLM.
The dispatch calls UGI's own MCP handler, which is NOT a full transport test.
"""
from __future__ import annotations


def plan_readonly(target, evaluate_subject=None, evaluate_object=None, predicate='TRANSITIVELY_DEPENDS_ON'):
    """Explicit branching by available observations; not a hardcoded ticket sequence."""
    if not target or not target.strip():
        raise ValueError('Target required')
    out = [{'tool': 'search_entities', 'arguments': {'name': target},
            'reason': 'Resolve exact target identity before graph traversal'}]
    if evaluate_subject and evaluate_object:
        out.append({'tool': 'evaluate_relationship', 'arguments': {
            'subject': evaluate_subject, 'object': evaluate_object, 'predicate': predicate},
            'reason': 'Check an explicitly requested relation and its multi-hop evidence'})
    return out


def actual_mcp_handler_probe(engine, target, evaluate_subject=None, evaluate_object=None,
                             predicate='TRANSITIVELY_DEPENDS_ON', max_steps=4):
    from ugi.mcp_server import call_tool
    steps = []
    for selection in plan_readonly(target, evaluate_subject, evaluate_object, predicate):
        if len(steps) >= max_steps:
            return {'status': 'BUDGET_EXHAUSTED', 'steps': steps, 'writes_attempted': 0}
        # Handler refuses write attempts because allow_writes is explicitly False.
        response = call_tool(engine, selection['tool'], selection['arguments'], allow_writes=False)
        steps.append({'tool': selection['tool'], 'arguments': selection['arguments'],
                      'reason': selection['reason'], 'result': response})
        if selection['tool'] == 'search_entities':
            ents = response.get('entities', []) if isinstance(response, dict) else []
            if len(ents) != 1:
                return {'status': 'AMBIGUOUS_OR_MISSING', 'steps': steps,
                        'writes_attempted': 0, 'reason': 'No unique target identity'}
    if steps and steps[-1]['tool'] == 'evaluate_relationship':
        result = steps[-1]['result']
        ids = result.get('supporting_claim_ids', []) if isinstance(result, dict) else []
        if ids:
            # Adaptive optional evidence retrieval; capped to one claim by design.
            cid = sorted(ids)[0]
            response = call_tool(engine, 'get_claim_evidence', {'claim_id': cid}, allow_writes=False)
            steps.append({'tool': 'get_claim_evidence', 'arguments': {'claim_id': cid},
                          'reason': 'Inspect exact supporting quote', 'result': response})
    return {'status': 'READ_ONLY_COMPLETED', 'steps': steps, 'writes_attempted': 0,
            'planner': 'deterministic_observation_driven_adapter',
            'mcp_level': 'UGI Python handler, not external stdio client'}
