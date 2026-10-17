# Friend B change manifest

Complete one row per proposed source artifact. Do not copy the artifact to
`ugi/` while the hold is active.

| Local artifact | Intended canonical file after approval | Named insertion point | State/endpoint used | Verification note |
| --- | --- | --- | --- | --- |
| `modules/graph_interaction.js` | `ugi/assets/app.js` | Lines 183–250 (`selectionContext`, `focusOpacity`, `selectRecord`, `clearSelection`, `bindPick`) | `GET /api/graph`, `GET /api/records/{id}`, `GET /api/events` | Tested with empty, single entity, binary claims, and n-ary relation events. Verified no silent edge-to-fact promotions. |
| `modules/orbit_interaction.js` | `ugi/assets/app.js` | Lines 750–1028 (`createOrbitRenderer`, `setViewMode`, fallback listeners) | Native WebGL canvas / shader compilation | Tested WebGL supported / unsupported detection; fallback switches cleanly to 2D without overlapping empty state. |
| `modules/graph_status.js` | `ugi/assets/app.js` | Lines 56–96 (`setGraphState`, `statusTone`, `statusTitle`, legend rendering) | `GET /health`, `GET /api/graph` (counts & truncation) | Maps all 7 verdict states from `UI_CONTRACT.md`. Tested truncation notice and empty state toggle. |
| `modules/guided_presentation.js` | `ugi/assets/guided.js` | Lines 1–92 (`runGuided`, `checkReceipt`, `showVerdict`, visibility listener) | `GET /health`, `POST /api/agent/guided`, `GET /api/agent/receipts/{id}/freshness` | Strictly requires both health flags. Honestly renders VALID, STALE, and UNKNOWN receipt states; only VALID is reusable. |
| `styles/interaction.css` | `ugi/assets/style.css` | Appended to stylesheet under a dedicated `/* UI-011 Friend B */` section | CSS custom properties `--signal`, `--amber`, `--red`, `--blue` | All classes scoped with `ugi-b-`. Includes high-contrast focus rings and reduced-motion rules. Zero collision with Friend A. |
| `modules/graph-guided-state.js` | `ugi/assets/app.js` and, only if required, `ugi/assets/guided.js` | Existing graph state/mode updates and guided response rendering | `/api/graph`, `/health`, guided and receipt responses | Exposes `window.ugiB`; binds no duplicate event handlers. |
| `fragments/graph-guided-status.html` | `ugi/index.html` | Map caption/notice and guided panel status regions | Existing 2D/3D/fallback and receipt states | No duplicate IDs; existing control IDs stay unchanged. |
| `styles/graph-guided.css` | `ugi/assets/style.css` | After existing graph/guided styles | Existing UI state/classes only | Every class uses `ugi-b-`; no friend-A selector changed. |

## Collision check

- [x] No proposed change owns the hero, source inspector structure or action copy.
- [x] JavaScript names use the `ugiB` prefix; CSS classes use `ugi-b-`.
- [x] 2D map, native orbit and 2D fallback semantics remain intact.
- [x] Guided/receipt states match `../UI_CONTRACT.md`.
