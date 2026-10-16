# Milestone G — versioned schemas and open interpretation

Baseline `5dc32149fe4443bb5dabe9f0c4c414fa9c58f30d` reproduced:231 tests,
including15 real FalkorDB. Local/remote main agreed and working tree was clean.
F's identity trust boundary, source IDs/evidence, quotas and no-paid-call defaults
remain. This is an incremental implementation, not a replacement graph engine.

## Increment1: declarative runtime

`ugi/schema.py` validates strict JSON/Pydantic schemas: namespace, semantic version,
schema version1, local entity types, predicate definitions, literal aliases, ordered
binary roles or repeated event roles/cardinalities, direction, qualifier policy,
up to4 explicitly hash-pinned dependencies and provenance. Unknown keys (including
code/queries/URLs) fail validation. No eval/import/template/regex supplied by packs,
file/network fetch or custom rule execution. No new dependency/database is added.
Optional structured field mappings are not implemented; existing triple/event
field names remain required. Packs cannot grant identity authority.

Pack hashes are SHA256 over UTF-8 sorted compact JSON **after schema defaults**.
Same namespace/version with different content rejects; new versions append.
DomainPack and PredicateDefinition records are immutable and dataset/tenant scoped.
Dependency definitions must already exist at their exact pinned hash. At most100
pack versions/dataset;40 predicates/pack,20 aliases/predicate,12 roles/predicate.
Registration requires process `UGI_SCHEMA_WRITES=true` plus explicit authorization
and existing tenant authentication. This prototype has no separate production
schema-admin RBAC: only trusted operators should have registration access.

Uploads optionally select up to4 refs using `pack_refs` (namespace/version/hash).
Accepted Claims/whole Events receive immutable SchemaBinding records in the **same
document write**, with original phrase, exact Evidence ID, definitions/pins and
shape diagnostics. Missing/ambiguous aliases stay UNRESOLVED; mismatched type/role
is INCOMPATIBLE, not a false claim that the uploaded source never asserted it.
Pack vocabulary is not universal semantic truth. No historical source is rewritten.
Duplicate source uploads require the same pins; silently reinterpreting old content
with a different pack version is refused. Explicit mapping revision is a later step.

Pack-bound assertions are deliberately excluded from legacy unqualified relationship
lookup and built-in path/rule inference. Query them using definition-scoped
`GET /api/schema/assertions?definition_id=...`, which uses the actual indexed
SchemaBinding.block_key. This avoids conflating IT/supply predicates with identical
names. Pack declarations do not authorize logical equivalence or any inference.
The existing dashboard reads their source assertions/events normally.

Bundled `ugi/packs/{it,supply,research}.json` are AI-authored synthetic CC0 example
vocabularies, all using the same Engine/RelationEvent/store. `ugi/demo_schema.py`
persists/reconnects typed IT binary, possible supply event and negated research
binary assertions. It is not a real-world language accuracy demonstration.

Local first full suite:247 passed, including16 actual FalkorDB; zero failed/skipped.
`evaluation/g1_schema_demo.json` records actual three-pack persistence/reconnect.
All six ledger-off capacity cases pass (`g1_capacity.json`);2k CSV/JSON ingest
5,960.134/5,964.384ms and writes1,545.664/1,528.872ms. These are local single
observations, not p95 or pack/identity-enabled2k capacity measurements.
New tests cover unsafe fields/versions, aliases/roles, pins/version conflicts,
dependency types, namespace ambiguity, tenant gates, exact evidence, no inference
leakage, actual indexed lookup, immutable records, reconnect and genuine late
server-side property-map rollback. The initial sandboxed TestClient-only process
stalled and was stopped; the full authorized localhost test run passed. No tests
were counted as skips. Existing TestClient warning remains.

## Research choices

[EDC](https://aclanthology.org/2024.emnlp-main.548/) motivates separating extraction,
definition and canonicalization; this implementation does not reproduce its model
or benchmark. [ReVerb](https://aclanthology.org/D11-1142/) and
[OpenIE6](https://aclanthology.org/2020.emnlp-main.306/) motivate literal relation
surfaces and coordination safety, not an installed learned extractor.
[SKOS](https://www.w3.org/TR/skos-reference/) distinguishes close mappings from
strong equivalence; [SHACL](https://www.w3.org/TR/shacl/) motivates shape validation
separate from truth. CESI, AutoSchemaKG, iText2KG, GraphRAG/LightRAG, FrameNet,
PropBank, Wikidata and schema.org are comparative design references, not imported
engines or reproduced results. No embedding/LLM similarity is treated as proof.

## Increment1 checkpoint (verified before increment2)

Increment1 `8c09924783e82f350c233baeb7d87506da7ceff3` was pushed and its
[hosted CI succeeded](https://github.com/divyashy20-boop/graph-hacks-2026/actions/runs/38865674421)
before increment2 began. The following supersedes its historical boundaries.

## Increment2: recovery and exact implementation

Usage limits interrupted final verification, not a successful push. Recovered11
modified tracked +11 untracked files at8c09924, copied all22 into ignored
`.evaluation-local/checkpoint-g2-20261016-recovery`, and continued without reset,
clean or overwrites. Recovery rerun258 passed; final264 pass:247 non-integration
+17 actual graph,0 failed/skipped. Prior257 result was treated as provisional.

`ugi/open_relations.py` is **opt-in bounded literal grammar**, not a trained OpenIE
model. It supports capitalized/quoted named surfaces, literal lowercase binary
phrases up to80 characters/10 words and enumerated temporal/cancellation tails.
An unfamiliar binary verb needs no verb-specific handler. Limits:60 inspected
sentences/60 binaries/12 events per chunk; clauses over1200 characters, unresolved
pronouns, ambiguous coordination, conditions and attribution abstain or retain the
existing review path. General prose/coreference remains unsupported.

`extract.py`, `nary.py` and `engine.py` integrate exact grounding and enclosing
sentence checks: shortened quotes cannot hide extra participants, conditions or
qualifiers. Original phrase, quote/offsets, polarity/modality and explicit dates
remain. Amounts/cancellation are literal binding qualifiers, not completed deals.
Optional SourceAttribution metadata retains public URL/title/locator/licence in
the source transaction; it performs no fetch/authentication and grants no trust.
The model provider is unchanged. No actual model/paid call occurred in G2.

Registry representation: immutable `PredicateDefinition`, immutable `SchemaBinding`,
mutable `SchemaBindingHead`, immutable `SchemaMappingRevision`. No separate DB.
Unmatched grounded phrases get deterministic namespace/surface/role-type hash IDs
and version1.0.0 literal definitions labelled PROVISIONAL. Repeated normalized
literal phrases with the same roles/types reuse definitions. Individual original
wordings/source examples/evidence/pins remain in bindings, not unbounded arrays
on definitions. These are conservative literal descriptions, not learned senses.

Only exact operator-declared names/aliases with compatible roles/types produce
KNOWN_COMPATIBLE. Ambiguous aliases or attempted/planned/proposed modifiers cannot
authorize equivalence: POSSIBLE_ALIAS retains its own provisional definition;
unmatched phrases are PROVISIONAL_NEW; shape mismatches are INCOMPATIBLE.
Similarity search/calibrated probabilities/frequency promotion are not implemented.
Per assertion, at most4 packs ×40 predicates are inspected, candidate IDs capped8;
new-definition reads are cached within the document. Source, definitions, bindings
and heads share the existing single atomic write. Pack text cannot execute code.

Schema-bound assertions remain excluded from legacy unqualified direct lookup and
built-in rule/path inference. Definition-scoped reads report separate interpretation
state, SOURCE_ASSERTED/SOURCE_NEGATED, or UNKNOWN with qualified_source=true for
non-asserted modality. The original qualifiers remain. Source assertion is not
independent truth; core HYPOTHESIS/CONNECTED_ONLY/CONTRADICTED semantics remain.

## Mapping history and group semantics

POST `/api/schema/revisions` requires operator schema_writes, tenant credentials,
explicit authorization, assertion ID, expected binding ID, pinned refs and reason/
idempotency key. New interpretations never rewrite original Claim/Event/Evidence.
Compensating undo refuses later/unrelated heads; exact replay is idempotent and
changed requests conflict. History cap100/assertion, record quota unchanged.
Definition reads show historical current/noncurrent bindings and current_binding_id.
G1 records lacking heads remain readable. Different source pins still cannot be
silently replayed; mapping revision does not rerun extraction or change original pins.

No schema-dependent artifact registration/invalidation or recomputation worker is
implemented. Clients must compare exact consumed binding IDs/current heads before
reuse. This is not automatic semantic reevaluation. F's identity staleness remains
separate and unchanged. No cross-domain bridge activates generated rules.

Collective collaborated/partnered-with frames retain left collaborators, right
partners and project in one event. Research frames retain every researcher/topic
and optional institution. Respectively handles equal2–6 lists for acquired/bought/
purchased, emitting aligned pairs only; unequal/unclear lists abstain. These are
specific coordination frames, not general language understanding. No Cartesian
product, unsupported BETWEEN projection or event-to-binary rule is added.

## Reproduced evaluation and limitations

- `g2_development_final.json`:12 AI-authored development cases, binary TP/predicted/
  targets4/4/8 off versus8/8/8 on; actual whole role sets0/2 ->2/2. All12 event-case
  comparisons include10 empty controls, not12 extracted events. Exact emitted
  quotations pass. These tuned specification cases are not independent human gold.
- `g_public_sources_v1.json` freezes the original32 FewRel texts, classification
  notes/hashes and CC BY-SA4.0 attribution. Archive hash pinned. Selection hash
  `c093a5468439a7b9a4aa3c84e694de2f2e88bdc1c52cea5ae2b6525ef2af571c`
  agrees with the initial interrupted run; prior seed17_128 and260 recorded text
  fields were excluded before sampling. No article-level independence proof.
- `g2_public_final.json`:both modes0 claims/0 events,0/32 directed-pair hits,
  32 abstentions,0 emitted quotes (quote accuracy undefined, not100%). Exact semantic
  binary/event, missing-relation, unsupported-prediction, canonicalization and
  qualifier scores are null/unscored: no complete independent source-entailment
  annotations. No F1/correct-abstention claim. Observed aggregate ingest139.213/
  131.859ms off/on, model calls0. Now inspected, not unseen for future tuning.
- `g2_novel_public_clause.json`:source-selected NASA/JPL “NACA evolved into NASA”
  registers provisionally, persists/reconnects and is queryable without adding a
  phrase-specific rule. It was absent from development/extraction code. This was
  convenience-selected from a primary source after code existed, not blind human
  adjudication. Input is an exact clause, not the whole sentence. Full context is
  retained in attribution and separately tested:full-context0 claims, clause1.
  No date, verified identity equality or full-document understanding is implied.
- `evaluation/recheck_g_metrics.py` recalculates arithmetic and source-selection
  correspondence without UGI/scorer imports. It does not adjudicate semantic truth.

Actual tests cover indexed retrieval, exact quote/roles, mapping add/undo/reconnect/
history, immutability, duplicate uploads, API/tenant gates and a genuine late
property-map failure rolling back definitions/binding/head/revision together.
No integration was silently skipped. Earlier review failure was a usage limit,
not permission to bypass review. One import-order lint issue fixed; existing
Starlette TestClient deprecation remains. No large dependency or UI redesign.

## Measured overhead, regressions and persistence

`g2_performance_final.json`:single traced local observations, identity ledger off.

| Rows | Off/on ingest Cypher queries | Off/on write ms | On ingest ms | On Python peak | On registry read ms |
|---|---:|---:|---:|---:|---:|
|10|65/67|11.713/13.425|75.023|455,677 bytes|16.600|
|30|185/187|24.866/29.586|244.515|1,291,188 bytes|47.506|
|80|485/487|63.583/78.081|976.350|3,368,924 bytes|120.859|

Pack parsing~0.04ms, registration~3.6–5.4ms; literal extraction on~0.66/1.80/3.62ms.
One repeated phrase yields one definition plus binding/head per assertion. Exact
records65/185/485 off versus86/246/646 on; same31/91/241 edges. Full reconnected
payload/label/incidence checks pass. Ingest query counts exclude later diagnostic
reads. Registry read includes bounded per-result assertion/head/evidence fetches,
not just index latency. Warm-up/noise means lower on-wall times are not a speedup
claim. Original first g2_performance.json retained. No p95/server RSS/large-scale claim.

All six **schema/ledger-disabled fresh** CSV/JSON100/1000/2000 cases pass again:
`g2_capacity.json`,2k ingest6,154.524/6,048.374ms, write1,637.816/1,562.561ms.
Per-query budget stays5s; total ingest can be longer. This is not2k feature-on or
large mixed-update certification. Three existing persistent agent demos pass.
Historical extraction remains10/10/15,F1 80%, public7/7/12,F1 73.68% on older tuned
provisional labels, not new independent accuracy; its research event remains missed.
F regressions retain6/6 constructed matches,4/4 conflicts,2/2 defensible splits/
reversals. F public identity remains12/12 candidates,0/12 approved without trusted IDs.

`g2_schema_demo_final.json` persists three packs, unfamiliar/cancelled/research/
collective/respectively cases, forged-ID abstention and mapping withdraw/undo.
Eight old/new seeded datasets retain exact payload/edge fingerprints across a real
API+graph restart (`g2_restart.json`), not just counts. Not crash/backup certification.
Rebuilt API ready; normal container provider offline, paid/schema writes/open
discovery/identity auto apply false. No graph/volume deletion or unrelated AWS change.

## Rejected shortcuts and remaining work

Rejected: arbitrary structured strings as proof of prose discovery; similarity as
equivalence; frequency as validation; schema as inference authorization; group
pairwise expansion; invented human labels; public post-hoc accuracy tuning; large
model installation without measured need. Optional actual local-model comparison
was deferred; zero new model calls, not a model-performance improvement claim.

Unimplemented: optional field mappings, learned semantic senses/alias search,
unrestricted prose/coreference, authenticated identity connectors, production
schema-admin RBAC, schema artifact workers, semantic recomputation, automatic
cross-domain rule induction and broad security/load certification. Connector
increment was not started during recovery. Next: separately design the secure
connector foundation and independently reviewed open-relation corpus; never weaken
F trust merely to improve recall.

## Windows reproduction

```powershell
$env:UGI_TEST_REDIS_URL='redis://127.0.0.1:6380/0'
python -m pytest -o addopts= -q
python -m ugi.demo_schema --execute --output evaluation/my_schema_demo.json
python -m ugi.eval_schema --output evaluation/my_open_development.json
python -m ugi.eval_schema_public --download --output evaluation/my_open_public.json
python -m ugi.probe_new_predicate --execute --output evaluation/my_public_clause.json
python -m ugi.benchmark_schema --output evaluation/my_schema_profile.json
python evaluation/recheck_g_metrics.py
python -m ugi.benchmark_conversion --sizes 100 1000 2000 --output evaluation/my_capacity.json
```

REST: POST/GET `/api/schema/packs`; POST `/api/uploads?pack_refs=<JSON list>`;
GET `/api/schema/assertions?definition_id=<immutable ID>`. The demonstration CLI
explicitly authorizes only its synthetic local schema/data writes.
Additional REST: GET `/api/schema/predicates`, POST `/api/schema/revisions`.
Select a definition ID, then use `/api/schema/assertions?definition_id=<ID>`;
check state/current flag and original evidence/qualifiers. Future uploads opt in
with `UGI_OPEN_PREDICATES=true`; pack writes/revisions additionally require
`UGI_SCHEMA_WRITES=true`. Keep both off for legacy behavior. No source grants
tool/connector/identity authority. Final SHA and actual CI are recorded after push.
