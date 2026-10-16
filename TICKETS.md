# UGI delivery tickets

## Delivery protocol

This backlog is intentionally sequential: start only the first ticket whose
dependencies are complete. Every ticket has its own branch named
`ticket/<id>-<short-name>`.

Before each ticket is committed:

1. Review `git status` and update `.gitignore` only for new local/generated
   artifacts introduced by that ticket. Never ignore source code, vendored
   runtime assets, demonstrations, or required evaluation evidence.
2. Run the ticket's stated checks plus the relevant existing regression suite.
3. Commit only the ticket's scoped changes, push its branch, and merge it to
   `main` only after its checks pass.

Do not overlap tickets or merge unrelated work into an active ticket branch.

## Correctness gates

### UGI-001 — Unify relationship verdicts

**Priority:** P0  
**Depends on:** none

Make `Engine.relationship()` produce one authoritative final reasoning verdict.
Derive the top-level status, `resolution.assessment`, rule metadata, and
explanation from that verdict so a result can never report `RULE_DERIVED` while
also saying `CONNECTED_BUT_NOT_ENTAILED`.

**Acceptance criteria:**

- A valid `DEPENDS_ON` chain returns `RULE_DERIVED`, the reachability rule ID,
  supporting claim IDs/path, and a compatible final assessment.
- Source assertions, negations, conflicts, unsupported connectivity, and
  unknown results retain their current semantic boundaries.
- Regression coverage includes the reported `proxy → backend → db` case and
  the existing shared-employer derivation.
- The complete test suite passes without paid or local-model calls.

### UGI-002 — Make scoped MCP entity lookup explicit

**Priority:** P0  
**Depends on:** UGI-001

Clarify the selected-project/dataset scope in the MCP contract. Add a bounded,
result-driven investigation workflow that resolves the requested subject and
object, evaluates the requested relationship, retrieves evidence when present,
and only then reports completion.

**Acceptance criteria:**

- `search_entities` clearly documents that `name` is an entity/service inside
  the already-selected project, not the project name itself.
- “Indirectly depends on” is mapped explicitly to
  `TRANSITIVELY_DEPENDS_ON` for this workflow.
- Wrong-scope feedback, at most two corrective retries, and incomplete-workflow
  reporting are visible in the tool history.
- Tests cover `nginx-flask-mysql` scope with `proxy` and `db`, ambiguity,
  evidence retrieval, premature completion, and an `UNKNOWN` completion.
- Live Qwen validation remains opt-in and is reported separately from mocks.

## UI foundation

### UGI-003 — Establish the dashboard visual system

**Priority:** P0  
**Depends on:** UGI-001

Replace the current utility dashboard styling with a responsive dark,
glassmorphic UGI visual system: typography, colour tokens, panels, result
states, focus treatment, and compact mobile layout. Preserve the existing
evidence-first wording and explicit action authorization.

**Acceptance criteria:**

- No endpoint or graph semantics change.
- The layout remains usable at 320px and desktop widths.
- Status, uncertainty, conflict, and source-backed states remain visually and
  textually distinguishable.
- Keyboard focus, contrast, and reduced-motion behavior are verified.

### UGI-004 — Upgrade the 2D evidence graph

**Priority:** P0  
**Depends on:** UGI-003

Implement a Flourish-style 2D graph experience using the existing API data:
spaced layout, direction indicators, event diamonds, claim styling, node/edge
selection, direct-neighbour highlighting, and dimming of unrelated records.

**Acceptance criteria:**

- Selecting a node highlights only its incident claims, neighbours, and
  relevant whole events; clicking empty canvas clears selection.
- Direction, historical status, polarity, modality, and event participation
  remain legible without implying unsupported facts.
- The source inspector receives the selected entity, claim, or event and keeps
  exact evidence/offsets available.
- Pan, zoom, drag, and keyboard selection work without breaking refreshes.

### UGI-005 — Add the local 3D orbit graph

**Priority:** P0  
**Depends on:** UGI-004

Add a user-controlled `3D Orbit` view alongside the 2D graph. Use a pinned,
locally served WebGL dependency with documented licence/provenance; do not add
a CDN dependency to the demo path.

**Acceptance criteria:**

- The user can switch between `2D Evidence` and `3D Orbit` without losing
  dataset, timeline, selection, or inspector context.
- Nodes, links, whole events, directed flow, selection, and source inspection
  preserve the same evidence semantics as 2D.
- Orbit, pan, zoom, click-to-focus, auto-rotate, resize, WebGL-unavailable, and
  reduced-motion paths are handled gracefully.
- The bundled dependency is explicitly whitelisted by the asset endpoint and
  is committed, not ignored.

### UGI-006 — Make evidence and investigations presentation-ready

**Priority:** P1  
**Depends on:** UGI-004, UGI-005

Refine the source inspector, relationship verdict card, action preview, saved
investigations, and review queue for the hackathon walkthrough.

**Acceptance criteria:**

- Verdict cards present one consistent final conclusion, rule trace, supported
  claim IDs, exact quote, source filename, and offsets.
- `CONNECTED_ONLY`, `UNKNOWN`, `HYPOTHESIS`, negation, and contradiction are
  clearly explained as non-equivalent outcomes.
- Action preview versus authorized persistent action remains impossible to
  confuse.
- The three supplied demonstration datasets load consistently and are usable
  in both graph modes.

### UGI-007 — Verify the final demo path

**Priority:** P0  
**Depends on:** UGI-002, UGI-006

Test and document the final local and Docker demo flows, covering engine
consistency, scoped agent investigations, 2D/3D presentation, provenance, and
authorized action boundaries.

**Acceptance criteria:**

- Unit/API/MCP tests pass; real FalkorDB checks run when the service is
  available and are labelled as live integration.
- The five agent requests are reported in strict and recovery modes with
  first-attempt correctness, completion, tool calls, evidence retrieval, and
  authorization outcomes separated.
- No evaluation artifact overwrites the original baseline reports.
- README/demo instructions identify known limitations honestly.
