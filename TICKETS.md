# UGI UI delivery tickets

## Delivery protocol

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
   `main` after checks pass.

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
