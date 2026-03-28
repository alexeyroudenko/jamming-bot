## Why

The home **Tags** page shows a semantic tag cloud but there was no automatic way to surface **multi-word phrases** from the cloud as a stream of combined text. A lightweight **combinator** helps exploration and future integration (e.g. filters) by periodically taking **2–3 consecutive tags** (in list order), highlighting them, and appending the space-joined phrase to a bottom feed.

## What Changes

- While the Tags page is active (after logs load), run a **timer loop** with **3–5 s** random delay between ticks.
- Each tick: pick a **random start index** in `tags` and highlight **2 or 3 consecutive** entries (array order); render those chips in **red**.
- Append the phrase (`join(' ')`) to a **fixed bottom, scrollable** feed; auto-scroll to latest line; cap history (e.g. last 200 lines).
- Use **`shuffle={false}`** on `TagCloud` so “consecutive” matches `tags` array order.
- Remove the old **click `alert`** on tags.
- No backend API changes in this change.

## Capabilities

### New Capabilities

- `semantic-cloud-words-combinator`: Tags page — automatic consecutive-phrase sampling, red highlight, bottom phrase feed, timer lifecycle, accessible feed region.

### Modified Capabilities

- _(none — no existing `openspec/specs/` entries.)_

## Impact

- **Code**: [`frontend/src/pages/tags.js`](frontend/src/pages/tags.js), [`frontend/src/App.css`](frontend/src/App.css) (`.tags-phrase-feed`, `.tags-page-root`).
- **Dependencies**: None new; `react-tagcloud` as today.
