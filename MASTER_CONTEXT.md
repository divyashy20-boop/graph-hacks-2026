# Universal Graph Intelligence — Master Project Context

**Purpose:** orientation for contributors planning work in this checkout. It identifies the active application, its runtime/data boundaries, and the supplied qualification material. It is deliberately not a UI-ticket plan.

**Checkout captured:** `UniversalGraphConverter`, branch `upstream-main`, synced to GitHub `upstream/main` at `7913afd` on 2026-10-17.

## What UGI is

Universal Graph Intelligence (UGI) is an event-time, evidence-grounded graph converter and investigation dashboard for Graph Hacks 2026 Track 1. It ingests supported file formats, grounds claims in exact source evidence, persists graph records, and supports bounded dependency investigation.

The product is an **inspectable evidence graph**, not a general truth engine. A visual connection, model suggestion, or graph path must not be presented as a new source fact.

FalkorDB is the intended persistent runtime. The memory backend is for unit tests and local seeded demos; it is not the production storage target.

## Fast orientation

| Need | Start here |
| --- | --- |
| Run the app | `compose.yaml`, `README.md`, `ugi/api.py` |
| Change the live UI | `ugi/index.html`, `ugi/assets/style.css`, `ugi/assets/app.js` |
| Change guided-agent/receipt UI | `ugi/assets/guided.js`, `ugi/agent_integration.py`, `ugi/agent_policy/`, `ugi/memory/` |
| Understand graph semantics | `ugi/models.py`, `ugi/engine.py`, `ugi/nary.py`, `ugi/store.py`, `docs/nary_graph.md` |
| Understand ingest/extraction | `ugi/extract.py`, `ugi/clauses.py`, `ugi/provider.py` |
| Understand active tests | `tests/`, especially dashboard and guided-memory tests |
| Use demos | `demo/`, preset logic in `ugi/api.py` / `ugi/assets/app.js` |
| Review limits and safeguards | `AGENTS.md`, `README.md`, `INTEGRATION_GUIDE.md`, `docs/UNIVERSAL_ARCHITECTURE.md` |

## Repository map

```text
UniversalGraphConverter/
├── ugi/                         # Active Python package and dashboard
│   ├── api.py                   # FastAPI routes, asset allowlist, demo seeding
│   ├── engine.py                # Ingest, evidence grounding, reasoning
│   ├── store.py                 # FalkorDB and memory storage abstraction
│   ├── extract.py, clauses.py   # Parsing and bounded extraction
│   ├── models.py                # Settings and typed contracts
│   ├── nary.py                  # Whole multi-participant event model
│   ├── identity*.py, resolution.py, schema.py
│   ├── mcp_server.py            # Bounded JSON-RPC tool interface
│   ├── agent_policy/            # Deterministic dependency rulebook
│   ├── memory/                  # SQLite receipt-memory sidecar
│   ├── index.html               # Dashboard DOM
│   └── assets/                  # app.js, guided.js and style.css
├── tests/                       # Root pytest suite for ugi/
├── demo/                        # Synthetic incident, supply, research/event fixtures
├── docs/                        # Architecture/n-ary graph documentation
├── evaluation/                  # Historical controlled-evaluation artifacts
├── UGI_All_In_One_Test/         # Supplied isolated validation package
├── UGI_Final_Qualification/     # Supplied pre-merge qualification package
├── UGI_Memory_Receipts_Lab/     # Supplied standalone receipt-memory reference lab
├── UGI_Reasoning_Controller_Test/# Supplied isolated controller experiment
├── compose.yaml                 # Local FalkorDB + API runtime
├── pyproject.toml               # Python package/dependencies
└── .env.example                 # Config and feature-flag reference
```

### Active versus supplied code

The root `ugi/` directory is the only application package declared by `pyproject.toml`. Root `tests/` is the active pytest path. For ordinary UI work, the live surface is:

- `ugi/index.html` — page structure and dashboard panels.
- `ugi/assets/style.css` — visual system, layout, graph surfaces and responsive rules.
- `ugi/assets/app.js` — API client, 2D/3D graph renderers, state, inspector, upload, evaluation, investigation and review interactions.
- `ugi/assets/guided.js` — an additive, feature-gated guided-agent and receipt-memory panel.

The top-level `UGI_*` folders are not imported by the root application. They are supplied test/reference packages with duplicated or experimental code. Do not edit them to change the running dashboard, and do not present their historic PASS reports as current root-app verification.

| Folder | Role |
| --- | --- |
| `UGI_All_In_One_Test/` | Isolated deterministic controller/validation material; manifest says live Docker verification remains pending. |
| `UGI_Reasoning_Controller_Test/` | Isolated rulebook test that patches a temporary Docker copy, not root `ugi/`. |
| `UGI_Memory_Receipts_Lab/` | Synthetic SQLite reference lab, explicitly not real UGI/FalkorDB integration. |
| `UGI_Final_Qualification/` | Pre-merge qualification suite, not a permanent deployment. |

## Runtime architecture

```text
Browser
  ├─ index.html + style.css + app.js
  │    ├─ graph/explorer endpoints
  │    ├─ source inspector and uploads
  │    └─ relationship, investigation and review workflows
  └─ guided.js (only if feature flags are on)
       └─ guided endpoint → MCP adapter → rulebook → SQLite receipt
          └─ receipt freshness endpoint → mandatory re-read

FastAPI (ugi/api.py)
  └─ Engine (ugi/engine.py) ↔ Store (ugi/store.py) ↔ FalkorDB
       ├─ parse/extract/provider
       ├─ evidence, identity, event and schema logic
       └─ bounded MCP interface
```

- `GET /` serves `ugi/index.html`; `GET /assets/{filename}` only allows `app.js`, `style.css`, and `guided.js` in the synced upstream application.
- Requests are scoped by `X-Dataset` (default `demo`). When keys are configured, `X-API-Key` determines owner scope.
- `compose.yaml` exposes FalkorDB on `127.0.0.1:6380` and the API/dashboard on `127.0.0.1:8001`.
- `event-graph` stores graph data; `event-receipts` stores receipt-sidecar data.

## Configuration modes

| Capability | Default | Boundary |
| --- | --- | --- |
| Persistent graph/dashboard | FalkorDB | Start via Docker Compose. |
| Local seeded demonstrations | memory backend only | Convenience/test mode, not durable deployment data. |
| AI extraction | offline | Provider and user upload checkbox must explicitly opt in. |
| Identity ledger | off | Provisional/history-preserving overlay; does not rewrite base facts. |
| Schema writes/open predicates | off | Registering vocabulary does not authorize inference. |
| Guided rulebook and memory | off | Requires both flags and absolute persistent `UGI_MEMORY_PATH`; read-only controller, no external action fence. |

## Evidence model and invariants

Core records include:

- **Source** and **Chunk** — uploaded material and its bounded location.
- **Entity** and **Mention** — typed graph node plus source-local reference.
- **Evidence** — exact quote, byte offsets, source and chunk links.
- **Claim** — grounded binary assertion with predicate, polarity, modality, timing, evidence and source links.
- **RelationEvent** — whole multi-participant assertion, never silently expanded to many binary facts.
- **ReviewTask**, **Investigation**, **AgentAction** and **Hypothesis** — review and audit workflow records.

Rules that UI and product copy must preserve:

- Exact evidence/source attribution and offsets remain accessible for supported claims.
- `SOURCE_ASSERTED`, `SOURCE_NEGATED`, `RULE_DERIVED`, `CONNECTED_ONLY`, `HYPOTHESIS`, `CONTRADICTED`, and `UNKNOWN` are distinct outcomes.
- A graph path can support bounded dependency derivation; it does not prove arbitrary relations or incident causality.
- Unsupported, negative, uncertain, conflicting, expired, or schema-bound assertions do not become ordinary inference evidence.
- `as_of` world-time filtering differs from recorded-time, identity, and receipt freshness.
- Whole-event participation does not establish a binary relation between participants. See `docs/nary_graph.md`.
- Identity overlays are provisional; shared names are not proof of real-world identity.

## Main application journeys

### Ingest and inspect

1. The user chooses a dataset or a demo preset.
2. `POST /api/uploads` accepts CSV, JSON, JSONL, TXT and text PDF; AI extraction is separately optional.
3. `Engine.ingest` parses, extracts, verifies, creates evidence/claim/event records and commits atomically.
4. The UI loads `GET /api/graph` and renders entities, claims and whole events.
5. Selecting a record retrieves provenance through `GET /api/records/{id}`; the inspector shows quote, offsets, source and event roles.

### Explore and decide

- `GET /api/graph` returns entities, claims, whole events, counts, date filter state and truncation.
- `GET /api/events` keeps whole events explicit and states that participation is not binary proof.
- `POST /api/relationships` returns a read-only verdict/evidence response.
- `POST /api/investigations` writes only through an explicit authorization contract.
- `POST /api/tasks/{task_id}/decision` records audited human judgement; it does not convert proposals into source truth.

### Guided agent and receipts

The feature is integrated but beta/feature-gated.

1. `guided.js` checks `/health` and only reveals the panel when both feature flags are enabled.
2. `POST /api/agent/guided` calls `agent_integration.run_guided`.
3. The rulebook accepts narrow, explicit two-entity dependency questions. Dataset names are context, not graph entities.
4. It validates structured MCP calls for lookup, relationship evaluation, evidence retrieval and preview-only investigation.
5. `memory/bridge.py` captures reads and stores an owner/dataset-scoped SQLite receipt.
6. `GET /api/agent/receipts/{id}/freshness` re-reads evidence and produces `VALID`, `STALE` or `UNKNOWN` before reuse.

It is not a general autonomous planner and does not provide distributed or external-side-effect atomicity.

## Current dashboard

### UI structure

The one-page dashboard contains a hero/control deck, dataset presets, statistics, graph map, source inspector, ingestion form, relationship evaluator, authorized investigation/review areas, and a feature-gated guided-memory panel.

It is a no-framework interface: there is no frontend build process, React/Vue codebase, or Node dependency tree. UI work is browser-native HTML/CSS/JavaScript.

### 2D map

- SVG renderer with spaced entity placement, directional claim markers and whole-event nodes.
- Record selection and neighbor/connection highlighting.
- Node drag, canvas pan/zoom, reset controls and `as_of` filtering.
- Source inspector remains the path back to stored provenance.

### 3D orbit

- The synced GitHub application uses a custom canvas/WebGL orbit renderer in `ugi/assets/app.js` (`createOrbitRenderer` and `setViewMode`).
- It provides orbit/pan/zoom, focus selection, labels, auto-orbit, keyboard guidance and a 2D fallback for unavailable WebGL.
- `tests/test_guided_ui_release.py` protects the native orbit functions and additive guided-script boundary.

### Local preserved 3D artifact

Before the upstream sync, this folder contained local uncommitted UI work and `ugi/assets/3d-force-graph.min.js`. That work is preserved in Git stash `stash@{0}` named `codex pre-upstream-main sync 2026-10-17`; the bundle currently remains as an untracked local file. It is **not** part of the synced upstream UI, and current upstream `api.py` does not allowlist/serve it. Treat it as preserved legacy work, not active runtime code, until a deliberate UI ticket decides otherwise.

## API surface

| Route family | Purpose |
| --- | --- |
| `GET /`, `GET /assets/{filename}` | Dashboard and allowlisted assets. |
| `GET /health`, `GET /ready` | Service/configuration and storage availability. |
| `POST /api/uploads` | Bounded ingest, optional AI, pinned packs. |
| `/api/graph`, `/api/events`, `/api/entities`, `/api/records/{id}` | Graph exploration/provenance. |
| `POST /api/relationships` | Read-only verdict/evidence evaluation. |
| `/api/investigations`, `/api/tasks` | Persistent investigation/review lifecycle. |
| `/api/identity/*`, `/api/schema/*` | Opt-in identity and schema facilities. |
| `POST /api/agent/guided` | Feature-gated guided read-only controller. |
| `GET /api/agent/receipts/{id}/freshness` | Feature-gated receipt fresh-check. |
| `GET /api/tools` | Bounded tooling/action declaration. |

## Demo datasets

With `UGI_BACKEND=memory`, the server seeds these named presets on first access:

| UI preset | Dataset | Fixture(s) |
| --- | --- | --- |
| IT incident | `showcase-b-incident` | `demo/incident.json` |
| Supply chain | `showcase-b-supply` | `demo/supply_network.json` |
| Research & identity | `showcase-b-research` | `demo/research_network.json`, `demo/research_identity.json` |

Additional fixtures include relation events, open text, supply CSV and shared-employer examples in `demo/`.

## Local running and tests

Install with project metadata (there is no root `requirements.txt`):

```powershell
python -m pip install -e ".[test]"
```

Persistent local runtime:

```powershell
docker compose up -d --build
# http://127.0.0.1:8001
```

Quick memory-mode UI:

```powershell
$env:UGI_BACKEND = 'memory'
python -m uvicorn ugi.api:app --host 127.0.0.1 --port 8001
```

Root tests:

```powershell
python -m pytest -q
```

Important active tests:

- `tests/test_dashboard.py` — dashboard assets, memory preset seeding and event precision.
- `tests/test_guided_ui_release.py` — UI assets, native orbit hooks, guided panel and routes.
- `tests/test_guided_memory_http.py` — feature flags, receipts, invalidation, conflicts, scopes and abstention; it uses the memory backend and is not FalkorDB proof.
- `RUN_INTEGRATED_E2E_WINDOWS.ps1` — disposable real HTTP/FalkorDB/MCP/receipt exercise; it retains its generated dataset for inspection.

Historical milestone test counts in reports are provenance, not proof that a later working tree is still green. Verify after changes.

## Safety and communication boundaries

- No arbitrary Cypher endpoint is exposed.
- Explicit authorization is required for persistent action routes; guided operation is read-only/preview-only.
- Do not expose keys, `.env`, local graph data, result files with private data, or volumes.
- Do not market synthetic demos as universal extraction accuracy, live incident causality, independent truth, or production readiness.
- Receipt memory does not make external actions safe; there is no distributed transaction/fence or universal agent capture.
- Preserve verdict labels faithfully; do not show `RULE_DERIVED` as source-asserted or `CONNECTED_ONLY` as entailed.

## Facts to use when writing future UI tickets

- The active UI is single-page native HTML/CSS/JavaScript.
- Tickets should target real journeys and states: loading/error/retry, no records, date filtering, truncation, source provenance, WebGL fallback, action authorization, and feature-gated guided mode.
- UI changes must keep the inspector/evidence trail demonstrable with a real preset or uploaded dataset; static mockups do not demonstrate UGI.
- Current styling is a dark spatial/industrial application interface, not a separate marketing site.
- The graph’s 3D mode and its accessible 2D fallback are existing product behavior and must be preserved or explicitly replaced through a tested ticket.
- `UGI_UI_MERGE_REPORT.json` records that the UI-008 files were preserved through the guided/P5 integration; guided behavior was added additively through `guided.js` and routes.

## Suggested reading order before UI work

1. `AGENTS.md`
2. This file
3. `ugi/index.html`
4. `ugi/assets/style.css`
5. `ugi/assets/app.js` — especially `refresh`, `render`, `inspect`, `createOrbitRenderer`, `setViewMode`
6. `ugi/assets/guided.js`
7. `tests/test_dashboard.py` and `tests/test_guided_ui_release.py`
8. Graph/record/upload/relationship routes in `ugi/api.py`

Use this context to make the next UI ticket file demonstrable, scoped to active code, and tied to verification rather than only visual changes.
