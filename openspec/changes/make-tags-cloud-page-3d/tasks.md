## 1. Flask route and template

- [x] 1.1 Add `GET /tags/3d/` in `app-service/flask/app.py` rendering `tags_3d.html`
- [x] 1.2 Create `app-service/flask/templates/tags_3d.html` with nav, WebGL container, and script hooks

## 2. Assets and libraries

- [x] 2.1 Add Three.js (CDN with SRI or copy `three.min.js` under `flask/static/` per CSP policy)
- [x] 2.2 Add optional `CSS2DRenderer` build or sprite-based text approach as chosen in implementation

## 3. Data and visualization

- [x] 3.1 Fetch `/api/tags/get/`, parse JSON to `{ name, count }[]` (mirror `tags.html` logic)
- [x] 3.2 Sort by count, cap to max N (default 200, configurable constant in script)
- [x] 3.3 Build 3D positions (e.g. sphere or jittered ball), scale/color by count
- [x] 3.4 Implement orbit controls (pointer + touch if feasible)

## 4. UX and errors

- [x] 4.1 On API error, show visible message in DOM
- [x] 4.2 On WebGL init failure, show fallback message; keep nav working
- [x] 4.3 Hover or click shows tag name and count (tooltip or console strip optional)

## 5. Navigation and docs

- [x] 5.1 Add “3D cloud” link in `tags.html` nav and in `bot.html` tag section
- [x] 5.2 Add back link from `tags_3d.html` to `/tags/` and home

## 6. Verify

- [x] 6.1 Manual test: `/tags/3d/` with populated tags API
- [x] 6.2 Manual test: API down and WebGL-disabled paths
