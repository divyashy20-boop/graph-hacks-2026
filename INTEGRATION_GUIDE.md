# UGI integrated Guided Agent + P5 Memory (beta)

## Scope and evidence

This repository is derived from the user-provided October 2026 event snapshot, **not** from historical prototypes. The H1 extraction, identity, schema and original API/UI remain intact. The audited deterministic rulebook, SQLite receipt engine, and actual UGI JSON-RPC MCP read bridge are now located under `ugi/` and exposed as opt-in HTTP/UI functionality.

**Validated earlier in isolated qualification:** Rulebook 49/49 bounded live cases; P5 17/17 synthetic cases; 11/11 combined FalkorDB MCP cases on the user's machine. The *new API/UI integration* is a distinct implementation and needs its own real Docker E2E before AWS. No native broad language or external-action fencing claim is made.

## Activate for local testing

1. Keep your existing data and H1 working tree. Backup any important graph data. Build API only:

   ```powershell
   $env:UGI_GUIDED_AGENT_ENABLED='true'
   $env:UGI_MEMORY_ENABLED='true'
   docker compose up -d --build --no-deps api
   docker compose ps
   ```

2. Visit http://127.0.0.1:8001/ . Select the dataset with ingested relationships, submit an explicit dependency question in **Guided agent + memory receipts**. Click **Check receipt freshness**. Also test new data ingestion then recheck the OLD receipt (STALE/UNKNOWN means do not reuse). The status reflects state at the moment of reading, not a lock against later graph writes.

3. HTTP examples:

   ```powershell
   $headers = @{ 'X-Dataset'='demo'; 'Content-Type'='application/json' }
   $r = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8001/api/agent/guided' -Headers $headers -Body '{"query":"Does Checkout indirectly depend on Cache?"}'
   $r | ConvertTo-Json -Depth 9
   $rid = $r.receipt_id
   if ($rid) { Invoke-RestMethod "http://127.0.0.1:8001/api/agent/receipts/$rid/freshness" -Headers $headers }
   ```

   If `UGI_API_KEYS` is configured, add `'X-API-Key'='your-real-key'` to the headers. Keep API keys and AWS credentials outside committed source.

4. Disable the beta:

   ```powershell
   $env:UGI_GUIDED_AGENT_ENABLED='false'
   $env:UGI_MEMORY_ENABLED='false'
   docker compose up -d --no-deps api
   ```

A new `event-receipts` volume stores SQLite receipt history separately from the existing `event-graph` volume. **Never run `docker compose down -v` to disable the feature.** The image owns `/var/lib/ugi` as `appuser`; volume creation is supported by Docker copy-up. For non-Compose deployments set `UGI_MEMORY_PATH` explicitly to a persistent absolute path writable by the service identity.

## What changed

- `ugi/agent_policy`: bounded deterministic MCP controller and guarded intent interpretation.
- `ugi/memory`: receipt storage, immutable read fingerprints, version/change conflict lattice, and tool argument registry.
- `ugi/agent_integration.py`: actual MCP JSON-RPC handler adapter in the **same authenticated owner and dataset** scope; automatic read capture, evidence verification, no action execution, mandatory re-read on status check.
- `ugi/api.py`: `POST /api/agent/guided`, `GET /api/agent/receipts/{rid}/freshness` behind both flags.
- `ugi/index.html`, `ugi/assets/app.js`: UI for guided queries, actual trace, receipt freshness, stale warning.
- `ugi/engine.py`: verified guarded explanation/resolution consistency fix; SHA record in `UGI_ENGINE_INTEGRATION_PATCH_RECEIPT.json`.

## Limitations / submission review blockers

- Existing uninstrumented endpoints and other external agents **are not automatically captured**, so do not claim universal memory capture or put their side effects behind this receipt gate.
- Validity is a *fresh-check snapshot*. A graph writer may change facts afterward; no distributed transaction or external-side-effect fencing exists. Do not add automatic external effects, payment, AWS mutations or production incident mitigation to this beta.
- SQLite is local single-instance durable storage on a volume; no multi-instance concurrent guarantee, remote replicated failover, managed DB, migration or disaster recovery proven.
- The rulebook works only on bounded explicit dependency questions and abstains safely on ambiguous/causal and unsupported intent; Qwen advisory and original free-form baseline are **not** the core controller.
- The receipt bridge conservatively tracks **all** returned MCP outputs, so unrelated changes in shared `search_entities` results can mark a receipt STALE. Original fingerprints, not 'events this refresh', determine impact.
- UGI source assertions are not independently verified truth. Actual incident causality is not proven by dependency paths. No claims about unseen graph datasets or all H1 NLP tasks should be made without new results.
- Features default OFF; authorization, tenant boundaries, load tests, health checks, security/IAM/secrets, AWS backups, rate limits, and actual deployed E2E require verification before public deployment.

## Local tests

```powershell
python -m pytest -q tests/test_guided_memory_http.py
python -m pytest -q
```

Set `UGI_TEST_REDIS_URL` and run the optional `integration`-marked tests only in a disposable test graph prefix; no old namespace should be reused or deleted. This package does **not** deploy AWS resources.
