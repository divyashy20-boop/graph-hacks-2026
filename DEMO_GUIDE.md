# UGI: three-minute evidence-to-action demonstration

Track 1: Agents That Act on Connected Data. All demo records are synthetic CC0.
The same engine, graph store, resolver and investigation policy serve all domains.
No model or internet service is needed for the core presentation.

## Prepare on Windows

From the repository root containing `ugi/` and `compose.yaml`:

```powershell
git status --short
git pull --ff-only origin main
docker compose up --build -d
py -m pip install -e ".[test]"
py -m ugi.demo --execute --dataset-prefix showcase-b --output evaluation/showcase_local.json
```

`--execute` authorizes creating local persistent investigations/review tasks.
Omit it to preview the actions. Ingestion itself persists the synthetic sources.
No external webhook or paid model is used. The seed command is intended for
loopback, no-key local mode; with configured API keys, upload through the UI
under that key rather than expecting CLI-local-owner data in its separate tenant.

Open http://localhost:8001. Choose a seeded demonstration in the dataset menu.
The graph, counts, paths and cases come from actual backend records. Empty
presets mean data has not been loaded for the current dataset/owner.

## Presentation script (~3 minutes)

**0:00–0:25 · Problem.** “A pile of documents tells us individual facts, but an
incident needs connected context: what depends on this component, which sources
support that dependency, and what remains uncertain? UGI turns those sources
into an auditable graph and records a reviewable action.”

**0:25–1:25 · IT incident.** Select `IT incident` (`showcase-b-incident`). Inspect
the Cache node and a DEPENDS_ON edge; read its exact source row. Evaluate:
Checkout → TRANSITIVELY_DEPENDS_ON → Cache. Expected RULE_DERIVED with two
source claims and highlighted paths. Ask the same pair for DEPENDS_ON: expected
CONNECTED_ONLY because reachability does not prove a direct dependency. Ask
Cache USES Redis: expected CONTRADICTED. The possible incident cause stays
unproven. Preview Cache investigation, then explicitly authorize execution.
Show the saved high-priority case, two exposed components, tool trace and linked
review tasks. This is a database write, not a generated paragraph.

**1:25–1:55 · Supply chain.** Select `Supply chain`. Inspect PROVISION: supplier,
component and factory are participants in one event, not misleading pairwise
supply facts. Harbor Factory → TRANSITIVELY_DEPENDS_ON → Nova Supply returns
RULE_DERIVED using separately supplied dependency assertions. Investigating
Nova Supply creates an exposure case for Sensor Unit and Harbor Factory.
Nova Supply → MAY_AFFECT → Harbor Factory with hypothesis opt-in is tentative;
it does not prove a disruption occurred.

**1:55–2:25 · Research.** Select `Research & identity`. Inspect COLLABORATION
roles and its 2021 interval. Apply 2021-06-01 to the graph; then 2023-06-01 to
see which dated assertions remain. The seed intentionally loads two distinct
people named Lina: a name-only Lina query returns UNKNOWN. Select an exact
entity ID from the node inspector to disambiguate. For the original Lina and
Noor, SHARES_EMPLOYER in 2021 is RULE_DERIVED, but their 2023 overlap is UNKNOWN.
Shared employment does not establish friendship.

**2:25–3:00 · Technical proof and limits.** “FalkorDB stores claims, exact
evidence, role-labelled events and actions. Bounded graph traversal retrieves
dependency paths and exclusions; the same case survives restart. SQL could
represent this with recursive joins, but this workflow uses graph incidence,
multi-hop traversal and persistent connected state directly. Our source labels
are assertions, not independently verified truth. Rule coverage is limited;
public prose and local Qwen remain weak. We report provisional evaluation and
hold uncertain proposals for review.”

## Verified expectations / repeatability

`python -m ugi.demo` asserts the above core graph conclusions. The output JSON
contains source evidence, case IDs, persisted task records and identity candidates.
Re-running reuses sources/actions; it never deletes the persistent volume.
For manual fresh cases, the UI generates a new idempotency key per target change.
Restart proof: note a saved case ID, run `docker compose restart api graph`, then
load the same dataset and inspect the same ID. Wait for healthy status first.

Core graph model and queries: [n-ary graph model](docs/nary_graph.md). The agent
follows a bounded deterministic tool policy; it is not an unrestricted planner.

## Submission checklist

- [ ] Participant reviews code, graph model, source/evidence semantics and limitations.
- [ ] Verify final Actions run and reproduce demo on the presenting laptop.
- [ ] Record the actual three-minute screen walkthrough; no video is claimed yet.
- [ ] Include public source repo, local setup, track, graph queries and AI disclosure.
- [ ] Check current organizer submission form/deadline and submit personally.
- [ ] Keep `.env`, credentials, restricted data and raw local annotation drafts out of Git.
- [ ] Discuss historical-prototype reuse eligibility with organizers if required.

No AWS deployment, paid Bedrock validation or public hosted service is claimed.
