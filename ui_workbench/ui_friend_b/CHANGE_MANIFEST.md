# Friend B change manifest

Complete one row per proposed source artifact. Do not copy the artifact to
`ugi/` while the hold is active.

| Local artifact | Intended canonical file after approval | Named insertion point | State/endpoint used | Verification note |
| --- | --- | --- | --- | --- |
| `modules/graph-guided-state.js` | `ugi/assets/app.js` and, only if required, `ugi/assets/guided.js` | Existing graph state/mode updates and guided response rendering | `/api/graph`, `/health`, guided and receipt responses | Exposes `window.ugiB`; binds no duplicate event handlers. |
| `fragments/graph-guided-status.html` | `ugi/index.html` | Map caption/notice and guided panel status regions | Existing 2D/3D/fallback and receipt states | No duplicate IDs; existing control IDs stay unchanged. |
| `styles/graph-guided.css` | `ugi/assets/style.css` | After existing graph/guided styles | Existing UI state/classes only | Every class uses `ugi-b-`; no friend-A selector changed. |

## Collision check

- [x] No proposed change owns the hero, source inspector structure or action copy.
- [x] JavaScript names use the `ugiB` prefix; CSS classes use `ugi-b-`.
- [x] 2D map, native orbit and 2D fallback semantics remain intact.
- [x] Guided/receipt states match `../UI_CONTRACT.md`.
