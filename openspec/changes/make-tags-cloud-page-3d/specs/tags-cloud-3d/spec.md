## ADDED Requirements

### Requirement: 3D tag cloud page is reachable

The system SHALL expose an HTTP GET route under the Flask app that renders a dedicated 3D tag cloud page (e.g. `/tags/3d/`).

#### Scenario: User opens 3D tag cloud

- **WHEN** a client requests the 3D tag cloud route with a normal browser
- **THEN** the server responds with HTML that loads the 3D visualization shell (canvas/WebGL container and navigation)

### Requirement: Tags data from existing API

The 3D page SHALL obtain tag data using the same tags listing API used by the 2D tag cloud (`/api/tags/get/` or documented equivalent), without requiring a new tags-service endpoint.

#### Scenario: API returns tag groups

- **WHEN** the page loads and fetches tag data successfully
- **THEN** the visualization derives a list of tags with display names and numeric weights (e.g. counts) sufficient to size or color labels

#### Scenario: API failure

- **WHEN** the tags API is unreachable or returns an error
- **THEN** the page SHALL show a user-visible error state and SHALL NOT leave the user on a blank WebGL view without explanation

### Requirement: Three-dimensional layout and interaction

The visualization SHALL render tags in three dimensions and SHALL allow the user to orbit or rotate the view (pointer and, where supported, touch).

#### Scenario: Orbit interaction

- **WHEN** the user drags on the primary view
- **THEN** the camera or scene rotates so the relative positions of tags change in a predictable way

### Requirement: Performance cap

The system SHALL limit the maximum number of tags drawn in 3D to a configurable default (not less than 100 and not more than 500 unless explicitly overridden in implementation docs) by selecting the highest-weight tags first.

#### Scenario: Large tag set

- **WHEN** the API returns more tags than the configured maximum
- **THEN** only the top tags by weight are included in the 3D layout

### Requirement: Navigation from existing tag UI

The 2D tag cloud page or main bot navigation SHALL include a link to the 3D tag cloud page, and the 3D page SHALL link back to home and/or the 2D tag cloud.

#### Scenario: Cross-linking

- **WHEN** the user is on `/tags/` or the main bot dashboard with tag links
- **THEN** they can navigate to the 3D tag cloud without typing the URL

### Requirement: WebGL unavailable fallback

When WebGL is not available, the page SHALL display a clear message (not only a console error) and SHALL keep global navigation usable.

#### Scenario: No WebGL

- **WHEN** WebGL context creation fails
- **THEN** a visible fallback message is shown explaining that 3D view is unavailable
