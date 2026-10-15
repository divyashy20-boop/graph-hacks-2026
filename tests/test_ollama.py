"""Local Ollama adapter contract tests; no HTTP requests leave the process."""
import io
import json

import pytest

from ugi.engine import Engine
from ugi.models import Extraction, Settings
from ugi.provider import Ollama, ProviderError
from ugi.store import Store


def settings(**kwargs):
    return Settings(backend="memory", provider="ollama",
                    model_id="qwen3:4b-instruct", **kwargs)


def fake_transport(outputs, captured):
    values = iter(outputs)

    def call(req, timeout):
        captured.append((json.loads(req.data), req.full_url, timeout))
        value = next(values)
        if isinstance(value, Exception):
            raise value
        return io.BytesIO(json.dumps({
            "message": {"content": value},
            "prompt_eval_count": 100, "eval_count": 30, "done_reason": "stop"
        }).encode())
    return call


def test_ollama_structured_output_no_paid_calls():
    tracked = []
    opts = settings()
    store = Store(opts)
    provider = Ollama(opts, store, transport=fake_transport(['{"relations":[]}'], tracked))
    assert provider.request("Extract only explicit relations", Extraction).relations == []
    assert tracked[0][0]["stream"] is False
    assert tracked[0][0]["think"] is False
    assert tracked[0][0]["format"] == Extraction.model_json_schema()
    assert tracked[0][0]["model"] == "qwen3:4b-instruct"
    assert tracked[0][1] == "http://host.docker.internal:11434/api/chat"
    assert provider.usage["calls"] == 1
    assert provider.usage["estimated_usd"] == 0
    assert len(store.list("Usage")) >= 1


def test_ollama_bounded_invalid_output_repair():
    captured = []
    opts = settings()
    store = Store(opts)
    provider = Ollama(opts, store, transport=fake_transport(
        ['{"claims":[]}', '{"relations":[]}'], captured))
    assert provider.request("Extract", Extraction).relations == []
    assert len(captured) == 2
    assert any(t["kind"] == "ReviewTask" for t in store.list("ReviewTask"))
    assert provider.calls == 2


def test_ollama_connection_failure_is_reviewable_and_bounded():
    opts = settings()
    store = Store(opts)
    provider = Ollama(opts, store, transport=fake_transport(
        [ConnectionError("not running")], []))
    with pytest.raises(ProviderError, match="reachable"):
        provider.request("Extract", Extraction)
    assert provider.calls == 1
    assert any(u.get("state") == "provider_failed" for u in store.list("Usage"))


def test_ollama_max_calls_and_input_guard():
    opts = settings(max_model_calls=1)
    provider = Ollama(opts, Store(opts), transport=fake_transport(
        ['{"relations":[]}'], []))
    provider.request("Extract", Extraction)
    with pytest.raises(ProviderError, match="budget"):
        provider.request("Extract", Extraction)
    opts = settings(max_input_tokens=100)
    provider = Ollama(opts, Store(opts), transport=fake_transport([], []))
    with pytest.raises(ProviderError, match="input"):
        provider.request("X" * 120, Extraction)


@pytest.mark.parametrize("url", [
    "https://example.org:11434",
    "http://169.254.169.254:11434",
    "http://host.docker.internal:8080",
    "http://localhost:11434/path",
    "http://user:pass@localhost:11434",
])
def test_ollama_blocks_external_or_credentialed_hosts(url):
    with pytest.raises(ValueError, match="restricted"):
        settings(ollama_url=url)


def test_ollama_requires_model_but_not_paid_opt_in():
    with pytest.raises(ValueError, match="model ID"):
        Settings(backend="memory", provider="ollama", model_id="")
    assert settings().allow_paid_calls is False


def test_ollama_engine_route_and_offline_hybrid_verification():
    opts = settings()
    store = Store(opts)
    provider = Ollama(opts, store, transport=fake_transport(
        ['{"relations":[]}'], []))
    engine = Engine(store, provider_factory=lambda: provider)
    report = engine.ingest("one.txt", b"Alice owns Acme.", use_ai=True)
    assert report["provider"] == "ollama"
    assert report["claims"] == 1 and report["review_tasks"] == 0
    assert report["usage"]["calls"] == 1
    assert store.claims()[0]["predicate"] == "OWNS"



def test_local_compact_model_extracts_semantic_relation_after_review():
    from ugi.models import BatchVerdicts, CompactExtraction
    from ugi.extract import text_candidates

    sentence = "Male Srakane is an island in the Adriatic Sea."
    # Copular noun phrases are not automatically meaningful S-V-O grammar.
    assert text_candidates(sentence) == []
    assert [(x.subject, x.object) for x in text_candidates("Orion is part of Pegasus.")] == [
        ("Orion", "Pegasus")
    ]
    raw = json.dumps({"relations": [{
        "subject": "Male Srakane",
        "predicate": "LOCATED_IN",
        "object": "Adriatic Sea",
        "evidence": sentence
    }]})
    review = json.dumps({"decisions": [{"index": 0, "supported": True,
                                        "reason": "Explicit source location"}]})
    tracked = []
    opts = settings()
    store = Store(opts)
    provider = Ollama(opts, store, transport=fake_transport([raw, review], tracked))
    engine = Engine(store, provider_factory=lambda: provider)
    outcome = engine.ingest("geography.txt", sentence.encode(), use_ai=True)
    assert outcome["claims"] == 1 and outcome["review_tasks"] == 0
    assert outcome["usage"]["calls"] == 2
    assert tracked[0][0]["format"] == CompactExtraction.model_json_schema()
    assert tracked[1][0]["format"] == BatchVerdicts.model_json_schema()
    claim = store.claims()[0]
    assert (claim["subject"], claim["predicate"], claim["object"]) == (
        "Male Srakane", "LOCATED_IN", "Adriatic Sea")
    quote = store.get(claim["evidence_id"])
    assert quote["quote"] == sentence


def test_local_model_unsupported_candidate_requires_review_not_claim():
    from ugi.extract import text_candidates

    # Exact entity names are in evidence but source does not say the
    # bridge directly crosses the river: semantic support still required.
    sentence = ("Lane Cove Road ends north of De Burghs Bridge and where the A3 "
                "crosses the Lane Cove River.")
    unsupported = json.dumps({"relations": [{
        "subject": "De Burghs Bridge", "predicate": "CROSSES",
        "object": "Lane Cove River", "evidence": sentence
    }]})
    denied = json.dumps({"decisions": [{"index": 0, "supported": False,
                                        "reason": "Only the A3 is said to cross"}]})
    outputs = [unsupported, denied]
    tracked = []
    opts = settings()
    store = Store(opts)
    provider = Ollama(opts, store, transport=fake_transport(outputs, tracked))
    e = Engine(store, provider_factory=lambda: provider)
    report = e.ingest("roads.txt", sentence.encode(), use_ai=True)
    assert not any(c["subject"] == "De Burghs Bridge" and c["object"] == "Lane Cove River"
                   for c in store.claims())
    assert report["review_tasks"] >= 1
