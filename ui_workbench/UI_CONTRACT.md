# UGI UI display contract

**Status:** UI-009 local draft. Update this document before either contributor
implements a new display state. It describes current application behavior; it
does not authorize backend/AWS changes.

## Existing display sources

| UI surface | Current endpoint/state | Display rules |
| --- | --- | --- |
| Backend readout | `GET /health` | Show backend/provider/feature state; do not claim live inference verification. |
| Evidence map | `GET /api/graph` | Render entities, claims, whole events, counts, truncation and `as_of` state. |
| Whole events | `GET /api/events` | Participant incidence is not a binary relationship proof. |
| Inspector | `GET /api/records/{id}` | Keep source quote, filename, offsets and event roles inspectable. |
| Ingest | `POST /api/uploads` | Report bounded ingest result; no-candidate output is not proof of no relationship. |
| Relationship verdict | `POST /api/relationships` | Preserve returned status, evidence and explanatory limits. |
| Investigation/reviews | `/api/investigations`, `/api/tasks` | Clearly separate read-only preview from explicit authorized persistence. |
| Guided agent | `POST /api/agent/guided` | Only present when both guided/memory flags are enabled. |
| Receipt freshness | `GET /api/agent/receipts/{id}/freshness` | `VALID` is reusable at check time; `STALE`/`UNKNOWN` mean do not reuse. |

## Required visible states

- loading, ready, empty, error and retry
- graph truncation and date-filter exclusion
- selected record and cleared selection
- WebGL orbit available and WebGL fallback to 2D
- evidence verdict: `SOURCE_ASSERTED`, `SOURCE_NEGATED`, `RULE_DERIVED`,
  `CONNECTED_ONLY`, `CONTRADICTED`, `HYPOTHESIS`, `UNKNOWN`
- preview versus explicitly authorized persistent action
- guided feature disabled, receipt `VALID`, receipt `STALE`, receipt `UNKNOWN`

## Pending backend/AWS confirmation

The backend/AWS owner must fill this section before UI-012 integration:

| Question | Owner response |
| --- | --- |
| Approved backend commit/branch for UI integration | Pending |
| Deployment URL and allowed test environment | Pending |
| Authentication/session/error response contract | Pending |
| New AWS-exposed UI-safe fields/endpoints | Pending |
| Feature flags and their safe user-facing labels | Pending |
| Any sensitive fields that must never be rendered | Pending |
