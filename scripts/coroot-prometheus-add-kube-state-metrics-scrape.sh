#!/usr/bin/env bash
# Coroot operator regenerates Prometheus with only self-scrape; the UI checks this
# Prometheus for kube_* metrics with the project's coroot_project_id selector (see
# coroot db/project.go PrometheusConfig). Plain kube-state-metrics must be scraped and
# each sample must get label coroot_project_id=<project id>.
#
# By default scales coroot-operator to 0 so the operator does not revert this patch.
set -euo pipefail

NS="${COROOT_NAMESPACE:-coroot}"
DEPLOY="${COROOT_PROMETHEUS_DEPLOYMENT:-coroot-prometheus}"
OPERATOR_DEPLOY="${COROOT_OPERATOR_DEPLOYMENT:-coroot-operator}"
KSM_TARGET="${KUBE_STATE_METRICS_SCRAPE_TARGET:-kube-state-metrics.kube-state-metrics.svc.cluster.local:8080}"
OUT_OF_ORDER="${PROMETHEUS_OUT_OF_ORDER_WINDOW:-1h}"
PAUSE_OPERATOR="${COROOT_PAUSE_OPERATOR:-1}"

resolve_project_id() {
  if [[ -n "${COROOT_PROJECT_ID:-}" ]]; then
    echo "$COROOT_PROJECT_ID"
    return 0
  fi
  local pod
  pod=$(kubectl get pod -n "$NS" -l app.kubernetes.io/component=coroot -o jsonpath='{.items[0].metadata.name}' 2>/dev/null) || true
  if [[ -z "$pod" ]]; then
    echo ""
    return 1
  fi
  kubectl exec -n "$NS" "$pod" -- python3 -c "
import sqlite3
c = sqlite3.connect('/data/db.sqlite')
rows = list(c.execute('SELECT id FROM project ORDER BY id'))
if len(rows) != 1:
    raise SystemExit('set COROOT_PROJECT_ID: expected 1 project in db, got %d (%s)' % (len(rows), [r[0] for r in rows]))
print(rows[0][0])
" 2>/dev/null
}

if ! kubectl get deployment "$DEPLOY" -n "$NS" &>/dev/null; then
  echo "WARN: no deployment/$DEPLOY in $NS — skip Prometheus KSM scrape patch" >&2
  exit 0
fi

if ! kubectl get svc kube-state-metrics -n kube-state-metrics &>/dev/null; then
  echo "WARN: kube-state-metrics service not found — run make k3s-kube-state-metrics first" >&2
  exit 0
fi

PROJECT_ID="$(resolve_project_id)" || true
if [[ -z "$PROJECT_ID" ]]; then
  echo "ERROR: could not resolve Coroot project id (set COROOT_PROJECT_ID or ensure one Coroot pod + single project in /data/db.sqlite)." >&2
  exit 1
fi
echo "Using coroot_project_id=$PROJECT_ID for kube-state-metrics scrape metric_relabel_configs."

if [[ "$PAUSE_OPERATOR" == "1" ]]; then
  echo "Scaling $OPERATOR_DEPLOY in $NS to 0 replicas (so the operator does not revert Prometheus)."
  kubectl scale deployment/"$OPERATOR_DEPLOY" -n "$NS" --replicas=0
  sleep 2
fi

INIT_ARG="cat <<'EOFM' > /config/prometheus.yml
storage:
  tsdb:
    out_of_order_time_window: ${OUT_OF_ORDER}
scrape_configs:
  - job_name: \"prometheus\"
    static_configs:
      - targets: [\"127.0.0.1:9090\"]
  - job_name: \"kube-state-metrics\"
    honor_labels: true
    scrape_interval: 30s
    static_configs:
      - targets: [\"${KSM_TARGET}\"]
    metric_relabel_configs:
      - source_labels: [__address__]
        regex: \"(.*)\"
        target_label: coroot_project_id
        replacement: \"${PROJECT_ID}\"
EOFM"

PATCH=$(python3 -c "import json,sys; print(json.dumps([{'op':'replace','path':'/spec/template/spec/initContainers/0/args/0','value':sys.argv[1]}]))" "$INIT_ARG")

kubectl patch deployment "$DEPLOY" -n "$NS" --type=json -p "$PATCH"
echo "Patched $NS/$DEPLOY — waiting for rollout..."
kubectl rollout status deployment/"$DEPLOY" -n "$NS" --timeout=180s

if [[ "$PAUSE_OPERATOR" == "1" ]]; then
  echo ""
  echo "coroot-operator is scaled to 0. Prometheus keeps the extra scrape job."
  echo "To reconcile Coroot CRs again: kubectl scale deployment/$OPERATOR_DEPLOY -n $NS --replicas=1"
  echo "(that will likely reset Prometheus — then re-run this script with COROOT_PAUSE_OPERATOR=1.)"
fi

echo "Smoke: kubectl exec -n $NS deploy/$DEPLOY -c prometheus -- curl -sS --get --data-urlencode 'query=count(kube_pod_info{coroot_project_id=\"${PROJECT_ID}\"})' 'http://127.0.0.1:9090/api/v1/query'"
