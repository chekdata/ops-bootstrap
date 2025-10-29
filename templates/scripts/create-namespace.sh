#!/usr/bin/env bash
set -euo pipefail

print_usage() {
  cat <<'USAGE'
Usage:
  create-namespace.sh --kubeconfig PATH --namespace NAME
  create-namespace.sh --kubeconfig PATH --product NAME --env ENV

Options:
  --kubeconfig PATH   Path to kubeconfig file (required)
  --namespace NAME    Full namespace name (e.g., miker-prod)
  --product NAME      Product name (used with --env)
  --env ENV           Environment name (dev|staging|prod)

Notes:
  - If --namespace is not provided, the script uses "<product>-<env>".
  - The script is idempotent. It creates the namespace if missing and
    applies baseline ResourceQuota, LimitRange, and default-deny NetworkPolicy.
USAGE
}

KUBECONFIG_PATH=""
NAMESPACE=""
PRODUCT=""
ENVIRONMENT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --kubeconfig)
      KUBECONFIG_PATH="$2"; shift 2;;
    --namespace)
      NAMESPACE="$2"; shift 2;;
    --product)
      PRODUCT="$2"; shift 2;;
    --env)
      ENVIRONMENT="$2"; shift 2;;
    -h|--help)
      print_usage; exit 0;;
    *)
      echo "Unknown argument: $1" >&2; print_usage; exit 2;;
  esac
done

if [[ -z "$KUBECONFIG_PATH" ]]; then
  echo "--kubeconfig is required" >&2; print_usage; exit 2
fi

if [[ -z "$NAMESPACE" ]]; then
  if [[ -z "$PRODUCT" || -z "$ENVIRONMENT" ]]; then
    echo "Provide --namespace or both --product and --env" >&2; print_usage; exit 2
  fi
  NAMESPACE="${PRODUCT}-${ENVIRONMENT}"
fi

export KUBECONFIG="$KUBECONFIG_PATH"

echo "[INFO] Ensuring namespace: $NAMESPACE"
if ! kubectl get ns "$NAMESPACE" >/dev/null 2>&1; then
  kubectl create namespace "$NAMESPACE"
  echo "[OK] Created namespace $NAMESPACE"
else
  echo "[OK] Namespace $NAMESPACE already exists"
fi

echo "[INFO] Applying baseline quotas, limits, and default deny policy"
cat <<'YAML' | kubectl -n "$NAMESPACE" apply -f -
apiVersion: v1
kind: ResourceQuota
metadata:
  name: rq-basic
spec:
  hard:
    requests.cpu: "4"
    requests.memory: 8Gi
    limits.cpu: "8"
    limits.memory: 16Gi
---
apiVersion: v1
kind: LimitRange
metadata:
  name: lr-defaults
spec:
  limits:
    - type: Container
      default:
        cpu: "500m"
        memory: 512Mi
      defaultRequest:
        cpu: "100m"
        memory: 128Mi
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
YAML

echo "[DONE] Namespace $NAMESPACE is ready."


