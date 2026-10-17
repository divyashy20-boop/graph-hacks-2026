"""Runtime module isolation and graph source-provenance preflight.

The v3 live run had a Python shadow-import regression: Python -m launched from
/tmp could import a previous /tmp/ugi_real_track1 over the packaged version.
Fail closed instead of silently interpreting absent provenance as valid.
"""
from __future__ import annotations
import argparse
import importlib
import json
from pathlib import Path

class PreflightError(RuntimeError):
    pass

MODULES=(
    'ugi_real_track1.real_suite',
    'ugi_rulebook.experiment',
    'ugi_rulebook.controller',
    'ugi_agent_fix.patch_engine',
)

def import_origins():
    return {name: str(Path(importlib.import_module(name).__file__).resolve()) for name in MODULES}

def assert_runtime_module_origins(expected_root, expected_engine=None):
    base=Path(expected_root).resolve()
    if not base.is_dir():
        raise PreflightError(f'EXPECTED_PACKAGE_ROOT_MISSING: {base}')
    locations={}
    for name in MODULES:
        expected=(base.joinpath(*name.split('.')).with_suffix('.py')).resolve()
        try:
            actual=Path(importlib.import_module(name).__file__).resolve()
        except (ImportError, AttributeError) as exc:
            raise PreflightError(f'STALE_OR_MISSING_MODULE: {name}: {exc}') from exc
        if actual!=expected:
            raise PreflightError(f'STALE_MODULE_IMPORTED: {name}: got {actual}, expected {expected}')
        locations[name]=str(actual)
    if expected_engine:
        actual=Path(importlib.import_module('ugi.engine').__file__).resolve()
        desired=Path(expected_engine).resolve()
        if actual!=desired:
            raise PreflightError(f'WRONG_ENGINE_IMPORT: got {actual}, expected {desired}')
        locations['ugi.engine']=str(actual)
    return locations

def validate_prepared_sources(prepared):
    if not isinstance(prepared,dict) or not prepared:
        raise PreflightError('SOURCE_METADATA_EMPTY')
    seen=set()
    for name,row in prepared.items():
        if not isinstance(row,dict):
            raise PreflightError(f'SOURCE_METADATA_NOT_A_DICT: {name}')
        srcid=row.get('source_id')
        if not isinstance(srcid,str) or not srcid.strip():
            raise PreflightError(f'SOURCE_ID_MISSING: {name}; likely stale ugi_real_track1 module or incompatible UGI ingest response')
        if srcid in seen:
            raise PreflightError(f'SOURCE_ID_DUPLICATED_ACROSS_DATASETS: {name}')
        if not isinstance(row.get('source'),dict) or row['source'].get('name')!=name:
            raise PreflightError(f'SOURCE_SCOPE_MISMATCH: {name}')
        seen.add(srcid)
    return True

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--expected-root',required=True)
    p.add_argument('--expected-engine')
    a=p.parse_args()
    origins=assert_runtime_module_origins(a.expected_root,a.expected_engine)
    print(json.dumps({'status':'PASS','module_origins':origins},indent=2),flush=True)
if __name__=='__main__': main()
