#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="${ROOT_DIR}/run"
LOG_DIR="${ROOT_DIR}/logs"
mkdir -p "${RUN_DIR}" "${LOG_DIR}"

APP_DOMAIN="${APP_DOMAIN:-medislim.cloud}"
WWW_DOMAIN="${WWW_DOMAIN:-www.medislim.cloud}"
ADMIN_DOMAIN="${ADMIN_DOMAIN:-admin.medislim.cloud}"

start_named_tunnel() {
  local name="$1"
  local domain="$2"
  local port="$3"
  local pid_file="${RUN_DIR}/${name}_custom_tunnel.pid"

  if [[ -f "${pid_file}" ]] && kill -0 "$(cat "${pid_file}")" 2>/dev/null; then
    echo "${name} custom tunnel already running with pid $(cat "${pid_file}")"
    return
  fi

  (
    cd "${ROOT_DIR}"
    nohup ./scripts/open_localhost_run_tunnel.sh "${domain}" "${port}" >"${LOG_DIR}/${name}_custom_tunnel.log" 2>&1 &
    echo $! >"${pid_file}"
  )

  sleep 2
  if kill -0 "$(cat "${pid_file}")" 2>/dev/null; then
    echo "started ${name} custom tunnel: ${domain} -> localhost:${port} (pid $(cat "${pid_file}"))"
  else
    echo "failed to start ${name} custom tunnel for ${domain}"
    exit 1
  fi
}

start_named_tunnel "app" "${APP_DOMAIN}" "8090"
start_named_tunnel "www" "${WWW_DOMAIN}" "8090"
start_named_tunnel "admin" "${ADMIN_DOMAIN}" "8093"
