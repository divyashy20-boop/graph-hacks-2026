"""Opt-in two-document LOCAL model smoke test; no independent accuracy claim."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import Engine
from .models import Settings, now
from .provider import Ollama
from .store import Store

SAMPLES = [
    ("spatial", "Pavo lies between Quill and Rowan."),
    ("supply", "Mica provides Sensor to Vale Factory."),
]


def run(model, url):
    rows = []
    for ident, text in SAMPLES:
        settings = Settings(backend="memory", provider="ollama", model_id=model, ollama_url=url,
                            max_model_calls=3, max_output_tokens=1800)
        store = Store(settings)
        provider = Ollama(settings, store)
        provider.trace_enabled = True
        engine = Engine(store, provider_factory=lambda: provider)
        report = engine.ingest(ident + ".txt", text.encode(), use_ai=True)
        rows.append({"id": ident, "source": text, "ingestion": report,
                     "events": store.events(), "claims": store.claims(),
                     "reviews": store.list("ReviewTask"), "provider_trace": provider.trace})
        print(json.dumps({"document": ident, "events": report["relation_events"],
                          "claims": report["claims"], "usage": report["usage"],
                          "elapsed_ms": report["elapsed_ms"]}), flush=True)
    return {"recorded_at": now(), "model": model, "documents": rows,
            "scope": "Two synthetic development smoke tests with deterministic templates; "
                     "model transport/schema compatibility only, not independent model accuracy",
            "cloud_api_calls": 0, "annotation": "AI-authored CC0 development text"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--url", default="http://127.0.0.1:11434")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.model, args.url)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
