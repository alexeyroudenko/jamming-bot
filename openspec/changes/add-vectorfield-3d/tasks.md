## 1. API and data (optional 3D vectors)

- [x] 1.1 Extend `build_embeddings_response` in `app-service/flask/tag_embeddings.py` to optionally include `vectors3d` (parallel to `words`), using spaCy vector components with documented normalization; omit key when model/vectors unavailable.
- [x] 1.2 Ensure `POST /api/tags/embeddings/` JSON remains backward-compatible (existing tests or manual curl still pass).

## 2. Flask route and template

- [x] 2.1 Add `@app.route('/tags/vectorfield-3d/')` in `app-service/flask/app.py` rendering a new template (e.g. `tags_vectorfield_3d.html`).
- [x] 2.2 Add `tags_vectorfield_3d.html` with shared nav/toolbar pattern, Three.js `PerspectiveCamera`, `WebGLRenderer`, particle `BufferGeometry`, `fieldAt3`, anchor build from tags + embeddings (use `vectors3d` when present, else documented \(z\) fallback).
- [x] 2.3 Implement camera interaction (minimal drag orbit or reuse pattern from `tags_3d.html` if controls already available).
- [x] 2.4 Wire `TagsVisControls` (freeze, export PNG), density select, Socket.IO debounced `reloadData`, and status/banner like `tags_vectorfield.html`.

## 3. Optional visualization polish

- [x] 3.1 Add optional 3D “field vectors” overlay (line segments on a coarse 3D grid or anchor arrows), toggled by toolbar control, with performance cap.
- [x] 3.2 Map embedding positions with min-max normalization extended to three axes (consistent with 2D page’s \([-1,1]\) mapping philosophy).

## 4. Navigation and discoverability

- [x] 4.1 Add links to `/tags/vectorfield-3d/` from `tags_vectorfield.html` and other tag-vis templates that already cross-link (`tags.html`, `tags_3d.html`, constellation/chaos/phrases as applicable).
- [x] 4.2 Add reverse link from 3D page back to 2D vector field and home.

## 5. Verification

- [x] 5.1 Manually verify: page loads, particles move, freeze/export work, reload on tag change, no console errors; test with and without `vectors3d` in API response.
