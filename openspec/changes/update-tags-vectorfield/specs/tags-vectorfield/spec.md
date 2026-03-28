## MODIFIED Requirements

### Requirement: Adaptive performance for the vector field

The vector field page SHALL reduce GPU/CPU work on constrained clients by lowering particle count, pixel ratio, and/or animation advancement when appropriate (e.g. `prefers-reduced-motion: reduce` and/or coarse device heuristics), while preserving the current default appearance on capable desktops with no reduced-motion preference.

#### Scenario: Reduced motion preference

- **WHEN** the user agent reports `prefers-reduced-motion: reduce`
- **THEN** the page SHALL use a lower-cost configuration (fewer particles and/or less temporal animation) compared to the default desktop path

#### Scenario: Capable desktop

- **WHEN** the user agent does not request reduced motion and the viewport is typical desktop size
- **THEN** the visualization MAY use the higher particle budget currently used as the default (approximately thousands of points)

### Requirement: Coalesced live reloads

The page SHALL NOT trigger unbounded concurrent reloads of tag and embedding data when multiple Socket.IO events arrive in a short interval.

#### Scenario: Burst of tag update events

- **WHEN** several `analyzed` or `tags_updated` events fire within a short window
- **THEN** the page SHALL coalesce them (e.g. debounced trailing reload) so at most one reload runs per coalescing window

### Requirement: Visible loading state

While tag or embedding fetches are in progress, the page SHALL indicate progress in the existing status area (not only the error banner).

#### Scenario: User triggers reload

- **WHEN** a data reload starts
- **THEN** the status strip shows a loading/updating message until completion or failure

### Requirement: Tag-count-aware field influence

When embeddings are available, anchor contributions to the flow field SHALL incorporate tag frequency (count) so that more frequent tags influence local flow more than rare tags, without breaking the fallback noise-only field.

#### Scenario: Embeddings present

- **WHEN** anchors are built from tags with counts and embedding vectors
- **THEN** higher-count tags have stronger steering influence than lower-count tags at comparable distance

### Requirement: Three.js delivery consistent with deployment

The page SHALL load Three.js in a way compatible with the project’s Content-Security-Policy for tag visualization pages (CDN allowed by policy, or self-hosted under Flask static).

#### Scenario: CSP blocks third-party script

- **WHEN** production CSP disallows the chosen CDN host
- **THEN** documentation or implementation switches to a self-hosted `three.min.js` under `flask/static/` (or another allowed origin)
