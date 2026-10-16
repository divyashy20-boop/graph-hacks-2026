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

## Checkpoint status

Increment1 implemented; hosted CI and exact delivery SHA are recorded after push.
Open-text semantic registry/revisions and connector foundation are not claimed
implemented at this checkpoint. No enterprise-scale claim or paid service use.

## Windows reproduction

```powershell
$env:UGI_TEST_REDIS_URL='redis://127.0.0.1:6380/0'
python -m pytest -o addopts= -q
python -m ugi.demo_schema --execute --output evaluation/my_schema_demo.json
```

REST: POST/GET `/api/schema/packs`; POST `/api/uploads?pack_refs=<JSON list>`;
GET `/api/schema/assertions?definition_id=<immutable ID>`. The demonstration CLI
explicitly authorizes only its synthetic local schema/data writes.
