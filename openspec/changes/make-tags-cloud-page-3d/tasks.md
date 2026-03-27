## 1. Flask route and template

- [ ] 1.1 Add `GET /tags/3d/` in `app-service/flask/app.py` rendering `tags_3d.html`
- [ ] 1.2 Create `app-service/flask/templates/tags_3d.html` with nav, WebGL container, and script hooks

## 2. Assets and libraries

- [ ] 2.1 Add Three.js (CDN with SRI or copy `three.min.js` under `flask/static/` per CSP policy)
- [ ] 2.2 Add optional `CSS2DRenderer` build or sprite-based text approach as chosen in implementation

## 3. Data and visualization

- [ ] 3.1 Fetch `/api/tags/get/`, parse JSON to `{ name, count }[]` (mirror `tags.html` logic)
- [ ] 3.2 Sort by count, cap to max N (default 200, configurable constant in script)
- [ ] 3.3 Build 3D positions (e.g. sphere or jittered ball), scale/color by count
- [ ] 3.4 Implement orbit controls (pointer + touch if feasible)

## 4. UX and errors

- [ ] 4.1 On API error, show visible message in DOM
- [ ] 4.2 On WebGL init failure, show fallback message; keep nav working
- [ ] 4.3 Hover or click shows tag name and count (tooltip or console strip optional)

## 5. Navigation and docs

- [ ] 5.1 Add “3D cloud” link in `tags.html` nav and in `bot.html` tag section
- [ ] 5.2 Add back link from `tags_3d.html` to `/tags/` and home

## 6. Verify

- [ ] 6.1 Manual test: `/tags/3d/` with populated tags API
- [ ] 6.2 Manual test: API down and WebGL-disabled paths
