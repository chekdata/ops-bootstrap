#!/usr/bin/env bash
set -euo pipefail

# Bootstrap a Kubernetes environment for miker per the guide.
# Usage:
#   ENV=dev DOMAIN=miker-dev.chekkk.com REGISTRY_ENDPOINT=... REGISTRY_USERNAME=... REGISTRY_PASSWORD=... \
#   ./ops-bootstrap/commands/k8s_env_bootstrap.sh

required() { [ -n "${!1:-}" ] || { echo "Missing required env: $1" >&2; exit 2; }; }

ENVIRONMENT=${ENV:-}
required ENV

NAMESPACE="miker-${ENVIRONMENT}"
DOMAIN_NAME=${DOMAIN:-}
[ -n "$DOMAIN_NAME" ] || echo "Warn: DOMAIN not set; skipping TLS/Ingress pieces"

REG_ENDPOINT=${REGISTRY_ENDPOINT:-}
REG_USER=${REGISTRY_USERNAME:-}
REG_PASS=${REGISTRY_PASSWORD:-}

if [ -n "$REG_ENDPOINT$REG_USER$REG_PASS" ]; then
  echo "Creating imagePullSecret vecr-auth in namespace $NAMESPACE"
  kubectl get ns "$NAMESPACE" >/dev/null 2>&1 || kubectl create namespace "$NAMESPACE"
  kubectl -n "$NAMESPACE" delete secret vecr-auth >/dev/null 2>&1 || true
  kubectl -n "$NAMESPACE" create secret docker-registry vecr-auth \
    --docker-server="$REG_ENDPOINT" \
    --docker-username="$REG_USER" \
    --docker-password="$REG_PASS"
else
  echo "Skip creating vecr-auth (REGISTRY_* not provided)"
fi

echo "Installing/Upgrading ingress-nginx"
kubectl get ns ingress-nginx >/dev/null 2>&1 || kubectl create namespace ingress-nginx
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx >/dev/null
helm repo update >/dev/null
helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  -f ops-bootstrap/templates/k8s/ingress-nginx/values.yaml

if [ -n "${TLS_SECRET_NAME:-}" ] && [ -f "${TLS_CRT:-tls.crt}" ] && [ -f "${TLS_KEY:-tls.key}" ]; then
  echo "Creating TLS secret ${TLS_SECRET_NAME} in ${NAMESPACE}"
  kubectl -n "$NAMESPACE" delete secret "$TLS_SECRET_NAME" >/dev/null 2>&1 || true
  kubectl -n "$NAMESPACE" create secret tls "$TLS_SECRET_NAME" \
    --cert="${TLS_CRT:-tls.crt}" --key="${TLS_KEY:-tls.key}"
fi

echo "Done. Next steps:"
echo "- Set FEISHU_CHAT_ID_DEV/FEISHU_CHAT_ID_STG secrets if not set"
echo "- Deploy miker via Helm chart with Service port name http and targetPort 3000"





