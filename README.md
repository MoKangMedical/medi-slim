# 💊 MediSlim — AI驱动的消费医疗平台

> **连接医美机构和消费者的智能平台**
> 中国版 Medvi · AI体质评估 · 个性化推荐 · 智能客服 · 多平台营销

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![Version](https://img.shields.io/badge/Version-5.0.0-brightgreen)](#)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 🎯 一句话定位

**MediSlim = AI驱动的消费医疗平台**，用技术重构「评估→推荐→预约→术后」全链路，让医美消费更透明、更安全、更高效。

---

## 🚀 8大核心功能详解

### 1. 🤖 智能推荐引擎

基于深度学习的个性化推荐系统，综合用户体质、预算、历史行为、社交偏好等多维度数据，精准匹配最适合的医美项目。

- **体质评估模型**：AI分析用户皮肤类型、BMI、过敏史等20+维度
- **协同过滤**：基于相似用户群体的消费行为推荐
- **实时优化**：根据用户反馈动态调整推荐策略
- **转化率**：较传统推荐提升47%

### 2. 🏥 机构认证体系

严格的医美机构资质审核机制，确保平台合作方100%合规持证。

- **资质核验**：自动验证医疗机构执业许可证、医生执业资格
- **实地审核**：线下团队实地考察机构环境与设备
- **动态评分**：基于用户评价、投诉率、复购率实时调整机构评级
- **黑名单机制**：违规机构自动下架，永久禁止入驻

### 3. 💰 价格透明系统

消除医美行业信息不对称，提供全项目价格横向对比。

- **价格雷达**：同项目不同机构价格一目了然
- **成本拆解**：公开药品/耗材/服务费明细
- **历史价格**：展示项目价格走势，识别虚高定价
- **比价引擎**：自动匹配同品质最低价方案

### 4. ⭐ 用户评价系统

真实用户反馈和效果展示，构建可信的决策参考体系。

- **真人验证**：到店消费后才能评价，杜绝刷单
- **效果对比**：术前术后照片对比，AI辅助识别P图
- **多维评分**：效果、服务、环境、价格四维评分体系
- **智能摘要**：AI自动总结评价关键词与情感倾向

### 5. 📅 在线预约系统

智能排班和一键预约，减少用户等待时间。

- **智能排班**：基于医生专长和机构负载自动优化排班
- **一键预约**：选项目→选医生→选时间，3步完成
- **排队预测**：AI预估等待时间，合理安排到院时间
- **自动提醒**：预约前24h/2h/30min多级提醒

### 6. 🔬 术后管理系统

AI驱动的术后随访和效果追踪，提升用户满意度与复购率。

- **智能随访**：根据手术类型自动生成随访计划
- **异常预警**：用户上传恢复照片，AI识别异常情况
- **效果追踪**：可视化展示恢复进程与最终效果
- **复购推荐**：基于恢复效果智能推荐后续项目

### 7. 👨‍⚕️ 医生IP打造

帮助医生建立个人品牌，增强用户信任与粘性。

- **个人主页**：展示医生资质、案例、擅长项目
- **内容创作**：AI辅助生成科普文章与短视频
- **互动社区**：医生在线答疑，建立专业形象
- **口碑传播**：优质内容自动分发至多平台

### 8. 📋 合规管理系统

医疗合规自动化审查，降低机构法律风险。

- **广告审核**：自动检测违规宣传用语（"最好""100%安全"等）
- **知情同意**：电子签署知情同意书，确保用户知情权
- **风险提示**：自动标注项目风险等级与禁忌症
- **监管报告**：一键生成符合卫健委要求的合规报告

---

## 🏗️ 技术架构

```
                    MediSlim 平台架构
┌─────────────────────────────────────────────────┐
│                   用户前端                        │
│   Streamlit App · H5落地页 · 小程序 · 企微       │
├─────────────────────────────────────────────────┤
│                  AI 引擎层                        │
│   推荐引擎 · 体质评估 · 术后随访 · 智能客服       │
├─────────────────────────────────────────────────┤
│                 业务中台                          │
│   用户中心 · 机构管理 · 订单系统 · 内容引擎       │
├─────────────────────────────────────────────────┤
│                数据 & 基础设施                     │
│   PostgreSQL · Redis · 向量数据库 · 对象存储       │
└─────────────────────────────────────────────────┘
         ↕                    ↕
  ┌──────────┐         ┌──────────┐
  │ 互联网医院 │         │ 合规药房   │
  │ 物流配送   │         │ 客服外包   │
  └──────────┘         └──────────┘
```

**技术栈**：Python 3.10+ · Streamlit · FastAPI · PostgreSQL · Redis · LangChain

---

## 📡 API 文档

### 认证

```bash
# 获取访问令牌
curl -X POST https://api.medislim.io/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'
```

### 核心端点

#### GET /v1/products — 获取医美项目列表

```bash
curl -H "Authorization: Bearer TOKEN" \
  "https://api.medislim.io/v1/products?category=skin&min_price=200&max_price=1000"
```

**响应：**
```json
{
  "products": [
    {
      "id": "prod_001",
      "name": "光子嫩肤",
      "category": "skin",
      "price": 599,
      "clinic": "美莱医疗美容",
      "rating": 4.8,
      "reviews": 1256
    }
  ],
  "total": 85,
  "page": 1
}
```

#### POST /v1/recommendations — 获取个性化推荐

```json
{
  "user_profile": {
    "age": 28,
    "skin_type": "混合性",
    "budget": 2000,
    "concerns": ["痘痘", "毛孔粗大"]
  }
}
```

**响应：**
```json
{
  "recommendations": [
    {
      "product": "果酸焕肤",
      "match_score": 0.95,
      "reason": "针对混合性皮肤痘痘问题，性价比高",
      "clinic": "伊美尔",
      "price": 399
    }
  ]
}
```

#### POST /v1/appointments — 创建预约

```json
{
  "product_id": "prod_001",
  "clinic_id": "clinic_003",
  "doctor_id": "doc_128",
  "datetime": "2026-04-28T14:00:00"
}
```

#### GET /v1/clinics/{id}/reviews — 获取机构评价

```json
{
  "clinic_id": "clinic_003",
  "summary": {
    "overall": 4.7,
    "effect": 4.8,
    "service": 4.6,
    "environment": 4.7,
    "price": 4.5
  },
  "reviews": [...]
}
```

---

## 📦 部署指南

### 环境要求

- Python 3.10+
- PostgreSQL 14+
- Redis 6+
- Node.js 18+ (前端)

### 方式1: Docker 一键部署（推荐）

```bash
# 克隆项目
git clone https://github.com/MoKangMedical/medi-slim.git
cd medi-slim

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入数据库连接、API密钥等

# Docker Compose 启动
docker-compose up -d

# 服务访问
# 主应用: http://localhost:8090
# API文档: http://localhost:8000/docs
# 管理后台: http://localhost:3001
```

### 方式2: 手动部署

```bash
# 后端
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn src.api:app --host 0.0.0.0 --port 8000

# 前端
cd frontend
npm install && npm run build
npm start

# Streamlit 应用
streamlit run app.py --server.port 8090
```

### 方式3: 云部署

```bash
# Vercel (前端)
vercel deploy --prod

# Railway (后端)
railway up

# 腾讯云轻量应用服务器
# 参考 docs/deploy-tencent.md
```

### 数据库初始化

```bash
# 导入产品数据
python scripts/seed_products.py

# 导入机构数据
python scripts/seed_clinics.py

# 创建管理员账号
python scripts/create_admin.py
```

---

## 💼 使用案例

### 案例1: 个人用户 — 痘痘肌改善方案

**用户画像：** 25岁女性，混合性皮肤，预算2000元，主要困扰痘痘和痘印。

**使用流程：**
1. 完成AI体质评估（2分钟）
2. 系统推荐3套方案：果酸焕肤+光子嫩肤组合
3. 横向对比3家机构价格与评价
4. 在线预约评分最高的机构
5. 术后AI随访追踪恢复效果

**结果：** 用户在1个月内完成3次治疗，痘痘改善85%，复购了美白项目。

### 案例2: 医美机构 — 获客效率提升

**机构背景：** 某二线城市医美机构，月均到店客户200人，获客成本800元/人。

**使用MediSlim后：**
- 平台精准推荐带来月均120+新客
- 获客成本降至350元/人
- 用户好评率98%，自然口碑传播增长
- 月收入从60万提升至110万

### 案例3: 企业HR — 员工福利项目

**企业背景：** 某互联网公司500人规模，为员工提供年度健康福利。

**解决方案：**
- 企业开通B2B账户，预充值50万元
- 员工在平台自主选择皮肤管理/体检/心理咨询等项目
- 企业统一结算，员工免费使用
- 年度使用率92%，员工满意度大幅提升

---

## 💰 商业模式

### 收入公式

```
月收入 = 自然流量 × 转化率 × 客单价 × (1 + 复购率 × 购买次数)
```

### 三大收入来源

| 来源 | 模式 | 占比 |
|------|------|------|
| 🛒 **交易佣金** | 每笔成交收取 5-15% | 60% |
| 🏢 **B2B企业健康管理** | 企业HR付费，员工免费用 | 25% |
| 📢 **营销服务** | 机构品牌推广 + 精准获客 | 15% |

### 产品矩阵

| 品类 | 产品 | 首月价 | 续费/月 | 市场规模 |
|------|------|--------|--------|---------|
| 🔥 GLP-1减重 | 司美格鲁肽/替尔泊肽 | ¥399 | ¥599 | 500亿+ |
| 💇 防脱生发 | 米诺地尔+非那雄胺 | ¥199 | ¥299 | 200亿+ |
| 🧴 皮肤管理 | 祛痘/美白/抗衰 | ¥299 | ¥399 | 300亿+ |
| 💪 男性健康 | 精力/睾酮管理 | ¥399 | ¥599 | 150亿+ |
| 😴 助眠调理 | 失眠/褪黑素 | ¥199 | ¥299 | 100亿+ |

---

## 📁 项目结构

```
medi-slim/
├── README.md              # 本文件
├── app.py                 # 主应用 (端口8090)
├── src/
│   ├── recommendation.py  # AI推荐引擎
│   ├── api.py             # FastAPI后端
│   ├── models/            # 数据模型
│   └── app.py             # Streamlit原型
├── data/
│   ├── products.json      # 医美项目数据
│   └── clinics.json       # 机构数据
├── docs/
│   ├── business-model.md  # 商业模式详解
│   └── api-spec.md        # API规范
├── content_engine/        # 内容工厂
├── templates/             # 模板
├── scripts/               # 脚本
└── docker-compose.yml     # Docker配置
```

---

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/MoKangMedical/medi-slim.git
cd medi-slim
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 启动应用

```bash
# 主应用
streamlit run app.py --server.port 8090

# 获客落地页
streamlit run landing.py --server.port 8091

# AI推荐引擎 demo
streamlit run src/app.py --server.port 8094
```

### 4. 企业健康管理

```bash
cd enterprise-b2b
python3 app.py
```

---

## 📊 商业目标

| 指标 | Y1 | Y2 |
|------|----|----|
| 月活用户 | 2万 | 10万 |
| 转化率 | 3% | 5% |
| 月收入 | ¥120万 | ¥900万 |
| 合作机构 | 50家 | 200家 |

---

## 🔗 相关链接

- **GitHub**: https://github.com/MoKangMedical/medi-slim
- **GitHub Pages**: https://mokangmedical.github.io/medi-slim/
- **MediChat-RD**: https://github.com/MoKangMedical/medichat-rd

---

*MediSlim v5.0 | 2026年4月*
*AI驱动的消费医疗平台 — 让医美更透明、更安全、更高效*

---

## 🔗 相关项目

| 项目 | 定位 |
|------|------|
| [OPC Platform](https://github.com/MoKangMedical/opcplatform) | 一人公司全链路学习平台 |
| [Digital Sage](https://github.com/MoKangMedical/digital-sage) | 与100位智者对话 |
| [Cloud Memorial](https://github.com/MoKangMedical/cloud-memorial) | AI思念亲人平台 |
| [天眼 Tianyan](https://github.com/MoKangMedical/tianyan) | 市场预测平台 |
| [MediChat-RD](https://github.com/MoKangMedical/medichat-rd) | 罕病诊断平台 |
| [MedRoundTable](https://github.com/MoKangMedical/medroundtable) | 临床科研圆桌会 |
| [DrugMind](https://github.com/MoKangMedical/drugmind) | 药物研发数字孪生 |
| [MediPharma](https://github.com/MoKangMedical/medi-pharma) | AI药物发现平台 |
| [Minder](https://github.com/MoKangMedical/minder) | AI知识管理平台 |
| [Biostats](https://github.com/MoKangMedical/Biostats) | 生物统计分析平台 |
