#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "请用 root 运行此脚本"
  exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
  echo "当前系统不是 Ubuntu / Debian，无法使用 apt-get。"
  echo "先运行: cat /etc/os-release"
  exit 1
fi

DOMAIN="${1:-medislim.cloud}"
WWW_DOMAIN="${2:-www.medislim.cloud}"
ADMIN_DOMAIN="${3:-admin.medislim.cloud}"
APP_USER="${APP_USER:-medislim}"
APP_DIR="${APP_DIR:-/opt/medi-slim}"
EMAIL="${EMAIL:-admin@${DOMAIN}}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP_NGINX="/tmp/medislim.nginx.conf"
TMP_APP_SERVICE="/tmp/medislim-app.service"
TMP_ADMIN_SERVICE="/tmp/medislim-admin.service"

export DOMAIN WWW_DOMAIN ADMIN_DOMAIN APP_USER APP_DIR EMAIL

echo "[1/8] 安装系统依赖"
apt-get update
apt-get install -y python3 python3-venv nginx certbot python3-certbot-nginx rsync gettext-base

echo "[2/8] 创建应用用户"
if ! id -u "${APP_USER}" >/dev/null 2>&1; then
  useradd --system --create-home --home-dir "${APP_DIR}" --shell /usr/sbin/nologin "${APP_USER}"
fi

echo "[3/8] 准备应用目录"
mkdir -p "${APP_DIR}"
rsync -a --delete \
  --exclude '.git' \
  --exclude '.env' \
  --exclude '.env.local' \
  --exclude '.env.production' \
  --exclude '__pycache__' \
  --exclude 'logs' \
  --exclude 'run' \
  --exclude '*.pyc' \
  "${ROOT_DIR}/" "${APP_DIR}/"
mkdir -p "${APP_DIR}/logs" "${APP_DIR}/run" "${APP_DIR}/data"
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"
if [[ -f "${APP_DIR}/.env" ]]; then
  chmod 600 "${APP_DIR}/.env"
fi

echo "[4/8] 写入 systemd 服务"
envsubst < "${ROOT_DIR}/scripts/server/medislim-app.service.template" > "${TMP_APP_SERVICE}"
envsubst < "${ROOT_DIR}/scripts/server/medislim-admin.service.template" > "${TMP_ADMIN_SERVICE}"
install -m 644 "${TMP_APP_SERVICE}" /etc/systemd/system/medislim-app.service
install -m 644 "${TMP_ADMIN_SERVICE}" /etc/systemd/system/medislim-admin.service

echo "[5/8] 写入 nginx 站点"
envsubst '${DOMAIN} ${WWW_DOMAIN} ${ADMIN_DOMAIN}' < "${ROOT_DIR}/scripts/server/nginx-medislim.conf.template" > "${TMP_NGINX}"
install -m 644 "${TMP_NGINX}" /etc/nginx/sites-available/medislim.conf
ln -sf /etc/nginx/sites-available/medislim.conf /etc/nginx/sites-enabled/medislim.conf
rm -f /etc/nginx/sites-enabled/default
nginx -t

echo "[6/8] 启动应用服务"
systemctl daemon-reload
systemctl enable medislim-app medislim-admin
systemctl restart medislim-app medislim-admin

echo "[7/8] 启动 nginx"
systemctl enable nginx
systemctl restart nginx

echo "[8/8] 申请 HTTPS 证书"
certbot --nginx --redirect --non-interactive --agree-tos -m "${EMAIL}" \
  -d "${DOMAIN}" -d "${WWW_DOMAIN}" -d "${ADMIN_DOMAIN}"

echo
echo "部署完成"
echo "前台: https://${DOMAIN}"
echo "前台: https://${WWW_DOMAIN}"
echo "后台: https://${ADMIN_DOMAIN}"
echo
echo "检查命令："
echo "  systemctl status medislim-app medislim-admin nginx"
echo "  journalctl -u medislim-app -n 80 --no-pager"
echo "  journalctl -u medislim-admin -n 80 --no-pager"
echo
echo "MiMo 配置："
echo "  cp ${APP_DIR}/.env.example ${APP_DIR}/.env"
echo "  vi ${APP_DIR}/.env   # 填写 MIMO_API_KEY"
echo "  systemctl restart medislim-app medislim-admin"
