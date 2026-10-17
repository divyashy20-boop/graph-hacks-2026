# Graphynx final model release — Qwen3 32B

**Selection (18 Oct 2026):** Qwen3 32B on AWS Bedrock `qwen.qwen3-32b-v1:0` in `ap-southeast-2`. Standard Sydney rate: $0.1545 per million input tokens / $0.6180 per million output tokens (check current AWS rates before billing). Do NOT use a `global.` prefix: Qwen3 32B's Bedrock Runtime model card lists an in-region ID and no global inference profile.

## Architecture remains intact

Browser / judge site (Amplify) → API Gateway and Lambda proxy → Graphynx FastAPI on private EC2 → UGI Engine / evidence validation / FalkorDB persisted per owner + dataset → Rulebook, explicit n-ary events, review tasks, hypothesis resolver and guided MCP/P5 SQLite receipt memory. Bedrock Qwen3 32B is an **opt-in inference provider**: `POST /api/uploads?use_ai=true` for extracted proposals and semantic review; `POST /api/relationships` can request tentative LLM hypothesis with `use_ai=true`. Supported claims still require source evidence and validation, and tentative hypotheses NEVER become verified facts. The bounded guided agent remains deterministic; it is NOT an arbitrary free-form generative QA agent.

No change to authentication, IAM, owner/dataset isolation, stored graphs, immutable source records, stateful volumes, judge gate, idle-stop automation, cost alerts, or related AWS projects.

## What the completed tournament actually established

Identical four public Re-DocRED documents (`doc_000`, `doc_005`, `doc_010`, `doc_019`) and two extraction window settings were tested. Qwen3 32B: `whole_compact` 6 accepted claims / 31 reviews / 5 of 6 graph-query-visible, and 12/12 fixed-reference questions / 7/12 own-graph questions. Its `split_context` had the same six accepted claims and worse review burden. Haiku's seven accepted claims included repeated Lavapuri allegation, leaving the same six unique subject/predicate/object/modality facts. DeepSeek tied fixed QA but had higher latency in this small test. OpenAI Luna/Terra inaccessible in that AWS account. This is NOT full Re-DocRED F1, independent accuracy, a test of every domain, or proof that every question is answerable: both `doc_000` and `doc_005` yielded zero accepted relations for every candidate. The shared strict validator/entity/coreference issue remains.

## Exact release settings

```text
UGI_PROVIDER=bedrock
UGI_ALLOW_PAID_CALLS=true
UGI_MODEL_ID=qwen.qwen3-32b-v1:0
UGI_AWS_REGION=ap-southeast-2
UGI_INPUT_PRICE=0.1545
UGI_OUTPUT_PRICE=0.6180
UGI_DAILY_COST_LIMIT=0.25
UGI_MAX_MODEL_CALLS=8
UGI_MAX_OUTPUT_TOKENS=2250
UGI_MAX_INPUT_TOKENS=12000
UGI_EXTRACTION_WINDOWS=1
```

The per-day cost reservation guard is NOT a hard AWS spending limit. Max calls are per provider instance. No token caching or temperature override. Do not reduce evidence validation, force merges, rewrite legacy claims or bypass review to inflate acceptance counts.

## Local/Compose-compatible deployment only

The base `compose.yaml` intentionally stays offline with `UGI_ALLOW_PAID_CALLS=false`. **Do not edit it globally.** To enable Qwen on a previously verified Compose-managed instance with the same Compose files, use:

```bash
docker compose -f compose.yaml -f compose.qwen.yaml config > /tmp/graphynx-qwen-effective.yaml
docker compose -f compose.yaml -f compose.qwen.yaml up -d --no-deps --build api
docker compose -f compose.yaml -f compose.qwen.yaml ps
curl -fsS http://127.0.0.1:8001/health
```

The overlay inherits graph containers and persistent volumes. Never use `docker compose down -v`, `GRAPH.DELETE`, `redis FLUSH*` or `docker system prune --volumes`.

**AWS deployment caveat:** the live Graphynx judge stack runs private EC2 containers named `graphynx-api` and `graphynx-db`, and may use a different deploy manifest than root `compose.yaml`. Before any live replacement, inspect `docker inspect graphynx-api` for its real image, labels, networks, ports, mounts, environment and AWS instance role. If it isn't managed by this Compose project, do NOT run these Compose commands against production. Re-create/restart only the API using the deployed manifest, preserving all other settings and containers; retain a previous image/manifest for rollback. Verify actual Bedrock `Converse` access and model usage on the target EC2 role before exposing Qwen-powered uploads.

## Verification / acceptance

Run `python -m pytest -q` and the existing real-FalkorDB tests. After deployment check `/health` returns `provider=bedrock` and `/ready` is true. In a fresh non-judge dataset explicitly upload one tiny synthetic TXT with `use_ai=true`, verify a `Usage` record for the correct Qwen model, the exact quote and persisted Claim/ReviewTask, and then test `POST /api/relationships`. This does not prove real-world accuracy. Verify the live Amplify judge flow and P5 `VALID` → `STALE` blocking before considering the release deployed. Revert API only on failure; never delete volumes. Leave production unchanged if any permission, service/health, API, graph, or P5 check fails.

## Source-of-truth caution

The previous AWS deployed source was pinned to `7913afd7a5ebced7f5d15f82658593e9cfdb58f8`, while the GitHub repository subsequently received further commits. Merging this release into `main` **does not automatically update** the pinned live EC2 Docker image, Lambda proxy, Amplify deployment or instance role. The AWS operator must perform and verify a separate, targeted deployment.
