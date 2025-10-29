#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   VECR_AK=... VECR_SK=... \
#   ./templates/scripts/vecr-create-namespace-and-repo.sh \
#     --namespace saas \
#     --repo frontend-saas \
#     --visibility PRIVATE \
#     --region cn-beijing \
#     --version 2022-01-01
#
# Notes:
# - This script signs requests for Volcengine OpenAPI (SigV4-like) and calls `vecr` service
# - Actions used: CreateNamespace, CreateRepository, DescribeNamespace (optional)
# - If DescribeNamespace is not available on your version, creation is still valid; you can verify by token endpoint

endpoint="https://open.volcengineapi.com"
service="vecr"
region="cn-beijing"
version="2022-01-01"
namespace=""
repo=""
visibility="PRIVATE"
description=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --namespace) namespace="$2"; shift 2;;
    --repo) repo="$2"; shift 2;;
    --visibility) visibility="$2"; shift 2;;
    --description) description="$2"; shift 2;;
    --region) region="$2"; shift 2;;
    --version) version="$2"; shift 2;;
    --endpoint) endpoint="$2"; shift 2;;
    *) echo "Unknown arg: $1" >&2; exit 2;;
  esac
done

if [[ -z "${VECR_AK:-}" || -z "${VECR_SK:-}" ]]; then
  echo "VECR_AK and VECR_SK env vars are required" >&2
  exit 2
fi
if [[ -z "$namespace" ]]; then
  echo "--namespace is required" >&2
  exit 2
fi
if [[ -z "$repo" ]]; then
  echo "--repo is required" >&2
  exit 2
fi

json_escape() { python3 - "$@" <<'PY'
import json,sys
print(json.dumps(sys.argv[1]))
PY
}

call_api() {
  local action="$1"; shift
  local body_json="$1"; shift
  local host
  host=$(echo "$endpoint" | sed -E 's#^https?://##')
  python3 - "$endpoint" "$service" "$region" "$version" "$action" "$body_json" "$VECR_AK" "$VECR_SK" <<'PY'
import sys, json, hashlib, hmac, datetime, urllib.parse
import base64
import os
import http.client

endpoint, service, region, version, action, body_json, ak, sk = sys.argv[1:9]
host = urllib.parse.urlparse(endpoint).netloc
amz_date = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
date_stamp = amz_date[:8]

payload = body_json.encode('utf-8')
payload_hash = hashlib.sha256(payload).hexdigest()

query = {
    'Action': action,
    'Version': version,
    'Region': region,
}
canonical_querystring = urllib.parse.urlencode(sorted(query.items()))

canonical_headers = f"content-type:application/json\nhost:{host}\nx-content-sha256:{payload_hash}\nx-date:{amz_date}\n"
signed_headers = 'content-type;host;x-content-sha256;x-date'
canonical_request = '\n'.join([
    'POST',
    '/',
    canonical_querystring,
    canonical_headers,
    signed_headers,
    payload_hash,
])

algorithm = 'HMAC-SHA256'
credential_scope = f"{date_stamp}/{region}/{service}/request"
string_to_sign = '\n'.join([
    algorithm,
    amz_date,
    credential_scope,
    hashlib.sha256(canonical_request.encode('utf-8')).hexdigest(),
])

def sign(key, msg):
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

k_date = sign(('VOLC' + sk).encode('utf-8'), date_stamp)
k_region = hmac.new(k_date, region.encode('utf-8'), hashlib.sha256).digest()
k_service = hmac.new(k_region, service.encode('utf-8'), hashlib.sha256).digest()
k_signing = hmac.new(k_service, b'request', hashlib.sha256).digest()
signature = hmac.new(k_signing, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

authorization_header = (
    f"VOLC {algorithm} Credential={ak}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
)

conn = http.client.HTTPSConnection(host)
path = f"/?{canonical_querystring}"
headers = {
    'Content-Type': 'application/json',
    'Authorization': authorization_header,
    'X-Date': amz_date,
    'X-Content-Sha256': payload_hash,
}
conn.request('POST', path, body=payload, headers=headers)
resp = conn.getresponse()
data = resp.read()
print(resp.status)
sys.stdout.buffer.write(data)
print()
if resp.status not in (200, 201, 202):
    sys.exit(3)
PY
}

echo "[1/3] CreateNamespace: $namespace"
ns_body=$(cat <<JSON
{ "NamespaceName": $(json_escape "$namespace"), "Description": $(json_escape "$description") }
JSON
)
call_api "CreateNamespace" "$ns_body" >/dev/null

echo "[2/3] CreateRepository: $namespace/$repo ($visibility)"
repo_body=$(cat <<JSON
{ "Namespace": $(json_escape "$namespace"), "RepoName": $(json_escape "$repo"), "Visibility": $(json_escape "$visibility") }
JSON
)
call_api "CreateRepository" "$repo_body" >/dev/null

echo "[3/3] Verify (DescribeNamespace)"
desc_body=$(cat <<JSON
{ "NamespaceName": $(json_escape "$namespace") }
JSON
)
set +e
call_api "DescribeNamespace" "$desc_body" >/dev/null || true
set -e

echo "Done: $namespace/$repo created (or already exists)."

#!/usr/bin/env bash
set -euo pipefail

# This helper prepares OpenAPI requests for VECR namespace/repository creation.
# It does NOT implement VolcEngine V4 signing. Provide signed headers via env or use your
# existing signing tool to execute the printed curl commands.

print_usage() {
  cat <<'USAGE'
Usage:
  vecr-create-namespace-and-repo.sh \
    --namespace miker \
    [--repo miker-web] \
    [--visibility PRIVATE|PUBLIC] \
    [--desc "Namespace for team miker"] \
    [--region cn-beijing] \
    [--execute]

Notes:
  - This script prints curl commands targeting https://open.volcengineapi.com for service "vecr".
  - You MUST provide VolcEngine OpenAPI V4 signing headers yourself.
    Option A: export pre-signed headers as env vars and use --execute.
    Option B: copy the printed curl and run it through your signer.

Env for --execute mode:
  X_DATE           e.g. 20251025T120000Z
  AUTHORIZATION    e.g. HMAC-SHA256 Credential=..., SignedHeaders=..., Signature=...
  X_CONTENT_SHA256 e.g. the SHA256 of body in hex ("UNSIGNED-PAYLOAD" if applicable)

Examples:
  # Print curl (manual signing)
  ./vecr-create-namespace-and-repo.sh --namespace miker --repo miker-web --visibility PRIVATE

  # Execute with pre-signed headers
  X_DATE=... AUTHORIZATION=... X_CONTENT_SHA256=UNSIGNED-PAYLOAD \
  ./vecr-create-namespace-and-repo.sh --namespace miker --repo miker-web --execute
USAGE
}

NAMESPACE=""
REPO=""
VISIBILITY="PRIVATE"
DESC=""
REGION="cn-beijing"
DO_EXECUTE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --namespace) NAMESPACE="$2"; shift 2;;
    --repo) REPO="$2"; shift 2;;
    --visibility) VISIBILITY="$2"; shift 2;;
    --desc) DESC="$2"; shift 2;;
    --region) REGION="$2"; shift 2;;
    --execute) DO_EXECUTE=true; shift;;
    -h|--help) print_usage; exit 0;;
    *) echo "Unknown arg: $1" >&2; print_usage; exit 2;;
  esac
done

if [[ -z "$NAMESPACE" ]]; then
  echo "--namespace is required" >&2; print_usage; exit 2
fi

OPENAPI_ENDPOINT="https://open.volcengineapi.com"
SERVICE="vecr"

create_namespace_body=$(jq -n \
  --arg ns "$NAMESPACE" \
  --arg d  "$DESC" \
  '{NamespaceName: $ns} + ( $d | length > 0 ? {Description: $d} : {} )')

curl_ns=(
  curl -sS -X POST "$OPENAPI_ENDPOINT/" \
    -H "Content-Type: application/json" \
    -H "X-Date: ${X_DATE:-}" \
    -H "Authorization: ${AUTHORIZATION:-}" \
    -H "X-Content-Sha256: ${X_CONTENT_SHA256:-}" \
    -d "$(jq -n \
          --arg a "CreateNamespace" \
          --arg v "latest" \
          --arg r "$REGION" \
          --argjson b "$create_namespace_body" \
          '{Action:$a, Version:$v, Region:$r} + $b)"
)

echo "# CreateNamespace request:"
printf '%q ' "${curl_ns[@]}"; echo

if [[ "$DO_EXECUTE" == true ]]; then
  echo "[EXEC] CreateNamespace..."
  "${curl_ns[@]}"
  echo
fi

if [[ -n "$REPO" ]]; then
  create_repo_body=$(jq -n \
    --arg ns "$NAMESPACE" \
    --arg rn "$REPO" \
    --arg vv "$VISIBILITY" \
    '{Namespace:$ns, RepoName:$rn, Visibility:$vv}')

  curl_repo=(
    curl -sS -X POST "$OPENAPI_ENDPOINT/" \
      -H "Content-Type: application/json" \
      -H "X-Date: ${X_DATE:-}" \
      -H "Authorization: ${AUTHORIZATION:-}" \
      -H "X-Content-Sha256: ${X_CONTENT_SHA256:-}" \
      -d "$(jq -n \
            --arg a "CreateRepository" \
            --arg v "latest" \
            --arg r "$REGION" \
            --argjson b "$create_repo_body" \
            '{Action:$a, Version:$v, Region:$r} + $b)"
  )

  echo "# CreateRepository request:"
  printf '%q ' "${curl_repo[@]}"; echo

  if [[ "$DO_EXECUTE" == true ]]; then
    echo "[EXEC] CreateRepository..."
    "${curl_repo[@]}"
    echo
  fi
fi

echo "[DONE] Generated VECR OpenAPI requests. Sign with VolcEngine V4 and execute if not using --execute mode."


