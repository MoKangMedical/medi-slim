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
# 直接运行（零依赖）
python3 app.py

# 访问
# 前端：http://localhost:8090
# API：http://localhost:8090/api/stats
```

## 🔌 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/products` | GET | 产品列表 |
| `/api/hospitals` | GET | 合作医院 |
| `/api/user/register` | POST | 用户注册 |
| `/api/assessment/start` | POST | 开始评估 |
| `/api/assessment/analyze` | POST | AI分析 |
| `/api/order/create` | POST | 创建订单 |
| `/api/order/status` | POST | 订单状态 |
| `/api/stats` | GET | 平台统计 |

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
