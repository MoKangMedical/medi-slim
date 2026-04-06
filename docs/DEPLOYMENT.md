# MediSlim 部署手册

本文档整理了可复用的服务器上线流程，适用于当前已跑通的域名方案：

- 前台：`medislim.cloud`
- 前台备用网址：`www.medislim.cloud`
- 后台：`admin.medislim.cloud`

## 1. 部署拓扑

```text
浏览器
  -> nginx :80/:443
  -> 127.0.0.1:8090  (app.py)
  -> 127.0.0.1:8093  (admin.py)
```

前后台 Python 服务只监听本机，由 `nginx` 对外暴露。

## 2. DNS 配置

在 DNSPod 中配置：

| 主机记录 | 记录类型 | 记录值 |
| --- | --- | --- |
| `@` | `A` | `43.134.3.158` |
| `www` | `A` | `43.134.3.158` |
| `admin` | `A` | `43.134.3.158` |

腾讯云轻量服务器防火墙/安全组需要放行：

- `22`
- `80`
- `443`

## 3. 首次上线

### 3.1 OpenCloudOS 9 / RHEL 9 系

```bash
dnf install -y git
rm -rf /opt/medi-slim
git clone -b codex/upload-medi-slim-code https://github.com/MoKangMedical/medi-slim.git /opt/medi-slim
cd /opt/medi-slim
bash ./scripts/server/install_opencloudos.sh medislim.cloud www.medislim.cloud admin.medislim.cloud
```

### 3.2 Ubuntu / Debian

```bash
apt-get update
apt-get install -y git
rm -rf /opt/medi-slim
git clone -b codex/upload-medi-slim-code https://github.com/MoKangMedical/medi-slim.git /opt/medi-slim
cd /opt/medi-slim
bash ./scripts/server/install_ubuntu.sh medislim.cloud www.medislim.cloud admin.medislim.cloud
```

如果代码已经合并到主分支，把上面的 `codex/upload-medi-slim-code` 替换为目标分支名。

## 3.3 配置 Xiaomi MiMo API

安装脚本会保留服务器上的 `/opt/medi-slim/.env`，不会在更新时被覆盖。

首次启用 MiMo：

```bash
cd /opt/medi-slim
cp .env.example .env
vi .env
```

至少填写：

```bash
MIMO_ENABLED=1
MIMO_API_KEY=你的 MiMo API Key
MIMO_CHAT_MODEL=mimo-v2-flash
MIMO_API_BASE_URL=https://api.xiaomimimo.com/v1
MIMO_TIMEOUT_SECONDS=20
```

保存后重启：

```bash
systemctl restart medislim-app medislim-admin
```

后台 `https://admin.medislim.cloud` 的系统状态页会显示 “小米 MiMo API” 是否已配置成功。

## 4. 验证清单

```bash
systemctl status medislim-app medislim-admin nginx --no-pager
ss -lntp | grep -E '(:80|:443|:8090|:8093)'
curl -I http://127.0.0.1:8090/api/health
curl -I http://127.0.0.1:8093/api/admin/health
curl -I https://medislim.cloud
curl -I https://www.medislim.cloud
curl -I https://admin.medislim.cloud
```

期望结果：

- `medislim-app` 为 `active (running)`
- `medislim-admin` 为 `active (running)`
- `nginx` 为 `active (running)`
- `127.0.0.1:8090`、`127.0.0.1:8093` 正在监听
- 三个域名均返回 `200` 或前台 `301 -> https`

## 5. 日常更新

```bash
cd /opt/medi-slim
git fetch origin
git checkout codex/upload-medi-slim-code
git pull --ff-only origin codex/upload-medi-slim-code
bash ./scripts/server/install_opencloudos.sh medislim.cloud www.medislim.cloud admin.medislim.cloud
```

如果是 Ubuntu，把最后一条换成：

```bash
bash ./scripts/server/install_ubuntu.sh medislim.cloud www.medislim.cloud admin.medislim.cloud
```

安装脚本会：

- 同步代码到部署目录
- 重新生成 systemd 服务文件
- 重新生成 nginx 配置
- 重启前后台与 nginx
- 在证书存在时复用 HTTPS 配置

## 6. 关键文件

- `app.py`：前台服务，默认端口 `8090`
- `admin.py`：后台服务，默认端口 `8093`
- `scripts/server/install_opencloudos.sh`：OpenCloudOS / RHEL 安装脚本
- `scripts/server/install_ubuntu.sh`：Ubuntu / Debian 安装脚本
- `scripts/server/medislim-app.service.template`：前台 systemd 模板
- `scripts/server/medislim-admin.service.template`：后台 systemd 模板
- `scripts/server/nginx-medislim.conf.template`：nginx 反向代理模板

## 7. 常见故障

### 7.1 访问返回 502

说明 `nginx` 起了，但后端服务没起。

```bash
systemctl status medislim-app medislim-admin --no-pager
journalctl -u medislim-app -n 80 --no-pager
journalctl -u medislim-admin -n 80 --no-pager
```

### 7.2 HTTPS 不通

先检查 `nginx` 是否正常：

```bash
nginx -t
systemctl status nginx --no-pager
```

再手动申请证书：

```bash
certbot --nginx --redirect --non-interactive --agree-tos \
  -m admin@medislim.cloud \
  -d medislim.cloud \
  -d www.medislim.cloud \
  -d admin.medislim.cloud
```

### 7.3 OpenCloudOS 上 nginx 无法反代本机端口

通常是 SELinux 限制：

```bash
setsebool -P httpd_can_network_connect 1
```

### 7.4 防火墙没放行

```bash
systemctl enable --now firewalld
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --reload
```

## 8. 当前线上入口

- [https://medislim.cloud](https://medislim.cloud)
- [https://www.medislim.cloud](https://www.medislim.cloud)
- [https://admin.medislim.cloud](https://admin.medislim.cloud)
