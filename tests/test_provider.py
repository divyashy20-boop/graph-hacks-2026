import json

import pytest

from ugi.models import Extraction, Settings
from ugi.provider import Bedrock, ProviderError
from ugi.store import Store


class Client:
    def __init__(self, outputs):
        self.outputs, self.requests = list(outputs), []

    def converse(self, **kwargs):
        self.requests.append(kwargs)
        output = self.outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return {"output": {"message": {"content": [{"text": output}]}},
                "usage": {"inputTokens": 100, "outputTokens": 20}, "stopReason": "end_turn"}


def setup(outputs, **kwargs):
    settings = Settings(backend="memory", provider="bedrock", model_id="test-model",
                        allow_paid_calls=True, input_price=1, output_price=2, **kwargs)
    store = Store(settings)
    client = Client(outputs)
    return Bedrock(settings, store, client), store, client


def test_schema_retry_preserves_invalid_response_and_accounts():
    model, store, client = setup(['{"claims":[]}', '{"relations":[]}'])
    assert not model.request("Extract", Extraction).relations
    assert len(client.requests) == 2
    assert all(r["inferenceConfig"]["maxTokens"] == 1500 for r in client.requests)
    assert store.list("ReviewTask")[0]["raw_output"] == '{"claims":[]}'
    assert model.usage["calls"] == 2
    assert model.usage["estimated_usd"] == pytest.approx(.00028)


def test_failed_provider_recorded_no_unbounded_retry():
    model, store, client = setup([RuntimeError("provider unavailable")])
    with pytest.raises(ProviderError):
        model.request("Extract", Extraction)
    assert len(client.requests) == 1
    assert any(r.get("state") == "provider_failed" for r in store.list("Usage"))


def test_calls_cost_and_input_limits():
    model, _, client = setup(["bad", "bad"], max_model_calls=1)
    with pytest.raises(ProviderError, match="budget"):
        model.request("Extract", Extraction)
    assert len(client.requests) == 1
    model, _, client = setup([], daily_cost_limit=.000001)
    with pytest.raises(ValueError, match="Quota"):
        model.request("Extract", Extraction)
    assert not client.requests
    model, _, client = setup([], max_input_tokens=100)
    with pytest.raises(ProviderError, match="input"):
        model.request("Extract", Extraction)
    assert not client.requests


def test_paid_opt_in_required():
    with pytest.raises(ValueError):
        Settings(provider="bedrock")
    with pytest.raises(ProviderError):
        Bedrock(Settings(backend="memory"), Store(Settings(backend="memory")), Client([]))


def test_hybrid_candidate_review_rejects_hallucination():
    from ugi.engine import Engine

    raw = {"relations": [dict(subject="Alice", object="Acme", predicate="knows",
                               evidence="Alice owns Acme.")]}
    model, store, _ = setup([json.dumps(raw)])
    engine = Engine(store, provider_factory=lambda: model)
    report = engine.ingest("sample.txt", b"Alice owns Acme.", use_ai=True)
    assert report["claims"] == 1 and report["review_tasks"] == 1
    assert store.claims()[0]["predicate"] == "OWNS"
