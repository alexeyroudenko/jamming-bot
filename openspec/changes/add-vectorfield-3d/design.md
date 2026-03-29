## Context

- Today `/tags/vectorfield/` uses **orthographic** 2D, `fieldAt(x,y,t)` blending **noise** with **anchors** built from `POST /api/tags/embeddings/` (`vectors2d` only; see `tag_embeddings.py`).
- Sibling pages (`tags_3d`, constellation, chaos) already use **Three.js** and shared chrome (`tags_vis_shared.css`, `tags_vis_controls.js`).
- Users expect the same **toolbar affordances** (density, freeze, export) and **live reload** debouncing under Socket.IO bursts.
- Use STYLE_GUIDE.md
 
## Goals / Non-Goals

**Goals:**

- Ship **`GET /tags/vectorfield-3d/`** with a readable 3D particle flow and optional **field vector** overlay (lines or short segments in 3D), reusing style-guide colors.
- Keep **60fps target** on mid-tier hardware via tiered particle counts and DPR caps (mirror 2D page logic).
- **Additive** API: embeddings JSON MAY include `vectors3d` array parallel to `words` / `vectors2d`.

**Non-Goals:**

- VR/WebXR, multi-user collaboration, or replacing the 2D page.
- Full scientific flow visualization (streamtubes, LIC); simple arrows / segments are enough for v1.
- Changing tags-service schema or tag storage.

## Decisions

1. **Third dimension source**  
   - **Preferred**: extend `build_embeddings_response` to compute **`vectors3d`** as normalized components \(v[0], v[1], v[2]\) from the same spaCy doc vectors already used (document exact formula in code comment).  
   - **Fallback** if model dimensionality or vectors are degenerate: derive \(z\) client-side from deterministic function of `vectors2d` + tag index (documented) so the page still runs without API changes in edge builds.

2. **Camera**  
   - **PerspectiveCamera** with orbit-style interaction: either minimal **manual** rotate (pointer drag) or **OrbitControls** from Three examples — prefer **Controls** only if available without heavy new asset pipeline (r128: often copy minimal orbit from examples or use built-in if project already vendors it). Decision: start with **simple yaw/pitch** on drag in-template to avoid extra script dependencies unless `tags_3d` already imports controls.

3. **World bounds**  
   - Normalized anchor positions mapped to a **symmetric box** (e.g. \([-1,1]^3\) scaled by `worldHalf` per axis) analogous to current 2D \([-1,1]\) min-max mapping extended to \(z\).

4. **Field model**  
   - `fieldAt3(x,y,z,t) -> {vx,vy,vz}`: sum of **curl-like noise** (3D analog of current `noise2`) plus **anchor influence** weighted by inverse distance (or distance²) in 3D, using anchor direction \((dx,dy,dz)\) from normalized embedding triplet.

5. **Export**  
   - Reuse **Export PNG** via current canvas/renderer snapshot; ensure vector overlay and particles share one render pass.

## Risks / Trade-offs

- **Performance** — 3D + more particles burns GPU → [Mitigation] same tier table as 2D; default particle cap lower than 2D if needed.  
- **API surface** — extra JSON keys → [Mitigation] optional field; Flask returns only when implementation enabled; document in OpenAPI/comments if any.  
- **CSP / CDN** — Three.js from unpkg → [Mitigation] align with existing tag pages; note in tasks if copying to `flask/static/` is required for strict CSP.

## Migration Plan

- Deploy app-service; no DB migrations. Rollback: remove route + template link; API extra field ignored by old clients.

## Open Questions

- Whether to reuse **exact** OrbitControls from `tags_3d` or keep zero new dependencies with minimal drag rotation (resolve during implementation by inspecting `tags_3d.html`).
