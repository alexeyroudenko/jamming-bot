#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/agent-a-implement.sh --issue <ISSUE_ID>

Behavior:
  - If open PR linked to issue exists, returns it.
  - Otherwise creates implementation branch + draft PR scaffold.
  - Prints PR number to stdout (single integer).

Notes:
  - Works in temporary git worktree, does not require clean local tree.
  - Creates file docs/auto-issues/issue-<id>.md as implementation scaffold.
EOF
}

slugify() {
  local s="$1"
  s="$(echo "$s" | tr '[:upper:]' '[:lower:]')"
  s="$(echo "$s" | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//')"
  if [[ -z "$s" ]]; then
    s="task"
  fi
  echo "$s"
}

ISSUE_ID=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --issue)
      ISSUE_ID="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$ISSUE_ID" ]]; then
  echo "ERROR: --issue is required" >&2
  usage
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: gh is required" >&2
  exit 1
fi

# 1) Try to find open PR that references this issue in title/body.
PR_NUMBER="$(gh pr list --state open --search "#$ISSUE_ID" --json number --jq '.[0].number // empty')"

if [[ -n "$PR_NUMBER" ]]; then
  echo "$PR_NUMBER"
  exit 0
fi

# 2) No PR found: create branch + scaffold + draft PR.
if ! command -v git >/dev/null 2>&1; then
  echo "ERROR: git is required" >&2
  exit 1
fi

ROOT_DIR="$(git rev-parse --show-toplevel)"
WORKTREE_DIR="$(mktemp -d -t agent-a-XXXXXX)"
cleanup() {
  git -C "$ROOT_DIR" worktree remove --force "$WORKTREE_DIR" >/dev/null 2>&1 || true
}
trap cleanup EXIT

TITLE="$(gh issue view "$ISSUE_ID" --json title --jq '.title')"
BODY="$(gh issue view "$ISSUE_ID" --json body --jq '.body // ""')"
SLUG="$(slugify "$TITLE")"
BRANCH="auto/issue-${ISSUE_ID}-${SLUG}"
PLAN_FILE="docs/auto-issues/issue-${ISSUE_ID}.md"

git -C "$ROOT_DIR" fetch origin main
if git -C "$ROOT_DIR" ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1; then
  git -C "$ROOT_DIR" worktree add -B "$BRANCH" "$WORKTREE_DIR" "origin/$BRANCH" >/dev/null
else
  git -C "$ROOT_DIR" worktree add -b "$BRANCH" "$WORKTREE_DIR" origin/main >/dev/null
fi

mkdir -p "$WORKTREE_DIR/docs/auto-issues"

cat > "$WORKTREE_DIR/$PLAN_FILE" <<EOF
# Issue #$ISSUE_ID: $TITLE

Source: $(gh issue view "$ISSUE_ID" --json url --jq '.url')

## Original description

$BODY

## Auto-generated implementation checklist

- [ ] Clarify acceptance criteria
- [ ] Implement code changes
- [ ] Add/update tests
- [ ] Update docs
- [ ] Verify CI
EOF

git -C "$WORKTREE_DIR" add "$PLAN_FILE"
if ! git -C "$WORKTREE_DIR" diff --cached --quiet; then
  git -C "$WORKTREE_DIR" commit -m "chore: scaffold implementation for issue #$ISSUE_ID" >/dev/null
  git -C "$WORKTREE_DIR" push -u origin "$BRANCH" >/dev/null
fi

PR_NUMBER="$(gh pr list --state open --head "$BRANCH" --json number --jq '.[0].number // empty')"
if [[ -n "$PR_NUMBER" ]]; then
  echo "$PR_NUMBER"
  exit 0
fi

PR_URL="$(gh pr create \
  --draft \
  --base main \
  --head "$BRANCH" \
  --title "WIP: #$ISSUE_ID $TITLE" \
  --body "$(cat <<EOF
Auto-generated implementation scaffold for issue #$ISSUE_ID.

Closes #$ISSUE_ID

## Context
- Issue: #$ISSUE_ID
- Source branch: $BRANCH

## Next steps
- [ ] Implement requested changes
- [ ] Add/adjust tests
- [ ] Complete review checklist
EOF
)" \
)"

PR_NUMBER="$(echo "$PR_URL" | sed -nE 's#.*/pull/([0-9]+).*#\1#p')"
if [[ -z "$PR_NUMBER" ]]; then
  echo "ERROR: failed to parse PR number from URL: $PR_URL" >&2
  exit 1
fi

echo "$PR_NUMBER"
