## Why

The 2D `/tags/vectorfield/` page already visualizes tag-driven flow with particles and optional vector overlays. A **3D** variant adds depth, parallax, and room for richer field structure (e.g. vertical layering by embedding or tag metadata) while reusing the same tag data and control patterns as the rest of the tags visualization suite.

## What Changes

- New full-screen page **`/tags/vectorfield-3d/`** served by app-service (Flask), aligned with `tags_vis_shared.css` / `tags_vis_controls.js` (Freeze, Export PNG, density tiering, Socket.IO reload debounce pattern).
- **Three.js** scene: `PerspectiveCamera`, particle system in **world volume** (~cube or padded box), **3D vector field** \(noise + anchor-based components\) driving particle velocities.
- **Navigation**: link from `/tags/vectorfield/` and sibling tag-vis pages to the new route (and back).
- **Embeddings API** (optional backward-compatible extension): response MAY include **`vectors3d`** — per-word \([x,y,z]\) derived from spaCy `en_core_web_md` (e.g. first three normalized components or documented projection) so anchor positions and field directions are consistent in 3D. Clients that only read `vectors2d` remain unchanged.

## Capabilities

### New Capabilities

- `tags-vectorfield-3d`: New 3D vector-field visualization page, field model, optional `vectors3d` in embeddings payload, nav integration, and shared UX with existing tag vis pages.

### Modified Capabilities

- _(none — `semantic-cloud-words-combinator` is unrelated)_

## Impact

- **app-service**: new template (e.g. `tags_vectorfield_3d.html`), `app.py` route, `tag_embeddings.py` optional `vectors3d` in JSON; touch `tags_vectorfield.html` / other tag templates for nav links only.
- **No breaking changes** to existing `POST /api/tags/embeddings/` consumers: new field is additive.
- **Deployment**: template + optional small Python change; no new microservices.
