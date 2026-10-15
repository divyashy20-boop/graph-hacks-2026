from __future__ import annotations

import re
from datetime import UTC, datetime
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def uid(*values) -> str:
    import json

    return sha256(json.dumps(values, sort_keys=True, default=str).encode()).hexdigest()


def now() -> str:
    return datetime.now(UTC).isoformat()


def key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


ALIASES = {
    "DEPENDS_ON": "DEPENDS_ON", "DEPEND_ON": "DEPENDS_ON",
    "IS_DEPENDENT_ON": "DEPENDS_ON", "DEPENDENCY": "DEPENDS_ON",
    "IS_OWNED_BY": "OWNED_BY", "WAS_OWNED_BY": "OWNED_BY",
    "WAS_DEPLOYED_BY": "DEPLOYED_BY", "WAS_ACQUIRED_BY": "ACQUIRED_BY",
    "WORKS_FOR": "WORKS_AT",
    "WORK_FOR": "WORKS_AT", "WORK_AT": "WORKS_AT",
    "IS_PART_OF": "PART_OF", "IS_LOCATED_IN": "LOCATED_IN",
    "SUPPLY": "SUPPLIES", "SUPPLIED_BY": "SUPPLIED_BY",
}


def predicate(value: str) -> str:
    normalized = re.sub(r"[^\w]+", "_", value.strip(), flags=re.UNICODE).strip("_").upper()
    if not normalized or len(normalized) > 80:
        raise ValueError("Predicate must contain 1-80 meaningful characters")
    return ALIASES.get(normalized, normalized)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="UGI_", extra="ignore")
    backend: Literal["falkordb", "memory"] = "falkordb"
    redis_url: str = "redis://127.0.0.1:6380/0"
    graph_prefix: str = "ugi_event"
    api_keys: str = ""
    max_upload_bytes: int = Field(default=5 * 1024 * 1024, ge=1)
    max_records: int = Field(default=2000, ge=1, le=2000)
    max_chars: int = Field(default=200000, ge=1)
    max_nodes: int = Field(default=5000, ge=1)
    max_claims: int = Field(default=20000, ge=1)
    max_hops: int = Field(default=4, ge=1, le=6)
    max_expansions: int = Field(default=1000, ge=1, le=5000)
    max_tool_steps: int = Field(default=8, ge=4, le=12)
    requests_per_minute: int = Field(default=120, ge=1)
    daily_ai_queries: int = Field(default=15, ge=1)
    global_daily_calls: int = Field(default=100, ge=1)
    provider: Literal["offline", "bedrock", "ollama"] = "offline"
    allow_paid_calls: bool = False
    model_id: str = ""
    ollama_url: str = "http://host.docker.internal:11434"
    aws_region: str = "us-east-1"
    input_price: float = Field(default=0, ge=0)
    output_price: float = Field(default=0, ge=0)
    daily_cost_limit: float = Field(default=0.25, gt=0)
    max_model_calls: int = Field(default=4, ge=1, le=8)
    max_output_tokens: int = Field(default=1500, ge=100, le=4096)
    max_input_tokens: int = Field(default=12000, ge=100, le=20000)

    @model_validator(mode="after")
    def configuration(self):
        if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_]{0,30}", self.graph_prefix):
            raise ValueError("Invalid graph prefix")
        if self.provider == "bedrock" and not (
            self.allow_paid_calls and self.model_id and self.input_price and self.output_price
        ):
            raise ValueError("Bedrock requires explicit paid opt-in, model ID and verified prices")
        if self.provider == "ollama":
            from urllib.parse import urlsplit

            url = urlsplit(self.ollama_url)
            if (not self.model_id or url.scheme != "http"
                    or url.hostname not in {"localhost", "127.0.0.1", "host.docker.internal"}
                    or url.port != 11434 or url.username or url.password
                    or url.path not in {"", "/"} or url.query or url.fragment):
                raise ValueError("Local Ollama requires model ID and restricted localhost:11434 URL")
        return self


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Candidate(Strict):
    subject: str = Field(min_length=1, max_length=160)
    predicate: str = Field(min_length=1, max_length=80)
    object: str = Field(min_length=1, max_length=160)
    evidence: str = Field(min_length=1, max_length=4000)
    subject_id: str | None = None
    object_id: str | None = None
    subject_type: str = "Entity"
    object_type: str = "Entity"
    subject_aliases: list[str] = Field(default_factory=list, max_length=20)
    object_aliases: list[str] = Field(default_factory=list, max_length=20)
    polarity: Literal["positive", "negative"] = "positive"
    modality: Literal["asserted", "possible", "alleged", "probable", "unknown"] = "asserted"
    event_time: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    time_precision: Literal["unknown", "year", "month", "day", "instant"] = "unknown"
    temporal_source: str | None = None
    historical: bool = False
    attribution: str | None = None
    event_id: str | None = None

    @model_validator(mode="after")
    def intervals(self):
        for field in ("event_time", "valid_from", "valid_to"):
            value = getattr(self, field)
            if value:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
        if self.valid_from and self.valid_to and self.valid_from > self.valid_to:
            raise ValueError("Reversed validity interval")
        return self


class Extraction(Strict):
    relations: list[Candidate] = Field(max_length=60)


class CompactRelation(Strict):
    """Small local-model schema; converted to Candidate before verification."""
    subject: str = Field(min_length=1, max_length=160)
    predicate: str = Field(min_length=1, max_length=80)
    object: str = Field(min_length=1, max_length=160)
    evidence: str = Field(min_length=1, max_length=4000)
    polarity: Literal["positive", "negative"] = "positive"
    modality: Literal["asserted", "possible", "alleged", "probable", "unknown"] = "asserted"
    historical: bool = False


class CompactExtraction(Strict):
    relations: list[CompactRelation] = Field(max_length=12)


class Verdict(Strict):
    supported: bool
    reason: str = Field(max_length=1000)


class IndexedVerdict(Strict):
    index: int = Field(ge=0, le=59)
    supported: bool
    reason: str = Field(min_length=1, max_length=600)


class BatchVerdicts(Strict):
    decisions: list[IndexedVerdict] = Field(max_length=60)


class HypothesisProposal(Strict):
    justified: bool
    explanation: str = Field(min_length=1, max_length=1500)
    supporting_claim_ids: list[str] = Field(max_length=20)
    assumptions: list[str] = Field(max_length=10)
    missing_evidence: list[str] = Field(max_length=10)


class RelationQuery(Strict):
    subject: str = Field(min_length=1, max_length=160)
    object: str = Field(min_length=1, max_length=160)
    predicate: str = Field(min_length=1, max_length=80)
    as_of: str | None = None
    allow_hypothesis: bool = False
    use_ai: bool = False


class InvestigationRequest(Strict):
    target: str = Field(min_length=1, max_length=160)
    idempotency_key: str = Field(min_length=1, max_length=100)
    authorise_action: bool = False
    as_of: str | None = None


class ReviewDecision(Strict):
    decision: Literal["accepted", "rejected"]
    reason: str = Field(min_length=5, max_length=1000)
