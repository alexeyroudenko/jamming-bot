#!/usr/bin/env bash

set -euo pipefail

# Orchestrator for two-agent flow:
# - Agent A implements issue and returns PR number
# - Agent B verifies, merges, deploys, and closes issue

usage() {
  cat <<'EOF'
Usage:
  scripts/auto-two-agent-loop.sh

Environment variables:
  MAX_TASKS            Number of open issues to process per run (default: 1)
  ISSUE_QUERY          Additional gh issue list filter (default: "")
  AGENT_A_CMD          Command Agent A executes per issue (default: scripts/agent-a-implement.sh)
  AGENT_B_CMD          Command Agent B executes per issue/PR (default: scripts/agent-b-release.sh)
  REQUIRE_CONFIRM      If "1", ask confirmation before Agent B close step (default: 1)

Contract for AGENT_A_CMD:
  - Called as: <AGENT_A_CMD> --issue <ISSUE_ID>
  - Must print PR number to stdout (single integer), e.g. "42"

Examples:
  MAX_TASKS=3 scripts/auto-two-agent-loop.sh
  REQUIRE_CONFIRM=0 scripts/auto-two-agent-loop.sh
EOF
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "ERROR: missing required command: $1" >&2
    exit 1
  fi
}

MAX_TASKS="${MAX_TASKS:-1}"
ISSUE_QUERY="${ISSUE_QUERY:-}"
AGENT_A_CMD="${AGENT_A_CMD:-scripts/agent-a-implement.sh}"
AGENT_B_CMD="${AGENT_B_CMD:-scripts/agent-b-release.sh}"
REQUIRE_CONFIRM="${REQUIRE_CONFIRM:-1}"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

require_cmd gh
gh auth status >/dev/null

if [[ ! -x "$AGENT_B_CMD" ]]; then
  echo "ERROR: Agent B command is not executable: $AGENT_B_CMD" >&2
  exit 1
fi

if [[ ! -x "$AGENT_A_CMD" ]]; then
  cat <<EOF
ERROR: Agent A command is not executable: $AGENT_A_CMD

Create executable script with this contract:
  $AGENT_A_CMD --issue <ISSUE_ID>
and print resulting PR number to stdout.
EOF
  exit 1
fi

echo "==> Fetching open issues (max: $MAX_TASKS)"
ISSUE_IDS="$(gh issue list --state open --limit "$MAX_TASKS" --search "$ISSUE_QUERY" --json number --jq '.[].number')"

if [[ -z "$ISSUE_IDS" ]]; then
  echo "No open issues found. Nothing to do."
  exit 0
fi

for ISSUE_ID in $ISSUE_IDS; do
  echo
  echo "============================================================"
  echo "Issue #$ISSUE_ID"
  echo "============================================================"
  gh issue view "$ISSUE_ID" --json number,title,url

  echo "==> Agent A: implement issue and return PR number"
  PR_NUMBER="$("$AGENT_A_CMD" --issue "$ISSUE_ID" | tr -d '[:space:]')"

  if [[ ! "$PR_NUMBER" =~ ^[0-9]+$ ]]; then
    echo "ERROR: Agent A did not return a valid PR number for issue #$ISSUE_ID: '$PR_NUMBER'" >&2
    exit 1
  fi

  echo "Agent A output: PR #$PR_NUMBER"
  gh pr view "$PR_NUMBER" --json number,title,state,url

  if [[ "$REQUIRE_CONFIRM" == "1" ]]; then
    echo
    echo "Manual gate: proceed with Agent B for issue #$ISSUE_ID / PR #$PR_NUMBER? [y/N]"
    read -r ans
    if [[ "$ans" != "y" && "$ans" != "Y" ]]; then
      echo "Skipped by operator."
      continue
    fi
  fi

  echo "==> Agent B: verify/merge/deploy/close"
  "$AGENT_B_CMD" --pr "$PR_NUMBER" --issue "$ISSUE_ID" --close-issue

  echo "Issue #$ISSUE_ID processed successfully."
done

echo
echo "Done."
