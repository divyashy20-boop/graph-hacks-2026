# UGI UI delivery tickets

## Current collaboration mode — local-only UI preparation

**Status:** active until the backend/AWS owner explicitly approves integration and push.

This repository is shared by three contributors. The backend/AWS owner is working
on a separate deployment track. The two UI contributors prepare their work
locally, in isolated folders, so the backend working tree and remote branch are
not disturbed.

### Hard rules during the hold

1. **Do not run `git add`, `git commit`, `git push`, `git merge`, `git rebase`,
   or create a pull request.** No UI work leaves this laptop/repository until
   the backend/AWS owner explicitly says it is safe.
2. Do not edit live application files under `ugi/`, API routes, Docker files,
   deployment files, environment files, or backend tests during the hold.
3. UI contributor A writes only under `ui_workbench/ui_friend_a/`; UI
   contributor B writes only under `ui_workbench/ui_friend_b/`.
4. Do not copy the complete `index.html`, `style.css`, or `app.js` into either
   workspace. Store only new, clearly named fragments/modules/styles plus a
   short change manifest. This keeps later integration reviewable.
5. `ui_workbench/UI_CONTRACT.md` is the shared API/state contract. If a desired
   backend/AWS capability is absent from the contract, record it as a question;
   do not invent an endpoint, response field, or security behavior in the UI.
6. Screenshots, browser recordings, temporary preview data, and local logs go
   in each contributor's `artifacts/` directory. They are local-only and must
   never be staged.

### Ownership split

| Contributor | Workspace | Owns | Must not own during the hold |
| --- | --- | --- | --- |
| UI friend A | `ui_workbench/ui_friend_a/` | Information hierarchy, controls, source inspector, verdict/action presentation, CSS component states | SVG/WebGL graph algorithms, camera interaction, guided-agent request logic |
| UI friend B | `ui_workbench/ui_friend_b/` | 2D/3D map interaction concepts, graph legend/status display, orbit controls, guided-agent/receipt presentation concepts | Hero/control-deck redesign, inspector content structure, action authorization copy |
| Backend/AWS friend | outside UI workspaces | API contract, feature availability, auth/deployment/AWS work | Local UI workspace implementation |

The labels `ui_friend_a` and `ui_friend_b` are intentional neutral folder names;
replace the contributor names in this document only when both people agree.

### Integration gate — only after explicit approval

When approval is given, do this in order:

1. Confirm the backend branch/commit, target environment, API contract, and
   feature flags with the backend/AWS owner.
2. Review each workspace's `CHANGE_MANIFEST.md`; reject any overlapping
   canonical-file ownership before copying code.
3. Create **two local integration branches** from the approved backend commit:
   one for friend A's changes and one for friend B's changes. Do not push them
   until the owner permits it.
4. Integrate friend A's presentation fragments into `ugi/index.html` and
   `ugi/assets/style.css`, then run the assigned checks.
5. Integrate friend B's interaction modules into `ugi/assets/app.js` and any
   narrowly scoped CSS. Preserve the 2D map, native WebGL orbit mode, and 2D
   fallback.
6. Run `python -m pytest -q`, the dashboard/guided UI tests, and a real
   memory-mode demonstration. Run Docker/AWS checks only with the backend
   owner's approved environment.
7. Resolve one combined review checklist, then wait again for explicit push
   approval. Do not make a remote update merely because local checks pass.

## New UI tickets — local preparation only

### UI-009 — Establish the frontend/backend display contract

**Status:** Complete locally — 2026-10-17
**Priority:** P0
**Owner:** both UI contributors (read/contract only)
**Workspace:** `ui_workbench/UI_CONTRACT.md`
**Depends on:** none

Record the existing API responses and all visible UI states that the backend can
currently support. Add a clearly marked `Pending backend confirmation` section
for AWS work; do not guess response schemas or add fake success states.

**Acceptance criteria:**

- Documents the existing graph, record, upload, relationship, investigation,
  health, guided-agent and receipt-freshness surfaces.
- Keeps evidence verdict semantics distinct: `SOURCE_ASSERTED`,
  `SOURCE_NEGATED`, `RULE_DERIVED`, `CONNECTED_ONLY`, `CONTRADICTED`,
  `HYPOTHESIS`, and `UNKNOWN`.
- Lists loading, empty, error, authorization, feature-disabled, date-filtered,
  WebGL-fallback, stale, and unknown-receipt states.
- Contains no live `ugi/` edits and no unapproved AWS assumption.

### UI-010 — Evidence and decision presentation module

**Status:** Complete locally — UI friend A, 2026-10-17
**Priority:** P1
**Owner:** UI friend A
**Workspace:** `ui_workbench/ui_friend_a/`
**Depends on:** UI-009

Prepare a restrained presentation module for dataset controls, source
provenance, relationship verdicts, action preview/authorization, saved cases,
and review decisions. The goal is to make existing backend evidence legible in a
demo, not to redesign the product or manufacture new results.

**Allowed local files:** `README.md`, `CHANGE_MANIFEST.md`, `fragments/`,
`styles/`, `artifacts/`.

**Acceptance criteria:**

- Every proposal maps to current fields in `UI_CONTRACT.md`.
- Source quote, filename, exact offsets, role participants, verdict status,
  reasoning limits, preview state, and authorized-write state remain distinct.
- CSS class names are prefixed `ugi-a-` to prevent integration collisions.
- The manifest names each eventual canonical insertion point; it must not ask
  friend B to modify the same DOM section.
- No change is copied into `ugi/` and no Git operation is performed.

### UI-011 — Graph and guided-state interaction module

**Status:** Complete locally — UI friend B, 2026-10-18
**Priority:** P1
**Owner:** UI friend B
**Workspace:** `ui_workbench/ui_friend_b/`
**Depends on:** UI-009

Prepare interaction modules for the existing 2D evidence map, native 3D orbit
mode, visible graph states, and the feature-gated guided-agent/receipt panel.
Do not replace working graph semantics or make receipt freshness look like a
guarantee of safe external action.

**Allowed local files:** `README.md`, `CHANGE_MANIFEST.md`, `modules/`,
`styles/`, `artifacts/`.

**Acceptance criteria:**

- Supports 2D selection/highlighting and preserves the source inspector path.
- Treats 3D as the existing native WebGL mode and keeps a clear return-to-2D
  fallback for unavailable WebGL.
- Shows guided mode only when backend health/config says both flags are enabled.
- Renders `VALID`, `STALE`, and `UNKNOWN` receipt states honestly; only
  `VALID` can be described as reusable at the time of the recheck.
- JavaScript names are prefixed `ugiB` and CSS names are prefixed `ugi-b-`.
- No change is copied into `ugi/` and no Git operation is performed.

### UI-012 — Approved integration and demonstration gate

**Status:** Blocked — requires backend/AWS owner approval
**Priority:** P0
**Owner:** both UI contributors with backend/AWS owner review
**Canonical targets after approval:** `ugi/index.html`, `ugi/assets/style.css`,
`ugi/assets/app.js`, and only when required `ugi/assets/guided.js`
**Depends on:** UI-010, UI-011, explicit approval

Integrate the two prepared modules against the exact backend commit approved by
the backend/AWS owner. This is the first ticket allowed to touch active UI
assets, and it remains local until a separate push approval is given.

**Acceptance criteria:**

- Both manifests are integrated without duplicate IDs, duplicate event
  handlers, unscoped global CSS, or conflicting ownership of a DOM section.
- Existing graph, provenance, verdict, authorization, 2D/3D, fallback, and
  guided-memory tests pass.
- Live backend/AWS states are shown only when verified in the approved
  environment; unavailable features have an honest UI state.
- A local demo proves incident, supply, and research presets plus one guided
  receipt freshness path when feature flags are available.
- Nothing is pushed without a new explicit instruction from the backend/AWS
  owner.

## Historical delivery protocol (UI-001 to UI-008)

This is a UI-only backlog. Work on one ticket at a time, in a branch named
`ticket/<id>-<short-name>`. The graph, evidence, API, and MCP semantics are
out of scope unless a UI change cannot function without a separately approved
backend change.

Before every ticket commit:

1. Review `git status` and update `.gitignore` only for newly introduced local
   or generated artifacts. Never ignore committed UI assets, demonstration
   data, or required evaluation evidence.
2. Run the ticket's checks and the relevant existing regression tests.
3. Commit only the ticket's scoped work, push its branch, then merge it to
   `main` after checks pass. This historical instruction is suspended by the
   current local-only collaboration mode above.

## UI-001 — Evidence console foundation

**Status:** Complete
**Priority:** P0  
**Depends on:** none

Establish a deliberate visual language for UGI: an evidence-operations console
with strong hierarchy, technical restraint, and clear state cues. This is not
a generic glass-card AI dashboard.

**Acceptance criteria:**

- No API endpoint, graph meaning, evidence wording, or action authorization
  behavior changes.
- The shell, controls, panels, typography, and result states form one coherent
  system at desktop and 320px widths.
- Source-backed, possible, conflicting, and unknown states remain visibly and
  textually distinct.
- Keyboard focus, readable contrast, and reduced-motion behavior are present.

## UI-002 — Interactive 2D evidence map

**Status:** Complete
**Priority:** P0  
**Depends on:** UI-001

Rework the current SVG network into a spatial, Flourish-inspired evidence map
with generous layout, directional relations, node/claim/event selection,
direct-neighbour highlighting, and clear dimming of unrelated context.

**Acceptance criteria:**

- Selection preserves the current source-inspector behavior and clears from the
  empty canvas.
- Direction, history, polarity, modality, and whole-event participation remain
  legible without implying unsupported facts.
- Pan, zoom, drag, refresh, and keyboard selection remain reliable.

## UI-003 — Spatial interface art direction

**Status:** Complete
**Priority:** P0  
**Depends on:** UI-002

Reframe the existing dashboard with an immersive spatial-tech direction inspired
by the supplied 5G AR reference: deep-violet depth, oversized typography,
red/blue signal accents, and a sculptural header composition. Adapt the visual
grammar; do not copy the original brand, content, illustration, or assets.

**Acceptance criteria:**

- All functional controls and evidence semantics remain unchanged.
- The visual system feels like one authored experience, not a generic dark
  dashboard or a pasted marketing template.
- Decorative depth remains optional, responsive, and suppressed for
  reduced-motion users.

## UI-004 — Local 3D orbit graph

**Status:** Complete
**Priority:** P0
**Depends on:** UI-003

Add a `3D Orbit` mode beside the 2D evidence map. It uses a native, local
WebGL renderer in the existing UI asset: no CDN, package, API change, or new
runtime dependency is introduced.

**Acceptance criteria:**

- Switching views retains dataset, timeline, selection, and inspector context.
- Nodes, links, events, direction, and selected evidence communicate the same
  semantics as 2D.
- Orbit, pan, zoom, focus, auto-rotate, resize, WebGL fallback, and
  reduced-motion paths are deliberately handled.

## UI-005 — Investigation storytelling and provenance

**Status:** Complete
**Priority:** P1  
**Depends on:** UI-004

Make the source inspector, relationship verdict, action preview, saved cases,
and review queue presentation-ready for a live walkthrough. Lead with one
consistent completed verdict, then make its trace, source evidence, and limits
inspectable without changing what the graph asserts.

**Acceptance criteria:**

- Every conclusion makes its status, rule trace, source quote, filename,
  offsets, and limits easy to read.
- Preview and authorized persistence cannot be confused.
- The three supplied demonstrations work consistently in both graph modes.

## UI-006 — Responsive demo quality gate

**Status:** Complete
**Priority:** P0  
**Depends on:** UI-005

Validate the final UI locally and in Docker, including desktop/mobile layouts,
keyboard paths, empty/loading/error states, and the complete demo walkthrough.
This ticket adds client-side loading/error recovery and keyboard guidance; live
browser and Docker visual checks remain environment-dependent and are reported
honestly at handoff.

**Acceptance criteria:**

- UI/API regressions pass and live FalkorDB checks are clearly labelled when
  available.
- No transient local build, browser-test, or visual-review artifact is staged.
- README/demo material describes the UI capabilities and limitations honestly.

## UI-007 — Editorial interface reset

**Status:** Complete
**Priority:** P0
**Depends on:** UI-006

Replace the over-styled spatial-tech treatment with a restrained evidence
workspace: neutral surfaces, one warm operational accent, readable sans-serif
utility text, and a composed header that does not compete with the graph.
Memory-mode demonstration selection must also load the named synthetic dataset
instead of presenting an empty graph.

**Acceptance criteria:**

- No Impact display treatment, neon-purple field, faux-terminal microtype, or
  decorative 3D hero remains in the default UI.
- The initial incident demonstration has visible source-backed graph data in
  memory mode; production/FalkorDB behavior is unchanged.
- The 2D and 3D evidence views retain their existing semantics and controls.

## UI-008 — Palette correction and Orbit fallback

**Status:** Complete
**Priority:** P0
**Depends on:** UI-007

Restore the established dark spatial composition while limiting the visual
change to a calmer palette and readable utility type. Fix the 3D fallback so
it never overlaps the empty graph state.

**Acceptance criteria:**

- The dark layout remains recognizably continuous with the earlier dashboard.
- Utility labels use readable sans-serif text, not faux-terminal microtype.
- A WebGL fallback is a single clear state with a working return-to-2D action.
