# Friend A change manifest

Complete one row per proposed source artifact. Do not copy the artifact to
`ugi/` while the hold is active.

| Local artifact | Intended canonical file after approval | Named insertion point | State/endpoint used | Verification note |
| --- | --- | --- | --- | --- |
| `fragments/evidence-decision-panel.html` | `ugi/index.html` | Dataset scope, source inspector, relationship result, action panel, saved case, review-task bodies | Selected record; `POST /api/relationships`; investigation/review records | No duplicate IDs; uses existing records and verdict semantics. |
| `styles/evidence-decision.css` | `ugi/assets/style.css` | After existing component styles | Existing UI state/classes only | Every new selector uses `ugi-a-`; no graph/orbit selector changed. |

## Collision check

- [x] No proposed change owns graph renderer/camera behavior.
- [x] CSS selectors use the `ugi-a-` prefix.
- [x] No backend/AWS fields were invented.
- [x] Artifact has been reviewed against `../UI_CONTRACT.md`.
