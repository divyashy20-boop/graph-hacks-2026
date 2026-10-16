# Milestone F — bounded, evidence-based identity intelligence

October16,2026; started clean at046534322501b89ffb27c6db485138ca22a4f72e.
Reproduced209 tests including13 actual FalkorDB, preserved graphs/volumes and all
prior commits. No cloud model, AWS/Khoj changes, external code archive or new ML
dependency. This is a prototype, not enterprise-scale autonomous truth discovery.

## Existing guarantees

Immutable MentionSnapshots and delta EntityCards retain source/Chunk/Claim/Event
anchors; current Entity names remain a legacy mutable view. IdentityRevision
records append decisions; mutable assignment heads select a projection. Manual
merge/split/revert requires explicit authorization, refuses stale undo and does
not rewire source facts. DerivedArtifact inputs use exact assignment revision IDs;
immutable KnowledgeRevision notices mark only registered dependents stale.
Staleness is not semantic re-evaluation. World validity stays separate from system
recorded_at. Existing hypotheses, rules, dashboard, MCP write gates are unchanged.

## Increment1 — indexed candidates and decisions

`UGI_IDENTITY_RESOLUTION=off|dry_run` requires ledger for dry_run; defaults off.
F-mode new mentions start at separate unresolved overlay anchors even if the
legacy graph reused an untrusted supplied ID. This does not fix/rewrite legacy
Claim endpoints. Name/alias blocks are normalized, type-scoped hashes; authoritative
identifier blocks additionally include exact namespace and case-sensitive value.
IdentityPosting.block_key has a real FalkorDB index. Bounded retrieval defaults20,
max50 candidates; overflow reports complete=false, never a complete cluster claim.
Index/decision records are staged in the same atomic source commit. Aliases only
generate candidates, never prove identity. No cross-tenant or cross-dataset lookup.

SAME_ENTITY requires matching policy-approved exclusive identifiers and no negative
constraint. Conflicting exclusive namespace values or declared types yield
DIFFERENT_ENTITY; exact normalized names alone yield POSSIBLY_SAME; insufficient
or internally inconsistent evidence yields UNRESOLVED. All assessments retain
algorithm/policy hashes, evidence IDs, categorical features and reasons; calibrated
is false and no numeric probability is fabricated. No provisional projection is
admitted to definitive inference.

### Trust boundary

Uploaded `trusted`, `authority` or model confidence fields do not establish trust.
The separate authority-observation inlet requires operator-configured authority ->
exclusive/stable namespace policy, explicit write authorization, tenant credentials
where configured, and exact matching structured source `identity` entries:

```json
{"name":"ABC Corp.","entity_type":"Organisation","namespace":"registry:example","value":"123"}
```

These entries belong in a triple/event row's `identity` list, not executable code.
The connector attests the source origin. There is **no independent registry lookup
or cryptographic source authentication**, and demo API keys are not production
RBAC: only trusted connector/operators should hold this write authority. Configure
only genuinely exclusive, stable namespaces; reused/nonunique IDs must not be
approved. Namespaces are not conflated, and corporate acquisitions/splits are not
identity equality merely because they are related events. Evidence-head replacement
preserves old immutable evidence; old postings may remain as extra candidates,
but current evidence is rechecked before any positive decision.

### Measured verification

220 tests pass, including14 actual FalkorDB integrations. New tests exercise
same-name/different-ID, renamed names/same ID, namespaces, type conflicts, untrusted
IDs, forged trust fields, grounding/authorization rejection, duplicates, bounded
candidate overflow, indexed actual plans, reconnect and dataset isolation.
`f_candidates_identity.json`:20 AI-authored development policy cases,6 expected
matches;6/6 positives,0 false positives,20/20 categories, candidate recall6/6.
These near-tautological specification checks are **not independent identity F1**.
Actual total1,801.354ms, traced Python peak is in the report, not server RSS/p95.
Name-only public products cannot be matched with this strict trust policy.
Public external evaluation remains separate; no invented human labels.

Six ledger-disabled100/1000/2000 CSV/JSON regressions and original three persistent
domain demonstrations were rerun. Exact final per-case timing is in
`evaluation/f_candidates_capacity.json`; no ledger-on2000 capacity claim.

## Increment2 — cluster consistency and correction

Not yet implemented at this checkpoint. Next: bounded indexed cluster membership,
negative constraints across the whole cluster, dry-run detection first, then
separate opt-in correction policy with atomic revision/invalidation and undo.
Ordinary location/employer/source disagreement must not trigger a split.

## Domain packs and remaining work

Domain packs/open-predicate registry are not implemented in this checkpoint.
They are optional after verified identity/detection increments. Independent public
identity accuracy, authoritative namespace calibration, complete legacy projection
migration, semantic recomputation, large mixed updates and enterprise load/security
certification remain open. Read-time card/history and candidate budgets remain
bounded; absence of candidates is not proof of different identity.

## Reproduction

```powershell
$env:UGI_TEST_REDIS_URL='redis://127.0.0.1:6380/0'
$env:UGI_ALLOW_PAID_CALLS='false'
python -m pytest -o addopts= -q
python -m ugi.eval_identity --output evaluation/my_identity_policy.json
python -m ugi.benchmark_conversion --output evaluation/my_capacity.json
```

REST additions: GET `/api/identity/candidates/{snapshot_id}`, GET
`/api/identity/compare?left=...&right=...`, POST `/api/identity/authority-observations`.
The latter's strict schema includes mention_snapshot_id, authority, identifiers,
idempotency_key and authorise_action. All use the existing tenant/dataset context.
Commit/actual hosted CI checkpoints are recorded after delivery verification,
not inferred from workflow text.
