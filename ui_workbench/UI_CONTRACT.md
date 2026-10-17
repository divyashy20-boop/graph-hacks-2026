# UGI UI display contract

**Ticket:** UI-009
**Status:** Complete locally — verified against current source/tests on 2026-10-17
**Scope:** current root application only (`ugi/`). This is a display contract,
not a backend/AWS specification or authorization to change live application files.

## 1. Shared request rules

The browser helper in `ugi/assets/app.js` sends these headers for normal API
requests:

| Header | Source | UI rule |
| --- | --- | --- |
| `X-Dataset` | Dataset input, default `demo` | Treat it as a data-scope change. Clear selected records, verdict highlights, action authorization and any saved guided receipt when it changes. |
| `X-API-Key` | Access-key input | Never display or log its value. A changed key is a new owner scope; clear selection and any receipt. |
| `Content-Type: application/json` | JSON POST body only | Do not set it for multipart uploads. |

The current public browser API has no session/profile endpoint. A UI must not
invent a signed-in user, deployment readiness, or an AWS-success state.

## 2. Current endpoint contract

### Service availability and feature flags

`GET /health` returns:

```json
{
  "service": "ugi",
  "backend": "memory | falkordb",
  "provider": "offline | ollama | bedrock",
  "live_inference_verified": false,
  "guided_agent_enabled": false,
  "memory_enabled": false,
  "external_action_fencing": false
}
```

Display rules:

- Show backend/provider as a technical readout only.
- `live_inference_verified` is currently false: never label a model or AWS
  result as verified inference.
- Reveal guided-agent UI only when both `guided_agent_enabled` and
  `memory_enabled` are true.
- `external_action_fencing` is false: receipt freshness is never permission to
  describe external action as safe or authorized.

`GET /ready` returns `{ "ready": boolean }`. It is an availability signal, not
a quality, data-completeness, or deployment certification signal.

### Dataset graph and whole events

`GET /api/graph?limit=250&as_of=YYYY-MM-DD` returns:

```json
{
  "entities": ["Entity records"],
  "claims": ["Claim records"],
  "events": ["RelationEvent records"],
  "counts": {"Entity": 0, "Claim": 0, "RelationEvent": 0},
  "as_of": "YYYY-MM-DD | null",
  "unknown_dates_excluded": false,
  "truncated": false
}
```

Display rules:

- `counts` describes all stored records; graph arrays are bounded by `limit`.
  If `truncated` is true, retain an explicit bounded-view notice.
- With `as_of`, claims/events without applicable date evidence are excluded.
  If `unknown_dates_excluded` is true, keep the date-filter warning visible.
- An empty array is a no-records state, not a statement that the world has no
  relationships.
- Entity, Claim and RelationEvent records have different meaning and must
  retain distinct visual treatment.

`GET /api/events?entity_id=<optional>&as_of=<optional>&limit=100` returns
`events`, `limit`, `filtered_after_limit`, and the semantic warning: whole
source events do not prove binary predicates. Event participants must not be
shown as automatically connected by a binary edge.

### Records and provenance

- `GET /api/entities?name=<name>` returns matching entity records. Multiple
  matches mean the UI must preserve ambiguity and allow use of an exact ID.
- `GET /api/records/{record_id}` returns one stored record or `404`.
- A Claim may reference `evidence_id`; an Evidence record carries `quote`,
  `start`, `end`, `source_id`, `chunk_id` and location information.
- A RelationEvent contains role-labelled `participants` and may also have an
  evidence reference.

When a record is selected, the inspector must preserve record kind/name/relation,
polarity/modality/temporal context where available, exact quote, source filename,
`start–end` offsets, event roles, and the distinction between source assertion
and independently verified truth.

### Ingestion

`POST /api/uploads?use_ai=<bool>&pack_refs=<json>` uses multipart form field
`file`. The current UI accepts CSV, JSON, JSONL, TXT and text PDF.

Successful reports include current ingest counts/context, typically `source_id`,
`chunks`, `entities`, `claims`, `relation_events`, `review_tasks`, `duplicate`,
`warnings`, `elapsed_ms`, `provider`, and `usage`.

- Report exact returned counts; do not promote skipped candidates into claims.
- `duplicate: true` means the source already exists, not that it was freshly
  processed.
- A no-candidate/warning result is not proof that a source contains no
  relationship.
- AI is optional and must use the configured provider; never render it as a
  mandatory or verified capability.

### Relationship evaluation

`POST /api/relationships` requires:

```json
{
  "subject": "name or exact ID",
  "object": "name or exact ID",
  "predicate": "PREDICATE",
  "as_of": "YYYY-MM-DD | null",
  "allow_hypothesis": false,
  "use_ai": false
}
```

Every response has a verdict-oriented base including `status`, `predicate`,
`evidence`, `paths`, `rules`, `explanation`, `hypotheses`, and `confidence_note`.
It can also include `resolution`, `supporting_claim_ids`, or conflict information.

| Status | UI title / meaning | Must not be presented as |
| --- | --- | --- |
| `SOURCE_ASSERTED` | Direct source assertion | Independently verified world truth |
| `SOURCE_NEGATED` | Source explicitly negates the relation | A conflict unless opposing overlapping evidence exists |
| `CONTRADICTED` | Opposing, overlapping source claims | A settled positive or negative fact |
| `RULE_DERIVED` | Bounded rule-derived conclusion with source claim IDs/rule trace | A direct source assertion or incident causality |
| `CONNECTED_ONLY` | Graph connection does not entail requested relation | A supported conclusion |
| `HYPOTHESIS` | Separately stored risk hypothesis | Source assertion |
| `UNKNOWN` | Insufficient supported evidence / ambiguous identity | A negative proof |

For `RULE_DERIVED`, the response must carry a rule and supporting claim IDs, and
`resolution.assessment` is also `RULE_DERIVED`. For a non-entailed path, use the
returned resolution/missing-evidence language rather than making up a positive
explanation.

### Investigation, review and action boundary

- `GET /api/investigations` returns stored Investigation records.
- `GET /api/tasks` returns ReviewTask records.
- `POST /api/investigations` requires `target`, `idempotency_key`,
  `authorise_action` and optional `as_of`.
- `POST /api/tasks/{task_id}/decision` requires `accepted` or `rejected` plus a
  reason of at least five characters.

An investigation preview is read-only and must never look like a saved case. A
write requires the explicit authorization control and returned execution state.
A review decision records judgement; it does not convert a proposal into a
source assertion. Dataset or key changes invalidate local action context.

### Guided agent and receipt freshness

These endpoints return `404` unless both health flags are enabled.

`POST /api/agent/guided` accepts `{ "query": "..." }` and returns `status`,
optional `reason`, `result`, optional `receipt_id`, `freshness`, `read_count`
and `writes_attempted: 0`. The `result` may contain `verdict` and
`verified_claim_ids`.

The controller is deterministic and read-only. It accepts narrow explicit
two-entity dependency questions; an abstention has no reusable receipt. Verified
claim IDs may be highlighted, but hypotheses must not be highlighted as proof.

`GET /api/agent/receipts/{receipt_id}/freshness` returns `receipt_id`,
`freshness`, `safe_to_reuse`, original-read differences, a `reason`, and
`external_actions_authorized: false`.

| Freshness | Required UI wording |
| --- | --- |
| `VALID` and `safe_to_reuse: true` | Reusable **at the time of this check**. |
| `STALE` | Do not reuse; obtain a fresh answer. |
| `UNKNOWN` | Do not reuse; evidence conflict/unavailability requires investigation. |

Never call a receipt permanent, globally fresh, action-authorizing, or externally
fenced. A different dataset or access key invalidates browser receipt context and
requires a new query.

## 3. Required browser states and existing hooks

| State | Existing element/hook | UI requirement |
| --- | --- | --- |
| Graph loading | `#graphstate`, `setGraphState("loading")` | Show retrieval state without hiding context permanently. |
| Graph error/retry | `#graphstate`, `#retrygraph`, `setGraphState("error")` | Make retry clear and preserve returned error detail. |
| No records | `#empty` | Suggest a real upload or seeded demo; do not imply absence of real-world facts. |
| Graph truncation/date filter | `#graphnotice` | Keep bounded/date notices readable. |
| Selection/clear selection | `selectedRecordId`, graph click handling | Preserve the source-inspector route and clear unrelated emphasis correctly. |
| 2D map | `#graph2d`, `#view2d` | Preserve selection, date scope and inspector context. |
| Native 3D orbit | `#graph3d`, `#orbitCanvas`, `#view3d`, `#autoRotate` | Preserve the same data semantics as 2D. |
| WebGL unavailable | `#orbitFallback`, `#fallback2d` | Present one clear fallback, never overlapping the empty state. |
| Upload/query/action status | `#uploadstatus`, `#querystatus`, `#actionstatus` | Use explicit working/success/error copy. |
| Guided disabled | `#guidedpanel[hidden]` | Do not show a fake unavailable workflow. |
| Guided/receipt status | `#guidedstatus`, `#guidedverdict`, `#receiptreport` | Preserve status, reason and safe-to-reuse boundary. |

## 4. Error/status handling

- `401`: valid API key required. Do not reveal whether data exists.
- `404`: missing record, feature disabled, or unknown/scoped receipt. Do not
  infer data existence from it.
- `409`: guided/memory policy or bridge conflict; show returned safe failure
  wording, not a client-side retry claim.
- `422`: invalid request/input/date; retain user input and show correction path.
- `429`: upload/request quota or concurrent ingest bound; wait/retry guidance,
  not a false success.
- `503`: storage unavailable or freshness unverifiable; say “do not reuse” for
  a receipt and never fall back to stale cached proof.

## 5. Pending backend/AWS confirmation

UI-012 cannot begin until the backend/AWS owner answers these items for the
approved integration commit:

| Question | Owner response |
| --- | --- |
| Approved backend commit/branch | Pending |
| Deployment URL and allowed test environment | Pending |
| Authentication/session/error response contract | Pending |
| New AWS-exposed UI-safe fields/endpoints | Pending |
| Feature flags and safe user-facing labels | Pending |
| Sensitive fields that must never be rendered | Pending |
| Rate-limit, timeout and retry guidance | Pending |
| Whether current `/health` semantics change in AWS | Pending |

## 6. Verification sources

- `ugi/api.py` — active routes and feature gates.
- `ugi/engine.py` — relationship verdict semantics and explanation consistency.
- `ugi/agent_integration.py` — guided/receipt response shape and action limits.
- `ugi/assets/app.js`, `ugi/assets/guided.js`, `ugi/index.html` — current
  browser elements/state hooks.
- `tests/test_dashboard.py`, `tests/test_guided_ui_release.py`,
  `tests/test_guided_memory_http.py` — tested behavior and safety boundaries.
