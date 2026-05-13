#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <name> <local_port>"
  exit 1
fi

NAME="$1"
LOCAL_PORT="$2"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/${NAME}-tunnel.log"

while true; do
  echo "[$(date '+%F %T')] starting tunnel for ${NAME} on port ${LOCAL_PORT}" >>"${LOG_FILE}"
  ssh \
    -o StrictHostKeyChecking=no \
    -o ServerAliveInterval=30 \
    -o ExitOnForwardFailure=yes \
    -R 80:localhost:"${LOCAL_PORT}" \
    nokey@localhost.run >>"${LOG_FILE}" 2>&1 || true
  echo "[$(date '+%F %T')] tunnel for ${NAME} disconnected, retrying in 5s" >>"${LOG_FILE}"
  sleep 5
done
