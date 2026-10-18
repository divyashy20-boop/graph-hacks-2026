#!/usr/bin/env python3
"""Run the frozen Graphynx tournament against Groq GPT-OSS 120B.

This wrapper imports the authoritative supplied ``run_remote.py`` and reuses
its prompts, splitting, validation, ingestion, scoring, QA, controls, and P5
logic. Only the provider transport and local execution/checkpointing differ.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
import time
from groq import APIStatusError, Groq
import uuid
from datetime import UTC, datetime
from pathlib import Path

MODEL = {
    "name": "Groq GPT-OSS 120B", "family": "OpenAI OSS",
    "id": "openai/gpt-oss-120b", "rate": (0.15, 0.60),
    "guard": (0.15, 0.60), "kind": "groq",
}
API_URL = "https://api.groq.com/openai/v1/chat/completions"
RUNNER_SHA256 = "ce6196938326aafb0ed7ccd22f6c7d0aa3f577a9123c9bcd49ebd7c6b7c4d75e"
MANIFEST_SHA256 = "ee56ad88898bfc1f7c155faf43d7b85e2b9fe99f8b2e8e9f4f9500a00f6b8fa0"
EXPECTED_SOURCE_HASHES = {
    "000": "b9a256c236ce9cbe3d051e3f131dfce9429b428182c2b5d76ca1eed6c64814a7",
    "005": "761608079465ed389cacab08e70240b2eb1bf4867df9ac86843369a222dd9d88",
    "010": "7ab2f96d0032394dad778b11ab8411f75c024aab8236b70d4733845fbe178fe0",
    "019": "3c9ae8bad923a3b127ec96022ce58ec0630d4b04e435ed3728948fdb1c7a885f",
}
EXPECTED_BASELINE = {
    "qwen_whole_score": 54.515, "qwen_whole_accepted": 6,
    "qwen_whole_exact": 6, "qwen_whole_reference_hits": 3,
    "qwen_whole_query_visible": 5, "qwen_whole_claim_queries": 6,
    "qwen_split_score": 52.015, "qwen_fixed_qa": 12, "qwen_own_qa": 7,
    "haiku_whole_score": 55.23,
}


class TournamentIncomplete(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str),
                         encoding="utf-8")
    temporary.replace(path)


def duration_seconds(value):
    if value is None:
        return None
    value = str(value).strip().lower()
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    for suffix, multiplier in (("ms", 0.001), ("s", 1), ("m", 60), ("h", 3600)):
        if value.endswith(suffix):
            try:
                return max(0.0, float(value[:-len(suffix)]) * multiplier)
            except ValueError:
                return None
    return None


def load_key(env_file: Path) -> str:
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if key:
        return key
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8-sig").splitlines():
            match = re.fullmatch(r"\s*(?:export\s+)?GROQ_API_KEY\s*=\s*(.*?)\s*", line)
            if match:
                candidate = match.group(1).strip().strip("\"").strip("'")
                if candidate:
                    return candidate
    raise TournamentIncomplete(
        "GROQ_API_KEY_MISSING: set it in the environment or an untracked repository .env",
    )


def verify_sources(source_dir: Path) -> dict:
    runner = source_dir / "run_remote.py"
    manifest_path = source_dir / "manifest.json"
    if not runner.is_file() or not manifest_path.is_file():
        raise TournamentIncomplete("Authoritative tournament directory is incomplete")
    if sha256(runner) != RUNNER_SHA256:
        raise TournamentIncomplete("Authoritative run_remote.py SHA-256 mismatch")
    if sha256(manifest_path) != MANIFEST_SHA256:
        raise TournamentIncomplete("Authoritative manifest.json SHA-256 mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if manifest.get("sources") != EXPECTED_SOURCE_HASHES:
        raise TournamentIncomplete("Manifest source hashes differ from the frozen tournament")
    verified = {}
    for doc, expected in EXPECTED_SOURCE_HASHES.items():
        text_path = source_dir / "cases" / f"doc_{doc}.txt"
        json_path = source_dir / "cases" / f"doc_{doc}.json"
        got = sha256(text_path)
        if got != expected or not json_path.is_file():
            raise TournamentIncomplete(f"Frozen document {doc} failed source verification")
        json.loads(json_path.read_text(encoding="utf-8-sig"))
        verified[doc] = got
    return verified


def verify_baseline(report_path: Path) -> dict:
    report = json.loads(report_path.read_text(encoding="utf-8-sig"))
    qwen = next((row for row in report["results"] if row["name"] == "Qwen3 32B"), None)
    haiku = next((row for row in report["results"] if row["name"] == "Claude Haiku 4.5"), None)
    if qwen is None or haiku is None:
        raise TournamentIncomplete("Saved report lacks Qwen or Claude Haiku results")
    whole = next(row for row in qwen["extraction"] if row["setting"] == "whole_compact")
    split = next(row for row in qwen["extraction"] if row["setting"] == "split_context")
    haiku_whole = next(row for row in haiku["extraction"] if row["setting"] == "whole_compact")
    observed = {
        "qwen_whole_score": whole["extraction_score"],
        "qwen_whole_accepted": whole["accepted_total"],
        "qwen_whole_exact": whole["evidence_exact"],
        "qwen_whole_reference_hits": whole["reference_pair_hits"],
        "qwen_whole_query_visible": whole["query_visible"],
        "qwen_whole_claim_queries": whole["claim_queries"],
        "qwen_split_score": split["extraction_score"],
        "qwen_fixed_qa": qwen["qa_reference"]["correct"],
        "qwen_own_qa": qwen["qa_own_graph"]["correct"],
        "haiku_whole_score": haiku_whole["extraction_score"],
    }
    if observed != EXPECTED_BASELINE:
        raise TournamentIncomplete("Saved comparison baseline does not match expected frozen values")
    return observed


def load_frozen(source_dir: Path):
    spec = importlib.util.spec_from_file_location("graphynx_frozen_tournament", source_dir / "run_remote.py")
    if spec is None or spec.loader is None:
        raise TournamentIncomplete("Could not load frozen tournament runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def prepare_runtime_sources(source_dir: Path, runtime_dir: Path) -> None:
    cases = runtime_dir / "cases"
    cases.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_dir / "manifest.json", runtime_dir / "manifest.json")
    for doc in EXPECTED_SOURCE_HASHES:
        for suffix in ("txt", "json"):
            shutil.copy2(source_dir / "cases" / f"doc_{doc}.{suffix}",
                         cases / f"doc_{doc}.{suffix}")


class GroqTournamentMeter:
    """Original Meter interface with Groq transport and durable response cache."""

    def __init__(self, key: str, checkpoint_path: Path, timeout=120):
        self.key = key
        self.checkpoint_path = checkpoint_path
        self.timeout = timeout
        self.guarded = 0.0
        self.actual_estimate_known = 0.0
        self.unknown_price_calls = 0
        self.calls = 0
        self.events = []
        self.next_request_at = 0.0
        self.remaining_tokens = None
        self.token_reset_at = 0.0
        if checkpoint_path.is_file():
            self.checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        else:
            self.checkpoint = {"version": 1, "model": MODEL["id"], "responses": {},
                               "attempts": [], "created_at": datetime.now(UTC).isoformat()}
        if self.checkpoint.get("model") != MODEL["id"]:
            raise TournamentIncomplete("Checkpoint belongs to another model")

    def save(self):
        self.checkpoint["updated_at"] = datetime.now(UTC).isoformat()
        atomic_json(self.checkpoint_path, self.checkpoint)

    @staticmethod
    def cache_key(prompt, max_tokens, api):
        material = json.dumps({"model": MODEL["id"], "prompt": prompt,
                               "max_tokens": max_tokens, "api": api},
                              ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    def pace(self, predicted_tokens):
        now = time.monotonic()
        target = self.next_request_at
        if self.remaining_tokens is not None and self.remaining_tokens < predicted_tokens:
            target = max(target, self.token_reset_at)
        wait = max(0.0, target - now)
        if wait:
            time.sleep(wait)
        self.next_request_at = time.monotonic() + 2.05

    @staticmethod
    def safe_headers(headers):
        allowed = {
            "retry-after", "x-ratelimit-limit-requests", "x-ratelimit-limit-tokens",
            "x-ratelimit-remaining-requests", "x-ratelimit-remaining-tokens",
            "x-ratelimit-reset-requests", "x-ratelimit-reset-tokens",
        }
        return {str(k).lower(): str(v) for k, v in headers.items()
                if str(k).lower() in allowed}

    def update_limits(self, headers):
        try:
            self.remaining_tokens = int(headers.get("x-ratelimit-remaining-tokens", ""))
        except ValueError:
            self.remaining_tokens = None
        reset = duration_seconds(headers.get("x-ratelimit-reset-tokens"))
        if reset is not None:
            self.token_reset_at = time.monotonic() + reset

    def call(self, model, prompt, max_tokens, api):
        if self.calls >= 235:
            raise TournamentIncomplete("GLOBAL_CALL_CEILING")
        raw_bytes = len(prompt.encode("utf-8"))
        if raw_bytes > 9500:
            raise TournamentIncomplete("PROMPT_BYTES_LIMIT")
        self.calls += 1
        predicted_input = max(1, (raw_bytes + 2) // 3)
        reserved = (predicted_input * model["rate"][0]
                    + max_tokens * model["rate"][1]) / 1e6
        self.guarded += reserved
        cache_key = self.cache_key(prompt, max_tokens, api)
        cached = self.checkpoint["responses"].get(cache_key)
        event = {"model": model["name"], "kind": api, "max_tokens": max_tokens,
                 "input_bytes": raw_bytes, "cache_key": cache_key}
        if cached:
            if cached.get("status") != "COMPLETE":
                raise TournamentIncomplete(
                    "Checkpoint contains a prior ambiguous/failed request; refusing blind retry",
                )
            usage = cached.get("usage", {})
            cost = (int(usage.get("prompt_tokens") or 0) * model["rate"][0]
                    + int(usage.get("completion_tokens") or 0) * model["rate"][1]) / 1e6
            self.actual_estimate_known += cost
            event.update(status="CACHED_COMPLETE", input_tokens=usage.get("prompt_tokens", 0),
                         output_tokens=usage.get("completion_tokens", 0),
                         latency_s=cached.get("latency_s", 0))
            self.events.append(event)
            return cached["output"], cached.get("finish_reason")

        client = Groq(api_key=self.key, timeout=self.timeout, max_retries=0)
        rate_retry = 0
        while True:
            predicted_total = predicted_input + max_tokens
            self.pace(predicted_total)
            started = time.monotonic()
            attempt = {"cache_key": cache_key, "kind": api, "max_tokens": max_tokens,
                       "issued_at": datetime.now(UTC).isoformat(), "status": "ISSUED"}
            self.checkpoint["attempts"].append(attempt)
            self.save()
            try:
                request_options = {
                    "model": model["id"],
                    "messages": [{"role": "user", "content": prompt}],
                    "max_completion_tokens": max_tokens,
                }
                # Unscored availability/JSON-only preflight. Benchmark calls remain unchanged.
                if api == "availability_json_preflight":
                    request_options["response_format"] = {"type": "json_object"}
                sdk_response = client.chat.completions.with_raw_response.create(
                    **request_options
                )
                parsed = sdk_response.parse()
                headers = self.safe_headers(sdk_response.headers)
                choice = parsed.choices[0]
                output = choice.message.content
                if not isinstance(output, str):
                    raise ValueError("Groq response content is not text")
                if len(output.encode("utf-8")) > 1024 * 1024:
                    raise ValueError("Groq response exceeded 1 MiB")
                usage = parsed.usage.model_dump() if parsed.usage else {}
                input_tokens = max(0, int(usage.get("prompt_tokens") or 0))
                output_tokens = max(0, int(usage.get("completion_tokens") or 0))
                latency = round(time.monotonic() - started, 3)
                cost = (input_tokens * model["rate"][0]
                        + output_tokens * model["rate"][1]) / 1e6
                self.actual_estimate_known += cost
                record = {"status": "COMPLETE", "output": output,
                          "finish_reason": choice.finish_reason, "usage": usage,
                          "latency_s": latency, "rate_headers": headers,
                          "completed_at": datetime.now(UTC).isoformat()}
                self.checkpoint["responses"][cache_key] = record
                attempt.update(status="COMPLETE", latency_s=latency, rate_headers=headers,
                               input_tokens=input_tokens, output_tokens=output_tokens)
                self.update_limits(headers)
                self.save()
                event.update(status="COMPLETE", input_tokens=input_tokens,
                             output_tokens=output_tokens, latency_s=latency,
                             estimated_usd=round(cost, 8), rate_headers=headers)
                self.events.append(event)
                return output, choice.finish_reason
            except APIStatusError as exc:
                status = int(exc.status_code)
                headers = self.safe_headers(exc.response.headers or {})
                attempt.update(status="RATE_LIMITED" if status == 429 else "FAILED_NO_RETRY",
                               http_status=status, rate_headers=headers,
                               latency_s=round(time.monotonic() - started, 3))
                self.update_limits(headers)
                self.save()
                if status == 429 and rate_retry == 0:
                    wait = duration_seconds(headers.get("retry-after"))
                    if wait is None:
                        wait = duration_seconds(headers.get("x-ratelimit-reset-tokens"))
                    time.sleep(min(90.0, max(2.05, wait or 2.05)))
                    rate_retry += 1
                    continue
                self.checkpoint["responses"][cache_key] = {
                    "status": "FAILED_OR_AMBIGUOUS", "http_status": status,
                    "recorded_at": datetime.now(UTC).isoformat(),
                }
                self.save()
                raise TournamentIncomplete(f"Groq HTTP {status}; request not blindly retried") from exc
            except Exception as exc:
                attempt.update(status="FAILED_AMBIGUOUS_NO_RETRY", error_type=type(exc).__name__,
                               latency_s=round(time.monotonic() - started, 3))
                self.checkpoint["responses"][cache_key] = {
                    "status": "FAILED_OR_AMBIGUOUS", "error_type": type(exc).__name__,
                    "recorded_at": datetime.now(UTC).isoformat(),
                }
                self.save()
                raise TournamentIncomplete(
                    "Groq request failed with ambiguous completion state; refusing automatic retry",
                ) from exc


def usage_summary(meter: GroqTournamentMeter) -> dict:
    attempts = meter.checkpoint.get("attempts", [])
    complete = [row for row in attempts if row.get("status") == "COMPLETE"]
    tokens_in = sum(int(row.get("input_tokens") or 0) for row in complete)
    tokens_out = sum(int(row.get("output_tokens") or 0) for row in complete)
    latencies = [float(row.get("latency_s") or 0) for row in complete]
    return {
        "logical_calls": meter.calls,
        "api_requests_issued_including_rate_limits_and_failures": len(attempts),
        "successful_api_requests": len(complete),
        "prompt_tokens": tokens_in, "completion_tokens": tokens_out,
        "total_tokens": tokens_in + tokens_out,
        "estimated_list_cost_usd": round(
            (tokens_in * MODEL["rate"][0] + tokens_out * MODEL["rate"][1]) / 1e6, 8),
        "latency_seconds_total": round(sum(latencies), 3),
        "latency_seconds_mean": round(sum(latencies) / len(latencies), 3) if latencies else None,
        "latency_seconds_max": round(max(latencies), 3) if latencies else None,
    }


def live_check(meter: GroqTournamentMeter) -> dict:
    prompt = 'Return exactly one JSON object and nothing else: {"ok":true}'
    raw, finish = meter.call(MODEL, prompt, 1024, "availability_json_preflight")
    try:
        parsed = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
    except (TypeError, ValueError) as exc:
        raise TournamentIncomplete("Groq preflight did not return valid JSON") from exc
    if parsed != {"ok": True}:
        raise TournamentIncomplete("Groq preflight JSON did not match the requested object")
    return {"passed": True, "finish_reason": finish}


def quality_gate(report: dict) -> dict:
    extraction = {row["setting"]: row for row in report["groq"]["extraction"]}
    whole = extraction.get("whole_compact")
    split = extraction.get("split_context")
    fixed = report["groq"].get("qa_reference") or {}
    own = report["groq"].get("qa_own_graph") or {}
    controls = report.get("controls") or {}
    p5 = controls.get("p5") or {}
    qa_cases = [*fixed.get("cases", []), *own.get("cases", [])]
    requirements = {
        "both_extraction_settings_complete": bool(
            whole and split and whole.get("status") == split.get("status") == "COMPLETE"),
        "whole_score_at_least_qwen": bool(whole and whole.get("extraction_score", -1) >= 54.515),
        "whole_at_least_6_accepted": bool(whole and whole.get("accepted_total", 0) >= 6),
        "whole_accepted_evidence_100_percent": bool(
            whole and whole.get("accepted_total", 0) > 0
            and whole.get("evidence_exact") == whole.get("accepted_total")),
        "whole_reference_hits_at_least_3_of_8": bool(
            whole and whole.get("reference_pair_hits", 0) >= 3),
        "fixed_reference_qa_12_of_12": fixed.get("correct") == fixed.get("total") == 12,
        "own_graph_qa_at_least_7_of_12": own.get("total") == 12 and own.get("correct", 0) >= 7,
        "all_28_reasoning_controls": controls.get("question_count") == 28
        and controls.get("passed") == 28,
        "p5_valid_stale_and_unsafe_controls": p5.get("passes") is True
        and p5.get("unsafe_abstained") is True
        and p5.get("negative_receipt_reuse_blocked") is True,
        "no_fabricated_qa_claim_ids": bool(qa_cases)
        and all(case.get("citations_valid") is True for case in qa_cases),
        "all_unknown_questions_abstained": fixed.get("negative_correct") == 4
        and own.get("negative_correct") == 4,
    }
    return {"requirements": requirements, "passed": all(requirements.values()),
            "verdict": "PASS" if all(requirements.values()) else "FAIL"}


def diagnostics(extractions) -> dict:
    stats = {}
    reviews = []
    proposals = 0
    exact = 0
    both_entities = 0
    for variant in extractions:
        for document in variant.get("documents", []):
            proposals += document.get("schema_valid_proposals", 0)
            exact += document.get("schema_valid_proposals_quote_exact", 0)
            both_entities += document.get("schema_proposals_both_entities_in_quote", 0)
            reviews.extend(document.get("review_reasons", []))
            for key, value in document.get("adapter_stats", {}).items():
                stats[key] = stats.get(key, 0) + value
    return {
        "schema_valid_proposals": proposals,
        "proposal_quotes_exact": exact,
        "proposals_with_both_entities_in_quote": both_entities,
        "proposal_nonexact_quote_count": proposals - exact,
        "adapter_stats": stats,
        "review_reason_counts": dict(sorted(
            ((reason, reviews.count(reason)) for reason in set(reviews)),
            key=lambda item: (-item[1], item[0]),
        )),
        "limitation": "Exact quotes and automated Graphynx review are provenance controls, not independent semantic ground truth.",
    }


def configure_frozen(frozen, runtime_dir: Path, redis_url: str):
    frozen.BASE = runtime_dir
    frozen.OUT = runtime_dir / "unused_original_report.json"
    frozen.RUN_ID = "gxgroq_" + uuid.uuid4().hex[:12]
    frozen.MODELS = (MODEL,)

    def build_model_settings(model, setting):
        return frozen.Settings(
            backend="falkordb", redis_url=redis_url, graph_prefix=frozen.RUN_ID,
            provider="groq", allow_paid_calls=True, model_id=model["id"], input_price=model["rate"][0],
            output_price=model["rate"][1], max_input_tokens=16000,
            max_output_tokens=setting["max_output"], max_model_calls=8,
            global_daily_calls=1000, daily_cost_limit=14.9,
            max_upload_bytes=500000, open_predicates=False,
        )

    frozen.build_model_settings = build_model_settings


def run(args) -> dict:
    source_dir = args.source_dir.resolve()
    hashes = verify_sources(source_dir)
    baseline = verify_baseline(args.original_report.resolve())
    frozen = load_frozen(source_dir)
    runtime_dir = args.work_dir.resolve() / "runtime"
    prepare_runtime_sources(source_dir, runtime_dir)
    configure_frozen(frozen, runtime_dir, args.redis_url)
    cases = frozen.read_sources()
    frozen.validate_all_model_settings()
    if args.verify_only:
        return {"status": "VERIFIED_OFFLINE", "source_hashes": hashes,
                "baseline": baseline, "runner_sha256": RUNNER_SHA256}

    key = load_key(Path(__file__).resolve().parents[1] / ".env")
    meter = GroqTournamentMeter(key, args.checkpoint.resolve(), timeout=args.timeout)
    report = {
        "version": "Graphynx Groq GPT-OSS 120B frozen tournament v1",
        "status": "IN_PROGRESS", "started_at": datetime.now(UTC).isoformat(),
        "audited_base_commit": "7913afd7a5ebced7f5d15f82658593e9cfdb58f8",
        "model": MODEL, "api_base": "https://api.groq.com/openai/v1",
        "fair_baseline": {
            "temperature_override": False, "structured_outputs": False,
            "tools": False, "reasoning_effort_override": False,
            "transport_only_change": True,
        },
        "source_hashes": hashes, "runner_sha256": RUNNER_SHA256,
        "qwen_saved_baseline": baseline,
        "limitations": [
            "This four-document proxy is not official Re-DocRED F1 or general-purpose accuracy.",
            "Exact evidence spans do not independently prove semantic entailment.",
            "Estimated list cost is informational; the run is authorized for available free-tier quota only.",
        ],
    }
    started = time.monotonic()
    try:
        report["controls"] = frozen.deterministic_checks()
        report["live_preflight"] = live_check(meter)
        if args.live_check_only:
            report["status"] = "LIVE_PREFLIGHT_COMPLETE"
            return report
        row = {"name": MODEL["name"], "family": MODEL["family"],
               "model_id": MODEL["id"], "extraction": [],
               "qa_reference": None, "qa_own_graph": None}
        for setting in frozen.SETTINGS:
            before = meter.guarded
            candidate = frozen.ingest_variant(MODEL, setting, meter, cases)
            candidate["cost_guard_reserved"] = round(meter.guarded - before, 8)
            candidate["extraction_score"] = frozen.extraction_utility(candidate)
            row["extraction"].append(candidate)
        best = max(row["extraction"], key=lambda item: item.get("extraction_score", -1))
        documents = {item["doc"]: item for item in best["documents"]}
        own_context = {doc: frozen.graph_context(documents[doc], MODEL, best)
                       for doc in frozen.DOCS}
        reference_context = {doc: frozen.ref_context(doc) for doc in frozen.DOCS}
        row["qa_reference"] = frozen.qa_test(
            MODEL, meter, cases, reference_context, "fixed_reference",
        )
        row["qa_own_graph"] = frozen.qa_test(
            MODEL, meter, cases, own_context, "own_best_graph",
        )
        report["groq"] = row
        report["candidate_diagnostics"] = diagnostics(row["extraction"])
        report["quality_gate"] = quality_gate(report)
        report["status"] = "COMPLETE"
        report["verdict"] = report["quality_gate"]["verdict"]
    except Exception as exc:
        report["status"] = "INCOMPLETE"
        report["verdict"] = "INCOMPLETE"
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)[:500]
    finally:
        report["usage"] = usage_summary(meter)
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        report["completed_at"] = datetime.now(UTC).isoformat()
        atomic_json(args.output.resolve(), report)
    return report


def parser():
    result = argparse.ArgumentParser()
    result.add_argument("--source-dir", type=Path, required=True)
    result.add_argument("--original-report", type=Path, required=True)
    result.add_argument("--output", type=Path, required=True)
    result.add_argument("--checkpoint", type=Path, required=True)
    result.add_argument("--work-dir", type=Path, required=True)
    result.add_argument("--redis-url", default="redis://graph:6379/0")
    result.add_argument("--timeout", type=int, default=120, choices=range(30, 181))
    result.add_argument("--verify-only", action="store_true")
    result.add_argument("--live-check-only", action="store_true")
    return result


def main():
    args = parser().parse_args()
    try:
        report = run(args)
    except Exception as exc:
        report = {"status": "INCOMPLETE", "verdict": "INCOMPLETE",
                  "error_type": type(exc).__name__, "error": str(exc)[:500]}
    atomic_json(args.output.resolve(), report)
    print(json.dumps({
        "status": report.get("status"), "verdict": report.get("verdict"),
        "output": str(args.output.resolve()), "usage": report.get("usage"),
    }, ensure_ascii=False))
    raise SystemExit(0 if report.get("status") in {"VERIFIED_OFFLINE", "LIVE_PREFLIGHT_COMPLETE", "COMPLETE"} else 2)


if __name__ == "__main__":
    main()
