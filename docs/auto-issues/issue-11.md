# Issue #11: Monitoring: add Coroot at coroot.jamming-bot.arthew0.online

Source: https://github.com/alexeyroudenko/jamming-bot/issues/11

## Original description

## Context
Need to add Coroot and expose it at:
- http://coroot.jamming-bot.arthew0.online/

Project already has Kubernetes deployment manifests and existing monitoring stack pieces (Prometheus/Grafana runbook, Jaeger, rq-exporter), so Coroot should be integrated into the current cluster setup without breaking existing routes.

## Goal
Deploy Coroot in `jamming-bot` infrastructure and make web UI reachable via `coroot.jamming-bot.arthew0.online`.

## Scope
- Add Coroot deployment manifests (or Helm-based install instructions pinned to reproducible version)
- Expose Coroot UI through ingress host `coroot.jamming-bot.arthew0.online`
- Ensure DNS + ingress routing works from public internet
- Document bootstrap/configuration and smoke checks

## Implementation tasks
- [ ] Decide deployment method (manifest vs Helm) and lock version
- [ ] Add Coroot runtime components required for Kubernetes observability
- [ ] Add/adjust Service and Ingress resources for host `coroot.jamming-bot.arthew0.online`
- [ ] Reuse existing TLS/cert-manager pattern if HTTPS is enabled for this host (or explicitly document HTTP-only choice)
- [ ] Verify Coroot can discover cluster workloads in namespace `jamming-bot`
- [ ] Add runbook doc: install/upgrade/rollback + troubleshooting

## Acceptance criteria (DoD)
- [ ] URL `http://coroot.jamming-bot.arthew0.online/` opens Coroot UI from outside cluster
- [ ] Coroot shows at least core services (`app-service`, `worker-service`, `redis`, `tags-service`, `storage-service`)
- [ ] No regression for existing ingress hosts (`app`, `rq`, `jaeger`, main domain routes)
- [ ] Deployment steps are reproducible from repo docs
- [ ] Rollback path documented and tested at least once (dry-run or real)

## Suggested verification
- [ ] `kubectl get pods -n jamming-bot` -> Coroot components are Running/Ready
- [ ] `kubectl get ingress -n jamming-bot` -> host `coroot.jamming-bot.arthew0.online` present
- [ ] Browser check: UI loads and graphs/services are visible
- [ ] Existing endpoints still healthy after apply

## Risks / notes
- Coroot may require additional permissions/CRDs and cluster-wide access; keep RBAC minimal but sufficient.
- Host routing can conflict with existing ingress resources if host/path rules overlap; validate merge behavior before apply.
- If HTTPS is required later, align certificate strategy with current cert-manager setup.

## Auto-generated implementation checklist

- [ ] Clarify acceptance criteria
- [ ] Implement code changes
- [ ] Add/update tests
- [ ] Update docs
- [ ] Verify CI
