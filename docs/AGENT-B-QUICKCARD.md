# Agent B Quickcard

Короткая последовательность действий для второго агента (ревью -> деплой -> закрытие issue).

```bash
# 0) Входные параметры
export ISSUE_ID=<issue_number>
export PR_NUMBER=<pr_number>

# 1) Pre-merge check
gh pr view "$PR_NUMBER" --json number,title,state,mergeStateStatus,reviewDecision
gh pr checks "$PR_NUMBER"
gh pr diff "$PR_NUMBER"

# 2) Merge (если все проверки OK)
gh pr merge "$PR_NUMBER" --squash --delete-branch
gh pr view "$PR_NUMBER" --json state,mergedAt,mergeCommit

# 3) Deploy to production
gh workflow run deploy.yml --ref main
gh run list --workflow deploy.yml --limit 1
export RUN_ID=$(gh run list --workflow deploy.yml --limit 1 --json databaseId --jq '.[0].databaseId')
gh run watch "$RUN_ID"
gh run view "$RUN_ID" --json status,conclusion,url

# 4) Close issue (только если deploy + smoke-check = PASS)
gh issue close "$ISSUE_ID" --comment "Merged to main, deployed via deploy.yml, smoke checks passed."
```

## Правило остановки

Если любой шаг неуспешен — не закрывать issue, оставить отчёт о блокере и перейти к rollback/фиксу.

Скрипт-обертка для этого процесса: `scripts/agent-b-release.sh --pr <PR_NUMBER> --issue <ISSUE_ID> [--close-issue]`.

Оркестратор "два агента" без параметров: `make auto-two-agent`.

Примечание: текущий `agent-a-implement.sh` автоматически создаёт scaffold branch + draft PR, если PR по issue ещё не существует.

Если checks появляются с задержкой или в репозитории нет PR-checks:

- Мягкий режим (разрешить отсутствие checks):  
  `ALLOW_NO_CHECKS=1 make auto-two-agent`
- Подождать появления checks до 120 сек:  
  `WAIT_FOR_CHECKS_SEC=120 make auto-two-agent`
