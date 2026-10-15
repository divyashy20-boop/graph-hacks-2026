# Universal Graph Intelligence (UGI)

An **event-time Graph Hacks 2026 Track 1 implementation** of a multi-format, evidence-grounded graph converter and dependency-investigation agent. FalkorDB is the persistent graph database. A deterministic policy can trace service dependencies and create real investigation/review records. An optional AWS Bedrock provider handles model-assisted extraction and hypothesis proposal behind strict opt-in.

**Status:** functional local prototype and demo, **not production-ready**. This repository contains a code-first implementation and a small synthetic evaluation, not a proven universally accurate graph extractor.

## Milestone C: measured conversion quality, not universal accuracy

**169 tests passed locally: 162 unit/API/provider/MCP + 7 actual FalkorDB tests.**
The new audit exercises extraction, persistent records, reconnected retrieval
and graph incidence. Actual Ollama/Qwen and a text-PDF smoke ran locally;
cloud/paid services remain disabled. All prior work and user graph volumes were
preserved. See [CONVERTER_AUDIT](CONVERTER_AUDIT.md) for reproduction commands,
domain failures, source attribution and the capability/readiness matrix.

Important quality gate results:

- Mixed **provisional development** binary F1 improved 22.22% -> 42.11%, but the
  public-only complete subset recovered just **1/12 targets**, F1 **15.38%**.
  These AI-authored labels are not independently adjudicated human truth.
- All 23 frozen public cases remain unreviewed: **no semantic accuracy/F1 claim**.
- Latest actual four-source Qwen probe: 5 calls, 3 accepted claims, 1 exact
  predicate match; no extra exact recall over rules, lower exact precision.
- 100-record CSV/JSON persistence, repeat and two-hop checks passed. Both
  1,000/2,000-record formats **timed out** under current graph budgets despite
  fitting upload quotas; existing data was preserved in the tested rollback case.
  The 2,000-record quota is a validation ceiling, not demonstrated capacity.
- Three structured synthetic demonstrations remain working. They do not establish
  general public-document conversion quality. No UI redesign was made in C.

[TEST_REPORT](TEST_REPORT.md), [WORK_LOG](WORK_LOG.md),
[human annotation workflow](evaluation/ANNOTATION_GUIDE.md),
[data licences](DATA_LICENSES.md). Human adjudication and scalable atomic writes
remain follow-ups; do not present this prototype as production-ready.

## Milestone B: recovered, measured, demonstrable (historical)

The interrupted work was preserved and completed on October 15. The dashboard
now has an interactive evidence graph, role-labelled whole events, historical
filter, exact-source inspector, labelled conclusions and explicitly authorized
persistent investigations/review tasks. Counts and traces come from the backend,
not display-only examples. Changing dataset/date clears action authorization.

**Local verification: 130 passed (126 unit/API/provider/MCP + 4 real FalkorDB
integration tests), no failures/skips.** Docker API and graph rebuilt/healthy;
incident, supply and research/identity demos ran on the real persistent graph.
See [TEST_REPORT](TEST_REPORT.md), [WORK_LOG](WORK_LOG.md) and the
[three-minute demonstration guide](DEMO_GUIDE.md).

```powershell
# Repository root; Docker Desktop running, app/test dependencies installed
docker compose up --build -d
python -m ugi.demo --execute --dataset-prefix showcase-b --output evaluation/showcase_local.json
# Open http://localhost:8001 and choose a seeded demonstration
$env:UGI_TEST_REDIS_URL='redis://127.0.0.1:6380/0'
python -m pytest -o addopts= -q
python -m ugi.eval_intelligence --fixture evaluation/intelligence_eval.json --development evaluation/intelligence_dev.json --output evaluation/intelligence_local.json
```

`--execute` authorizes local investigation writes. The seed command uses the
no-key local tenant; configured API-key tenants must ingest their own sources.
No cloud model calls are needed. Do not remove the Docker volume to update.

The frozen **AI-authored provisional** 12-passage evaluation recovered 6/8
binary relations: precision 100%, recall 75%, F1 **85.71%**; 4/4 whole events and
14/14 participant roles. Independent recalculation from labels/predictions
confirmed the arithmetic, **not the truth of the labels**. Two complex prose
relations were missed. Similar grammar templates and tiny samples limit
generalization. Exact quote matches (10/10) establish provenance, not truth.

Actual local Qwen development probes reduced the document-review rate from
50% to 25% after date recovery/deduplication; extraction F1 was unchanged, with
rules already covering these examples. Four new public FewRel sentences used
five local calls and yielded **zero accepted relations**. Their source-entailment
labels are unreviewed, so no public F1 is claimed. The broader prior 128-source
offline diagnostic also remains poor (0/128 target pairs). See the
[annotation protocol](evaluation/ANNOTATION_GUIDE.md) to prepare 24 fresh public
sources and complete independent human adjudication. Paid Bedrock/AWS and any
public hosting remain disabled/unverified; this is not production readiness.

## What is included

- CSV, JSON, JSONL, TXT and text-based PDF ingestion, with source/chunk locations and size limits.
- Open-text rule extraction + explicit structured-triple extraction; optional Bedrock-assisted extraction and model review.
- Conservative entity IDs: explicit IDs or document-local IDs. Collisions across documents remain ambiguous instead of automatically merging.
- Exact source-backed Claim/Evidence records, qualifiers, historical intervals, polarity and hypotheses.
- `SOURCE_ASSERTED`, `SOURCE_NEGATED`, `RULE_DERIVED`, `CONNECTED_ONLY`, `HYPOTHESIS`, `CONTRADICTED`, `UNKNOWN` status vocabulary.
- FalkorDB Cypher-backed storage, bounded traversals and a persistent, opt-in incident investigation action.
- Browser UI, FastAPI endpoints and four **application-specific MCP tools** over stdio.
- Synthetic cross-domain demo and evaluation fixtures.

## Quick start: Docker Desktop (Windows/Linux/macOS)

Use the **repository root** (the directory containing `ugi/` and `compose.yaml`). Ensure Docker Desktop is running.

```bash
cd graph-hacks-2026
# optionally configure local-only access keys in .env; never commit the real file
cp .env.example .env
# For a demo shared beyond your own machine, set a strong UGI_API_KEYS and use HTTPS + a reverse proxy.
docker compose up --build -d
docker compose ps
```

Open **http://localhost:8001/**. Docker Compose only binds the API and graph ports to `127.0.0.1`. The FalkorDB development UI, if provided by the image, is bound at http://localhost:3001/.

Upload `demo/incident.json`, investigate `Cache`, and inspect the saved review tasks. Next upload `demo/supply_chain.csv` or `demo/open_text.txt` using a **different dataset name** for a second-domain demonstration. The stored graph persists across service restarts via the Docker volume.

Local-only debugging (requires an installed Redis Python driver and a running FalkorDB):

```bash
python -m pip install -e '.[test]'
export UGI_REDIS_URL='redis://127.0.0.1:6380/0'
uvicorn ugi.api:app --host 127.0.0.1 --port 8000
```

On PowerShell, replace `export` with `$env:UGI_REDIS_URL='redis://127.0.0.1:6380/0'`.

### Reproducible tests

```bash
python -m pip install -e '.[test]'
python -m pytest -q
# With the local Docker graph running:
export UGI_TEST_REDIS_URL='redis://127.0.0.1:6380/0'
python -m pytest -q -m integration
python -m ugi.evaluate --output evaluation/my_report.json
```

### Continuous integration (GitHub Actions)

The workflow [Verify UGI](.github/workflows/verify.yml) is configured for pushes to `main`, pull requests, and manual dispatch. It installs the app, runs unit/API/MCP checks, starts an **actual isolated FalkorDB Docker container**, runs `tests/test_integration.py` and `tests/test_http_integration.py` against it, and runs the small offline fixture. Bedrock and paid calls are disabled. **A workflow file existing does not prove a successful run**; inspect the [Actions tab](https://github.com/divyashy20-boop/graph-hacks-2026/actions) for evidence.

`tests/test_http_integration.py` covers HTTP upload, two-hop relation evidence, persisted investigation, review decision after a new API instance, and tenant isolation using a randomly namespaced test graph. It safely cleans up only its own test graphs.

If GitHub Actions has been disabled for your repository, enable it under GitHub repository **Settings → Actions → General**; then open the Actions tab and run **Verify UGI (unit + real FalkorDB)** with **Run workflow**.

### Keeping your Windows checkout in sync

This repository receives changes from both GitHub and local Windows PowerShell. Before the next local commit, from this repository's folder run:

```powershell
git status --short
git pull --ff-only origin main
docker compose up --build -d
```

If `git status --short` shows modified files, **do not force pull** or overwrite local work; commit or stash those edits first. After local changes have passed tests: `git add .`, inspect `git status --short` for secrets, `git commit -m "..." `, then `git push`. Never commit `.env`, credentials, or actual private data.

The 20-passage evaluation contains AI-assisted synthetic ground truth from two domains; do not represent its scores as production accuracy. The three offline extraction variants deliberately share the same candidates; no live-model comparison is implied.

### Evidence-aware multi-hop inference example

Upload `demo/shared_employer.json` into a fresh dataset (such as `people`), then submit:

```json
{"subject":"Alice","object":"Bob","predicate":"SHARES_EMPLOYER","as_of":"2021-06-01"}
```

The expected `RULE_DERIVED` response includes rule `shared_employer_temporal_overlap_v1`, two exact source-backed employment claims, and the connecting graph path. The same identities with `FRIENDS_WITH` return **CONNECTED_ONLY**, not proof of friendship. Asking `SHARES_EMPLOYER` for `2023-06-01` returns **UNKNOWN** because Alice's supplied employment ends in 2022. Undated employment records **do not** establish overlapping dated employment. These are deductions about what the uploaded sources assert, not external employment verification.

Entity identifiers are now **scoped by entity type**: a person and an organisation with the same external ID remain separate nodes. Previously stored untyped IDs are reused when their existing declared type matches, avoiding unnecessary duplicate entities during local upgrades. Conflicting types are never automatically merged.

The verifier also now separates contradictory grammar for the **same entity pair** (still rejected) from an **unrelated, unparsed clause** in the evidence passage (eligible for opt-in LLM review). This reduces false rejections without removing the deterministic contradiction guard. The offline parser remains conservative; no universal extraction accuracy claim is made.

## Reality check: independent text evaluation

Two separate offline extraction diagnostics now run automatically in GitHub Actions, with per-sample JSON reports retained as workflow artifacts:

```bash
python -m ugi.eval_challenge --output /tmp/challenge.json
python -m ugi.eval_fewrel --download --limit 128 --seed 17 --output /tmp/fewrel.json
```

**Synthetic challenge:** 26 new, AI-assisted examples spanning operations, people, finance, retail, science and supply; labels were written before the evaluation code was used. This is distinct from the earlier 20-example development fixture but **is not a human-adjudicated external dataset**. Baseline offline score: 17/25 expected relations recovered, 19 predictions, 89.5% precision / 68.0% recall / **77.3% F1**, with all 5 intentionally empty cases correctly abstaining. The exact-quote provenance check passed 19/19; that check measures span correctness, **not semantic entailment**. Do not conflate this new F1 with the earlier fixture's 95.7%.

**External FewRel validation:** the repository downloads (does not redistribute) the upstream Wikipedia-derived, human-annotated FewRel `val_wiki.json` file from [thunlp/FewRel](https://github.com/thunlp/FewRel). Fixed-seed sample: 128 examples from 16 Wikidata relation classes; the input includes head/tail entity surfaces but those labels **are used only to grade the result, not provided to the extractor**. The current offline grammar produced **0/128 matching directed head/tail pairs** (and one unrelated extracted claim); source head/tail strings both occurred in 120/128 reconstructed sentences. The benchmark **does not calculate relation-label F1**, because Wikidata PID classes cannot be directly compared against the app's open predicates. It reveals the grammar's severe limits on ordinary natural Wikipedia prose, not an alleged failure of an LLM. This is a public validation set, not FewRel's hidden test set.

For a private externally annotated JSON benchmark, supply the same `evaluation/challenge_v1.json` schema and run `python -m ugi.eval_challenge --fixture path/to/annotations.json --output results.json`. Never report a tuned development set as unbiased accuracy. Independent human adjudication and genuine model-based testing remain outstanding.

## Optional local Ollama extraction (zero cloud API billing)

UGI has an **opt-in local Ollama provider**, separate from AWS Bedrock. It sends source text only to the explicitly configured local Ollama server, requests schema-constrained JSON, and subjects candidates to exact-span, directional, polarity, temporal and semantic checks. Mock transport tests and actual Windows Qwen probes were run. Model approval is fallible and not independent truth verification; no consistent public-prose quality gain has been established. See the Milestone C audit for accepted/rejected claims and limitations.

To experiment on your own Windows computer:

1. Install [Ollama for Windows](https://ollama.com/download/windows). In a new PowerShell, run `ollama pull qwen3:4b-instruct` and verify `ollama list` and `http://127.0.0.1:11434/api/tags`.
2. In your local **untracked** `.env`, set `UGI_PROVIDER=ollama`, `UGI_MODEL_ID=qwen3:4b-instruct` and `UGI_OLLAMA_URL=http://host.docker.internal:11434`.
3. Run `docker compose up --build -d`. Confirm connectivity from the API container using `docker compose exec api python -c "import urllib.request; print(urllib.request.urlopen('http://host.docker.internal:11434/api/tags',timeout=5).status)"`. If Windows Ollama is only loopback-bound and inaccessible from Docker, do not expose it to the internet to fix this; run UGI directly on the Windows host with `UGI_OLLAMA_URL=http://127.0.0.1:11434`, reusing the existing local FalkorDB `127.0.0.1:6380`.
4. Use `POST /api/uploads?use_ai=true` with a **new dataset name** and a short text sample. Normal uploads (`use_ai=false`) remain deterministic and do not call a model. The API caps model calls and writes usage/review records.

**Controlled FewRel local-model probe (Docker Desktop preferred):** After Ollama is reachable from the Docker API container, execute these commands from the project folder:

```powershell
docker compose exec api python -m ugi.eval_fewrel --download --limit 4 --seed 17
docker compose exec api python -m ugi.eval_fewrel --download --limit 4 --seed 17 --local-model qwen3:4b-instruct
```

For deeper debugging, run the bounded model diagnostic with **public FewRel text only**:

```powershell
docker compose exec api python -m ugi.eval_fewrel --download --limit 4 --seed 17 --local-model qwen3:4b-instruct --diagnose --output /tmp/fewrel-debug.json
docker compose exec api python -c "import json; d=json.load(open('/tmp/fewrel-debug.json')); [print(json.dumps({'text':r['text'],'model_json':r['diagnostics']['provider_responses'],'reviews':r['diagnostics']['review_reasons'],'accepted':r['predicted']},ensure_ascii=False,indent=2)) for r in d['samples']]"
```

The diagnostic exposes the *local model's structured JSON* (including empty relation arrays), semantic review responses and rejections, and the final accepted graph claims. This is **explicit opt-in** because model JSON may contain source text. It stays in the user's Docker container; the normal API does not log/return this trace. Do not enable diagnostic output for private or regulated documents without access controls.

**Do not optimize for all four FewRel annotated head/tail pairs blindly.** A FewRel relational label may need information outside the explicit sentence; some pairs (e.g. distinct election years) are not stated as direct relations in the sentence. Conservative abstention can be correct even when pair-coverage is zero. Use per-sample source entailment review and independent annotations before interpreting apparent improvements.

The local-model extraction uses a compact constrained schema (subject, predicate, object, exact quote plus polarity/modality), followed by **one bounded batched model review for up to 12 semantically unresolved candidates per passage** instead of one review call per candidate. Deterministic guards still reject bad exact quotes, incomplete evidence, ambiguous participial agents, and n-ary `SITUATED_BETWEEN` wrongly flattened into binary claims. Missing/duplicate batch verdict indices are held for human review, never treated as approval. The earlier real Qwen run made **8 calls on 4 examples**, created 4 accepted claims but hit 0/4 annotated FewRel pairs, and produced 2 review tasks; see `TEST_REPORT.md`. **The batch implementation has now been rerun on real local Qwen:** on the same four diagnostic sentences, model calls decreased 8 → 5, but accepted claims dropped 4 → 1, review tasks increased 2 → 5, and FewRel annotated pair hits remained 0/4. This is a small development diagnostic, not a general accuracy estimate. A spatial false-negative was identified and the latest code now canonicalizes clear just-north/south/east/west predicates to their weaker directional base while retaining exact source spans. This latest normalization is regression-tested but has not yet been rerun with real Qwen.

The first command is the grammar baseline; the second makes real local Ollama calls to process **the same four source examples**. Neither command uses AWS. Ollama must be installed and started separately; the container connects through the restricted `UGI_OLLAMA_URL`.

If Ollama is not accessible from the container despite working on Windows localhost, an alternative is to run the model probe on **Windows host Python** after `py -m pip install -e ".[test]"`:

```powershell
py -m ugi.eval_fewrel --download --limit 4 --seed 17 --local-model qwen3:4b-instruct --output "$env:TEMP/ugi-fewrel-local.json"
```

Compare only runs with **matching seeds, sample counts and upstream SHA**, not the 128-example offline figure. The model probe permits **at most six examples per invocation**, is entirely opt-in, and reports real local model calls, review-task counts and directed entity-pair hits; it **does not** calculate semantic predicate correctness or relation F1. The model download and model execution have *not* been performed in project CI; the adapter/probe have mock tests only. If a provider call fails, the run stops rather than returning a misleading score.

Ollama must already be running and the selected model downloaded; Docker does **not** download or start it. The URL is restricted to loopback or Docker Desktop's `host.docker.internal:11434`; remote/cloud endpoints are rejected. `UGI_ALLOW_PAID_CALLS=false` stays locked in Docker Compose, so opting into Ollama does **not** enable Bedrock. Inference can still consume local CPU/GPU/RAM and time. Keep private inputs on machines you trust.

## Model Context Protocol (MCP) adapter

UGI provides an application-level MCP **stdio** server, separate from FalkorDB's general-purpose MCP implementation. It exposes typed graph investigations and evidence, *not arbitrary Cypher*.

```bash
# From the event directory, with the same Python dependencies and FalkorDB available
python -m ugi.mcp_server
```

Example MCP client command configuration:

```json
{
  "mcpServers": {
    "ugi": {
      "command": "python",
      "args": ["-m", "ugi.mcp_server"],
      "env": {"UGI_BACKEND": "falkordb", "UGI_REDIS_URL": "redis://127.0.0.1:6380/0"}
    }
  }
}
```

Launch it from the **event directory** or with the package installed. Supported tools are `search_entities`, `evaluate_relationship`, `get_claim_evidence` and `investigate_dependency_incident`. The investigation tool defaults to preview-only. A write requires **both** the client's explicit `authorise_action=true` **and** `UGI_MCP_ALLOW_WRITES=1` in the MCP subprocess environment. MCP uses a local-process trust boundary, so restrict who can launch the server or read its environment. Tests cover JSON-RPC handshake/tools and a local subprocess; it has **not** been independently certified against every MCP client or full SDK conformance suite.

For graph-general read tools, consider using the existing official [FalkorDB MCP](https://github.com/FalkorDB/falkordb-mcp) alongside UGI's domain-specific tools. Avoid exposing raw write access to an LLM.

## API walkthrough

- `POST /api/uploads` (multipart `file`, optional query `use_ai`)
- `GET /api/graph` and `GET /api/entities?name=...`
- `POST /api/relationships` with subject, object, predicate, optional `as_of` and `allow_hypothesis`
- `POST /api/investigations` with target, idempotency_key and `authorise_action`
- `GET /api/investigations`, `GET /api/tasks` and `POST /api/tasks/{id}/decision`
- `GET /api/records/{id}`, `/api/tools`, `/health`, `/ready`

If `UGI_API_KEYS` is set to a comma-separated list of random secrets, provide an `X-API-Key` header; an optional `X-Dataset` header partitions records into separate dataset graphs. **These demo API keys are not a full production authentication/authorization solution.** Default no-key mode is intended for loopback-only local demonstration.

## Optional Bedrock (disabled by default)

`UGI_PROVIDER=offline` and `UGI_ALLOW_PAID_CALLS=false` by default. No model APIs are called in offline mode. To enable Bedrock, you must explicitly configure the model ID, AWS region, per-million-token prices, positive daily cost ceiling and paid-call flag. Review model access and rates in your account first. Keep credentials in IAM roles or your private AWS configuration; never commit `.env` or copy keys into README.

App-side quotas, request caps and estimated pre-reserved costs are safeguards, **not an AWS account-level billing cap**. No live Bedrock calls were made during the ChatGPT follow-up work, and the Bedrock adapter was tested with mocked clients only.

## Domain and graph semantics

`Source -> HAS_CHUNK -> Chunk`. Source claims have exact `Evidence` records, tied to their originating chunk and supporting Claim. Entity-to-Entity `RELATES` connections are keyed by Claim ID and preserve direction, predicate, qualifier and source ID in the related Claim record. For agent actions, `Investigation -> HAS_TASK -> ReviewTask`; `AgentAction -> ACTED_ON -> Investigation`.

A source *asserting* a relationship is not independent truth verification. A connected path alone is not a semantic inference. A hypothesis does not become a Claim without separate evidence. Negative source claims are now distinguished from contradictory positive+negative assertions. `TRANSITIVELY_DEPENDS_ON` requires at least two direct dependency hops.

### Whole relations with three or more participants

Upload `demo/relation_events.txt` to a fresh dataset, for example `events-demo`.
It produces four whole events: a four-island BETWEEN relation, a supplier/item/factory
provision, an acquisition including its consideration and year, and a research
collaboration involving two researchers, a project and an institution. These
examples are synthetic CC0 demonstration data. No separate binary claims are
created from the event spokes.

`RelationEvent -> HAS_PARTICIPANT {role} -> Entity` preserves every participant
and role. `Evidence -> SUPPORTS -> RelationEvent` and `Evidence -> CITES -> Chunk`
retain exact quotations and offsets. Event records preserve original relation
type, normalized type, source/chunk, polarity/modality, time precision, event time,
validity, attribution, review method and model. Type-scoped explicit IDs link
structured event participants to existing entities; name-only identities remain
document-local. All writes use the existing atomic document commit and dataset
graph isolation. Role-order permutations deduplicate, while different occurrences,
dates, polarity and modality remain separate. Repeated quotes need exact offsets.

`demo/relation_events.json` demonstrates an uncertain, time-bounded structured
provision and an ordinary binary location claim sharing the same factory ID.
JSON/JSONL event rows contain `relation_type` and `participants` (3–12 entries,
each with `role`, `name`, optional `entity_type`, `external_id`, `aliases`).
Structured evidence is the original serialized row, not externally verified prose.

New read endpoints:

- `GET /api/events?entity_id=ENTITY_ID&as_of=2026-06-01&limit=100`
- `GET /api/graph` includes `events` alongside compatible `entities` and `claims`.
- `GET /api/records/{evidence_id}` reads an event's exact evidence.

The browser draws events as diamonds and role-labelled spokes, with amber for
uncertainty, red for negation and dashed historical participation. Select the
event or role label to inspect evidence. These spokes are incidence edges, not
binary world assertions, and do not enter the binary UNKNOWN resolver's proof
paths. No general logical rule derives a pairwise relation from shared participation.

Ollama's existing compact extraction can return an optional `events` array in the
same response. Deterministic whole-event guards precede at most one event-review
batch of six unresolved events; the existing global/per-request call ceilings
still apply. Missing or duplicated verdicts, incomplete anchor groups, invented
participants, altered quotes and lost qualifiers fail closed into review tasks.
The binary batch path is preserved. Extra event review may consume an additional
call, so this is not an unmeasured speed/accuracy improvement claim.

The deterministic event templates cover only clear supported sentence forms.
Relative-clause attachment and broad event extraction remain limited. Complex
events require model/human review; live local-model event quality is reported
separately from mocked tests in `TEST_REPORT.md`. Temporal filtering is bounded:
the limit is applied before filtering, and the endpoint reports this explicitly.

## Known limitations

- Offline text extraction is a conservative grammar/rule system, not universal natural-language understanding. In particular, ambiguous pronouns are deliberately not assigned to a person/entity.
- Local Ollama has mock transport tests and actual bounded Windows Qwen probes. Exact public predicate recall has not improved over rules in the latest matched subset; review can both accept underspecified claims and reject supported ones.
- The main incident agent follows a bounded deterministic investigation policy. It is **not** an unrestricted conversational LLM planner; tool interfaces are available for external agents.
- Entity linking is conservative across documents and may fragment true identities unless a stable explicit ID is available.
- Nontext/scanned PDFs need OCR; OCR is not bundled.
- JSON and CSV must fit configured limits; even within quotas, 1,000/2,000-record synthetic local writes timed out. 100-record CSV/JSON checks passed. No production-scale guarantee is made.
- Updated package verification includes a successful GitHub-hosted Docker/FalkorDB integration run and participant-supplied Windows Docker Desktop results showing real upload, graph inference, persisted agent action and recovery after an API + graph container restart. See `TEST_REPORT.md` for scoped evidence. This is a prototype smoke test, not production-grade durability testing.
- API keys and application-specific quotas are not substitutes for robust IAM, TLS, tenant policies, WAF controls, global cloud spending caps or independent security audit. Do not publicly expose the demo container as-is.
- The synthetic held-out fixture may not generalise to open-ended unseen text or documents; quantitative scores in `evaluation/current_report.json` apply **only to that fixture**.

See `TEST_REPORT.md` for test evidence and `WORK_LOG.md` for event-time provenance.

## Submission checklist

- [x] Run live FalkorDB integration and persistence/restart smoke tests on Windows Docker Desktop (participant-provided logs; see `TEST_REPORT.md`).
- [ ] Verify eligibility of historical baseline/reference reuse with organisers where unclear.
- [ ] Demonstrate incident graph + persisted investigation + evidence path.
- [ ] Demonstrate second unrelated domain with the same code.
- [ ] Decide whether to authorise paid Bedrock tests and deploy with proper access controls.
- [ ] Publish a clean repository with no credentials, plus a demo video and any required form information.
- [ ] Disclose AI-assisted development accurately.
