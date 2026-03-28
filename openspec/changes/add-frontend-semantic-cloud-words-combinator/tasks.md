## 1. State and timer loop

- [x] 1.1 Add `phraseHighlightValues`, `phraseHistory`, `_phraseLoopActive`, `_phraseTimeoutId`, `_phraseFeedRef` on `Tags`
- [x] 1.2 Start `_startPhraseHighlightLoop()` after successful `fetchAPI`; use `_schedulePhraseTick` / `_runPhraseTick` with 3–5 s jitter
- [x] 1.3 Each tick: random start, 2–3 consecutive tags from `prev.tags`, update highlight + append `join(' ')` to history (cap 200)

## 2. TagCloud and renderer

- [x] 2.1 Extend `tagsTagRenderer` with `highlightSet`; red styling when `tag.value` is in set
- [x] 2.2 `TagCloud` `shuffle={false}`; `renderer` closes over `phraseHighlightValues`; remove click `alert`

## 3. Feed UI and styles

- [x] 3.1 Bottom `.tags-phrase-feed` with `ref`, `role="log"`, `aria-live`, `aria-label`; map `phraseHistory` to lines
- [x] 3.2 `App.css`: `.tags-page-root` padding-bottom, `.tags-phrase-feed` fixed bar + scroll + line styles

## 4. Lifecycle

- [x] 4.1 `componentWillUnmount`: stop loop, `clearTimeout` phrase timer, existing socket/interval cleanup
