"""Conservative graph projections inspired by project1 graph tools.

Works on existing UGI records, with no direct database writes.
Network centrality and weak components are NOT semantic impact/causality.
"""
from __future__ import annotations
from collections import defaultdict, deque
from datetime import date

MAX_NODES = 1200
MAX_CLAIMS = 4000


def _interval(c):
    low = (c.get('valid_from') or c.get('event_time') or '0001-01-01')[:10]
    high = (c.get('valid_to') or '9999-12-31')[:10]
    if c.get('event_time') and not c.get('valid_from') and not c.get('valid_to'):
        # Event-time assertions are instantaneous unless an explicit interval is supplied.
        high = low
    return low, high


def _overlap(a, b):
    al, ah = _interval(a); bl, bh = _interval(b)
    return max(al, bl) <= min(ah, bh)


def _active(c, as_of=None):
    if c.get('historical') and as_of is None and not c.get('valid_to'):
        return False
    when = (as_of or date.today().isoformat())[:10]
    low, high = _interval(c)
    if low > high:
        return False
    return low <= when <= high


def projection(entities, claims, as_of=None, allow_predicates=('DEPENDS_ON',), blocked_assertion_ids=()):
    """Make an explicitly narrow graph. Never infer from schema/open provisional claims."""
    if len(entities) > MAX_NODES or len(claims) > MAX_CLAIMS:
        raise ValueError('Read budget exceeded; not a complete graph analysis')
    ids = {e['id'] for e in entities}
    allow = set(allow_predicates)
    def key(c):
        return (c.get('subject_id'), c.get('predicate'), c.get('object_id'))
    blocked_ids = set(blocked_assertion_ids)
    neg = defaultdict(list)
    for c in claims:
        if c.get('polarity') == 'negative' and c.get('predicate') in allow:
            neg[key(c)].append(c)
    permitted, excluded = [], []
    for c in claims:
        reason = None
        if c.get('id') in blocked_ids:
            reason = 'schema_bound_excluded_from_legacy_inference'
        elif c.get('predicate') not in allow:
            reason = 'predicate_not_selected'
        elif c.get('subject_id') not in ids or c.get('object_id') not in ids:
            reason = 'endpoint_unresolved'
        elif c.get('polarity', 'positive') != 'positive':
            reason = 'negative_or_unknown_polarity'
        elif c.get('modality', 'asserted') != 'asserted':
            reason = 'non_asserted_modality'
        elif c.get('eligible_for_inference') is False or c.get('provisional') is True:
            reason = 'unverified_or_provisional'
        elif c.get('schema_binding_id') or c.get('pack_refs'):
            reason = 'schema_bound_without_semantic_rule'
        elif not _active(c, as_of):
            reason = 'inactive_for_requested_time'
        elif any(_overlap(c, n) and _active(n, as_of) for n in neg[key(c)]):
            reason = 'directly_contradicted'
        if reason:
            excluded.append({'claim_id': c.get('id'), 'reason': reason})
        else:
            permitted.append(c)
    return {'entities': entities, 'claims': permitted,
            'included_count': len(permitted), 'excluded': excluded,
            'semantics': 'source-asserted connectivity only; not causal impact',
            'allow_predicates': sorted(allow), 'as_of': as_of}


def shortest_path(view, start_id, end_id, max_hops=4, max_expansions=300):
    if not 1 <= max_hops <= 6 or not 1 <= max_expansions <= 2000:
        raise ValueError('Unsafe search budget')
    ids = {e['id'] for e in view['entities']}
    if start_id not in ids or end_id not in ids:
        return {'found': False, 'reason': 'entity_not_in_bounded_view', 'truncated': False}
    adj = defaultdict(list)
    for c in view['claims']:
        adj[c['subject_id']].append(c)
    for group in adj.values():
        group.sort(key=lambda c: (c['object_id'], c['id']))
    q = deque([(start_id, [], {start_id}, '0001-01-01', '9999-12-31')])
    expansions = 0
    while q:
        node, path, seen, low, high = q.popleft()
        if node == end_id and path:
            return {'found': True, 'claim_ids': [c['id'] for c in path],
                    'path_ids': [start_id] + [c['object_id'] for c in path],
                    'hops': len(path), 'truncated': False,
                    'meaning': 'connected by selected source assertions; not proof of causal impact'}
        if len(path) >= max_hops:
            continue
        for c in adj[node]:
            if c['object_id'] in seen:
                continue
            cl, ch = _interval(c)
            if max(low, cl) > min(high, ch):
                continue
            if expansions >= max_expansions:
                return {'found': False, 'reason': 'search_budget_exhausted', 'truncated': True}
            expansions += 1
            q.append((c['object_id'], path + [c], seen | {c['object_id']}, max(low,cl), min(high,ch)))
    return {'found': False, 'reason': 'no_eligible_path', 'truncated': False}


def components(view, max_components=100):
    """WEAK connected components; not Louvain/Leiden communities."""
    if not 1 <= max_components <= 200:
        raise ValueError('Invalid component budget')
    adj = {e['id']: set() for e in view['entities']}
    for c in view['claims']:
        adj[c['subject_id']].add(c['object_id'])
        adj[c['object_id']].add(c['subject_id'])
    seen, out = set(), []
    for id_ in sorted(adj):
        if id_ in seen:
            continue
        q = [id_]; seen.add(id_); member = []
        for u in q:
            member.append(u)
            for v in sorted(adj[u]):
                if v not in seen:
                    seen.add(v); q.append(v)
        out.append(sorted(member))
    out.sort(key=lambda arr: (-len(arr), arr[0]))
    return {'components': out[:max_components], 'total_components': len(out),
            'truncated': len(out) > max_components, 'kind': 'weakly_connected_components'}


def pagerank(view, top_k=12, damping=0.85, iterations=60):
    """Krish-style directed PageRank; not a business risk score."""
    if not 1 <= top_k <= 100:
        raise ValueError('Invalid ranking limit')
    ids = sorted({e['id'] for e in view['entities']})
    if not ids:
        return {'rankings': [], 'iterations': 0, 'meaning': 'connectivity only'}
    out = {i: set() for i in ids}
    for c in view['claims']:
        out[c['subject_id']].add(c['object_id'])
    rank = {i: 1/len(ids) for i in ids}
    for k in range(iterations):
        nxt = {i: (1-damping)/len(ids) for i in ids}
        dangling = damping * sum(rank[i] for i in ids if not out[i]) / len(ids)
        for i in ids:
            nxt[i] += dangling
        for i in ids:
            for dest in sorted(out[i]):
                nxt[dest] += damping * rank[i]/len(out[i])
        delta = sum(abs(nxt[i] - rank[i]) for i in ids)
        rank = nxt
        if delta < 1e-9:
            break
    names = {e['id']: e.get('name',e['id']) for e in view['entities']}
    order = sorted(ids, key=lambda i: (-rank[i], i))
    return {'rankings': [{'id': i, 'name': names[i], 'score': round(rank[i], 8)} for i in order[:top_k]],
            'iterations': k+1, 'meaning': 'PageRank connectivity, NOT verified importance/risk',
            'truncated': len(order) > top_k}
