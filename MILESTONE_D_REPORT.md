# Milestone D — controlled extraction and ingestion increments

Started October 16, 2026 (Asia/Calcutta) on verified C
`2a0a5df6add5816c9f8d6dd575b8f1ebb2d7ac6b`; working tree was clean, C work
preserved. Public/synthetic source licences remain in DATA_LICENSES. No paid
provider, unrelated AWS project, restricted dataset or user volume is involved.

## Increment 1: extraction diagnosis and measured improvement

C architecture: parse/chunk -> structured mapping or constrained sentence grammar
plus optional compact local-model proposal -> deterministic span/identity/scope
guards -> bounded semantic review -> deduplication -> type-scoped/document-local
identity resolution -> whole events/claims/evidence -> atomic store commit.
There was no separate NER model or independent truth-verification stage.

`d_failure_baseline.json` runs the C extractor loaded directly from the base Git
commit in a separate Python process, against the newly recorded unchanged-code
actual-Falkor baseline. No working file or source fixture is overwritten.
`d_failure_analysis.json` applies the same diagnostic to final offline outputs.

| Requested failure category | Baseline -> final offline observations |
|---|---|
| Entity not identified | Cannot isolate from proposal generation; no independent NER stage |
| Candidate never proposed | 12 -> 6 (binary11 ->5, whole event1 ->1) |
| Wrong subject/object | 0 observed; absent proposal does not expose its intended attachment |
| Wrong direction | 0 observed on these complete labels |
| Incorrect predicate | 0 offline; model probes show ontology/predicate disagreements |
| Lost qualifiers | 0 offline; first local probe exposed partial-quote history/date loss |
| Wrong evidence span | 0 accepted offline; actual model proposals with altered/absent surfaces rejected |
| False verifier rejection | 0 offline proposals; prior C preparing-for-launch rejection remains historical evidence |
| Unsafe acceptance | 0 complete-label offline disagreements, not an adjudicated hallucination rate |
| Accepted-to-graph failure | 0; actual reconnect payload/incidence checks agree |

Participant surfaces absent from offline proposals are a secondary diagnostic,
not an entity NER error estimate. Public organization/history still lose five
binary targets; research's entire four-role intersection event remains missed.
Partial finance/spatial and incomplete synthetic cases are not silently empty gold.

Changes in `ugi/clauses.py` and `ugi/extract.py`:

- Bounded occupation appositives recover explicit organization-role affiliations
  separately from main-clause tense. A former affiliation never makes present
  ownership historical. Known role vocabulary and exact syntactic scope only.
- Responsibility frames preserve contractor relationships, explicit action lists
  and preparation purpose, including negation/modality/history. Responsibility
  does not imply completed construction, ownership or dependency. Unknown clause
  attachment, OR, conditions, attributed tails and temporal suffixes fail closed.
- Local prompting gets bounded exact source surface/offset hints, not gold labels,
  guessed aliases or external knowledge. Deterministic checks still veto model
  underspecification. No spaCy/Stanza/transformer dependency was added: the measured
  bounded frame gain did not justify download, memory and licensing complexity.
- First real model probe exposed a short quote escaping full-sentence grammar
  and an explicitly dated occupation losing its interval. Verification now also
  checks a contained quote against its enclosing grammar frame without rewriting
  the quote. Dates are recovered only from a full exact pair-anchored quote with
  an immediately following explicit interval, never the first date of a paragraph.

Existing C appositive test expected exactly one main-clause candidate. It now
explicitly asserts the added former-affiliation candidate and unchanged main
clause; this is intentional additive coverage, not lowering an accuracy target.
Positive, conditional/negative, historical, responsibility-not-completion, partial
quote, exact-offset and unrelated-date regressions were added. An initial test run
was polluted by the host-only Ollama URL environment; the unchanged Docker-default
transport assertion passed after clearing that variable before tests.

### Same development corpus, actual persisted graph

All labels remain AI provisional and tuned development. No human review was
invented. The previously inspected C23 frozen set was not used to tune these
changes, is not fresh unseen data and still has no accuracy ground truth.

| Measure | Unchanged C baseline | D extraction final |
|---|---:|---:|
| Mixed binary TP / predictions / targets |4 /4 /15 |10 /10 /15 |
| Mixed precision / recall / F1 |100% /26.67% /42.11% |100% /66.67% /80% |
| Public-only complete binary |1 /1 /12 |7 /7 /12 |
| Public recall / F1 |8.33% /15.38% |58.33% /73.68% |
| Qualified-binary F1 |42.11% |80% |
| Participant-surface F1 (not NER) |45.71% |71.43% |
| Public whole event / roles |0/1;0/4 |0/1;0/4 |
| Emitted exact quotes, including unscored cases |5/5 |12/12 |

New public matches: one former-engineering affiliation and five contractor/action/
purpose responsibilities. These are general syntax patterns tested with different
names/actions, not source-entity or benchmark-answer lookups. The domain sample is
tiny (operations2/2, supply5/5; research, organization/history still weak), so no
unbiased domain ranking or universal performance claim follows.

Actual host `qwen3:4b-instruct`, identical first four public development texts:
baseline4 calls,1/1/9 exact binary,F1 20%; final5 calls,7/8/9,F1 **82.35%**.
Offline on those same texts7/7/9,F1 **87.5%**: no additional exact model recall;
one extra model label disagreement lowers exact precision to87.5%. Its occupation
is explicitly sourced but uses a predicate outside the provisional label ontology;
the reviewer is not an independent adjudicator. Temporal scope is now retained.
First probe6 calls,7/9/9,F1 77.78% is retained as `d_qwen_first_probe.json`, not
hidden. All15 actual calls are local; cloud billing$0, local compute unmeasured.
Per-case calls/tokens/reviews/timings and exact persisted claims are in reports.
No accuracy improvement from mocked providers is claimed.

Verification before graph-store changes: **186 tests passed (179 non-integration,
7 actual FalkorDB)**; prior20 synthetic22/24,F1 95.65%; B12 binary6/8,F1 85.71%,
4 events/14 roles; prior26 challenge17/18/25,F1 79.07%; UNKNOWN12/12. Reports:
`d_original_regression.json`, `d_legacy_regression.json`, `d_challenge_regression.json`.
Independent arithmetic: `python evaluation/recheck_d_metrics.py`. No UI redesign.

## Increment 2: safe graph-write profiling and optimization

Completed after recovering the interrupted working tree and saving a recoverable
ignored checkpoint. D1 was pushed as459b4a74de4487906b2865bba939db31f91e55f4;
[hosted CI passed](https://github.com/divyashy20-boop/graph-hacks-2026/actions/runs/38789810577).

### Diagnosis and bounded fix

Actual fresh100-record operator profiling shows60,200 pending records emitted
by each repeated endpoint lookup. Indexed scans exist; the bottleneck was not
simply a missing index. Eight pending scans across four edge kinds dominate the
write, becoming quadratic. The client also issued6,005 Cypher queries at1,000
records and12,005 at2,000. Document-scoped, lease-protected identity/name read
caches reduce those to3,008/6,008, with no cross-upload stale cache.

The new all-new-record writer binds created nodes and links deterministic sorted
node ordinals instead of repeatedly matching pending endpoints. Classification
and the one mutating query share the existing dataset lease, including nested
provider commits. No timeout increase, partial-document batch commits, schema
projection or provenance loss. Missing endpoints reject before mutation.

Direct UNWIND MERGE experiments failed real label/payload checks. A CREATE path
that still MERGEd endpoints passed correctness but large cases still timed out.
A combined new/persisted node pool passed fresh benchmarks but full regression
caught two `Invalid node id` failures. It is **not shipped**: any existing endpoint
selects the proven C writer. Large mixed/update documents retain the old capacity
limitation. The intermediate fresh-only `d_performance_write_only.json` does not
certify that rejected mixed path. All observations are retained, not best-run
cherry-picking.

[GRAPH.PROFILE](https://docs.falkordb.com/commands/graph.profile) actually executes
the write: profiles run only on another owned empty graph, not replayed on user
data. [GRAPH.EXPLAIN](https://docs.falkordb.com/commands/graph.explain) records the
plan without executing. All queries keep the existing
[TIMEOUT](https://docs.falkordb.com/commands/graph.query)5,000ms budget.

### Actual measured results

One traced observation per case, local Docker/Windows, not throughput/p95. Times
include client serialization, round trips and graph execution. The independent
capacity run overlapped an API image rebuild, so do not infer controlled speedup.

| Format / rows | Baseline ingest / write ms | Final profile ingest / write ms | Independent repeat ingest / write ms |
|---|---:|---:|---:|
| CSV100 |846.272 /290.714 |503.475 /97.064 |491.174 /94.517 |
| CSV1,000 |timeout /5,983.752 |4,131.120 /946.116 |4,292.938 /954.479 |
| CSV2,000 |timeout /7,066.450 |8,073.122 /1,936.444 |8,921.559 /2,061.497 |
| JSON100 |1,132.669 /345.165 |393.952 /92.228 |559.638 /121.803 |
| JSON1,000 |timeout /5,573.018 |4,119.243 /894.661 |5,092.526 /978.624 |
| JSON2,000 |timeout /6,125.509 |10,172.989 /1,910.951 |8,792.972 /1,922.482 |

Final profiles verify602/6,002/12,002 exact records and400/4,000/8,000 exact edges
at100/1,000/2,000 rows, both formats. Kind labels, payloads, provenance and incidence
all agree after reconnect. Client traced allocation peaks~2.8/28/56MB; client CPU
~203–219/2,031–2,266/4,469–4,750ms. Successful cumulative graph internal time
~13–14/131–134/270–281ms is not the complete wall time. Server CPU/RSS and failed
query internal time are not measured. Independent five-query medians13–18ms.

**191 tests passed (181 non-integration +10 actual FalkorDB)**. Runtime property-map
errors verify atomic rollback on both paths, including preservation of seeded
records. Concurrent same-ID writers, mixed references, link replay, whole-event
roles and binary evidence are covered. The first full run failed10 integrations
because Docker Desktop was down; services were restored without volume deletion,
then all191 passed. No failed tests are counted as skips or ignored.

The actual14-case audit retains10/10/15 and12/12 exact quotes with complete graph
incidence; three-domain demos pass with authorized idempotent actions and identity/
historical checks. Rebuilt packaged API is healthy. Controlled restart verification
compares every synthetic demo payload, edge and investigation ID before/after a
real graph/API restart (`d_restart.json`), not just counts. This is not crash or
backup testing. User graphs/volumes and unrelated AWS infrastructure are untouched.

## Reproduction and delivery

From the repository root with its Python environment activated:

```powershell
$env:UGI_TEST_REDIS_URL='redis://127.0.0.1:6380/0'
$env:UGI_ALLOW_PAID_CALLS='false'
Remove-Item Env:UGI_OLLAMA_URL -ErrorAction SilentlyContinue
python -m pytest -o addopts= -q
python -m ugi.conversion_audit --fixture evaluation/c_development.json --output evaluation/d_extraction_local.json
python evaluation/recheck_d_metrics.py
python -m ugi.profile_ingestion --output evaluation/d_profile_local.json
python -m ugi.benchmark_conversion --output evaluation/d_capacity_local.json
python -m ugi.demo --execute --dataset-prefix showcase-b --output evaluation/d_demo_local.json
# Controlled restart check, only after seeding these synthetic demo datasets:
python -m ugi.check_restart --snapshot .evaluation-local/d_restart_local.json
docker compose restart api graph
docker compose up -d --wait api graph
python -m ugi.check_restart --compare .evaluation-local/d_restart_local.json --output evaluation/d_restart_local.json
python -m ugi.extraction_diagnosis --persisted-report evaluation/d_extraction_local.json --output evaluation/d_diagnosis_local.json
# Optional actual local model, never Bedrock:
$env:UGI_OLLAMA_URL='http://127.0.0.1:11434'
python -m ugi.conversion_audit --fixture evaluation/c_development.json --local-model qwen3:4b-instruct --limit 4 --output evaluation/d_qwen_local.json
```

These local checks were executed by the agent; no routine user action is needed.
Commit SHAs and actual hosted CI conclusions are recorded in the final handoff,
not inferred from the presence of a workflow file.
