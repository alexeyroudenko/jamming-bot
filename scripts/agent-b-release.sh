#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/agent-b-release.sh --pr <PR_NUMBER> --issue <ISSUE_ID> [--close-issue]

Options:
  --pr <PR_NUMBER>      Pull request number to verify and merge.
  --issue <ISSUE_ID>    Issue number to close after successful release.
  --close-issue         Actually close issue after deploy success.
                        Without this flag script stops before closing.
  -h, --help            Show this help.

Examples:
  scripts/agent-b-release.sh --pr 42 --issue 15
  scripts/agent-b-release.sh --pr 42 --issue 15 --close-issue

Environment variables:
  STRICT_CHECKS=1        Fail when checks are missing/failed (default: 1)
  ALLOW_NO_CHECKS=0      If 1, allow "no checks reported" (default: 0)
  WAIT_FOR_CHECKS_SEC=0  Wait for checks to appear before decision (default: 0)
EOF
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "ERROR: missing required command: $1" >&2
    exit 1
  fi
}

PR_NUMBER=""
ISSUE_ID=""
CLOSE_ISSUE="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --pr)
      PR_NUMBER="${2:-}"
      shift 2
      ;;
    --issue)
      ISSUE_ID="${2:-}"
      shift 2
      ;;
    --close-issue)
      CLOSE_ISSUE="true"
      shift
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

if [[ -z "$PR_NUMBER" || -z "$ISSUE_ID" ]]; then
  echo "ERROR: --pr and --issue are required." >&2
  usage
  exit 1
fi

require_cmd gh

STRICT_CHECKS="${STRICT_CHECKS:-1}"
ALLOW_NO_CHECKS="${ALLOW_NO_CHECKS:-0}"
WAIT_FOR_CHECKS_SEC="${WAIT_FOR_CHECKS_SEC:-0}"

checks_pass_or_allowed() {
  local pr="$1"
  local output rc
  output="$(gh pr checks "$pr" 2>&1)" || rc=$?
  rc="${rc:-0}"

  if [[ "$rc" -eq 0 ]]; then
    echo "$output"
    return 0
  fi

  case "$output" in
    *"no checks reported"*)
    echo "$output"
    if [[ "$ALLOW_NO_CHECKS" == "1" || "$STRICT_CHECKS" == "0" ]]; then
      echo "WARN: no checks reported, but policy allows continue." >&2
      return 0
    fi
    return 1
    ;;
  esac

  echo "$output"
  return 1
}

echo "==> Step 1/7: Checking GitHub auth"
gh auth status >/dev/null

echo "==> Step 2/7: Pre-merge PR status"
gh pr view "$PR_NUMBER" --json number,title,state,mergeStateStatus,reviewDecision

echo "==> Step 3/7: Required checks"
if [[ "$WAIT_FOR_CHECKS_SEC" -gt 0 ]]; then
  echo "Waiting up to ${WAIT_FOR_CHECKS_SEC}s for checks to appear..."
  elapsed=0
  interval=10
  while true; do
    if checks_pass_or_allowed "$PR_NUMBER"; then
      break
    fi
    if [[ "$elapsed" -ge "$WAIT_FOR_CHECKS_SEC" ]]; then
      echo "ERROR: checks did not pass within ${WAIT_FOR_CHECKS_SEC}s" >&2
      exit 1
    fi
    sleep "$interval"
    elapsed=$((elapsed + interval))
  done
else
  if ! checks_pass_or_allowed "$PR_NUMBER"; then
    echo "ERROR: required checks failed (or missing with strict policy)." >&2
    exit 1
  fi
fi

echo "==> Step 4/7: Merging PR #$PR_NUMBER"
gh pr merge "$PR_NUMBER" --squash --delete-branch
gh pr view "$PR_NUMBER" --json state,mergedAt,mergeCommit

echo "==> Step 5/7: Triggering deploy workflow"
gh workflow run deploy.yml --ref main

echo "==> Step 6/7: Waiting for deploy run"
RUN_ID="$(gh run list --workflow deploy.yml --limit 1 --json databaseId --jq '.[0].databaseId')"
if [[ -z "$RUN_ID" || "$RUN_ID" == "null" ]]; then
  echo "ERROR: could not resolve deploy run id." >&2
  exit 1
fi
gh run watch "$RUN_ID"
CONCLUSION="$(gh run view "$RUN_ID" --json conclusion --jq '.conclusion')"
RUN_URL="$(gh run view "$RUN_ID" --json url --jq '.url')"
if [[ "$CONCLUSION" != "success" ]]; then
  echo "ERROR: deploy failed with conclusion=$CONCLUSION" >&2
  echo "Run URL: $RUN_URL" >&2
  exit 1
fi
echo "Deploy run succeeded: $RUN_URL"

echo "==> Step 7/7: Manual smoke-check gate"
echo "Please run/confirm smoke checks before closing issue #$ISSUE_ID."
if [[ "$CLOSE_ISSUE" != "true" ]]; then
  echo "Dry stop: issue remains open. Re-run with --close-issue after smoke-check PASS."
  exit 0
fi

gh issue close "$ISSUE_ID" --comment "Merged via PR #$PR_NUMBER, deployed to production (run: $RUN_URL), smoke checks passed."
echo "Issue #$ISSUE_ID closed."
