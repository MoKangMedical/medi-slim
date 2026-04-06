# 💊 MediSlim — 中国版Medvi消费医疗平台

> AI驱动的轻量级消费医疗平台，完全复刻Medvi极简架构模式

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Deploy](https://img.shields.io/badge/Deploy-Production-brightgreen)](#部署)

## 🚀 一句话

**只做流量层，医疗合规全外包。** 一个人 + AI工具 = 消费医疗平台。

## 📦 产品矩阵

| 品类 | 产品 | 首月价 | 续费/月 | 市场规模 |
|------|------|-------|--------|---------|
| 🔥 GLP-1减重 | 司美格鲁肽/替尔泊肽 | ¥399 | ¥599 | 500亿+ |
| 💇 防脱生发 | 米诺地尔+非那雄胺 | ¥199 | ¥299 | 200亿+ |
| 🧴 皮肤管理 | 祛痘/美白/抗衰 | ¥299 | ¥399 | 300亿+ |
| 💪 男性健康 | 精力/睾酮管理 | ¥399 | ¥599 | 150亿+ |
| 😴 助眠调理 | 失眠/褪黑素 | ¥199 | ¥299 | 100亿+ |

## 🏗️ 架构

```
MediSlim (我们)              合作伙伴 (全外包)
┌─────────────────┐         ┌──────────────────┐
│ 品牌/流量        │  ←→    │ 互联网医院        │
│ AI健康评估       │  ←→    │ 合规药房          │
│ 用户运营/复购    │  ←→    │ 物流配送          │
│ 微信小程序       │  ←→    │ 支付通道          │
└─────────────────┘         └──────────────────┘
```

## ⚡ 快速启动

```bash
# 主站（产品页 / 评估 / 订单演示）
python3 app.py

# 独立后台（CRM / 内容 / 平台配置）
python3 admin.py
```

访问入口：
- 前台首页：`http://localhost:8090/`
- 评估中心：`http://localhost:8090/assess`
- 体质辨识：`http://localhost:8090/constitution`
- 成片 Demo：`http://localhost:8090/demo-film`
- 业务流：`http://localhost:8090/flow`
- 运营导航：`http://localhost:8090/admin`
- 管理后台：`http://localhost:8093/`
- 内容预览库：`http://localhost:8096/`
- 转化追踪看板：`http://localhost:8097/api/dashboard`
- 智能排期：`http://localhost:8100/api/schedule/today`
- A/B 看板：`http://localhost:8101/api/ab/dashboard`
- 主站健康检查：`http://localhost:8090/api/health`
- 后台健康检查：`http://localhost:8093/api/admin/health`

## 🤖 小米 MiMo API

主链路里的两类交互现在支持调用 Xiaomi MiMo：

- `/api/assessment/analyze`：保留本地规则判定，再由 MiMo 生成用户可见的说明、注意事项和下一步建议
- `/api/constitution/analyze`：保留体质分型和分数，再由 MiMo 生成更自然的体质解读

本地或服务器配置方式：

```bash
cp .env.example .env
```

然后填写：

```bash
MIMO_ENABLED=1
MIMO_API_KEY=你的小米 MiMo API Key
MIMO_CHAT_MODEL=mimo-v2-flash
MIMO_API_BASE_URL=https://api.xiaomimimo.com/v1
MIMO_TIMEOUT_SECONDS=20
```

重启服务后生效：

```bash
python3 app.py
python3 admin.py
```

或在线上环境执行：

```bash
systemctl restart medislim-app medislim-admin
```

## 🎬 纯前端成片 Demo

现在有一套纯前端动画成片页，包含中文旁白、中文字幕、半真实人物视觉和数据可视化：

- 成片页：`/demo-film`
- 首页默认使用静音循环版
- 配音版保留给手动打开或对外演示

重新导出命令：

```bash
python3 scripts/export_frontend_demo.py
```

导出文件：

- `static/media/demo/medislim-demo-loop.mp4`
- `static/media/demo/medislim-demo-loop.webm`
- `static/media/demo/medislim-demo-voiceover.mp4`
- `static/media/demo/medislim-demo-voiceover.webm`
- `static/media/demo/medislim-demo-poster.png`
- `static/media/demo/medislim-film-manifest.json`
- `static/media/demo/medislim-film-voiceover.wav`

## 🌐 公网访问与自定义域名

匿名公网隧道：

```bash
./scripts/start_services.sh
./scripts/start_public_tunnels.sh
./scripts/read_public_urls.py
```

自定义域名隧道（localhost.run 付费/固定域名方案）：

1. 在 `https://admin.localhost.run` 开通账号与 custom domain。
2. 把本机公钥 `~/.ssh/medislim_localhost_run.pub` 加到 localhost.run 账号。
3. 按 localhost.run 控制台要求，在 DNS 提供商侧完成 `medislim.cloud` / `www.medislim.cloud` / `admin.medislim.cloud` 的验证与解析。
4. 解析生效后启动：

```bash
./scripts/start_services.sh
./scripts/start_custom_domain_tunnels.sh
```

可覆盖默认域名：

```bash
APP_DOMAIN=medislim.cloud \
WWW_DOMAIN=www.medislim.cloud \
ADMIN_DOMAIN=admin.medislim.cloud \
./scripts/start_custom_domain_tunnels.sh
```

## ☁️ 腾讯云轻量服务器部署

如果域名已经直接解析到腾讯云轻量服务器 IP，例如 `43.134.3.158`，不要再走 tunnel，直接看部署手册：

- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

部署模板在这里：

- `scripts/server/install_ubuntu.sh`
- `scripts/server/install_opencloudos.sh`
- `scripts/server/medislim-app.service.template`
- `scripts/server/medislim-admin.service.template`
- `scripts/server/nginx-medislim.conf.template`

## 🔌 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/products` | GET | 产品列表 |
| `/api/hospitals` | GET | 合作医院 |
| `/api/pharmacies` | GET | 合作药房 |
| `/api/partners` | GET | 支付/医院/药房/物流伙伴列表 |
| `/api/user/register` | POST | 用户注册 |
| `/api/user/tracking` | GET | 用户物流查询 |
| `/api/user/refill` | POST | 用户发起续费 |
| `/api/lead/create` | POST | 创建销售线索 |
| `/api/assessment/start` | POST | 开始评估 |
| `/api/assessment/analyze` | POST | AI分析 |
| `/api/constitution/questions` | GET | 九型体质问卷 |
| `/api/constitution/analyze` | POST | 九型体质辨识 |
| `/api/order/create` | POST | 创建订单 |
| `/api/order/action` | POST | 推进订单状态 |
| `/api/order/status` | POST | 订单状态 |
| `/api/pay/create` | POST | 创建支付意图 |
| `/api/pay/callback` | POST | 支付回调 |
| `/api/pay/refund` | POST | 退款并关闭订单 |
| `/api/ih/create_consultation` | POST | 创建互联网医院问诊单 |
| `/api/ih/check_status` | POST | 查询问诊状态 |
| `/api/ih/get_prescription` | POST | 获取电子处方 |
| `/api/pharmacy/submit_order` | POST | 提交药房单 |
| `/api/pharmacy/check_status` | POST | 查询药房状态 |
| `/api/pharmacy/get_tracking` | POST | 查询物流信息 |
| `/api/callback/payment` | POST | 模拟支付回调 |
| `/api/callback/doctor-review` | POST | 模拟医审回调 |
| `/api/callback/logistics` | POST | 模拟物流回调 |
| `/api/subscriptions` | GET | 订阅列表 |
| `/api/subscription/action` | POST | 暂停/恢复/提醒/续费 |
| `/api/wecom/queue` | GET | 企微承接队列 |
| `/api/wecom/handoff` | POST | 新建企微承接任务 |
| `/api/wecom/action` | POST | 企微任务动作 |
| `/api/wecom/message` | POST | 企微任务消息 |
| `/api/content/funnel` | GET | 内容漏斗摘要 |
| `/api/content/performance` | GET | 内容表现排名 |
| `/api/leads` | GET | 线索列表 |
| `/api/stats` | GET | 平台统计 |
| `/api/health` | GET | 主站健康检查 |
| `/api/admin/overview` | GET | 后台总览 |
| `/api/admin/orders` | GET | 后台订单列表 |
| `/api/admin/orders/action` | POST | 后台推进订单动作 |
| `/api/admin/leads` | GET | 后台线索列表 |
| `/api/admin/attribution` | GET | 后台渠道归因汇总 |
| `/api/admin/subscriptions` | GET | 后台订阅中心 |
| `/api/admin/subscriptions/action` | POST | 后台订阅动作 |
| `/api/admin/partners` | GET | 后台伙伴层概览 |
| `/api/admin/wecom` | GET | 后台企微队列 |
| `/api/admin/wecom/action` | POST | 后台企微动作 |
| `/api/admin/content/summary` | GET | 内容中心摘要 |
| `/api/admin/system` | GET | 后台系统状态 |
| `/api/admin/health` | GET | 后台健康检查 |

## 🗂️ 数据文件

- `data/users.json`：前台注册用户
- `data/crm_users.json`：后台 CRM 用户池
- `data/leads.json`：线索池
- `data/orders.json`：订单主存储
- `data/subscriptions.json`：订阅中心
- `data/wecom_queue.json`：企微承接队列
- `data/partner_records.json`：支付/问诊/处方/药房伙伴记录

当前版本会自动兼容早期把订单写入 `products.json` 的旧数据格式，并在启动时迁移到 `orders.json`。

## 🔄 订单链路

当前订单状态机：

`pending_payment` → `paid` → `doctor_review` → `approved` → `pharmacy_processing` → `shipped` → `delivered` → `completed`

异常分支：

`doctor_review` → `rejected`

`pending_payment / paid / doctor_review / approved` → `cancelled`

前台评估页会创建 `pending_payment` 订单；支付回调会自动把订单推进到 `doctor_review`；后续可以通过回调接口或后台按钮继续推进。

## ♻️ 续费链路

- 首单履约完成后自动创建订阅档案
- 订阅状态支持：`pending_activation` / `active` / `paused` / `cancelled` / `past_due`
- 后台可发送提醒、暂停/恢复、取消订阅和直接生成续费订单
- 续费订单会带 `order_kind=renewal` 和 `subscription_id`

## 💰 商业模型

详见 [docs/BUSINESS-MODEL.md](docs/BUSINESS-MODEL.md)

**财务预测（对标Medvi）：**
- 月1-2：冷启动 ¥50万/月
- 月3-6：增长期 ¥500万/月
- 月7-12：规模化 ¥3000万/月
- 净利率：28%（Medvi为16.2%）

## 🔗 关联项目

- **MediChat-RD** — 罕见病AI诊断平台（技术品牌）
- **MediSlim** — 消费医疗平台（本项目，印钞机）

## 📄 License

MIT
