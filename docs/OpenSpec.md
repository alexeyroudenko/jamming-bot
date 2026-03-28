
```
/opsx:propose add-dark-mode
```

#### Creates `openspec/changes/add-dark-mode/` with:
- `proposal.md` — why and what changes
- `design.md` — technical approach
- `specs/` — delta specifications (ADDED/MODIFIED/REMOVED requirements)
- `tasks.md` — implementation checklist


```
/opsx:apply
```

#### Execute tasks from tasks.md, checking off items as they're completed.

```
/opsx:archive
```

- Merges delta specs into `openspec/specs/` (the baseline)
- Moves the change to `openspec/changes/archive/`


## https://github.com/Fission-AI/OpenSpec