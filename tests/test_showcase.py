import os
from uuid import uuid4

import pytest

from ugi.demo import showcase
from ugi.models import Settings
from ugi.store import Store


def test_three_domains_share_engine_and_action_authorization():
    result = showcase(Settings(backend="memory"), execute=False)
    assert not result["domains"]["incident"]["action"]["executed"]
    result = showcase(Settings(backend="memory"), execute=True)
    assert result["domains"]["incident"]["action"]["executed"]
    assert result["domains"]["supply"]["action"]["executed"]
    assert len(result["domains"]["supply"]["derived"]["evidence"]) == 2
    assert result["domains"]["research"]["after_collision"]["status"] == "UNKNOWN"


@pytest.mark.integration
def test_real_three_domain_demo_and_saved_state():
    url = os.getenv("UGI_TEST_REDIS_URL")
    if not url:
        pytest.skip("Requires real FalkorDB")
    settings = Settings(redis_url=url, graph_prefix="ugi_demo_" + uuid4().hex[:12])
    try:
        result = showcase(settings, "isolated", execute=True)
        for domain in ("incident", "supply"):
            store = Store(settings, dataset="isolated-" + domain)
            assert store.get(result["domains"][domain]["action"]["id"])
            assert store.list("ReviewTask")
        repeated = showcase(settings, "isolated", execute=True)
        assert repeated["domains"]["incident"]["action"]["duplicate"]
    finally:
        for domain in ("incident", "supply", "research"):
            store = Store(settings, dataset="isolated-" + domain)
            assert store.graph.startswith(settings.graph_prefix + "_")
            store.client.execute_command("GRAPH.DELETE", store.graph)
