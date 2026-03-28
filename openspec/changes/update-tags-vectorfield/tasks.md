## 1. Performance and motion

- [x] 1.1 Add a small helper (inline or in `tags_vis_controls.js`) to compute effective `PARTICLES`, `MAX_DPR`, and optionally `MAX_TAGS` from `prefers-reduced-motion` and viewport / `hardwareConcurrency`.
- [x] 1.2 Re-run `layoutParticles` / resize paths when effective `PARTICLES` changes (e.g. orientation) if the tier can change.
- [x] 1.3 When `prefers-reduced-motion: reduce`, prefer **frozen-by-default** or minimal `tAnim` advancement (document choice in code comment).

## 2. Reload coalescing

- [x] 2.1 Replace direct `reloadData()` calls from Socket.IO handlers with a **debounced** `scheduleReload()` (single in-flight guard optional).
- [x] 2.2 Ensure manual first load still runs immediately; only burst paths use debounce.

## 3. UX / status

- [x] 3.1 During `reloadData()`, set status text to loading/updating; clear on success/failure.
- [x] 3.2 Optional: minimal toolbar control for “Density: low / med / high” overriding auto tier (stores in `sessionStorage`).

## 4. Field tuning

- [x] 4.1 Weight anchor influence by tag **count** (monotonic, normalized) in `buildAnchorsFromEmb`.
- [x] 4.2 Verify fallback path (no embeddings) unchanged visually aside from counts.

## 5. Assets / CSP

- [x] 5.1 Align Three.js script URL with sibling tag vis pages; if unpkg is blocked in prod, copy min build to `flask/static/` and switch `src`.

## 6. Verify

- [x] 6.1 Desktop: embeddings on/off, freeze, export PNG.
- [x] 6.2 Simulate rapid `tags_updated` (devtools or mock) — single network wave per debounce window.
- [x] 6.3 Reduced motion: lower cost path active, no runaway RAF work.
