## Why

The `/tags/vectorfield/` page already combines **tag embeddings** (`POST /api/tags/embeddings/`) with a **2D flow field** (noise + anchor directions) and shared **Freeze / Export** controls. Iteration is needed to improve **performance on weak devices**, **stability under burst Socket.IO events**, **visual clarity** of the field, and **alignment** with the rest of the tags visualization suite (shared patterns, hints, asset policy).

## What Changes

- **Performance & motion**: Cap particle count and animation cost using viewport / `prefers-reduced-motion` (and optional manual density), without removing the current default look on capable desktops.
- **Live updates**: Debounce or coalesce `analyzed` / `tags_updated` reloads so rapid backend events do not stack concurrent fetches or thrash the GPU loop.
- **UX polish**: Clear loading / “rebuilding field” state in the status strip; optional toolbar controls (e.g. particle budget or noise vs embedding mix) if kept minimal.
- **Field quality (incremental)**: Small, documented tweaks to how embedding directions blend with noise (e.g. normalization, weighting by tag count) so the visualization better reflects tag importance.
- **Assets**: Document or implement preferred Three.js delivery (CDN vs `flask/static/`) consistent with CSP used in production for other tag vis pages.

## Capabilities

### New Capabilities

- `tags-vectorfield` (delta): Amendments to the existing vector-field page behavior: performance caps, reload behavior, UX states, and field tuning.

### Modified Capabilities

- _(none in `openspec/specs/` today — delta lives in this change’s `specs/` only)_

## Impact

- **app-service**: `templates/tags_vectorfield.html`, possibly `static/tags_vis_shared.css` / `tags_vis_controls.js` if shared patterns are reused.
- **No breaking API changes** to `/api/tags/get/` or `/api/tags/embeddings/`; optional query/body usage stays backward-compatible.
- **Deployment**: static/template-only; no new microservices.
