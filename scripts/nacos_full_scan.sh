#!/usr/bin/env bash
set -euo pipefail

# Args (env or defaults):
#   NACOS_ADDR (host:port), NACOS_USER, NACOS_PASS
#   NS_FALLBACK (default: public)
#   NAMESPACE_HINT (optional override)
NACOS_ADDR="${NACOS_ADDR:-172.31.120.5:8848}"
NACOS_USER="${NACOS_USER:-nacos}"
NACOS_PASS="${NACOS_PASS:-tnM*fb6P}"
NS_FALLBACK="${NS_FALLBACK:-public}"

ns_from_k8s="$(kubectl -n miker-prod get deploy osm-gateway -o json 2>/dev/null | python3 - <<'PY'
import sys, json
try:
  d=json.load(sys.stdin)
  env=d['spec']['template']['spec']['containers'][0].get('env',[])
  print(next((e.get('value','') for e in env if e.get('name')=='NACOS_NAMESPACE'),'')) 
except Exception:
  print('')
PY
)"

kubectl -n miker-prod delete pod nacos-curl --ignore-not-found >/dev/null 2>&1 || true
kubectl -n miker-prod run nacos-curl --image=docker.m.daocloud.io/curlimages/curl:8.10.1 --restart=Never --command -- sh -lc 'sleep 600' >/dev/null
kubectl -n miker-prod wait --for=condition=Ready pod/nacos-curl --timeout=120s >/dev/null

login_json="$(kubectl -n miker-prod exec nacos-curl -- sh -lc \
  "curl -sS -X POST 'http://${NACOS_ADDR}/nacos/v1/auth/login' \
   -H 'Content-Type: application/x-www-form-urlencoded' \
   --data-urlencode 'username=${NACOS_USER}' \
   --data-urlencode 'password=${NACOS_PASS}'")"
token="$(printf "%s" "$login_json" | sed -En 's/.*\"accessToken\":\"([^\"]+)\".*/\\1/p')"
if [ -z "$token" ]; then
  echo "ERROR: failed to login Nacos"
  exit 1
fi
echo "Nacos token length: ${#token}"

# discover namespaces
namespaces_json="$(kubectl -n miker-prod exec nacos-curl -- sh -lc \
  "curl -sS 'http://${NACOS_ADDR}/nacos/v1/console/namespaces?accessToken=${token}'")" || true
ns_list="$(printf "%s" "$namespaces_json" | python3 - <<'PY'
import sys, json
try:
  d=json.load(sys.stdin)
  arr=d.get('data',[])
  print(' '.join([ (it.get('namespace') or it.get('namespaceId') or '') for it in arr if (it.get('namespace') or it.get('namespaceId')) ]))
except Exception:
  print('')
PY
)"
if [ -z "$ns_list" ]; then
  ns_list="$ns_from_k8s"
fi
if [ -z "$ns_list" ]; then
  ns_list="$NS_FALLBACK"
fi
echo "Namespaces: $ns_list"

found_any=0
for ns in $ns_list; do
  echo "== Namespace: $ns =="
  services="$(kubectl -n miker-prod exec nacos-curl -- sh -lc \
    "curl -sS 'http://${NACOS_ADDR}/nacos/v1/ns/service/list?pageNo=1&pageSize=1000&namespaceId=${ns}&accessToken=${token}'")"
  count="$(printf "%s" "$services" | sed -En 's/.*\"count\":([0-9]+).*/\\1/p')"
  echo "services_count: ${count:-0}"
  # dump names
  printf "%s" "$services" | python3 - <<'PY'
import sys, json
try:
  d=json.load(sys.stdin)
  doms=d.get('doms') or []
  for name in doms:
    print(name)
except Exception:
  pass
PY
  # probe osm related names quickly (common variants)
  for name in osm-gateway osmgateway gateway-osm osm_gateway DEFAULT_GROUP@@osm-gateway; do
    echo "-- instances for: $name"
    kubectl -n miker-prod exec nacos-curl -- sh -lc \
      "curl -sS 'http://${NACOS_ADDR}/nacos/v1/ns/instance/list?serviceName=${name}&groupName=DEFAULT_GROUP&namespaceId=${ns}&accessToken=${token}'" \
      | sed -n '1,200p'
  done
done

kubectl -n miker-prod delete pod nacos-curl --ignore-not-found >/dev/null 2>&1 || true
echo "Done."


