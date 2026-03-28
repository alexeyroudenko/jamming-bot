## Context

- **Route**: `GET /tags/vectorfield/` → `tags_vectorfield.html` (`app.py`).
- **Data**: `GET /api/tags/get/` then `POST /api/tags/embeddings/` with top tags by count; fallback field when embeddings missing.
- **Rendering**: Three.js r128 orthographic `Points`, additive blending, ~3200 particles, `MAX_TAGS` 48, simplex-like noise + IDW-weighted anchor directions.
- **Live**: Socket.IO `analyzed` / `tags_updated` both call `reloadData()` immediately.

## Goals / Non-Goals

**Goals:**

- Avoid **jank** and unnecessary **memory/CPU** when the tab is busy or the device is constrained.
- Prevent **reload storms** from Socket.IO.
- Keep **one-file** template style unless a tiny shared helper in `tags_vis_controls.js` clearly reduces duplication.
- Preserve current **aesthetic** (dark field, cyan-fast particles) as the default on capable hardware.

**Non-Goals:**

- Replacing Three.js with another renderer.
- New backend endpoints or changing embedding dimensions.
- Full mobile gesture redesign.

## Decisions

1. **Particle budget tiers**  
   - Derive effective `PARTICLES` (and optionally `MAX_DPR`) from `matchMedia('(prefers-reduced-motion: reduce)')` and a coarse screen heuristic (e.g. `innerWidth` / `hardwareConcurrency` if available).  
   - *Alternative*: single global constant — rejected; we already see OOM pressure elsewhere on the same host app.

2. **Socket reload coalescing**  
   - Single debounced `scheduleReload(delayMs)` (e.g. 400–800 ms) merging `analyzed` and `tags_updated`; trailing edge flush.  
   - *Alternative*: queue depth — heavier; debounce is enough.

3. **Status / loading UX**  
   - Set `tags-vis-status` to a short “Loading…” / “Updating field…” during `reloadData()`; restore anchor/particle summary after success.  
   - On error, keep existing banner + status line behavior.

4. **Anchor weighting**  
   - When building `anchors`, scale influence weights by tag **count** (e.g. sqrt or log1p) so high-frequency tags steer the field more than rare ones.  
   - Keep normalization so the field does not explode.

5. **Three.js source**  
   - Prefer **same CDN family** as `tags_constellation` / `tags_3d` if already standardized; otherwise add a one-line comment in `tasks.md` to self-host under `flask/static/` when CSP blocks unpkg.

## Risks / Trade-offs

- **Lower particles** may look sparse on large monitors — mitigate with tier that still allows ~3200 on desktop with `prefers-reduced-motion: no preference`.  
- **Debounced reload** delays freshness by one interval — acceptable for visualization.

## Migration Plan

1. Ship template/JS/CSS changes.  
2. Manual verify: cold load, embedding fallback, burst socket events, export PNG, freeze.  
3. Rollback: revert commit.

## Open Questions

- Exact tier constants (particle counts) — tune in implementation using a quick laptop + throttled CPU sample.  
- Whether to expose a **user-visible** density slider in v1 or only automatic tiers.
