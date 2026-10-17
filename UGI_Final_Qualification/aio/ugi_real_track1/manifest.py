"""Narrow Docker Compose explicit depends_on reader. NOT arbitrary YAML support.
Recognizes only top-level services, service stanza, and explicit depends_on mapping/list.
Never treats environment/network/ports or inferred runtime relationship as depend_on.
"""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCES = json.loads((ROOT / 'sources.json').read_text(encoding='utf-8'))
NAME = r'[A-Za-z_][A-Za-z0-9_.-]*'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_manifest(source, source_dir=None):
    root = Path(source_dir) if source_dir else ROOT / 'snapshots'
    path = root / source['snapshot']
    data = path.read_bytes()
    if digest(data) != source['sha256']:
        raise ValueError('PINNED_SOURCE_HASH_MISMATCH: ' + source['name'])
    return data.decode('utf-8')


def extract_explicit_dependencies(text):
    services, links, section, current, in_depends = set(), [], '', None, False
    for n, raw in enumerate(text.splitlines(), 1):
        uncommented = raw.split('#', 1)[0].rstrip()
        if not uncommented.strip():
            continue
        indent = len(uncommented) - len(uncommented.lstrip(' '))
        if '\t' in raw[:indent]:
            raise ValueError('Tab indentation is not supported')
        tok = uncommented.strip()
        if indent == 0 and re.fullmatch(r'[a-zA-Z][\w-]*:\s*', tok):
            section = tok.split(':')[0]
            current, in_depends = None, False
            continue
        if section != 'services':
            continue
        m = re.fullmatch(rf'({NAME}):\s*', tok)
        if indent == 2 and m:
            current = m.group(1)
            if current in services:
                raise ValueError('Duplicate service key: ' + current)
            services.add(current)
            in_depends = False
            continue
        if not current or indent < 4:
            raise ValueError(f'Invalid or unsupported service content on line {n}')
        prop = re.match(r'^([A-Za-z][\w-]*):(?:\s|$)', tok)
        if indent == 4 and prop:
            in_depends = prop.group(1) == 'depends_on'
            if in_depends and tok != 'depends_on:':
                raise ValueError('Inline depends_on unsupported; abstain')
            continue
        if in_depends:
            item = re.fullmatch(rf'-\s*({NAME})\s*', tok)
            obj = re.fullmatch(rf'({NAME}):\s*', tok)
            if item and indent in (4, 6):
                links.append(dict(subject=current, object=item.group(1), line=n, snippet=raw.strip()))
            elif obj and indent == 6:
                links.append(dict(subject=current, object=obj.group(1), line=n, snippet=raw.strip()))
            # nested fields e.g. condition: service_healthy intentionally ignored
    for l in links:
        if l['object'] not in services or l['subject'] == l['object']:
            raise ValueError('Invalid depends_on service target')
    return sorted(services), links


def directed_reachable(edges, src, dest):
    graph = {}
    for u, v in edges:
        graph.setdefault(u, set()).add(v)
    found, todo = {src}, [(src, 0)]
    for node, hops in todo:
        for nxt in sorted(graph.get(node, [])):
            if nxt == dest:
                return hops + 1
            if nxt not in found:
                found.add(nxt)
                todo.append((nxt, hops + 1))
    return None


def generate_questions(source):
    """Golden answers manually annotated from source files; no UGI output used."""
    edges = [tuple(p) for p in source['expected_edges']]
    services = sorted({s for edge in edges for s in edge})
    qs = []
    for a, b in edges:
        qs.append(dict(q=f'Does {a} directly depend on {b}?', subject=a, object=b,
                       predicate='DEPENDS_ON', expected='SOURCE_ASSERTED'))
    for a, b in edges:
        qs.append(dict(q=f'Does {b} directly depend on {a}?', subject=b, object=a,
                       predicate='DEPENDS_ON', expected='UNKNOWN'))
    for a in services:
        for b in services:
            hops = directed_reachable(edges, a, b)
            if hops is not None and hops > 1:
                qs.append(dict(q=f'Does {a} transitively depend on {b}?', subject=a, object=b,
                               predicate='TRANSITIVELY_DEPENDS_ON', expected='RULE_DERIVED'))
    # Non-causal checks: never infer causality just from connected infrastructure.
    if edges:
        a, b = edges[0]
        qs.append(dict(q=f'Is {a} proven to cause failure in {b}?', subject=a, object=b,
                       predicate='CAUSED', expected='NOT_PROVEN'))
    return qs
