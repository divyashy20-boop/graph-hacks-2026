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
Profiles retain at most20 aliases plus the mention name; alias truncation makes
retrieval incomplete and vetoes automatic growth. Opaque identifier values reject
blank/surrounding whitespace rather than guessing normalization. Structured
identity evidence must be a bounded list (at most100 entries).

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

Implemented after increment1c77a5a0d72fd2c71a6b8ed3f975700bc8032630e and its
[successful hosted CI](https://github.com/divyashy20-boop/graph-hacks-2026/actions/runs/38838921392).
`IdentityCluster` immutable membership universes plus indexed assignment.cluster_id
lookups establish bounded coverage, not a global scan. Moved members remain in
history; current heads must agree with the universe. Legacy/unindexed or >50-member
clusters report INCOMPLETE and cannot be automatically corrected. There is no
silent legacy backfill. Indexed plans are checked on the real pinned graph image.

Whole-cluster analysis checks up to1,225 pairs (50 members), caching observations,
evidence and misses within the operation. It does not compare every entity with
every card. SAME connected components are only proposals: a negative constraint
inside a transitive component (A≈B≈C but A≠C) vetoes automatic interpretation.
Unknown within/cross-group edges and internally conflicting evidence prevent a
definitive partition. For automatic splits, cross-group differences need approved
exclusive identifier conflicts; declared source types alone can flag inconsistency
but **cannot authorize an automatic split**. Address/employer/source disagreement
is not an exclusive identity constraint. Name similarity never authorizes merging.

Automatic merges require every pair across complete bounded candidate clusters to
have compatible SAME evidence. Automatic partitions require all within-group pairs
SAME and all cross-group pairs justified DIFFERENT. Otherwise the cluster is flagged
INCONSISTENT/UNRESOLVED without a forced split. Candidate overflow also vetoes growth.

Default remains detection-only. Separate `UGI_IDENTITY_AUTO_APPLY=true` authorizes
only the identity overlay under the configured policy; it requires resolver/ledger
opt-in. New authorized authority observations trigger the policy automatically.
No routine review confirmation is needed. Dry runs persist explainable IdentityRun
proposals, not assignment changes. The GET cluster endpoint is read-only.

Applied corrections stage immutable IdentityRevision, replacement heads, membership
universes and exact dependent stale notices **with the new evidence in one atomic
graph write**. No original Claim/Event/Evidence/Mention/Card is changed. Compensating
undo uses the existing authorization/stale-head guards; another authority observation
will reconsider the restored inconsistent projection. Reversal never clears an
artifact's stale status without a new evaluation. Unregistered outputs/implicit
dependencies are not tracked. No semantic re-evaluation worker is implemented.

### Actual verification and performance

**231 tests pass:216 non-integration +15 real FalkorDB**, zero failed/skipped.
Real tests verify candidate/cluster Index Scan, namespace evidence, automatic
partition and selective staleness, undo/recheck, complete n-ary role/evidence
preservation, reconnect and a genuine late server-side property-map failure.
That failure occurs after staging evidence/heads/revision/notices; every payload
is unchanged afterward. An earlier run failed5 real tests because Docker Desktop's
engine was stopped (missing pipe/connection refused); services were restored
without deleting volumes, then all tests passed. A test-import lint issue was fixed.

`f_policy_identity_final.json`:20 AI-provisional development cases,6/6 positive
decisions and overlays,0/14 false merges,8/8 expected abstentions,20/20 categories.
`f_cluster_evaluation_final.json`:6 deliberately constructed policy clusters,
4/4 inconsistencies detected,0/2 false alarms,2/2 defensible splits,0/4 false splits,
2/2 reversals and6/6 artifact/payload preservation cases. Ambiguous ABC/unknown
clusters are flagged, not arbitrarily partitioned. These are specification tests,
**not independent detection precision/recall or real-world split accuracy**.
Recorded actual graph runs include both detection-only and explicitly enabled
automatic correction (`f_dryrun_demo.json`, `f_autonomous_demo.json`). Each preserves
24 original payloads, with only the apply demo's registered dependent artifact
becoming stale; the unrelated output remains unchanged. The legacy namespace
assertion is deliberately incorrect in the demo; later registry evidence arrives
as an authorized observation over source identifiers already present, not a
claimed external registry scrape or a new real-world corporate event.

Actual bounded resolver overhead (`f_resolution_performance.json`):

| Rows / mentions | Ingest / write ms | Ingest Cypher queries | Candidate wall ms / count | Python allocation peak |
|---|---:|---:|---:|---:|
|10 /20 |131.561 /28.691 |134 |1.984 /9 complete |1,121,239 bytes |
|30 /60 |591.849 /99.333 |639 |2.430 /20 incomplete |4,572,006 bytes |
|80 /160 |1,861.998 /307.247 |2,039 |2.250 /20 incomplete |14,133,705 bytes |

Card reconstruction18.964/46.592/140.226ms; singleton cluster checks~6ms. These
are single traced local observations, not large-cluster throughput/p95, server
CPU/RSS or million-record capacity. Candidate pressure intentionally overflows
20 at30/80 rows and prevents auto merge. Six ledger-off chain sizes still pass;
2,000 CSV/JSON ingest6,056.548/6,210.637ms, writes1,678.922/1,539.527ms in the final
repeat. Five-second per-query budget unchanged; total ingest is longer than5s.
Original development extraction remains10/10/15,F1 80%, public7/7/12,F1 73.68%;
these are prior tuned provisional labels, not an identity accuracy improvement.
All six seeded old/new demo datasets retain exact record/edge hashes across an
actual API+graph restart (`f_restart.json`). This is not crash/backup certification.

## Independent public diagnostic and split integrity

[T2D correspondences](https://webdatacommons.org/webtables/goldstandard.html) were
selected because their row-to-DBpedia correspondences were human generated and
the correspondences are Apache2.0 licensed. Only the447,665-byte correspondence
archive is downloaded locally; no Web tables or DBpedia dump is redistributed.
Archive SHA256 is pinned in the adapter:
`1a1c64113d0eb6054bc567a73af89947165cb2a1085290ad3eed20ead3c2cbfa`.
The already inspected first-table preview is excluded. Fixed seed20261016 samples
12 positive URI groups across different tables and12 different-group negatives.
The gold URI field is used only for selection/grading; the resolver receives row
surfaces and opaque row IDs, no trusted identifiers, URIs or match labels.

`f_public_t2d_frozen.json`:24 row-pairs/24 records,12 gold matches; matching candidate
recall12/12 **within this small pool**,0 approved matches,0 false merges, recall0,
F1 0, missed-match rate100%, precision **undefined**,24 abstentions. Do not call
all abstentions correct or interpret zero false merges as useful real-world recall.
This reveals the strict matcher's limitation without independently trusted evidence.
It is a derived pair probe, not the full T2D entity-linking benchmark. No matching
rule was tuned to these outputs. These sources are now inspected; future tuning
must not describe them as unseen. Downloads remain ignored; reports retain row
hashes/labels but not source surfaces or gold URI strings. No human review invented.

Synthetic pair/cluster fixtures are separate development files and retain explicit
AI-provisional provenance. `evaluation/recheck_f_metrics.py` recomputes counts and
partition comparisons without importing engine/resolver/scorer helpers; it verifies
arithmetic/fixture consistency, not annotation truth or authority trustworthiness.

## Domain packs and remaining work

The optional third increment (domain packs/open-predicate registry) is deliberately
deferred to keep the two priority increments coherent and tested, as permitted in
the request. General open-text identity recognition remains unresolved: no learned
name/context scorer, externally authenticated registry connector or calibrated
identity probability exists. Public positive recall is zero in the name-only probe.
Complete legacy migration, semantic recomputation, large mixed updates and enterprise
load/security certification remain open. No old Claim endpoint is automatically
repaired; all overlays remain excluded from definitive inference.

## Reproduction

```powershell
$env:UGI_TEST_REDIS_URL='redis://127.0.0.1:6380/0'
$env:UGI_ALLOW_PAID_CALLS='false'
python -m pytest -o addopts= -q
python -m ugi.eval_identity --output evaluation/my_identity_policy.json
python -m ugi.eval_identity --auto-apply --output evaluation/my_identity_apply.json
python -m ugi.eval_identity_clusters --output evaluation/my_clusters.json
python -m ugi.eval_identity_public --download --output evaluation/my_public_probe.json
python -m ugi.benchmark_resolution --output evaluation/my_resolution_profile.json
python -m ugi.demo_identity_policy --execute --output evaluation/my_dryrun.json
python -m ugi.demo_identity_policy --execute --apply --output evaluation/my_apply_demo.json
python evaluation/recheck_f_metrics.py
python -m ugi.benchmark_conversion --output evaluation/my_capacity.json
```

REST additions: GET `/api/identity/candidates/{snapshot_id}`, GET
`/api/identity/compare?left=...&right=...`, POST `/api/identity/authority-observations`.
The latter's strict schema includes mention_snapshot_id, authority, identifiers,
idempotency_key and authorise_action. All use the existing tenant/dataset context.
Commit/actual hosted CI checkpoints are recorded after delivery verification,
not inferred from workflow text.

Read-only cluster audit: GET `/api/identity/clusters/{snapshot_id}`. There is no
public arbitrary partition/Cypher endpoint. Normal API defaults keep automation
off; demonstration CLIs explicitly authorize only their synthetic local writes.
Next technical decision: implement an authenticated authority connector/namespace
lifecycle before broadening weak name/context matching; names/LLM similarity alone
must not be promoted just to improve recall.
