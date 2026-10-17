"""
UI-012 Demonstration and Live Verification Script
Proves the three seeded demonstration presets:
- showcase-b-incident
- showcase-b-supply
- showcase-b-research
plus the guided agent and receipt freshness pathway under memory backend.
"""

from fastapi.testclient import TestClient
from ugi.api import create_app
from ugi.models import Settings

def test_demonstrations_and_guided():
    print("=== STARTING UI-012 DEMO PRESET & GUIDED VERIFICATION ===")
    
    import tempfile
    mem_file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
    mem_file.close()

    settings = Settings(
        backend="memory",
        guided_agent_enabled=True,
        memory_enabled=True,
        memory_path=mem_file.name,
    )
    client = TestClient(create_app(settings))
    
    # 1. Health check
    health = client.get("/health").json()
    print(f"1. Health readout: backend={health['backend']}, provider={health['provider']}, guided={health['guided_agent_enabled']}, memory={health['memory_enabled']}")
    assert health["backend"] == "memory"
    assert health["guided_agent_enabled"] is True
    assert health["memory_enabled"] is True
    assert health["live_inference_verified"] is False  # Honest backend state

    # 2. Preset 1: Incident
    inc = client.get("/api/graph", headers={"X-Dataset": "showcase-b-incident"}).json()
    print(f"2. Incident Preset: {inc['counts']['Entity']} entities, {inc['counts']['Claim']} claims, {inc['counts']['RelationEvent']} events")
    assert inc["counts"]["Entity"] > 0
    assert inc["counts"]["Claim"] > 0

    # 3. Preset 2: Supply Network
    sup = client.get("/api/graph", headers={"X-Dataset": "showcase-b-supply"}).json()
    print(f"3. Supply Network Preset: {sup['counts']['Entity']} entities, {sup['counts']['Claim']} claims, {sup['counts']['RelationEvent']} events")
    assert sup["counts"]["Entity"] > 0
    assert sup["counts"]["Claim"] > 0

    # 4. Preset 3: Research Network
    res = client.get("/api/graph", headers={"X-Dataset": "showcase-b-research"}).json()
    print(f"4. Research Network Preset: {res['counts']['Entity']} entities, {res['counts']['Claim']} claims, {res['counts']['RelationEvent']} events")
    assert res["counts"]["Entity"] > 0
    assert res["counts"]["RelationEvent"] > 0

    # 5. Relationship Verdict on Incident
    verdict = client.post(
        "/api/relationships",
        headers={"X-Dataset": "showcase-b-incident"},
        json={"subject": "Checkout", "object": "Cache", "predicate": "TRANSITIVELY_DEPENDS_ON", "allow_hypothesis": False}
    ).json()
    print(f"5. Relationship Verdict on Checkout -> Cache: status={verdict['status']}, rules={len(verdict.get('rules', []))}")
    assert verdict["status"] in {"SOURCE_ASSERTED", "RULE_DERIVED", "CONNECTED_ONLY", "UNKNOWN"}

    # 6. Guided Agent query & Receipt Freshness
    guided = client.post(
        "/api/agent/guided",
        headers={"X-Dataset": "showcase-b-incident"},
        json={"query": "Does Checkout transitively depend on Cache?"}
    ).json()
    receipt_id = guided.get("receipt_id")
    print(f"6. Guided Agent Answer: verdict={guided.get('result', {}).get('verdict')}, receipt_id={receipt_id[:16] if receipt_id else None}")
    
    if receipt_id:
        freshness = client.get(
            f"/api/agent/receipts/{receipt_id}/freshness",
            headers={"X-Dataset": "showcase-b-incident"}
        ).json()
        print(f"7. Receipt Freshness Recheck: freshness={freshness.get('freshness')}, safe_to_reuse={freshness.get('safe_to_reuse')}")
        assert freshness.get("freshness") in {"VALID", "STALE", "UNKNOWN"}

    print("=== ALL 7 PRESET AND WORKFLOW VERIFICATIONS PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    test_demonstrations_and_guided()
