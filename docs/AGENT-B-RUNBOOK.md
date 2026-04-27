# Agent B Runbook (Verifier + Release)

Этот runbook описывает работу второго агента: проверка PR, контроль деплоя в production и закрытие задачи только после успешной валидации.

## Роль Agent B

- Проверяет готовность PR к merge.
- Блокирует merge при рисках/ошибках.
- Запускает деплой в production через GitHub Actions (`deploy.yml`).
- Подтверждает результат по rollout и smoke-check.
- Закрывает issue только после успешной прод-проверки.

## Обязательные ограничения

- На сервере использовать только Kubernetes-процесс деплоя (`kubectl apply -f deployment.yaml` через workflow).
- Не использовать `docker compose` на production-сервере.
- Не закрывать issue до успешной пост-деплой проверки.

## Входные данные

- `ISSUE_ID` — номер задачи.
- `PR_NUMBER` — номер PR, который реализует задачу.
- `BASE_BRANCH=main`.

## Фаза 1: pre-merge проверка PR

1. Проверить статус PR:
   - `gh pr view $PR_NUMBER --json number,title,state,mergeStateStatus,reviewDecision`
2. Проверить CI:
   - `gh pr checks $PR_NUMBER`
3. Проверить diff и риски:
   - `gh pr diff $PR_NUMBER`

### Критерии FAIL (merge запрещён)

- Любой required check не `pass`.
- Есть блокирующие замечания по безопасности, данным, миграциям или rollback.
- Не описан тест-план или он явно неполный для изменения.

### Решение по фазе 1

- Если есть блокеры: `request changes`, оставить комментарий с причинами.
- Если всё в порядке: `approve` и переход к merge.

## Фаза 2: merge в main

1. Выполнить merge:
   - `gh pr merge $PR_NUMBER --squash --delete-branch`
2. Убедиться, что PR в `merged`:
   - `gh pr view $PR_NUMBER --json state,mergedAt,mergeCommit`

Если merge не удался, не переходить к деплою.

## Фаза 3: деплой в production

1. Запустить workflow деплоя:
   - `gh workflow run deploy.yml --ref main`
2. Получить последний запуск:
   - `gh run list --workflow deploy.yml --limit 1`
3. Дождаться завершения:
   - `gh run watch <RUN_ID>`
4. Проверить итог:
   - `gh run view <RUN_ID> --json status,conclusion,url`

### Критерии FAIL (прод не подтверждён)

- `conclusion != success`.
- Rollout завершился с ошибками.
- Smoke-check после деплоя не прошёл.

## Фаза 4: пост-деплой валидация

Минимальный чеклист:

- Сервис(ы), затронутые PR, отвечают по health endpoint.
- Критический пользовательский сценарий (smoke) проходит.
- Нет явной деградации по логам/ошибкам сразу после релиза.

Если любой пункт не выполнен — задача не закрывается, нужен rollback/фикс.

## Фаза 5: закрытие issue

Закрывать issue только после `success` в фазах 3 и 4:

- `gh issue close $ISSUE_ID --comment "Merged to main, deployed via deploy.yml, smoke checks passed."`

## Шаблон отчёта Agent B

Использовать в комментарии к PR или issue:

```text
Agent B report
- PR: #<PR_NUMBER>
- Pre-merge checks: PASS|FAIL
- Merge to main: PASS|FAIL
- Deploy workflow: PASS|FAIL (run: <url>)
- Smoke checks: PASS|FAIL
- Decision: APPROVED FOR CLOSE | BLOCKED
- Notes: <short details>
```

## Быстрый rollback-протокол

Если деплой сломан:

1. Зафиксировать симптом и affected сервис.
2. Остановить автозакрытие issue.
3. Выполнить rollback по текущему операционному процессу команды.
4. Добавить комментарий в issue/PR с причиной и статусом.
5. Открыть follow-up issue на исправление.

## Рекомендуемые GitHub настройки

- Branch protection для `main` с required checks.
- Ограничение прав: Agent A без production deploy, Agent B с deploy-доступом.
- Environment `production` с required reviewers (human gate).
