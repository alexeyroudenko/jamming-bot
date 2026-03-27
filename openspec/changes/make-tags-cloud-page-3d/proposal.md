## Why

The current tag cloud at `/tags/` is a 2D canvas layout. A dedicated **3D** view improves exploration of tag frequency and relationships and aligns with the project’s experimental, visual-first dashboard. This change adds a new page (or mode) without removing the existing 2D experience unless we explicitly consolidate later.

## What Changes

- Add a **3D tag cloud page** (new route, e.g. `/tags/3d/` or equivalent) that visualizes tags from the existing tags API (`/api/tags/get/` or tags-service).
- Use **WebGL** (Three.js or similar) for rendering; keep bundle size and CSP implications in mind.
- **Navigation**: link from `bot.html` / `tags.html` nav to the 3D page and back.
- Preserve **accessibility basics**: keyboard focus for nav, optional reduced-motion respect where feasible.
- **No breaking API changes** to tags-service; reuse existing JSON shape.

## Capabilities

### New Capabilities

- `tags-cloud-3d`: User-facing 3D tag cloud page for Jamming Bot: data source, layout, interaction (orbit / hover / click), performance bounds, and navigation from existing tag pages.

### Modified Capabilities

- _(none — no existing OpenSpec specs in `openspec/specs/` yet)_

## Impact

- **app-service** Flask: new route, new template (or static entry), static assets (Three.js from CDN or vendored).
- **Templates**: `tags.html`, `bot.html` (or shared nav) — add links.
- **Dependencies**: optional npm-free approach via CDN script tags consistent with current `tags.html` pattern.
- **Deployment**: no new microservices; ingress unchanged unless new path needs explicit rule (usually covered by existing app prefix).
