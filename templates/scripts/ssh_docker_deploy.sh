#!/usr/bin/env bash
set -euo pipefail

# Local helper to deploy over SSH, mirroring the GitLab template logic.
# Requires: ssh access to ${DEPLOY_USER}@${DEPLOY_HOST}

: "${DEPLOY_HOST?}"
: "${DEPLOY_USER?}"
: "${CONTAINER_NAME?}"
: "${DEPLOY_PORTS?}"
: "${IMAGE_REF?}"

RUN_PORTS=""
IFS=',' read -ra PORTS_ARR <<< "${DEPLOY_PORTS}"
for mapping in "${PORTS_ARR[@]}"; do
  RUN_PORTS="$RUN_PORTS -p ${mapping}"
done

RUN_ENVS=""
if [[ -n "${ENV_VARS:-}" ]]; then
  for kv in ${ENV_VARS}; do
    RUN_ENVS="$RUN_ENVS -e ${kv}"
  done
fi

RUN_VOLUMES=""
if [[ -n "${VOLUMES:-}" ]]; then
  for vol in ${VOLUMES}; do
    RUN_VOLUMES="$RUN_VOLUMES -v ${vol}"
  done
fi

RUN_NETWORK=""
if [[ -n "${NETWORK:-}" ]]; then
  RUN_NETWORK="--network ${NETWORK}"
fi

EXTRA_ARGS="${ADDITIONAL_RUN_ARGS:-}"

ssh "${DEPLOY_USER}@${DEPLOY_HOST}" bash -s <<EOS
set -euo pipefail
echo "Pulling: ${IMAGE_REF}"
docker pull "${IMAGE_REF}"
if docker ps -a --format '{{.Names}}' | grep -Eq "^${CONTAINER_NAME}$"; then
  docker rm -f "${CONTAINER_NAME}" || true
fi
echo "Starting: ${CONTAINER_NAME}"
# shellcheck disable=SC2086
docker run -d --restart=always --name "${CONTAINER_NAME}" ${RUN_PORTS} ${RUN_ENVS} ${RUN_VOLUMES} ${RUN_NETWORK} ${EXTRA_ARGS} "${IMAGE_REF}"
docker ps --filter name="${CONTAINER_NAME}" --format 'table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
EOS

if [[ -n "${HEALTHCHECK_URL:-}" ]]; then
  echo "Waiting for healthcheck: ${HEALTHCHECK_URL}"
  for _ in {1..30}; do
    if curl -fsS "${HEALTHCHECK_URL}" >/dev/null 2>&1; then
      echo "Healthy"
      exit 0
    fi
    sleep 2
  done
  echo "Healthcheck failed"
  exit 1
fi


