"""
MediSlim 中央管理平台
统一管理：内容发布 / 用户CRM / 订单管理 / 数据分析 / 多平台对接
"""
import os
import json
from datetime import datetime
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from order_flow import decorate_order
from partner_hub import partner_dashboard
from storage import BASE_DIR, load_json, save_json, load_orders, migrate_legacy_orders, now_iso, short_id
from subscription_engine import list_subscriptions, due_subscriptions
from wecom_handoff import queue_summary

try:
    from content_engine.tracking import get_funnel, get_content_performance
    from content_engine.ab_testing import analyze_ab
    from content_engine.scheduler import generate_schedule
except Exception:  # pragma: no cover - optional integration
    get_funnel = None
    get_content_performance = None
    analyze_ab = None
    generate_schedule = None

APP_ORIGIN = os.environ.get("MEDISLIM_APP_ORIGIN", "http://127.0.0.1:8090")
CONTENT_CATALOG_PATH = BASE_DIR / "content_engine" / "output" / "catalog.json"
STATIC_CONTENT_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}

def load_db(name):
    return load_json(name, {})

def save_db(name, data):
    save_json(name, data)

def now():
    return now_iso()

def gen_id():
    return short_id()


def static_content_type(filepath):
    return STATIC_CONTENT_TYPES.get(Path(filepath).suffix.lower(), "application/octet-stream")


def load_all_users():
    merged = {}

    for user in load_db("users").values():
        key = user.get("phone") or user.get("id")
        merged[key] = {
            "id": user.get("id"),
            "name": user.get("name", "用户"),
            "phone": user.get("phone", ""),
            "channel": "direct",
            "tags": [],
            "lifecycle": "lead",
            "health_profile": {},
            "orders": user.get("orders", []),
            "interactions": [],
            "value_score": 0,
            "created_at": user.get("created_at", now()),
            "updated_at": user.get("created_at", now()),
        }

    for user in load_db("crm_users").values():
        key = user.get("phone") or user.get("id")
        merged[key] = {
            **merged.get(key, {}),
            **user,
        }

    return {user["id"]: user for user in merged.values() if user.get("id")}


def sorted_items(mapping):
    return sorted(
        mapping.values(),
        key=lambda item: item.get("updated_at") or item.get("created_at") or "",
        reverse=True,
    )


def check_service(url):
    try:
        with urlopen(url, timeout=1.2) as response:
            if response.status < 400:
                return "running"
    except URLError:
        return "stopped"
    except Exception:
        return "stopped"

    return "degraded"


def forward_app_post(path, payload):
    body = json.dumps(payload).encode("utf-8")
    request = urlopen
    from urllib.request import Request

    req = Request(
        f"{APP_ORIGIN}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request(req, timeout=2.5) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        payload = json.loads(exc.read().decode("utf-8"))
        raise ValueError(payload.get("error", "应用服务请求失败")) from exc
    except URLError as exc:
        raise ValueError("主站服务不可达，无法执行订单动作") from exc


def system_status():
    return [
        {
            "name": "主站前台",
            "entry": "app.py",
            "port": 8090,
            "health_url": "http://127.0.0.1:8090/api/health",
            "description": "产品页、评估、下单演示",
            "status": check_service("http://127.0.0.1:8090/api/health"),
        },
        {
            "name": "管理后台",
            "entry": "admin.py",
            "port": 8093,
            "health_url": "http://127.0.0.1:8093/api/admin/health",
            "description": "CRM、内容、平台配置",
            "status": check_service("http://127.0.0.1:8093/api/admin/health"),
        },
        {
            "name": "内容预览库",
            "entry": "content_engine/preview_server.py",
            "port": 8096,
            "health_url": "http://127.0.0.1:8096/api/stats",
            "description": "浏览、筛选、预览已生成内容",
            "status": check_service("http://127.0.0.1:8096/api/stats"),
        },
        {
            "name": "转化追踪",
            "entry": "content_engine/tracking.py",
            "port": 8097,
            "health_url": "http://127.0.0.1:8097/api/funnel",
            "description": "内容归因、UTM、转化漏斗",
            "status": check_service("http://127.0.0.1:8097/api/funnel"),
        },
        {
            "name": "智能排期",
            "entry": "content_engine/scheduler.py",
            "port": 8100,
            "health_url": "http://127.0.0.1:8100/api/schedule/today",
            "description": "每日内容排期与发布时间建议",
            "status": check_service("http://127.0.0.1:8100/api/schedule/today"),
        },
        {
            "name": "A/B 分析",
            "entry": "content_engine/ab_testing.py",
            "port": 8101,
            "health_url": "http://127.0.0.1:8101/api/ab/analysis",
            "description": "内容排名、品类对比和转化洞察",
            "status": check_service("http://127.0.0.1:8101/api/ab/analysis"),
        },
    ]

# ========== 平台配置 ==========
PLATFORMS = {
    "wechat": {
        "name": "微信公众号",
        "icon": "💬",
        "status": "pending",
        "config_fields": ["app_id", "app_secret", "token", "encoding_aes_key"],
        "capabilities": ["auto_reply", "menu", "template_msg", "customer_service", "payment"],
        "setup_url": "https://mp.weixin.qq.com",
        "docs": "需要：营业执照 + 认证服务号（¥300/年）",
    },
    "wechat_mini": {
        "name": "微信小程序",
        "icon": "📱",
        "status": "pending",
        "config_fields": ["app_id", "app_secret"],
        "capabilities": ["assessment", "order", "tracking", "community"],
        "setup_url": "https://mp.weixin.qq.com",
        "docs": "需要：营业执照 + 小程序认证（¥300）+ 类目审核（医疗需资质）",
    },
    "wecom": {
        "name": "企业微信",
        "icon": "🏢",
        "status": "ready",
        "config_fields": ["corp_id", "agent_id", "secret"],
        "capabilities": ["customer_service", "group_chat", "crm", "auto_reply"],
        "setup_url": "https://work.weixin.qq.com",
        "docs": "免费注册，可直接用作客服和私域运营",
    },
    "xiaohongshu": {
        "name": "小红书",
        "icon": "📕",
        "status": "pending",
        "config_fields": ["account_id", "cookie"],
        "capabilities": ["publish", "analytics", "comment_manage"],
        "setup_url": "https://www.xiaohongshu.com",
        "docs": "企业号需营业执照，个人号直接注册",
    },
    "douyin": {
        "name": "抖音",
        "icon": "🎵",
        "status": "pending",
        "config_fields": ["client_key", "client_secret"],
        "capabilities": ["publish", "analytics", "live", "ads"],
        "setup_url": "https://developer.open-douyin.com",
        "docs": "企业号需营业执照+对公打款验证",
    },
    "alipay": {
        "name": "支付宝",
        "icon": "💰",
        "status": "pending",
        "config_fields": ["app_id", "private_key", "alipay_public_key"],
        "capabilities": ["payment", "refund", "transfer"],
        "setup_url": "https://open.alipay.com",
        "docs": "需要：营业执照 + 对公账户",
    },
    "wechat_pay": {
        "name": "微信支付",
        "icon": "💚",
        "status": "pending",
        "config_fields": ["mch_id", "api_key", "cert_path"],
        "capabilities": ["payment", "refund", "transfer", "bill"],
        "setup_url": "https://pay.weixin.qq.com",
        "docs": "需要：营业执照 + 对公账户 + 认证服务号",
    },
    "sf_express": {
        "name": "顺丰物流",
        "icon": "📦",
        "status": "pending",
        "config_fields": ["customer_code", "check_word"],
        "capabilities": ["create_order", "tracking", "cancel"],
        "setup_url": "https://open.sf-express.com",
        "docs": "需要签约顺丰月结客户",
    },
}

# ========== 内容管理 ==========
class ContentManager:
    """多平台内容管理"""
    
    TEMPLATES = {
        "xiaohongshu": {
            "glp1_case": {
                "title": "🔥 {name}减重{days}天记录：从{start}kg到{end}kg",
                "content": "分享我的减重经历...\n#减重 #{product} #科学减重",
                "type": "case",
            },
            "tcm_health": {
                "title": "中医体质自测：你是哪种体质？9种体质对照表",
                "content": "根据中医理论，人的体质分为9种...\n#中医 #体质 #养生",
                "type": "education",
            },
            "product_review": {
                "title": "💊 我在MediSlim的{product}体验：{summary}",
                "content": "使用{days}天后的真实感受...\n#{product} #健康",
                "type": "review",
            },
        },
        "douyin": {
            "hook_video": {
                "title": "{hook}",
                "script": "前3秒：{hook}\n中间：解决问题\n结尾：引导评论",
                "duration": "30-60s",
            },
            "doctor_explain": {
                "title": "医生说：{topic}",
                "script": "专业科普+通俗表达+数据支撑",
                "duration": "60-90s",
            },
        },
        "wechat_article": {
            "deep_dive": {
                "title": "{topic}：你需要知道的一切",
                "sections": ["引言", "原理", "方法", "案例", "总结", "CTA"],
            },
        },
    }
    
    @staticmethod
    def generate_content(platform, template_id, variables=None):
        """生成内容"""
        variables = variables or {}
        template = ContentManager.TEMPLATES.get(platform, {}).get(template_id, {})
        if not template:
            return {"error": "模板不存在"}
        
        result = {}
        for key, value in template.items():
            if isinstance(value, str) and "{" in value:
                try:
                    result[key] = value.format(**variables)
                except KeyError:
                    result[key] = value
            else:
                result[key] = value
        
        result["id"] = gen_id()
        result["platform"] = platform
        result["template_id"] = template_id
        result["status"] = "draft"
        result["created_at"] = now()
        
        # 保存到内容库
        contents = load_db("contents")
        contents[result["id"]] = result
        save_db("contents", contents)
        
        return result

# ========== 用户CRM ==========
class CRMManager:
    """客户关系管理"""
    
    CHANNELS = ["wechat", "xiaohongshu", "douyin", "direct", "referral"]
    
    @staticmethod
    def add_user(name, phone, channel="direct", tags=None):
        """添加用户"""
        users = load_db("crm_users")
        # 检查是否已存在
        existing = [u for u in users.values() if u.get("phone") == phone]
        if existing:
            return existing[0]
        
        user = {
            "id": gen_id(),
            "name": name,
            "phone": phone,
            "channel": channel,
            "tags": tags or [],
            "lifecycle": "lead",
            "health_profile": {},
            "orders": [],
            "interactions": [],
            "value_score": 0,
            "created_at": now(),
            "updated_at": now(),
        }
        users[user["id"]] = user
        save_db("crm_users", users)
        return user
    
    @staticmethod
    def update_lifecycle(user_id, new_stage):
        """更新用户生命周期"""
        stages = ["lead", "assessed", "first_order", "active", "vip", "churned"]
        if new_stage not in stages:
            return None
        users = load_db("crm_users")
        user = users.get(user_id)
        if user:
            old_stage = user.get("lifecycle", "lead")
            user["lifecycle"] = new_stage
            user["updated_at"] = now()
            user["interactions"].append({
                "time": now(),
                "type": "lifecycle_change",
                "detail": f"从 {old_stage} 到 {new_stage}",
            })
            save_db("crm_users", users)
        return user
    
    @staticmethod
    def get_dashboard():
        """CRM看板"""
        users = load_all_users().values()
        by_lifecycle = {}
        by_channel = {}
        for u in users:
            lc = u.get("lifecycle", "unknown")
            ch = u.get("channel", "unknown")
            by_lifecycle[lc] = by_lifecycle.get(lc, 0) + 1
            by_channel[ch] = by_channel.get(ch, 0) + 1
        
        return {
            "total_users": len(list(users)),
            "by_lifecycle": by_lifecycle,
            "by_channel": by_channel,
        }

# ========== 数据分析 ==========
class AnalyticsManager:
    """数据分析引擎"""
    
    @staticmethod
    def get_overview():
        """总览数据"""
        users = load_all_users()
        orders = load_orders()
        leads = load_db("leads")
        contents = load_db("contents")
        lead_phones = {lead.get("phone") for lead in leads.values() if lead.get("phone")}
        converted_leads = sum(
            1
            for user in users.values()
            if user.get("phone") in lead_phones and len(user.get("orders", [])) > 0
        )
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        return {
            "overview": {
                "total_users": len(users),
                "total_orders": len(orders),
                "total_leads": len(leads),
                "total_content": len(contents),
            },
            "today": {
                "new_users": sum(1 for u in users.values() if u.get("created_at", "")[:10] == today),
                "new_leads": sum(1 for l in leads.values() if l.get("created_at", "")[:10] == today),
                "new_orders": sum(1 for o in orders.values() if o.get("created_at", "")[:10] == today),
            },
            "conversion": {
                "lead_to_order": round(converted_leads / max(len(leads), 1) * 100, 1) if leads else 0.0,
                "content_published": sum(1 for c in contents.values() if c.get("status") == "published"),
            },
        }

    @staticmethod
    def get_attribution_summary():
        leads = load_db("leads")
        orders = load_orders()

        summary = {}
        for lead in leads.values():
            attribution = lead.get("attribution", {})
            source = attribution.get("utm_source") or lead.get("source") or "direct"
            campaign = attribution.get("utm_campaign") or "organic"
            key = f"{source}::{campaign}"
            bucket = summary.setdefault(key, {
                "source": source,
                "campaign": campaign,
                "ref": attribution.get("ref", ""),
                "leads": 0,
                "orders": 0,
                "revenue": 0,
            })
            bucket["leads"] += 1

        for order in orders.values():
            attribution = order.get("attribution", {})
            source = attribution.get("utm_source") or attribution.get("source") or "direct"
            campaign = attribution.get("utm_campaign") or "organic"
            key = f"{source}::{campaign}"
            bucket = summary.setdefault(key, {
                "source": source,
                "campaign": campaign,
                "ref": attribution.get("ref", ""),
                "leads": 0,
                "orders": 0,
                "revenue": 0,
            })
            bucket["orders"] += 1
            bucket["revenue"] += order.get("price", 0)

        rows = []
        for item in summary.values():
            item["lead_to_order"] = round(item["orders"] / item["leads"] * 100, 1) if item["leads"] else 0.0
            rows.append(item)

        rows.sort(key=lambda item: (item["orders"], item["leads"], item["revenue"]), reverse=True)
        return rows

    @staticmethod
    def get_content_summary():
        catalog = []
        if CONTENT_CATALOG_PATH.exists():
            catalog = json.loads(CONTENT_CATALOG_PATH.read_text(encoding="utf-8"))

        funnel = get_funnel(hours=168) if get_funnel else {}
        performance = get_content_performance(6) if get_content_performance else []
        ab_report = analyze_ab() if analyze_ab else {}
        today_schedule = generate_schedule() if generate_schedule else {}

        return {
            "catalog": {
                "total": len(catalog),
                "products": len({entry.get("product_id", "") for entry in catalog}) if catalog else 0,
                "styles": len({entry.get("style", "") for entry in catalog}) if catalog else 0,
                "palettes": len({entry.get("palette_id", "") for entry in catalog}) if catalog else 0,
            },
            "funnel": funnel,
            "performance": performance,
            "ab": {
                "insights": ab_report.get("insights", []),
                "top_10": ab_report.get("top_10", [])[:5],
            } if isinstance(ab_report, dict) else {},
            "schedule": today_schedule,
            "links": {
                "preview": "http://127.0.0.1:8096/",
                "tracking": "http://127.0.0.1:8097/api/dashboard",
                "scheduler": "http://127.0.0.1:8100/api/schedule/today",
                "ab": "http://127.0.0.1:8101/api/ab/dashboard",
            },
        }

# ========== HTTP管理后台 ==========
ADMIN_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MediSlim 管理后台</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,sans-serif;background:#f5f5f5}
.header{background:linear-gradient(135deg,#07C160,#059B48);color:#fff;padding:20px;display:flex;justify-content:space-between;align-items:center}
.header h1{font-size:22px}
.nav{display:flex;gap:8px}
.nav a{color:rgba(255,255,255,.8);text-decoration:none;padding:8px 16px;border-radius:8px;font-size:14px}
.nav a.active{background:rgba(255,255,255,.2);color:#fff}
.container{max-width:1200px;margin:20px auto;padding:0 20px}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px}
.stat-card{background:#fff;border-radius:12px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.stat-card .label{font-size:13px;color:#999}
.stat-card .value{font-size:28px;font-weight:700;color:#07C160;margin-top:8px}
.stat-card .change{font-size:12px;color:#999;margin-top:4px}
.card{background:#fff;border-radius:12px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,.06);margin-bottom:16px}
.card h3{font-size:16px;font-weight:600;margin-bottom:16px;display:flex;align-items:center;gap:8px}
table{width:100%;border-collapse:collapse}
th,td{padding:12px;text-align:left;border-bottom:1px solid #f0f0f0;font-size:14px}
th{color:#999;font-weight:500}
.badge{padding:4px 10px;border-radius:12px;font-size:12px;font-weight:500}
.badge-green{background:#D1FAE5;color:#065F46}
.badge-yellow{background:#FEF3C7;color:#92400E}
.badge-red{background:#FEE2E2;color:#991B1B}
.badge-gray{background:#F3F4F6;color:#6B7280}
.btn{padding:8px 16px;border:none;border-radius:8px;font-size:13px;cursor:pointer;font-weight:500}
.btn-primary{background:#07C160;color:#fff}
.btn-outline{background:transparent;border:1px solid #07C160;color:#07C160}
.platform-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.platform-card{border:2px solid #E5E7EB;border-radius:12px;padding:16px;cursor:pointer;transition:all .15s}
.platform-card:hover{border-color:#07C160}
.platform-card.connected{border-color:#07C160;background:#F0FFF4}
.platform-icon{font-size:28px;margin-bottom:8px}
.platform-name{font-size:15px;font-weight:600}
.platform-status{font-size:12px;margin-top:4px}
.content-list{display:flex;flex-direction:column;gap:12px}
.content-item{display:flex;justify-content:space-between;align-items:center;padding:12px;background:#F9FAFB;border-radius:10px}
.content-item .title{font-size:14px;font-weight:500}
.content-item .meta{font-size:12px;color:#999}
</style>
</head>
<body>
<div class="header">
  <h1>💊 MediSlim 管理后台</h1>
  <div class="nav">
    <a href="#" class="active">📊 总览</a>
    <a href="#platforms">🔗 平台</a>
    <a href="#content">📝 内容</a>
    <a href="#crm">👥 用户</a>
  </div>
</div>

<div class="container">
  <!-- 统计卡片 -->
  <div class="grid" id="stats-grid"></div>

  <!-- 平台接入 -->
  <div class="card" id="platforms">
    <h3>🔗 多平台接入</h3>
    <div class="platform-grid" id="platform-grid"></div>
  </div>

  <!-- 内容管理 -->
  <div class="card" id="content">
    <h3>📝 内容管理</h3>
    <div style="display:flex;gap:8px;margin-bottom:16px">
      <button class="btn btn-primary" onclick="genContent('xiaohongshu')">📕 生成小红书</button>
      <button class="btn btn-primary" onclick="genContent('douyin')">🎵 生成抖音</button>
      <button class="btn btn-outline" onclick="genContent('wechat_article')">💬 生成公众号</button>
    </div>
    <div class="content-list" id="content-list"></div>
  </div>

  <!-- CRM -->
  <div class="card" id="crm">
    <h3>👥 用户CRM</h3>
    <table>
      <thead><tr><th>用户</th><th>渠道</th><th>阶段</th><th>价值</th><th>操作</th></tr></thead>
      <tbody id="crm-table"></tbody>
    </table>
  </div>

  <!-- 系统状态 -->
  <div class="card">
    <h3>⚙️ 系统状态</h3>
    <div class="grid" id="system-grid"></div>
  </div>
</div>

<script>
const API = location.origin;

async function loadDashboard() {
  // 总览数据
  const overview = await fetch('/api/admin/overview').then(r=>r.json());
  document.getElementById('stats-grid').innerHTML = `
    <div class="stat-card"><div class="label">总用户</div><div class="value">${overview.overview.total_users}</div><div class="change">今日新增 ${overview.today.new_users}</div></div>
    <div class="stat-card"><div class="label">总线索</div><div class="value">${overview.overview.total_leads}</div><div class="change">今日新增 ${overview.today.new_leads}</div></div>
    <div class="stat-card"><div class="label">总订单</div><div class="value">${overview.overview.total_orders}</div><div class="change">今日新增 ${overview.today.new_orders}</div></div>
    <div class="stat-card"><div class="label">转化率</div><div class="value">${overview.conversion.lead_to_order}%</div><div class="change">线索→订单</div></div>
  `;

  // 平台接入
  const platforms = await fetch('/api/admin/platforms').then(r=>r.json());
  document.getElementById('platform-grid').innerHTML = Object.entries(platforms).map(([k,v])=>`
    <div class="platform-card ${v.status==='ready'?'connected':''}">
      <div class="platform-icon">${v.icon}</div>
      <div class="platform-name">${v.name}</div>
      <div class="platform-status">
        <span class="badge ${v.status==='ready'?'badge-green':'badge-gray'}">${v.status==='ready'?'已连接':'待配置'}</span>
      </div>
      <div style="font-size:12px;color:#999;margin-top:8px">${v.docs}</div>
    </div>
  `).join('');

  // 内容
  const contents = await fetch('/api/admin/contents').then(r=>r.json());
  document.getElementById('content-list').innerHTML = contents.length ? contents.slice(-5).reverse().map(c=>`
    <div class="content-item">
      <div><div class="title">${c.title||'无标题'}</div><div class="meta">${c.platform} · ${c.type||'未知'} · ${c.status}</div></div>
      <span class="badge ${c.status==='published'?'badge-green':'badge-yellow'}">${c.status}</span>
    </div>
  `).join('') : '<p style="color:#999;text-align:center;padding:20px">暂无内容，点击上方按钮生成</p>';

  // CRM
  const crm = await fetch('/api/admin/crm').then(r=>r.json());
  document.getElementById('crm-table').innerHTML = Object.values(crm).slice(-5).reverse().map(u=>`
    <tr>
      <td>${u.name||'未命名'}</td>
      <td><span class="badge badge-gray">${u.channel}</span></td>
      <td><span class="badge ${u.lifecycle==='active'?'badge-green':'badge-yellow'}">${u.lifecycle}</span></td>
      <td>${u.value_score||0}</td>
      <td><button class="btn btn-outline" style="font-size:12px;padding:4px 12px">详情</button></td>
    </tr>
  `).join('') || '<tr><td colspan="5" style="text-align:center;color:#999">暂无用户</td></tr>';

  // 系统状态
  document.getElementById('system-grid').innerHTML = `
    <div class="stat-card"><div class="label">app.py</div><div class="value" style="font-size:16px">🟢 :8090</div><div class="change">评估+下单</div></div>
    <div class="stat-card"><div class="label">landing.py</div><div class="value" style="font-size:16px">🟢 :8091</div><div class="change">获客落地页</div></div>
    <div class="stat-card"><div class="label">flow_engine</div><div class="value" style="font-size:16px">🟢 :8092</div><div class="change">业务流引擎</div></div>
    <div class="stat-card"><div class="label">admin</div><div class="value" style="font-size:16px">🟢 :8093</div><div class="change">管理后台</div></div>
  `;
}

async function genContent(platform) {
  const templates = {xiaohongshu:'glp1_case',douyin:'hook_video',wechat_article:'deep_dive'};
  await fetch('/api/admin/content/generate',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({platform,template_id:templates[platform]||'glp1_case',variables:{name:'用户',days:'30',start:'85',end:'70',product:'GLP-1',summary:'效果很好',hook:'你知道吗？30天瘦了15斤',topic:'科学减重',}})
  });
  loadDashboard();
}

loadDashboard();
</script>
</body>
</html>"""

class AdminHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self._send_common_headers("application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]

        if path in ("/", "/index.html"):
            self._serve("templates/admin_dashboard.html", "text/html; charset=utf-8")
        elif path.startswith("/static/"):
            self._serve(path[1:], static_content_type(path))
        elif path == "/api/admin/overview":
            self._json(AnalyticsManager.get_overview())
        elif path == "/api/admin/platforms":
            self._json(PLATFORMS)
        elif path == "/api/admin/contents":
            self._json(sorted_items(load_db("contents")))
        elif path == "/api/admin/orders":
            self._json(sorted_items({key: decorate_order(value) for key, value in load_orders().items()}))
        elif path == "/api/admin/leads":
            self._json(sorted_items(load_db("leads")))
        elif path == "/api/admin/crm":
            self._json(load_all_users())
        elif path == "/api/admin/crm/dashboard":
            self._json(CRMManager.get_dashboard())
        elif path == "/api/admin/attribution":
            self._json(AnalyticsManager.get_attribution_summary())
        elif path == "/api/admin/subscriptions":
            self._json({
                "items": list_subscriptions(),
                "due": due_subscriptions(),
            })
        elif path == "/api/admin/partners":
            self._json(partner_dashboard())
        elif path == "/api/admin/wecom":
            self._json(queue_summary())
        elif path == "/api/admin/system":
            self._json(system_status())
        elif path == "/api/admin/content/templates":
            self._json(ContentManager.TEMPLATES)
        elif path == "/api/admin/content/summary":
            self._json(AnalyticsManager.get_content_summary())
        elif path == "/api/admin/health":
            self._json({"status": "ok", "service": "admin"})
        else:
            self._json({"error": "Not found"}, 404)
    
    def do_POST(self):
        try:
            data = self._read_json_body()
        except ValueError as exc:
            self._json({"error": str(exc)}, 400)
            return
        
        path = self.path.split("?")[0]
        
        if path == "/api/admin/content/generate":
            result = ContentManager.generate_content(
                data.get("platform", ""),
                data.get("template_id", ""),
                data.get("variables", {})
            )
            self._json(result)

        elif path == "/api/admin/orders/action":
            order_id = data.get("order_id", "")
            action = data.get("action", "")
            if not order_id or not action:
                self._json({"error": "order_id 和 action 不能为空"}, 400)
                return
            try:
                order = forward_app_post("/api/order/action", data)
            except ValueError as exc:
                self._json({"error": str(exc)}, 400)
                return
            self._json(order)

        elif path == "/api/admin/subscriptions/action":
            try:
                result = forward_app_post("/api/subscription/action", data)
            except ValueError as exc:
                self._json({"error": str(exc)}, 400)
                return
            self._json(result)

        elif path == "/api/admin/wecom/action":
            try:
                result = forward_app_post("/api/wecom/action", data)
            except ValueError as exc:
                self._json({"error": str(exc)}, 400)
                return
            self._json(result)

        elif path == "/api/admin/wecom/message":
            try:
                result = forward_app_post("/api/wecom/message", data)
            except ValueError as exc:
                self._json({"error": str(exc)}, 400)
                return
            self._json(result)
        
        elif path == "/api/admin/crm/add":
            user = CRMManager.add_user(
                data.get("name", ""),
                data.get("phone", ""),
                data.get("channel", "direct"),
                data.get("tags", [])
            )
            self._json(user)
        
        elif path == "/api/admin/platform/config":
            # 保存平台配置
            platform = data.get("platform", "")
            config = data.get("config", {})
            configs = load_db("platform_configs")
            configs[platform] = {"config": config, "updated_at": now()}
            save_db("platform_configs", configs)
            self._json({"success": True, "platform": platform})
        
        else:
            self._json({"error": "Not found"}, 404)
    
    def _html(self, html):
        self.send_response(200)
        self._send_common_headers("text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _serve(self, relative_path, content_type):
        full = BASE_DIR / relative_path
        if not full.exists():
            self._json({"error": "Not found"}, 404)
            return

        self.send_response(200)
        self._send_common_headers(content_type)
        self.end_headers()
        self.wfile.write(full.read_bytes())
    
    def _json(self, data, status=200):
        self.send_response(status)
        self._send_common_headers("application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))

    def _send_common_headers(self, content_type):
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}

        try:
            body = self.rfile.read(length).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("请求体编码必须是 UTF-8") from exc

        if not body.strip():
            return {}

        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise ValueError("请求体不是合法 JSON") from exc
    
    def log_message(self, *a): pass

def main():
    migrate_legacy_orders()
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8093))
    server = ThreadingHTTPServer((host, port), AdminHandler)
    print(f"🖥️ MediSlim 管理后台启动: http://{host}:{port}")
    print(f"💚 健康检查: http://localhost:{port}/api/admin/health")
    server.serve_forever()

if __name__ == "__main__":
    main()
