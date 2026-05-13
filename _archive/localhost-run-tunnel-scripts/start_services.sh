#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="${ROOT_DIR}/run"
LOG_DIR="${ROOT_DIR}/logs"

mkdir -p "${RUN_DIR}" "${LOG_DIR}"

start_service() {
  local name="$1"
  local cmd="$2"
  local pid_file="${RUN_DIR}/${name}.pid"
  local log_file="${LOG_DIR}/${name}.log"

  if [[ -f "${pid_file}" ]] && kill -0 "$(cat "${pid_file}")" 2>/dev/null; then
    echo "${name} already running with pid $(cat "${pid_file}")"
    return
  fi

  (
    cd "${ROOT_DIR}"
    nohup ${cmd} >"${log_file}" 2>&1 &
    echo $! >"${pid_file}"
  )

  sleep 1
  if kill -0 "$(cat "${pid_file}")" 2>/dev/null; then
    echo "started ${name}: pid $(cat "${pid_file}")"
  else
    echo "failed to start ${name}, check ${log_file}"
    exit 1
  fi
}

start_service "app" "python3 app.py"
start_service "admin" "python3 admin.py"
