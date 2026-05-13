#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="${ROOT_DIR}/run"
LOG_DIR="${ROOT_DIR}/logs"
mkdir -p "${RUN_DIR}" "${LOG_DIR}"

start_tunnel() {
  local name="$1"
  local port="$2"
  local pid_file="${RUN_DIR}/${name}_tunnel.pid"

  if [[ -f "${pid_file}" ]] && kill -0 "$(cat "${pid_file}")" 2>/dev/null; then
    echo "${name} tunnel already running with pid $(cat "${pid_file}")"
    return
  fi

  (
    cd "${ROOT_DIR}"
    nohup ./scripts/tunnel_worker.sh "${name}" "${port}" >"${LOG_DIR}/${name}_tunnel_stdout.log" 2>&1 &
    echo $! >"${pid_file}"
  )

  sleep 2
  if kill -0 "$(cat "${pid_file}")" 2>/dev/null; then
    echo "started ${name} tunnel: pid $(cat "${pid_file}")"
  else
    echo "failed to start ${name} tunnel"
    exit 1
  fi
}

start_tunnel "app" "8090"
start_tunnel "admin" "8093"
