# UI workbench — local collaboration area

This directory is a **local-only preparation area** while backend/AWS work is in
progress. It is intentionally outside the live `ugi/` application package.

- `ui_friend_a/` holds the evidence/decision presentation module.
- `ui_friend_b/` holds the graph/guided-state interaction module.
- `UI_CONTRACT.md` is the shared source of truth for visible API/state behavior.

Do not put full copies of `ugi/index.html`, `ugi/assets/style.css`, or
`ugi/assets/app.js` here. Store isolated fragments, modules and scoped styles
only. See root `TICKETS.md` for the hold rules and later integration gate.

No Git staging, commits, pushes, merges, rebases or pull requests are permitted
from this workbench until the backend/AWS owner explicitly approves them.
