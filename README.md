# Universal Graph Intelligence (UGI)

An **event-time Graph Hacks 2026 Track 1 implementation** of a multi-format, evidence-grounded graph converter and dependency-investigation agent. FalkorDB is the persistent graph database. A deterministic policy can trace service dependencies and create real investigation/review records. An optional AWS Bedrock provider handles model-assisted extraction and hypothesis proposal behind strict opt-in.

**Status:** functional local prototype and demo, **not production-ready**. This repository contains a code-first implementation and a small synthetic evaluation, not a proven universally accurate graph extractor.

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

Use the **`event/` directory** as the working directory. Ensure Docker Desktop is running.

```bash
cd event
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

UGI has an **opt-in local Ollama provider**, separate from AWS Bedrock. It sends source text only to the explicitly configured local Ollama server, requests schema-constrained JSON, and still subjects every relationship to the same exact-span, directional, polarity, temporal and semantic checks. A failed or ambiguous model response goes to review, not directly into the graph as established truth. This integration has been tested with **mocked local HTTP responses**; **no actual model-quality gain has been verified yet**.

To experiment on your own Windows computer:

1. Install [Ollama for Windows](https://ollama.com/download/windows). In a new PowerShell, run `ollama pull qwen3:4b-instruct` and verify `ollama list` and `http://127.0.0.1:11434/api/tags`.
2. In your local **untracked** `.env`, set `UGI_PROVIDER=ollama`, `UGI_MODEL_ID=qwen3:4b-instruct` and `UGI_OLLAMA_URL=http://host.docker.internal:11434`.
3. Run `docker compose up --build -d`. Confirm connectivity from the API container using `docker compose exec api python -c "import urllib.request; print(urllib.request.urlopen('http://host.docker.internal:11434/api/tags',timeout=5).status)"`. If Windows Ollama is only loopback-bound and inaccessible from Docker, do not expose it to the internet to fix this; run UGI directly on the Windows host with `UGI_OLLAMA_URL=http://127.0.0.1:11434`, reusing the existing local FalkorDB `127.0.0.1:6380`.
4. Use `POST /api/uploads?use_ai=true` with a **new dataset name** and a short text sample. Normal uploads (`use_ai=false`) remain deterministic and do not call a model. The API caps model calls and writes usage/review records.

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

## Known limitations

- Offline text extraction is a conservative grammar/rule system, not universal natural-language understanding. In particular, ambiguous pronouns are deliberately not assigned to a person/entity.
- Local Ollama integration is schema/transport tested with mocks only; there is no verified improvement on FewRel or unseen prose yet.
- The main incident agent follows a bounded deterministic investigation policy. It is **not** an unrestricted conversational LLM planner; tool interfaces are available for external agents.
- Entity linking is conservative across documents and may fragment true identities unless a stable explicit ID is available.
- Nontext/scanned PDFs need OCR; OCR is not bundled.
- JSON and CSV must fit the configured ingestion limits. Large-scale real-world benchmarks have not been run.
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
