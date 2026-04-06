#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <subdomain> <local_port>"
  echo "Example: $0 medislim.lhr.rocks 8090"
  exit 1
fi

SUBDOMAIN="$1"
LOCAL_PORT="$2"
KEY_PATH="${HOME}/.ssh/medislim_localhost_run"

if [[ ! -f "${KEY_PATH}" ]]; then
  echo "Missing SSH key: ${KEY_PATH}"
  echo "Generate it first with:"
  echo "  ssh-keygen -t ed25519 -f ${KEY_PATH} -N '' -C 'medislim-localhost-run'"
  exit 1
fi

exec ssh \
  -i "${KEY_PATH}" \
  -o StrictHostKeyChecking=accept-new \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 \
  -R "${SUBDOMAIN}:80:localhost:${LOCAL_PORT}" \
  plan@localhost.run
