## ADDED Requirements

### Requirement: Geo globe page is reachable

The system SHALL expose an HTTP GET route under the Flask app that renders a dedicated **WebGL globe** page for geographic visualization of stored step geo fields (e.g. `/geo/`).

#### Scenario: User opens geo globe

- **WHEN** a client requests the geo globe route with a normal browser
- **THEN** the server responds with HTML that loads the globe shell (canvas/WebGL container, navigation, and script hooks)

### Requirement: Slim geo API

The system SHALL expose **`GET /api/storage_geo/`** under the Flask app, returning only rows suitable for the globe, each including **`number`**, **`ip`**, **`latitude`**, **`longitude`**, and **`city`** (values as strings or numbers consistent with storage). Rows without valid, non-sentinel coordinates SHALL be omitted (same validity rules as the globe page: e.g. exclude non-finite and `(0,0)` if treated as unknown).

#### Scenario: Client fetches geo slice

- **WHEN** a client requests `/api/storage_geo/` (optionally with a `limit` query parameter)
- **THEN** the response includes a JSON list (or a documented wrapper object with a `data` array) of records containing the five fields above

#### Scenario: Unauthenticated access for public globe

- **WHEN** the globe page loads without an authenticated session
- **THEN** `/api/storage_geo/` remains reachable under the same **public prefix** policy as `/api/storage_latest/` (documented in implementation)

### Requirement: Globe page data source

The **`/geo/`** page SHALL obtain marker data from **`GET /api/storage_geo/`** once that endpoint exists. Until migration, it MAY use **`GET /api/storage_latest/`** as a fallback. Plot points SHALL use **parseable numeric latitude and longitude** only.

#### Scenario: Successful load

- **WHEN** the geo API returns a list of records with `number`, `ip`, `latitude`, `longitude`, `city`
- **THEN** the client builds a set of globe markers sufficient to render the visualization

#### Scenario: API failure

- **WHEN** the API is unreachable or returns an error
- **THEN** the page SHALL show a user-visible error state and SHALL NOT leave the user on a blank WebGL view without explanation

### Requirement: Globe visual style (globe.gl reference)

The Earth representation SHALL follow the **look and feel** of the [globe.gl “US international outbound” airline-routes example](https://github.com/vasturiano/globe.gl/blob/master/example/airline-routes/us-international-outbound.html): **night Earth texture** on the sphere (e.g. `earth-night.jpg` from the three-globe / jsdelivr asset path used in that example or equivalent), and **points** styled in the same spirit (e.g. accent color, small radius on the surface, merged points if using globe.gl). **Animated arcs** between points are **optional** and only required if explicitly added as a product feature.

#### Scenario: Textured globe

- **WHEN** the user opens `/geo/` with WebGL available
- **THEN** the globe shows a night-style Earth image on the surface, not a flat placeholder color only

### Requirement: Globe interaction

The visualization SHALL display a **globe** (sphere representing Earth) and SHALL allow the user to **orbit and zoom** the camera (pointer and, where supported, touch).

#### Scenario: Orbit

- **WHEN** the user drags on the primary view
- **THEN** the camera moves around the globe in a predictable way (e.g. orbit controls)

### Requirement: Point–metadata affordance

For at least **hover or click** on a marker, the UI SHALL show **identifying metadata** (e.g. step number, city, and URL or shortened label) for the associated step.

#### Scenario: Inspect a point

- **WHEN** the user selects a marker (click) or hovers a marker (if implemented)
- **THEN** they see human-readable metadata tied to that step’s record

### Requirement: Performance cap

The system SHALL limit how many markers are drawn (by **sampling or truncating** the latest records) so that typical datasets remain interactive; the default cap SHALL be documented in `tasks.md` or code comments.

#### Scenario: Many geo steps

- **WHEN** the API returns more valid geo points than the configured cap
- **THEN** the visualization uses a subset (e.g. most recent) rather than freezing the page

### Requirement: Navigation from existing UI

The main bot dashboard or an existing nav cluster (tags / screenshots) SHALL include a **link** to the geo globe page, and the geo page SHALL link back to **home** and/or the main dashboard.

#### Scenario: Discoverability

- **WHEN** the user is on the linked entry page
- **THEN** they can open the geo globe without typing the URL manually

### Requirement: WebGL unavailable fallback

When WebGL is not available, the page SHALL display a **clear message** and SHALL keep global navigation usable.

#### Scenario: No WebGL

- **WHEN** WebGL context creation fails
- **THEN** a visible fallback message explains that the 3D globe cannot be shown
