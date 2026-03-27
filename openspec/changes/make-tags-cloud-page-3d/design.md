## Context

- **Current state**: `/tags/` serves `tags.html`, a full-viewport **2D canvas** tag cloud fed by `GET /api/tags/get/` (Flask → tags-service). Tags include counts; layout uses physics-style repulsion and mouse repel.
- **Stack**: Flask templates, inline scripts, Socket.IO already used elsewhere; D3 v3 used heavily on `bot.html` for graphs.
- **Constraint**: Prefer consistency with existing pattern (single template + CDN scripts) unless we introduce a build step for this change only.

## Goals / Non-Goals

**Goals:**

- Ship a **3D tag cloud** page reachable from the app (new route).
- Reuse **existing tag API**; no schema change to tags-service.
- **Orbit / zoom** interaction (mouse + touch where practical); **hover** or **click** shows tag name and count.
- **Performance**: cap max rendered labels (e.g. top N by count) with a documented default.

**Non-Goals:**

- Replacing or removing the 2D `/tags/` page in this change.
- Real-time Socket.IO updates on the 3D page (optional follow-up).
- Full accessibility audit for WebGL (beyond nav and fallback message).

## Decisions

1. **Renderer: Three.js (r128+ or current stable) via CDN**  
   - *Rationale*: Mature WebGL stack, sprites or `CSS2DRenderer` for text labels.  
   - *Alternative*: Raw WebGL — too much code; **Babylon.js** — heavier learning curve for one page.

2. **Layout: spherical or scattered 3D cloud with font size / scale from tag count**  
   - *Rationale*: Simple, readable; matches “cloud” mental model.  
   - *Alternative*: Force graph in 3D — overlaps with bot graph; defer.

3. **Route: `/tags/3d/`** serving a new template `tags_3d.html`  
   - *Rationale*: Clear URL, mirrors `/tags/phrases/`.  
   - *Alternative*: Query param `?mode=3d` on same template — harder to bookmark and test.

4. **Data**: Parse same JSON as `tags.html` (grouped tags endpoint); flatten to `{ name, count }` list server-side optional or client-side only — **client-side** to match 2D page and avoid Flask changes beyond route.

5. **CSP / SRI**: If production sets CSP, allow `cdnjs` or self-host `three.min.js` under `/flask_static/` (prefer **self-host** if CSP is strict — note in tasks).

## Risks / Trade-offs

- **[Risk] WebGL unavailable (old GPU, software rendering)** → Show short message in DOM: “WebGL required”; keep nav usable.  
- **[Risk] Too many tags → frame drops** → Cap N (e.g. 200) by sort on count; document in spec.  
- **[Risk] Text legibility in 3D** → Use billboarding sprites or CSS2D labels; limit simultaneous sharp labels.  
- **[Trade-off] CDN dependency** → Offline dev needs network unless file vendored.

## Migration Plan

1. Deploy Flask changes (new template + route).  
2. No DB migration.  
3. **Rollback**: remove route and template; revert nav links.

## Open Questions

- Exact **N** for max tags (product decision; default 150–200).  
- Whether to **self-host Three.js** immediately or use CDN like Socket.IO on `tags.html`.
