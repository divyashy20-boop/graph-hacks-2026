"""Small, bounded MCP stdio adapter for evidence-based UGI agent tools.

Transport: newline-delimited JSON-RPC 2.0 via stdin/stdout.  Uses application
services rather than exposing arbitrary Cypher or unrestricted graph writes.
Intended for locally launched, trusted clients; no network listener is created.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any

from pydantic import ValidationError

from .engine import Engine
from .models import InvestigationRequest, RelationQuery, Settings
from .store import Store

PROTOCOL_VERSION = "2025-11-25"

TOOLS = [
    {
        "name": "search_entities",
        "description": "Resolve an entity name or alias; ambiguous identities remain separate.",
        "inputSchema": {"type": "object", "properties": {"name": {"type": "string", "minLength": 1, "maxLength": 160}},
                        "required": ["name"], "additionalProperties": False},
    },
    {
        "name": "evaluate_relationship",
        "description": "Inspect a requested relation with exact source evidence, graph paths and uncertainty. Read-only; no inferred hypotheses are persisted.",
        "inputSchema": {"type": "object", "properties": {
            "subject": {"type": "string", "minLength": 1},
            "object": {"type": "string", "minLength": 1},
            "predicate": {"type": "string", "minLength": 1},
            "as_of": {"type": "string", "description": "Optional ISO calendar date"},
        }, "required": ["subject", "object", "predicate"], "additionalProperties": False},
    },
    {
        "name": "get_claim_evidence",
        "description": "Retrieve one stored claim and its exact source-citation record by ID.",
        "inputSchema": {"type": "object", "properties": {"claim_id": {"type": "string", "minLength": 1}},
                        "required": ["claim_id"], "additionalProperties": False},
    },
    {
        "name": "investigate_dependency_incident",
        "description": "Preview a bounded multi-hop dependency investigation; with explicit authorisation and server opt-in, persist investigation and review tasks.",
        "inputSchema": {"type": "object", "properties": {
            "target": {"type": "string", "minLength": 1},
            "idempotency_key": {"type": "string", "minLength": 1},
            "as_of": {"type": "string", "description": "Optional ISO calendar date"},
            "authorise_action": {"type": "boolean", "default": False},
        }, "required": ["target", "idempotency_key"], "additionalProperties": False},
    },
]


def _exact_fields(arguments: dict, fields: set[str]):
    if not isinstance(arguments, dict) or set(arguments) - fields:
        raise ValueError("Unexpected tool arguments")


def call_tool(engine: Engine, name: str, arguments: dict, allow_writes=False) -> Any:
    if name == "search_entities":
        _exact_fields(arguments, {"name"})
        raw = arguments["name"]
        if not isinstance(raw, str) or not 1 <= len(raw) <= 160:
            raise ValueError("Invalid entity name")
        return {"entities": engine.store.entities(raw)}
    if name == "evaluate_relationship":
        _exact_fields(arguments, {"subject", "object", "predicate", "as_of"})
        # This is a strictly read-only tool. No LLM requests or hypothesis writes.
        args = dict(arguments)
        args.pop("allow_hypothesis", None)
        return engine.relationship(RelationQuery(**args, allow_hypothesis=False, use_ai=False))
    if name == "get_claim_evidence":
        _exact_fields(arguments, {"claim_id"})
        identifier = arguments.get("claim_id")
        if not isinstance(identifier, str) or len(identifier) > 160:
            raise ValueError("Invalid claim identifier")
        claim = engine.store.get(identifier)
        if not claim or claim["kind"] != "Claim":
            raise ValueError("Claim not found")
        return {"claim": claim, "evidence": engine.store.get(claim["evidence_id"])}
    if name == "investigate_dependency_incident":
        _exact_fields(arguments, {"target", "idempotency_key", "as_of", "authorise_action"})
        request = InvestigationRequest(**arguments)
        if request.authorise_action and not allow_writes:
            raise ValueError("MCP write actions disabled; set UGI_MCP_ALLOW_WRITES=1 to opt in")
        return engine.investigate(request, actor="mcp_operator")
    raise ValueError("Unknown MCP tool")


def handle_message(message: dict, engine: Engine, allow_writes=False) -> dict | None:
    """Handler intentionally side-effect free until tools/call and operator permission."""
    method = message.get("method")
    if "id" not in message:
        return None  # JSON-RPC notifications, including notifications/initialized.
    identifier = message["id"]
    try:
        if message.get("jsonrpc") != "2.0":
            raise ValueError("Expected JSON-RPC 2.0")
        if method == "initialize":
            return {"jsonrpc": "2.0", "id": identifier, "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "universal-graph-intelligence", "version": "1.0.0"},
            }}
        if method == "ping":
            return {"jsonrpc": "2.0", "id": identifier, "result": {}}
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": identifier, "result": {"tools": TOOLS}}
        if method == "tools/call":
            params = message.get("params") or {}
            if not isinstance(params, dict):
                raise ValueError("Invalid tool request")
            result = call_tool(engine, params.get("name", ""), params.get("arguments", {}),
                               allow_writes=allow_writes)
            return {"jsonrpc": "2.0", "id": identifier, "result": {
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, default=str)}],
                "structuredContent": result,
                "isError": False,
            }}
        return {"jsonrpc": "2.0", "id": identifier, "error": {"code": -32601,
                                                                     "message": "Unknown method"}}
    except (ValueError, ValidationError, TypeError) as exc:
        if method == "tools/call":
            return {"jsonrpc": "2.0", "id": identifier, "result": {
                "content": [{"type": "text", "text": str(exc)}], "isError": True,
            }}
        return {"jsonrpc": "2.0", "id": identifier, "error": {"code": -32602,
                                                                 "message": str(exc)}}


def main():
    settings = Settings()
    owner = os.getenv("UGI_MCP_OWNER", "local-mcp")
    dataset = os.getenv("UGI_MCP_DATASET", "demo")
    # STDIO is a local subprocess transport; do not accept arbitrary graph names.
    if not 1 <= len(owner) <= 80 or not 1 <= len(dataset) <= 60 or not all(
        c.isalnum() or c in "_-" for c in dataset
    ):
        raise ValueError("Invalid MCP identity or dataset")
    engine = Engine(Store(settings, owner=owner, dataset=dataset))
    allow_writes = os.getenv("UGI_MCP_ALLOW_WRITES", "0") == "1"
    for line in sys.stdin:
        try:
            message = json.loads(line)
            if not isinstance(message, dict):
                raise ValueError("JSON-RPC request must be an object")
            response = handle_message(message, engine, allow_writes=allow_writes)
        except (ValueError, TypeError) as exc:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700,
                                                                    "message": str(exc)}}
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False, default=str) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
