"""Feature-flagged, tenant-scoped, read-only UGI guided agent + P5 receipt bridge.

No external actions or graph writes. Only this opt-in endpoint is instrumented;
legacy API operations are NOT claimed to be receipt-gated. The mandatory
MCP re-read is fail-closed, but not atomically fenced with concurrent graph writes.
"""
from __future__ import annotations

from datetime import date
from functools import lru_cache

from .mcp_server import handle_message
from .memory.core import Memory, PolicyError
from .memory.bridge import BridgeError, track_and_register, refresh_receipt
from .memory.registry import RegistryError


class LocalMCP:
    """Calls the actual UGI JSON-RPC MCP handler under the authenticated HTTP scope."""
    def __init__(self, engine):
        self.engine = engine
        self.seq = 0

    def request(self, method, params=None, **kwargs):
        if method not in {"tools/list", "tools/call", "initialize", "ping"}:
            raise BridgeError("NON_ALLOWLISTED_MCP_METHOD")
        self.seq += 1
        result = handle_message({"jsonrpc": "2.0", "id": self.seq, "method": method,
                                 "params": params or {}}, self.engine, allow_writes=False)
        if not isinstance(result, dict):
            raise BridgeError("EMPTY_MCP_RESPONSE")
        return result

    def tool(self, name, arguments):
        return self.request("tools/call", {"name": name, "arguments": arguments}).get("result", {})


def scope_for(engine):
    # One isolated ledger address per authenticated owner and graph dataset.
    return "ugi::" + engine.store.owner + "::" + engine.store.graph


@lru_cache(maxsize=4)
def receipts(memory_path: str):
    if not memory_path:
        raise PolicyError("MEMORY_PATH_NOT_CONFIGURED")
    return Memory(memory_path)


def run_guided(engine, settings, dataset, query):
    names = engine.store.list("Entity", 1201)
    if len(names) > 1200: raise BridgeError("ENTITY_INVENTORY_TRUNCATED")
    sources = engine.store.list("Source", 2001)
    if len(sources) > 2000: raise BridgeError("SOURCE_INVENTORY_TRUNCATED")
    scope = scope_for(engine) + "::" + dataset
    rec = track_and_register(receipts(settings.memory_path), LocalMCP(engine),
                scope=scope, dataset=dataset, query=query,
                entities=[n['name'] for n in names], day=date.today().isoformat(),
                allowed_source_ids={s['id'] for s in sources})
    # Only return the bounded trace, output, and receipt ID; never expose ledger internals.
    return {'status':rec['outcome']['status'], 'reason':rec['outcome'].get('reason'),
            'result':rec['outcome'], 'receipt_id':rec['receipt']['rid'] if rec['receipt'] else None,
            'freshness':rec['receipt']['status'] if rec['receipt'] else 'UNKNOWN',
            'read_count':len(rec['observations']), 'writes_attempted':0}


def check_receipt(engine, settings, dataset, receipt_id):
    memory = receipts(settings.memory_path)
    scope = scope_for(engine) + "::" + dataset
    record = memory.receipt(receipt_id)
    if record['scope'] != scope:
        # No cross-tenant disclosure of receipt existence or dependencies.
        raise PolicyError('UNKNOWN_RECEIPT_OR_SCOPE')
    state = refresh_receipt(memory, LocalMCP(engine), scope=scope,
                            receipt={'rid':receipt_id}, day=date.today().isoformat())
    return {'receipt_id':receipt_id, 'freshness':state['receipt_status'],
            'safe_to_reuse':state['receipt_status']=='VALID',
            'original_read_difference_count':state['original_read_difference_count'],
            'original_read_difference_keys':state['original_read_difference_keys'],
            'new_observation_events':state['changed'],
            'reason':memory.receipt(receipt_id)['reason'],
            'external_actions_authorized':False}
