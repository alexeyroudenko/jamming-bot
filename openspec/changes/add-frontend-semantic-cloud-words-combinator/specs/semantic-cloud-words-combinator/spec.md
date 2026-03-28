## ADDED Requirements

### Requirement: Automatic phrase ticks on Tags page

After the Tags page has finished loading its main content (logs fetch succeeded), the system SHALL run a recurring timer that fires at an interval between 3 and 5 seconds (inclusive bounds implemented as a random delay in that range per scheduling step).

#### Scenario: Timer starts after load

- **WHEN** logs data has loaded successfully and the Tags main view is shown
- **THEN** the phrase sampling loop SHALL be active

#### Scenario: Jittered delay

- **WHEN** one tick completes and the next is scheduled
- **THEN** the delay until the next tick SHALL be a pseudorandom duration between 3000 ms and 5000 ms

### Requirement: Consecutive words highlighted in red

On each tick, the system SHALL choose a random valid starting index in the current `tags` array and SHALL select 2 or 3 consecutive tags (or fewer if the array is shorter than the chosen length). Tags whose values belong to that slice SHALL be rendered with a distinct red highlight (e.g. red background) compared to non-highlighted tags.

#### Scenario: Two or three words

- **WHEN** the tags array has at least two entries and a tick runs
- **THEN** the highlighted slice SHALL contain two or three consecutive entries when the array is long enough

#### Scenario: Cloud order matches array

- **WHEN** the tag cloud is rendered
- **THEN** tag order SHALL follow the `tags` array order (no shuffle) so “consecutive” in data matches the cloud

### Requirement: Phrase appended to bottom feed

Each tick SHALL append a single line to a bottom feed: the space-joined text of the highlighted words in order. The feed SHALL be scrollable vertically and SHALL scroll to show the newest line after an append.

#### Scenario: Append and scroll

- **WHEN** a tick produces the phrase `a b`
- **THEN** that string SHALL appear as a new line in the feed and the feed SHALL be scrolled to reveal the latest content

### Requirement: History bound and cleanup

The system SHALL retain only a bounded number of recent phrase lines (e.g. 200). On unmount, the phrase timer SHALL be cancelled so no further ticks run.

#### Scenario: Unmount

- **WHEN** the user navigates away from the Tags page
- **THEN** the phrase loop SHALL stop and pending timeouts SHALL be cleared

### Requirement: Feed accessibility

The phrase feed SHALL expose an accessible name (e.g. `aria-label`) and MAY use `role="log"` with polite live updates.

#### Scenario: Name available

- **WHEN** assistive technology inspects the feed container
- **THEN** a non-empty accessible name SHALL be available
