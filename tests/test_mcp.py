import json

from ugi.engine import Engine
from ugi.mcp_server import TOOLS, call_tool, handle_message
from ugi.models import Settings
from ugi.store import Store


def test_mcp_handshake_and_contract():
    engine = Engine(Store(Settings(backend="memory")))
    init = handle_message({"jsonrpc": "2.0", "method": "initialize", "id": 1,
                           "params": {"protocolVersion": "2025-11-25"}}, engine)
    assert init["result"]["capabilities"]["tools"] == {"listChanged": False}
    names = [t["name"] for t in handle_message({"jsonrpc": "2.0", "method": "tools/list",
                                                "id": 2}, engine)["result"]["tools"]]
    assert names == [t["name"] for t in TOOLS]
    assert "evaluate_relationship" in names
    assert handle_message({"jsonrpc": "2.0", "method": "notifications/initialized"}, engine) is None


def test_mcp_read_evidence_and_write_guard():
    from pathlib import Path
    engine = Engine(Store(Settings(backend="memory")))
    root = Path(__file__).parents[1]
    engine.ingest("incident.json", (root / "demo/incident.json").read_bytes())
    query = call_tool(engine, "evaluate_relationship", {
        "subject": "Checkout", "object": "Cache", "predicate": "TRANSITIVELY_DEPENDS_ON"
    })
    assert query["status"] == "RULE_DERIVED"
    claim_id = query["evidence"][0]["claim"]["id"]
    quoted = call_tool(engine, "get_claim_evidence", {"claim_id": claim_id})
    assert quoted["evidence"]["quote"]
    request = {"target": "Cache", "idempotency_key": "mcp-saved", "authorise_action": True}
    denied = handle_message({"jsonrpc": "2.0", "method": "tools/call", "id": 3,
                             "params": {"name": "investigate_dependency_incident",
                                        "arguments": request}}, engine)
    assert denied["result"]["isError"]
    assert not engine.store.list("Investigation")
    preview = call_tool(engine, "investigate_dependency_incident", {
        "target": "Cache", "idempotency_key": "mcp-preview"})
    assert preview["executed"] is False
    case = call_tool(engine, "investigate_dependency_incident", request, allow_writes=True)
    assert case["executed"] and engine.store.get(case["id"])["kind"] == "Investigation"
    assert engine.store.list("ReviewTask")


def test_mcp_cannot_force_hypothesis_writes_or_arbitrary_cypher():
    engine = Engine(Store(Settings(backend="memory")))
    response = handle_message({"jsonrpc": "2.0", "method": "tools/call", "id": 4,
                              "params": {"name": "evaluate_relationship", "arguments": {
                                  "subject": "a", "object": "b", "predicate": "FRIENDS_WITH",
                                  "allow_hypothesis": True}}}, engine)
    assert response["result"]["isError"]
    assert not engine.store.list("Hypothesis")
    assert not any(t["name"] == "query_cypher" for t in TOOLS)


def test_mcp_tool_result_json_serialisable():
    engine = Engine(Store(Settings(backend="memory")))
    result = handle_message({"jsonrpc": "2.0", "method": "tools/call", "id": 5,
                             "params": {"name": "search_entities", "arguments": {"name": "None"}}},
                            engine)
    assert json.loads(json.dumps(result))["result"]["structuredContent"] == {"entities": []}


def test_mcp_actual_stdio_subprocess_in_offline_memory_mode():
    import os
    import subprocess
    import sys

    env = dict(os.environ, UGI_BACKEND="memory", UGI_PROVIDER="offline", UGI_ALLOW_PAID_CALLS="false")
    payloads = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {
                "name": "test", "version": "1.0.0"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ]
    completed = subprocess.run(
        [sys.executable, "-m", "ugi.mcp_server"],
        input="\n".join(json.dumps(item) for item in payloads) + "\n",
        text=True, capture_output=True, timeout=10, env=env,
    )
    assert completed.returncode == 0, completed.stderr
    lines = [json.loads(line) for line in completed.stdout.splitlines()]
    assert len(lines) == 2 and lines[0]["id"] == 1
    assert any(tool["name"] == "investigate_dependency_incident"
               for tool in lines[1]["result"]["tools"])
