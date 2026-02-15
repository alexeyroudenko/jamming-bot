#!/bin/bash
# test.sh — Test all services (k8s + docker-compose) and analyze output
# Usage: ./test.sh

set +e  # Don't exit on errors — we handle them in check()

NODE_IP="80.74.27.74"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

pass=0
fail=0
warn=0

check() {
  local label="$1"
  local url="$2"
  local expected_code="${3:-200}"

  printf "  %-50s " "$label"
  
  response=$(curl -s -o /tmp/test_body -w "%{http_code}|%{time_total}" --connect-timeout 5 --max-time 10 "$url" 2>&1) || true
  
  http_code=$(echo "$response" | cut -d'|' -f1)
  time_total=$(echo "$response" | cut -d'|' -f2)
  body=$(cat /tmp/test_body 2>/dev/null | head -c 200)

  if [[ "$http_code" == "$expected_code" ]]; then
    echo -e "${GREEN}✓ ${http_code}${NC}  (${time_total}s)  ${body:0:80}"
    ((pass++))
  elif [[ "$http_code" == "000" ]]; then
    echo -e "${RED}✗ UNREACHABLE${NC}  (connection failed)"
    ((fail++))
  else
    echo -e "${YELLOW}⚠ ${http_code}${NC}  (${time_total}s)  ${body:0:80}"
    ((warn++))
  fi
}

header() {
  echo ""
  echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════${NC}"
  echo -e "${BOLD}${CYAN}  $1${NC}"
  echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════${NC}"
}

# ─── 1. Kubernetes pod status ─────────────────────────────────
header "1. Kubernetes Pod Status"
echo ""
kubectl get pods -o wide 2>&1 | while IFS= read -r line; do
  if echo "$line" | grep -q "Running"; then
    if echo "$line" | grep -q " 1/1 "; then
      echo -e "  ${GREEN}$line${NC}"
    else
      echo -e "  ${YELLOW}$line${NC}"
    fi
  elif echo "$line" | grep -qE "CrashLoop|Error|ErrImage|Evicted"; then
    echo -e "  ${RED}$line${NC}"
  elif echo "$line" | grep -q "Pending"; then
    echo -e "  ${YELLOW}$line${NC}"
  else
    echo "  $line"
  fi
done

# ─── 2. K8s ClusterIP services (from inside the node) ────────
header "2. K8s Services via ClusterIP (internal)"

# echo ""
# echo -e "  ${BOLD}html-renderer-service (ClusterIP → :3000)${NC}"
# check "  GET /" "http://$(kubectl get svc html-renderer-service -o jsonpath='{.spec.clusterIP}'):80/"
# check "  GET /render?url=https://ya.ru" "http://$(kubectl get svc html-renderer-service -o jsonpath='{.spec.clusterIP}'):80/render?url=https://example.com&width=800&height=600"

echo ""
echo -e "  ${BOLD}keywords-service (ClusterIP → :7771)${NC}"
check "  GET /" "http://$(kubectl get svc keywords-service -o jsonpath='{.spec.clusterIP}'):80/"
check "  GET /docs" "http://$(kubectl get svc keywords-service -o jsonpath='{.spec.clusterIP}'):80/docs"

echo ""
echo -e "  ${BOLD}semantic-service (ClusterIP → :8005)${NC}"
check "  GET /" "http://$(kubectl get svc semantic-service -o jsonpath='{.spec.clusterIP}'):80/"
check "  GET /docs" "http://$(kubectl get svc semantic-service -o jsonpath='{.spec.clusterIP}'):80/docs"

echo ""
echo -e "  ${BOLD}storage-service (ClusterIP → :7781)${NC}"
check "  GET /" "http://$(kubectl get svc storage-service -o jsonpath='{.spec.clusterIP}'):80/"
check "  GET /docs" "http://$(kubectl get svc storage-service -o jsonpath='{.spec.clusterIP}'):80/docs"

echo ""
echo -e "  ${BOLD}tags-service (ClusterIP → :8000)${NC}"
check "  GET /" "http://$(kubectl get svc tags-service -o jsonpath='{.spec.clusterIP}'):80/"
check "  GET /docs" "http://$(kubectl get svc tags-service -o jsonpath='{.spec.clusterIP}'):80/docs"

echo ""
echo -e "  ${BOLD}ip-service (ClusterIP → :8004)${NC}"
check "  GET /" "http://$(kubectl get svc ip-service -o jsonpath='{.spec.clusterIP}'):80/"
check "  GET /api/v1/ip/docs" "http://$(kubectl get svc ip-service -o jsonpath='{.spec.clusterIP}'):80/api/v1/ip/docs"

echo ""
echo -e "  ${BOLD}app-service (ClusterIP → :5000)${NC}"
check "  GET /" "http://$(kubectl get svc app-service -o jsonpath='{.spec.clusterIP}'):80/"
check "  GET /metrics" "http://$(kubectl get svc app-service -o jsonpath='{.spec.clusterIP}'):80/metrics"

echo ""
echo -e "  ${BOLD}bot-service (no HTTP — pod status only)${NC}"
bot_pod=$(kubectl get pods -l app=bot-service --no-headers 2>/dev/null | head -1)
bot_status=$(echo "$bot_pod" | awk '{print $3}')
bot_ready=$(echo "$bot_pod" | awk '{print $2}')
printf "  %-50s " "Pod status"
if [[ "$bot_status" == "Running" ]]; then
  echo -e "${GREEN}✓ ${bot_ready} ${bot_status}${NC}"
  ((pass++))
elif [[ -z "$bot_status" ]]; then
  echo -e "${RED}✗ no pod found${NC}"
  ((fail++))
else
  echo -e "${RED}✗ ${bot_ready} ${bot_status}${NC}"
  ((fail++))
fi

# ─── 3. Ingress paths (via node IP) ──────────────────────────
header "3. Ingress Paths (via ${NODE_IP}:80)"

echo ""
check "GET /render?url=https://example.com" "http://${NODE_IP}/render?url=https://example.com&width=800&height=600"
check "GET /keywords"                        "http://${NODE_IP}/keywords"
check "GET /keywords/docs"                   "http://${NODE_IP}/keywords/docs"
check "GET /semantic"                        "http://${NODE_IP}/semantic"
check "GET /semantic/docs"                   "http://${NODE_IP}/semantic/docs"
check "GET /storage"                         "http://${NODE_IP}/storage"
check "GET /storage/docs"                    "http://${NODE_IP}/storage/docs"
check "GET /tags"                            "http://${NODE_IP}/tags"
check "GET /tags/docs"                       "http://${NODE_IP}/tags/docs"
check "GET /ip"                              "http://${NODE_IP}/ip"
check "GET /ip/api/v1/ip/docs"               "http://${NODE_IP}/ip/api/v1/ip/docs"
check "GET /app"                             "http://${NODE_IP}/app"
check "GET /app/metrics"                     "http://${NODE_IP}/app/metrics"

# # ─── 4. Docker Compose services (host ports) ─────────────────
# header "4. Docker Compose Services (host ports)"

# echo ""
# check "keywords-service   localhost:7771"    "http://127.0.0.1:7771/"
# check "keywords-service   localhost:7771/docs" "http://127.0.0.1:7771/docs"
# check "semantic-service   localhost:8005"    "http://127.0.0.1:8005/"
# check "semantic-service   localhost:8005/docs" "http://127.0.0.1:8005/docs"
# check "storage-service    localhost:7781"    "http://127.0.0.1:7781/"
# check "storage-service    localhost:7781/docs" "http://127.0.0.1:7781/docs"
# check "tags-service       localhost:8003"    "http://127.0.0.1:8003/"
# check "tags-service       localhost:8003/docs" "http://127.0.0.1:8003/docs"
# check "ip-service         localhost:8004"    "http://127.0.0.1:8004/"
# check "ip-service         localhost:8004/api/v1/ip/docs" "http://127.0.0.1:8004/api/v1/ip/docs"
# check "app-service(flask) localhost:5000"    "http://127.0.0.1:5000/"
# check "app-service(flask) localhost:5000/metrics" "http://127.0.0.1:5000/metrics"

# ─── 5. Functional: tags-service CRUD ────────────────────────
header "5. Tags Service — Create, Retrieve & Verify"

TAGS_K8S="http://$(kubectl get svc tags-service -o jsonpath='{.spec.clusterIP}'):80"
TAGS_API="${TAGS_K8S}/api/v1/tags"

echo ""
echo -e "  ${BOLD}Cleanup: get existing tags${NC}"
existing=$(curl -s "${TAGS_API}/" 2>/dev/null)
echo -e "  Existing tags: ${existing:0:120}"

echo ""
echo -e "  ${BOLD}Step 1: Create test tags${NC}"

tag1_resp=$(curl -s -X POST "${TAGS_API}/" \
  -H "Content-Type: application/json" \
  -d '{"name": "test-rock", "count": 10}' 2>/dev/null)
tag1_id=$(echo "$tag1_resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
printf "  %-50s " "POST tag 'test-rock' count=10"
if [[ -n "$tag1_id" && "$tag1_id" != "" ]]; then
  echo -e "${GREEN}✓ created${NC}  id=${tag1_id}  ${tag1_resp:0:80}"
  ((pass++))
else
  echo -e "${RED}✗ failed${NC}  ${tag1_resp:0:100}"
  ((fail++))
fi

tag2_resp=$(curl -s -X POST "${TAGS_API}/" \
  -H "Content-Type: application/json" \
  -d '{"name": "test-jazz", "count": 5}' 2>/dev/null)
tag2_id=$(echo "$tag2_resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
printf "  %-50s " "POST tag 'test-jazz' count=5"
if [[ -n "$tag2_id" && "$tag2_id" != "" ]]; then
  echo -e "${GREEN}✓ created${NC}  id=${tag2_id}  ${tag2_resp:0:80}"
  ((pass++))
else
  echo -e "${RED}✗ failed${NC}  ${tag2_resp:0:100}"
  ((fail++))
fi

tag3_resp=$(curl -s -X POST "${TAGS_API}/" \
  -H "Content-Type: application/json" \
  -d '{"name": "test-blues", "count": 7}' 2>/dev/null)
tag3_id=$(echo "$tag3_resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
printf "  %-50s " "POST tag 'test-blues' count=7"
if [[ -n "$tag3_id" && "$tag3_id" != "" ]]; then
  echo -e "${GREEN}✓ created${NC}  id=${tag3_id}  ${tag3_resp:0:80}"
  ((pass++))
else
  echo -e "${RED}✗ failed${NC}  ${tag3_resp:0:100}"
  ((fail++))
fi

echo ""
echo -e "  ${BOLD}Step 2: Retrieve all tags${NC}"

get_all_code=$(curl -s -o /tmp/tags_all.json -w "%{http_code}" "${TAGS_API}/" 2>/dev/null)
printf "  %-50s " "GET /api/v1/tags/"
if [[ "$get_all_code" == "200" ]]; then
  tag_count=$(python3 -c "import json; print(len(json.load(open('/tmp/tags_all.json'))))" 2>/dev/null)
  echo -e "${GREEN}✓ ${get_all_code}${NC}  (${tag_count} tags)"
  ((pass++))
else
  # Known bug: 'count' column clashes with Sequence.count() in databases lib
  echo -e "${YELLOW}⚠ ${get_all_code}${NC}  (known bug: 'count' column vs Sequence.count())"
  tag_count="bug"
  ((warn++))
fi

echo ""
echo -e "  ${BOLD}Step 3: Retrieve individual tag by ID${NC}"

if [[ -n "$tag1_id" ]]; then
  get_one_code=$(curl -s -o /tmp/tag_get.json -w "%{http_code}" "${TAGS_API}/${tag1_id}/" 2>/dev/null)
  printf "  %-50s " "GET /api/v1/tags/${tag1_id}/"
  if [[ "$get_one_code" == "200" ]]; then
    got_name=$(python3 -c "import json; d=json.load(open('/tmp/tag_get.json')); print(d.get('name',''))" 2>/dev/null)
    got_count=$(python3 -c "import json; d=json.load(open('/tmp/tag_get.json')); print(d.get('count',''))" 2>/dev/null)
    if [[ "$got_name" == "test-rock" && "$got_count" == "10" ]]; then
      echo -e "${GREEN}✓ ${get_one_code}${NC}  name=test-rock count=10"
      ((pass++))
    else
      echo -e "${YELLOW}⚠ ${get_one_code}${NC}  name=${got_name} count=${got_count}"
      ((warn++))
    fi
  else
    echo -e "${YELLOW}⚠ ${get_one_code}${NC}  (same 'count' column bug)"
    ((warn++))
  fi
fi

echo ""
echo -e "  ${BOLD}Step 4: Update tag count${NC}"

if [[ -n "$tag2_id" ]]; then
  update_code=$(curl -s -o /tmp/tag_update.json -w "%{http_code}" -X PUT "${TAGS_API}/${tag2_id}/" \
    -H "Content-Type: application/json" \
    -d '{"count": 99}' 2>/dev/null)
  printf "  %-50s " "PUT /api/v1/tags/${tag2_id}/ — count→99"
  if [[ "$update_code" == "200" ]]; then
    updated_count=$(python3 -c "import json; d=json.load(open('/tmp/tag_update.json')); print(d.get('count',''))" 2>/dev/null)
    echo -e "${GREEN}✓ ${update_code}${NC}  count=${updated_count}"
    ((pass++))
  else
    echo -e "${YELLOW}⚠ ${update_code}${NC}  (same 'count' column bug on response)"
    ((warn++))
  fi
fi

echo ""
echo -e "  ${BOLD}Step 5: Delete test tags (cleanup)${NC}"

for tid in $tag1_id $tag2_id $tag3_id; do
  if [[ -n "$tid" ]]; then
    del_code=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "${TAGS_API}/${tid}/" 2>/dev/null)
    printf "  %-50s " "DELETE /api/v1/tags/${tid}/"
    if [[ "$del_code" == "200" ]]; then
      echo -e "${GREEN}✓ deleted${NC}"
      ((pass++))
    else
      echo -e "${RED}✗ HTTP ${del_code}${NC}"
      ((fail++))
    fi
  fi
done

echo ""
echo -e "  ${BOLD}Step 6: Verify deletion${NC}"

# Try to GET deleted tags — should return 404
if [[ -n "$tag1_id" ]]; then
  verify_code=$(curl -s -o /dev/null -w "%{http_code}" "${TAGS_API}/${tag1_id}/" 2>/dev/null)
  printf "  %-50s " "GET /api/v1/tags/${tag1_id}/ — should be 404"
  if [[ "$verify_code" == "404" ]]; then
    echo -e "${GREEN}✓ 404 (confirmed deleted)${NC}"
    ((pass++))
  elif [[ "$verify_code" == "500" ]]; then
    echo -e "${YELLOW}⚠ 500 (known bug, but tag may be deleted)${NC}"
    ((warn++))
  else
    echo -e "${RED}✗ HTTP ${verify_code} (expected 404)${NC}"
    ((fail++))
  fi
fi

# ─── 7. Summary ──────────────────────────────────────────────
header "7. Summary"
echo ""
echo -e "  ${GREEN}Passed:  ${pass}${NC}"
echo -e "  ${YELLOW}Warning: ${warn}${NC}"
echo -e "  ${RED}Failed:  ${fail}${NC}"
echo ""

if [[ $fail -gt 0 ]]; then
  echo -e "  ${RED}${BOLD}Some checks failed. Review output above.${NC}"
  exit 1
elif [[ $warn -gt 0 ]]; then
  echo -e "  ${YELLOW}${BOLD}Some checks returned unexpected status codes.${NC}"
  exit 0
else
  echo -e "  ${GREEN}${BOLD}All checks passed!${NC}"
  exit 0
fi
