## ADDED Requirements

### Requirement: 3D vector field page route

The system SHALL expose an HTTP GET route `/tags/vectorfield-3d/` that renders a full-viewport Three.js visualization of particles advected by a three-dimensional vector field derived from tag embeddings and procedural noise, using the same shared tag-visualization chrome (nav, toolbar pattern, Freeze / Export) as other `/tags/*` art pages unless explicitly documented as deferred in tasks.

#### Scenario: Page loads

- **WHEN** a client requests `GET /tags/vectorfield-3d/`
- **THEN** the response SHALL be HTML that loads the visualization script and shared styles consistent with `tags_vis_shared.css`

#### Scenario: Navigation cross-links

- **WHEN** the 2D vector field page (`/tags/vectorfield/`) is shown
- **THEN** it SHALL include a visible link to `/tags/vectorfield-3d/` alongside other tag visualization links

### Requirement: Three-dimensional field and particles

The visualization SHALL maintain a bounded 3D world volume in which particle positions are updated each frame using a velocity field that combines at least (a) time-varying procedural noise components on all three axes and (b) anchor-based directional bias from tag embedding data mapped into 3D positions.

#### Scenario: Particles stay bounded

- **WHEN** particles are advected over time
- **THEN** the implementation SHALL wrap or respawn particles that exit the configured world bounds so the scene does not diverge numerically

#### Scenario: Reduced motion and density tiers

- **WHEN** `prefers-reduced-motion: reduce` is active or the user selects a lower density tier
- **THEN** the system SHALL reduce animation cost (e.g. fewer particles and/or slower time evolution) in line with the pattern used on `/tags/vectorfield/`

### Requirement: Optional vectors3d in embeddings response

The `POST /api/tags/embeddings/` handler SHALL remain backward-compatible. When spaCy vectors are available for a word, the JSON response MAY include a `vectors3d` array parallel to `words`, where each element is an array of three finite numbers representing a consistent 3D direction or position seed for that word for use by the 3D vector field page. When not implemented or unavailable, the field SHALL be omitted and the 3D page SHALL still function using a documented client-side fallback for the third axis.

#### Scenario: Legacy clients unchanged

- **WHEN** a client parses only `vectors2d` and ignores unknown keys
- **THEN** its behavior SHALL be unchanged whether or not `vectors3d` is present

#### Scenario: 3D page consumes optional field

- **WHEN** `vectors3d` is present and valid for a subset of tags
- **THEN** the 3D visualization SHALL use those values for anchor placement and/or field direction for those tags

### Requirement: Live tag updates

The 3D page SHALL subscribe to the same Socket.IO events used by the 2D vector field page for tag-driven reloads (`tags_updated`, `analyzed` or equivalent) and SHALL debounce or coalesce rapid events so multiple bursts do not overlap unstable reloads.

#### Scenario: Debounced reload

- **WHEN** two qualifying events arrive within a short interval
- **THEN** at most one data reload cycle SHALL run for that interval (same order of magnitude as the 2D page debounce)
