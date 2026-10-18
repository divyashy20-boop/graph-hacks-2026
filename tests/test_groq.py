"""Groq adapter contract tests; all HTTP traffic is in-process and synthetic."""
from __future__ import annotations

import io
import json
import urllib.error
from email.message import Message

import pytest

from ugi.engine import Engine
from ugi.models import Extraction, Settings
from ugi.provider import GROQ_API_BASE, Groq, ProviderError
from ugi.store import Store


class Response(io.BytesIO):
    def __init__(self, payload, headers=None):
        super().__init__(json.dumps(payload).encode())
        self.headers = headers or {}


def settings(**kwargs):
    return Settings(
        **{**dict(backend="memory", provider="groq", allow_paid_calls=True,
                 model_id="openai/gpt-oss-120b", input_price=0.15, output_price=0.60),
           **kwargs},
    )


def completion(content='{"relations":[]}', finish="stop"):
    return {
        "choices": [{"message": {"content": content}, "finish_reason": finish}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 30, "total_tokens": 130},
    }


def transport(outputs, captured):
    values = iter(outputs)

    def send(request, timeout):
        captured.append({
            "url": request.full_url, "headers": dict(request.headers),
            "payload": json.loads(request.data), "timeout": timeout,
        })
        value = next(values)
        if isinstance(value, Exception):
            raise value
        if isinstance(value, tuple):
            return Response(value[0], value[1])
        return Response(value)
    return send


@pytest.fixture(autouse=True)
def key(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-secret-never-persist")
    monkeypatch.setattr("ugi.provider._groq_next_request_at", 0.0)


def provider(opts, outputs, captured, sleeps=None):
    clock = iter(range(10000))
    return Groq(
        opts, Store(opts), transport=transport(outputs, captured),
        sleeper=sleeps.append if sleeps is not None else (lambda _: None),
        monotonic=lambda: next(clock),
    )


def test_groq_comparable_request_and_usage_accounting():
    captured = []
    opts = settings()
    model = provider(opts, [completion()], captured)
    assert model.request("Extract", Extraction).relations == []
    sent = captured[0]
    assert sent["url"] == GROQ_API_BASE + "/chat/completions"
    assert sent["payload"]["model"] == "openai/gpt-oss-120b"
    assert sent["payload"]["max_completion_tokens"] == 1500
    assert "temperature" not in sent["payload"]
    assert sent["payload"]["reasoning_effort"] == "low"
    assert sent["payload"]["response_format"]["type"] == "json_schema"
    assert sent["payload"]["response_format"]["json_schema"]["strict"] is True
    assert model.usage["calls"] == 1
    assert model.usage["total_tokens"] == 130
    assert model.usage["estimated_usd"] == pytest.approx(0.000033)
    rows = model.store.list("Usage")
    request_row = next(row for row in rows if row.get("provider") == "groq")
    assert request_row["state"] == "returned"
    assert "test-secret-never-persist" not in json.dumps(rows)


def test_groq_schema_repair_is_bounded_and_reviewable():
    captured = []
    model = provider(settings(), [completion('{"claims":[]}'), completion()], captured)
    assert model.request("Extract", Extraction).relations == []
    assert len(captured) == 2 and model.calls == 2
    assert model.store.list("ReviewTask")[0]["raw_output"] == '{"claims":[]}'
    assert "Previous output failed validation" in captured[1]["payload"]["messages"][0]["content"]


def test_groq_retries_one_explicit_429_and_honours_retry_after():
    headers = Message()
    headers["retry-after"] = "0"
    limited = urllib.error.HTTPError(
        GROQ_API_BASE + "/chat/completions", 429, "rate limited", headers, io.BytesIO(b"{}"),
    )
    captured, sleeps = [], []
    model = provider(settings(), [limited, completion()], captured, sleeps)
    assert model.request("Extract", Extraction).relations == []
    assert len(captured) == 2 and model.usage["rate_limit_retries"] == 1
    assert sleeps and sleeps[-1] >= 2.0
    assert any(row.get("state") == "rate_limited" for row in model.store.list("Usage"))


@pytest.mark.parametrize("failure", [
    TimeoutError("ambiguous timeout"),
    urllib.error.HTTPError(
        GROQ_API_BASE + "/chat/completions", 503, "unavailable", Message(), io.BytesIO(b"{}"),
    ),
])
def test_groq_ambiguous_failures_are_not_retried_or_leaked(failure):
    captured = []
    model = provider(settings(), [failure], captured)
    with pytest.raises(ProviderError, match="persisted usage") as caught:
        model.request("Extract", Extraction)
    assert len(captured) == 1 and model.calls == 1
    assert "test-secret-never-persist" not in str(caught.value)
    assert "test-secret-never-persist" not in json.dumps(model.store.list("Usage"))


def test_groq_requires_runtime_key_and_valid_configuration(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY")
    opts = settings()
    with pytest.raises(ProviderError, match="runtime environment"):
        Groq(opts, Store(opts))
    with pytest.raises(ValueError, match="verified list prices"):
        Settings(backend="memory", provider="groq", allow_paid_calls=True,
                 model_id="openai/gpt-oss-120b")


def test_groq_requires_explicit_cloud_inference_optin():
    with pytest.raises(ValueError, match="explicit paid opt-in"):
        settings(allow_paid_calls=False)


def test_groq_daily_budget_rejects_before_network():
    captured = []
    opts = settings(daily_cost_limit=0.000001)
    model = provider(opts, [completion()], captured)
    with pytest.raises(ValueError, match="Quota exceeded"):
        model.request("Extract", Extraction)
    assert captured == []


def test_groq_engine_route_preserves_hybrid_evidence_checks():
    sentence = "Alice owns Acme."
    raw = json.dumps({"relations": [{
        "subject": "Alice", "predicate": "KNOWS", "object": "Acme", "evidence": sentence,
    }]})
    captured = []
    opts = settings()
    model = provider(opts, [completion(raw)], captured)
    store = model.store
    result = Engine(store, provider_factory=lambda: model).ingest(
        "source.txt", sentence.encode(), use_ai=True,
    )
    assert result["provider"] == "groq"
    assert result["claims"] == 1 and result["review_tasks"] == 1
    claim = store.claims()[0]
    assert (claim["subject"], claim["predicate"], claim["object"]) == (
        "Alice", "OWNS", "Acme",
    )


def test_groq_p2_split_uses_1550_and_keeps_strict_schema():
    captured = []
    model = provider(settings(max_output_tokens=2250, extraction_windows=2),
                     [completion()], captured)
    assert model.request("Extract", Extraction).relations == []
    payload = captured[0]["payload"]
    assert payload["max_completion_tokens"] == 1550
    assert payload["reasoning_effort"] == "low"
    assert payload["response_format"]["json_schema"]["strict"]


def test_groq_sdk_is_exclusive_live_transport(monkeypatch):
    import sys
    import types
    from types import SimpleNamespace

    captured = []
    class Raw:
        headers = {"x-ratelimit-remaining-tokens": "7000"}
        def parse(self):
            return SimpleNamespace(model_dump=lambda: completion('{"relations":[],"events":[]}'))
    class WithRaw:
        def create(self, **kwargs):
            captured.append(kwargs)
            return Raw()
    class Official:
        def __init__(self, **kwargs):
            assert kwargs["max_retries"] == 0
            self.chat = SimpleNamespace(completions=SimpleNamespace(with_raw_response=WithRaw()))
    fake = types.ModuleType("groq")
    fake.Groq = Official
    fake.APIStatusError = type("APIStatusError", (Exception,), {})
    monkeypatch.setitem(sys.modules, "groq", fake)
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: (_ for _ in ()).throw(
        AssertionError("urllib used for production")))
    opts = settings(max_output_tokens=2250)
    model = Groq(opts, Store(opts), sleeper=lambda _: None,
                 monotonic=lambda: 100.0)
    assert model.request("Extract", Extraction).relations == []
    assert captured[0]["response_format"]["json_schema"]["strict"]
    assert captured[0]["reasoning_effort"] == "low"
    assert captured[0]["max_completion_tokens"] == 2250
    assert model.usage["calls"] == 1


def test_groq_review_calls_do_not_impersonate_p2_extraction():
    from ugi.models import Verdict
    captured = []
    model = provider(settings(), [completion('{"supported":false,"reason":"unknown"}')],
                     captured)
    assert model.request("Review", Verdict).supported is False
    assert "reasoning_effort" not in captured[0]["payload"]
    assert "response_format" not in captured[0]["payload"]
