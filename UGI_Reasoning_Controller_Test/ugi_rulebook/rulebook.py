"""A bounded evidence-first rulebook; tool arguments are constructed from validated state.

The controller is guided/deterministic, not a free-form autonomous MCP planner.
Dataset context is separate from entity identities. It does not use benchmark answers.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Mapping, Any

ALLOWED_STATUS = frozenset({'SOURCE_ASSERTED', 'SOURCE_NEGATED', 'CONTRADICTED',
                            'RULE_DERIVED', 'CONNECTED_ONLY', 'UNKNOWN'})
ALLOWED_TOOLS = frozenset({'search_entities','evaluate_relationship',
                            'get_claim_evidence','investigate_dependency_incident'})
# These contracts mirror the UGI MCP server; validate them against live tools/list too.
CONTRACTS = {
    'search_entities': {'required': {'name'}, 'allowed': {'name'}},
    'evaluate_relationship': {'required': {'subject','object','predicate'},
                              'allowed': {'subject','object','predicate','as_of'}},
    'get_claim_evidence': {'required': {'claim_id'}, 'allowed': {'claim_id'}},
    'investigate_dependency_incident': {'required': {'target','idempotency_key'},
                                       'allowed': {'target','idempotency_key','as_of','authorise_action'}},
}
UNSAFE_QUERY = re.compile(r'\b(?:delete|drop|wipe|exfiltrat|send\s+secrets|steal\s+data)\b', re.I)

class RulebookError(Exception):
    """Safe abstention or validation failure (never silently turn into a query)."""

@dataclass(frozen=True)
class Intent:
    dataset: str
    subject: str
    object: str
    predicate: str
    preview: bool
    requested_text: str
    method: str = 'explicit_service_mentions'


def remove_scope_phrase(text: str, dataset: str) -> str:
    """Remove only known scope wording; don't globally erase possible entity mentions."""
    safe = re.escape(dataset)
    pat = re.compile(r'\b(?:in|for)\s+(?:the\s+)?' + safe +
                     r'\s+(?:example|project|configuration|compose\s+file)\b', re.I)
    return pat.sub(' ', text)


def interpret_request(query: str, dataset: str, known_entities: list[str]) -> Intent:
    """Interpret explicit relationship questions only; abstain if direction is ambiguous.

    This is intentionally a *narrow* deterministic interpreter, not arbitrary-language NLU.
    Available names come from actual dataset entities, NEVER benchmark answer fields.
    """
    if not isinstance(query, str) or not 5 <= len(query) <= 2000:
        raise RulebookError('QUERY_LENGTH_INVALID')
    if UNSAFE_QUERY.search(query):
        raise RulebookError('UNSAFE_REQUEST_REQUIRES_OPERATOR_REVIEW')
    content = remove_scope_phrase(query, dataset)
    names = sorted(set(known_entities), key=lambda s: (-len(s), s))
    if not names or len(names) > 1200:
        raise RulebookError('ENTITY_INVENTORY_UNAVAILABLE_OR_TOO_LARGE')
    locations = []
    for name in names:
        hits = list(re.finditer(r'(?<![\w.-])' + re.escape(name) + r'(?![\w-]|\.[\w])', content, re.I))
        for m in hits:
            locations.append((m.start(), name))
    locations.sort()
    seen = []
    for _, name in locations:
        if name not in seen:
            seen.append(name)
    if len(seen) != 2:
        raise RulebookError('NEEDS_EXACTLY_TWO_UNAMBIGUOUS_ENTITY_NAMES')
    if re.search(r'\b(?:indirect(?:ly)?|transitiv(?:e|ely))\b', content, re.I):
        predicate = 'TRANSITIVELY_DEPENDS_ON'
    elif re.search(r'\b(?:direct(?:ly)?|declared|depends?\s+on|dependency)\b', content, re.I):
        predicate = 'DEPENDS_ON'
    else:
        raise RulebookError('UNSUPPORTED_OR_AMBIGUOUS_RELATIONSHIP')
    # Explicit "between A and B" is directionally ambiguous unless the user
    # specifically asks a declared dependency and gives order; state that limit.
    if re.search(r'\bbetween\b', content, re.I) and not re.search(r'\b(?:declared|actual)\b', content, re.I):
        raise RulebookError('BETWEEN_RELATION_DIRECTION_AMBIGUOUS')
    return Intent(dataset=dataset, subject=seen[0], object=seen[1], predicate=predicate,
                  preview=bool(re.search(r'\b(?:preview|investigat(?:e|ion)|assess\s+impact)\b', content, re.I)),
                  requested_text=query)


def validate_arguments(name: str, args: dict, schemas: Mapping[str, Any] | None = None) -> None:
    if name not in CONTRACTS or not isinstance(args, dict):
        raise RulebookError('UNKNOWN_TOOL_OR_BAD_ARGUMENTS')
    contract = CONTRACTS[name]
    if not contract['required'] <= args.keys() or args.keys() - contract['allowed']:
        raise RulebookError('TOOL_SCHEMA_INVALID_FIELDS:' + name)
    if any(not isinstance(args[k], str) or not args[k].strip() or len(args[k]) > 240
           for k in args if k != 'authorise_action'):
        raise RulebookError('TOOL_SCHEMA_INVALID_STRING:' + name)
    if name == 'investigate_dependency_incident' and args.get('authorise_action') is not False:
        raise RulebookError('WRITE_TOOL_MUST_BE_PREVIEW_ONLY')
    if schemas is not None:
        remote = schemas.get(name)
        if remote is None:
            raise RulebookError('MCP_TOOL_MISSING:' + name)
        schema = remote.get('inputSchema') or {}
        if not contract['required'] <= set((schema.get('properties') or {}).keys()):
            raise RulebookError('MCP_SCHEMA_DISAGREES_WITH_RULEBOOK:' + name)
        if set(args) - set((schema.get('properties') or {}).keys()):
            raise RulebookError('MCP_SCHEMA_UNKNOWN_ARGUMENT:' + name)


def determine_step(state: Mapping, intent: Intent) -> str:
    if intent.subject not in state['resolved']:
        return 'resolve_subject'
    if intent.object not in state['resolved']:
        return 'resolve_object'
    if state['relation'] is None:
        return 'evaluate_relationship'
    for ident in sorted(state['evidence_ids'] - state['checked_ids']):
        return 'retrieve:' + ident
    if intent.preview and not state['preview_done']:
        return 'preview'
    return 'DONE'


def expected_args(step: str, intent: Intent) -> tuple[str, dict]:
    if step == 'resolve_subject':
        return 'search_entities', {'name': intent.subject}
    if step == 'resolve_object':
        return 'search_entities', {'name': intent.object}
    if step == 'evaluate_relationship':
        return 'evaluate_relationship', {'subject': intent.subject,
                                         'object': intent.object, 'predicate': intent.predicate}
    if step.startswith('retrieve:'):
        return 'get_claim_evidence', {'claim_id': step.partition(':')[2]}
    if step == 'preview':
        # Read-only preview request: the graph write gate in the underlying MCP
        # server independently denies authorisation.
        import hashlib
        k=hashlib.sha256((intent.dataset+'|'+intent.subject+'|'+intent.object+'|'+intent.predicate).encode()).hexdigest()[:24]
        return 'investigate_dependency_incident', {'target': intent.object,
                  'idempotency_key': 'rulebook-preview-' + k, 'authorise_action': False}
    raise RulebookError('NO_TOOL_FOR_STATE')
