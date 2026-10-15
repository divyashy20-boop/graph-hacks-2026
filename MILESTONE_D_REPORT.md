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

Not yet completed in this increment. The suspected bottleneck is repeated
FOREACH/MERGE matching and many client-side identity/collision reads, not a claim
that FalkorDB cannot store2,000 records. The store remains unchanged for the first
commit. Profile and real-server correctness tests must precede any replacement;
five-second timeout remains unchanged. C1,000/2,000 timeouts remain the verified
capacity limitation until a subsequent measured result replaces them.

## Reproduction and delivery

From the repository root with its Python environment activated:

```powershell
$env:UGI_TEST_REDIS_URL='redis://127.0.0.1:6380/0'
$env:UGI_ALLOW_PAID_CALLS='false'
Remove-Item Env:UGI_OLLAMA_URL -ErrorAction SilentlyContinue
python -m pytest -o addopts= -q
python -m ugi.conversion_audit --fixture evaluation/c_development.json --output evaluation/d_extraction_local.json
python evaluation/recheck_d_metrics.py
python -m ugi.extraction_diagnosis --persisted-report evaluation/d_extraction_local.json --output evaluation/d_diagnosis_local.json
# Optional actual local model, never Bedrock:
$env:UGI_OLLAMA_URL='http://127.0.0.1:11434'
python -m ugi.conversion_audit --fixture evaluation/c_development.json --local-model qwen3:4b-instruct --limit 4 --output evaluation/d_qwen_local.json
```

These local checks were executed by the agent; no routine user action is needed.
Commit SHAs and actual hosted CI conclusions are recorded in the final handoff,
not inferred from the presence of a workflow file.
