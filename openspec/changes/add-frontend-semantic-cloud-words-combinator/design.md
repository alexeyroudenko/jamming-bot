## Context

The **Tags** page ([`frontend/src/pages/tags.js`](frontend/src/pages/tags.js)) loads tag data on an interval and renders `TagCloud`. The product choice shifted from **manual click-to-combine** to **automatic phrase sampling** for a passive “combinator” stream.

## Goals / Non-Goals

**Goals:**

- Start the phrase loop only after **`fetchAPI`** succeeds (`loaded` path), alongside existing socket init.
- **Jittered interval**: `3000 + Math.random() * 2000` ms between ticks.
- **Phrase length**: 2 or 3 words, consecutive in `tags` slice; random start in valid range.
- **Highlight**: pass `Set(phraseHighlightValues)` into `tagsTagRenderer`; red background/border for chips.
- **Feed**: `phraseHistory` array, append each phrase; `ref` + `scrollTop = scrollHeight` after update; slice to last 200 entries.
- **Unmount**: `_phraseLoopActive = false`, `clearTimeout` for phrase timer.

**Non-Goals:**

- Clipboard copy / clear-all / per-chip remove (manual combinator).
- Backend submission of phrases.

## Decisions

1. **`shuffle={false}`** — required so consecutive indices match visible cloud order from `tags`.
2. **Highlight by `tag.value`** in a `Set` — duplicate names in data would highlight all matching chips (acceptable).
3. **Fixed bottom feed** — `position: fixed`, `z-index` above page; `padding-bottom` on `.tags-page-root` so content is not fully obscured.

## Risks / Trade-offs

- **[Risk]** Very short `tags` array — tick returns empty highlight; loop continues.
- **[Risk]** `phraseHistory` keys by index — list truncation to 200 may shift keys (cosmetic re-mount); acceptable.

## Migration Plan

- Frontend-only deploy; revert by removing phrase loop and feed markup/CSS.

## Open Questions

- Whether to pause the loop when the tab is hidden (`document.visibilityState`).
