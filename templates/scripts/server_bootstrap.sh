#!/usr/bin/env bash
set -euo pipefail

# Usage: bash server_bootstrap.sh
# Prepares a fresh Linux host to receive SSH-based Docker deploys.

if [[ $(id -u) -ne 0 ]]; then
  echo "Run as root (sudo)" >&2
  exit 1
fi

DEPLOY_USER=${DEPLOY_USER:-deploy}

echo "[1/5] Ensuring user '${DEPLOY_USER}' exists..."
if ! id -u "$DEPLOY_USER" >/dev/null 2>&1; then
  useradd -m -s /bin/bash "$DEPLOY_USER"
fi
mkdir -p "/home/${DEPLOY_USER}/.ssh"
chmod 700 "/home/${DEPLOY_USER}/.ssh"
touch "/home/${DEPLOY_USER}/.ssh/authorized_keys"
chmod 600 "/home/${DEPLOY_USER}/.ssh/authorized_keys"
chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "/home/${DEPLOY_USER}/.ssh"

echo "[2/5] Installing Docker (if missing)..."
if ! command -v docker >/dev/null 2>&1; then
  if command -v apt-get >/dev/null 2>&1; then
    apt-get update -y
    apt-get install -y ca-certificates curl gnupg lsb-release
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/$(. /etc/os-release; echo "$ID")/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo \ 
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$(. /etc/os-release; echo \"$ID\") \"$(. /etc/os-release; echo \"$VERSION_CODENAME\")\" stable" \
      | tee /etc/apt/sources.list.d/docker.list >/dev/null
    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io
  elif command -v yum >/dev/null 2>&1; then
    yum install -y yum-utils device-mapper-persistent-data lvm2
    yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    yum install -y docker-ce docker-ce-cli containerd.io
    systemctl enable docker
    systemctl start docker
  else
    echo "Unsupported distro. Install Docker manually." >&2
    exit 1
  fi
fi

echo "[3/5] Adding '${DEPLOY_USER}' to docker group..."
usermod -aG docker "$DEPLOY_USER" || true

echo "[4/5] Enabling Docker at boot..."
systemctl enable docker || true
systemctl restart docker || true

echo "[5/5] Optional: create docker network 'app-net'"
if ! docker network ls --format '{{.Name}}' | grep -q '^app-net$'; then
  docker network create app-net >/dev/null || true
fi

echo "Bootstrap complete. Upload your CI public key to /home/${DEPLOY_USER}/.ssh/authorized_keys"


