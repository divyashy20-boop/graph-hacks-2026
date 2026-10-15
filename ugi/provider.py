from __future__ import annotations

import json
from datetime import UTC, datetime

from pydantic import ValidationError

from .models import now, uid


class ProviderError(ValueError):
    pass


class Bedrock:
    """Bounded Converse calls; JSON schema and corrective retry share one contract."""

    def __init__(self, settings, store, client=None):
        self.settings, self.store = settings, store
        self.calls = 0
        self.usage = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "estimated_usd": 0.0}
        self.client = client
        if settings.provider != "bedrock" or not settings.allow_paid_calls:
            raise ProviderError("Live inference disabled")
        if client is None:
            import boto3
            from botocore.config import Config

            self.client = boto3.Session(region_name=settings.aws_region).client(
                "bedrock-runtime", config=Config(
                    connect_timeout=3, read_timeout=25,
                    retries={"total_max_attempts": 1, "mode": "adaptive"},
                    max_pool_connections=2,
                ),
            )

    def request(self, instruction, schema):
        prompt = instruction + "\nReturn only JSON matching this schema:\n" + json.dumps(
            schema.model_json_schema(), separators=(",", ":"),
        )
        errors = []
        for attempt in range(2):
            if self.calls >= self.settings.max_model_calls:
                raise ProviderError("Model call budget exhausted")
            # UTF-8 bytes upper-bound token count for ordinary byte-backed tokenizers.
            upper_input = len(prompt.encode("utf-8"))
            if upper_input > self.settings.max_input_tokens:
                raise ProviderError("Conservative input token budget exceeded")
            today = datetime.now(UTC).date().isoformat()
            self.store.consume("calls:" + today, self.settings.global_daily_calls)
            reserve = (upper_input * self.settings.input_price
                       + self.settings.max_output_tokens * self.settings.output_price) / 1e6
            self.store.consume("cost:" + today, int(self.settings.daily_cost_limit * 1e6),
                               max(1, int(reserve * 1e6 + 1)))
            self.calls += 1
            usage_record = dict(id=uid(self.store.owner, now(), self.calls), kind="Usage",
                                model=self.settings.model_id, state="reserved",
                                reserved_usd=reserve, recorded_at=now())
            self.store.commit([usage_record])
            try:
                response = self.client.converse(
                    modelId=self.settings.model_id,
                    messages=[{"role": "user", "content": [{"text": prompt}]}],
                    inferenceConfig={"maxTokens": self.settings.max_output_tokens},
                )
                usage = response.get("usage", {})
                in_tokens, out_tokens = usage.get("inputTokens", 0), usage.get("outputTokens", 0)
                cost = (in_tokens * self.settings.input_price
                        + out_tokens * self.settings.output_price) / 1e6
                self.usage["calls"] += 1
                self.usage["input_tokens"] += in_tokens
                self.usage["output_tokens"] += out_tokens
                self.usage["estimated_usd"] += cost
                raw = "".join(b.get("text", "") for b in response["output"]["message"]["content"])
                usage_record.update(state="returned", input_tokens=in_tokens,
                                    output_tokens=out_tokens, estimated_usd=cost)
                self.store.commit([usage_record])
            except Exception as exc:
                usage_record.update(state="provider_failed", error_type=type(exc).__name__)
                self.store.commit([usage_record])
                raise ProviderError("Provider failed; see persisted usage record") from exc
            try:
                if response.get("stopReason") == "max_tokens":
                    raise ValueError("Output truncated")
                return schema.model_validate_json(raw)
            except (ValidationError, ValueError) as exc:
                errors.append(type(exc).__name__)
                self.store.commit([dict(
                    id=uid(usage_record["id"], "invalid"), kind="ReviewTask",
                    status="open", reason="Invalid model response", raw_output=raw[:16000],
                    model=self.settings.model_id, recorded_at=now(),
                )])
                if attempt == 0:
                    prompt += "\nPrevious output failed validation: " + str(exc)[:1200]
                    prompt += "\nCorrect schema/field errors; return the complete JSON."
        raise ProviderError("Invalid extraction after bounded repair: " + ",".join(errors))
