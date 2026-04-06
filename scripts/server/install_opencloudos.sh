#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "请用 root 运行此脚本"
  exit 1
fi

if ! command -v dnf >/dev/null 2>&1; then
  echo "当前系统没有 dnf，不像 OpenCloudOS / RHEL 9。"
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

echo "[1/9] 安装系统依赖"
dnf makecache
dnf install -y python3 nginx rsync gettext firewalld policycoreutils-python-utils

if ! dnf install -y certbot python3-certbot-nginx; then
  echo "certbot 包在当前仓库不可用，请先启用可用仓库后重试。"
  echo "建议检查：dnf repolist"
  exit 1
fi

echo "[2/9] 创建应用用户"
if ! id -u "${APP_USER}" >/dev/null 2>&1; then
  useradd --system --create-home --home-dir "${APP_DIR}" --shell /usr/sbin/nologin "${APP_USER}"
fi

echo "[3/9] 准备应用目录"
mkdir -p "${APP_DIR}"
rsync -a --delete \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude 'logs' \
  --exclude 'run' \
  --exclude '*.pyc' \
  "${ROOT_DIR}/" "${APP_DIR}/"
mkdir -p "${APP_DIR}/logs" "${APP_DIR}/run" "${APP_DIR}/data"
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"

echo "[4/9] 写入 systemd 服务"
envsubst < "${ROOT_DIR}/scripts/server/medislim-app.service.template" > "${TMP_APP_SERVICE}"
envsubst < "${ROOT_DIR}/scripts/server/medislim-admin.service.template" > "${TMP_ADMIN_SERVICE}"
install -m 644 "${TMP_APP_SERVICE}" /etc/systemd/system/medislim-app.service
install -m 644 "${TMP_ADMIN_SERVICE}" /etc/systemd/system/medislim-admin.service

echo "[5/9] 写入 nginx 站点"
envsubst '${DOMAIN} ${WWW_DOMAIN} ${ADMIN_DOMAIN}' < "${ROOT_DIR}/scripts/server/nginx-medislim.conf.template" > "${TMP_NGINX}"
install -m 644 "${TMP_NGINX}" /etc/nginx/conf.d/medislim.conf
nginx -t

echo "[6/9] 配置 firewalld"
systemctl enable --now firewalld || true
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --reload

echo "[7/9] 配置 SELinux 反向代理权限"
setsebool -P httpd_can_network_connect 1 || true

echo "[8/9] 启动应用和 nginx"
systemctl daemon-reload
systemctl enable --now medislim-app medislim-admin nginx
systemctl restart medislim-app medislim-admin nginx

echo "[9/9] 申请 HTTPS 证书"
certbot --nginx --redirect --non-interactive --agree-tos -m "${EMAIL}" \
  -d "${DOMAIN}" -d "${WWW_DOMAIN}" -d "${ADMIN_DOMAIN}"

echo
echo "部署完成"
echo "前台: https://${DOMAIN}"
echo "前台: https://${WWW_DOMAIN}"
echo "后台: https://${ADMIN_DOMAIN}"
echo
echo "检查命令："
echo "  systemctl status medislim-app medislim-admin nginx --no-pager"
echo "  journalctl -u medislim-app -n 80 --no-pager"
echo "  journalctl -u medislim-admin -n 80 --no-pager"
echo "  curl -I https://${DOMAIN}"
