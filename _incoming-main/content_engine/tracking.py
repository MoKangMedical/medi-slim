"""
MediSlim 流量承接 & 转化追踪系统
UTM链接生成 → 落地页承接 → 事件埋点 → 漏斗看板
零依赖，Python标准库
"""
import os
import json
import uuid
import time
from datetime import datetime, timedelta
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# ========== 数据读写 ==========

def load_json(name, default=None):
    p = DATA_DIR / f"{name}.json"
    if p.exists():
        return json.loads(p.read_text())
    return default if default is not None else {}

def save_json(name, data):
    (DATA_DIR / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))


# ========== 1. UTM链接生成 ==========

BASE_URL = "https://mokangmedical.github.io/medi-slim"

# 小红书不支持直接超链接，实际引流路径：
# 小红书笔记 → 评论区/主页引导搜索 → 微信/落地页
# 为每套内容生成：
#   1. 追踪码（用于落地页识别来源）
#   2. 引导话术（评论区第一条）
#   3. 落地页URL（带UTM参数）

PLATFORMS = {
    "xiaohongshu": {"name": "小红书", "prefix": "xhs"},
    "douyin": {"name": "抖音", "prefix": "dy"},
    "weixin": {"name": "微信", "prefix": "wx"},
    "weibo": {"name": "微博", "prefix": "wb"},
}


def generate_tracking_links(catalog_entry, platform="xiaohongshu"):
    """为一条内容生成全套追踪链接"""
    content_id = catalog_entry["id"]
    product_id = catalog_entry["product_id"]
    prefix = PLATFORMS[platform]["prefix"]

    # 追踪码：平台_品类_内容ID前8位
    track_code = f"{prefix}_{product_id}_{content_id[:8]}"

    # UTM参数
    utm = {
        "utm_source": platform,
        "utm_medium": "social",
        "utm_campaign": f"medislim_{product_id}",
        "utm_content": content_id[:12],
        "utm_term": catalog_entry.get("hook_category", ""),
        "ref": track_code,
    }

    utm_str = "&".join(f"{k}={v}" for k, v in utm.items())
    landing_url = f"{BASE_URL}?{utm_str}"

    # 评论区引导话术（小红书风格）
    cta_comments = _generate_cta_comments(catalog_entry, track_code)

    return {
        "track_code": track_code,
        "landing_url": landing_url,
        "utm": utm,
        "platform": platform,
        "cta_comments": cta_comments,
    }


def _generate_cta_comments(entry, track_code):
    """生成评论区引导话术（小红书引流核心）"""
    product_id = entry["product_id"]
    product_emoji = {"glp1": "🔥", "hair": "💇", "skin": "🧴", "mens": "💪", "sleep": "😴"}
    emoji = product_emoji.get(product_id, "💊")

    return [
        f"{emoji} 想了解的姐妹扣1，我私你链接～",
        f"回复【{track_code}】获取专属优惠方案",
        f"🔍 搜「MediSlim」小程序，输入口令「{track_code[-6:]}」解锁隐藏优惠",
        f"有同款困扰的姐妹可以看看我主页～详细方案都写在里面了",
        f"想了解更多扣「要」，我一个个发你～",
    ]


# ========== 2. 转化事件追踪 ==========

EVENT_TYPES = [
    "impression",    # 小红书笔记曝光
    "click",         # 点击笔记/链接
    "comment",       # 评论互动
    "landing",       # 到达落地页
    "assess_start",  # 开始评估
    "assess_done",   # 完成评估
    "order_create",  # 创建订单
    "order_pay",     # 支付完成
    "reorder",       # 复购
]


def track_event(track_code, event_type, extra=None):
    """记录一个转化事件"""
    if event_type not in EVENT_TYPES:
        return {"error": f"unknown event type: {event_type}"}

    events = load_json("tracking_events", [])
    event = {
        "id": str(uuid.uuid4())[:12],
        "track_code": track_code,
        "event_type": event_type,
        "timestamp": datetime.now().isoformat(),
        "ts": time.time(),
        "extra": extra or {},
    }
    events.append(event)

    # 只保留最近30天
    cutoff = time.time() - 30 * 86400
    events = [e for e in events if e.get("ts", 0) > cutoff]

    save_json("tracking_events", events)
    return {"ok": True, "event_id": event["id"]}


def get_events(track_code=None, event_type=None, hours=24):
    """查询事件"""
    events = load_json("tracking_events", [])
    cutoff = time.time() - hours * 3600
    events = [e for e in events if e.get("ts", 0) > cutoff]

    if track_code:
        events = [e for e in events if e["track_code"] == track_code]
    if event_type:
        events = [e for e in events if e["event_type"] == event_type]

    return events


# ========== 3. 转化漏斗 ==========

def get_funnel(product_id=None, hours=168):
    """获取转化漏斗数据（默认7天）"""
    events = load_json("tracking_events", [])
    cutoff = time.time() - hours * 3600
    events = [e for e in events if e.get("ts", 0) > cutoff]

    if product_id:
        events = [e for e in events if e["track_code"].startswith(f"_") or
                  any(f"_{product_id}_" in e["track_code"] for p in PLATFORMS.values())]

    funnel = {}
    for et in EVENT_TYPES:
        funnel[et] = len([e for e in events if e["event_type"] == et])

    # 计算转化率
    rates = {}
    prev = funnel.get("impression", 0)
    for et in EVENT_TYPES[1:]:
        curr = funnel.get(et, 0)
        rates[et] = round(curr / prev * 100, 2) if prev > 0 else 0
        prev = curr if curr > 0 else prev

    return {
        "funnel": funnel,
        "rates": rates,
        "period_hours": hours,
        "total_events": len(events),
    }


def get_content_performance(top_n=20):
    """获取各内容的转化表现排名"""
    events = load_json("tracking_events", [])

    # 按track_code聚合
    by_code = {}
    for e in events:
        code = e["track_code"]
        if code not in by_code:
            by_code[code] = {et: 0 for et in EVENT_TYPES}
        by_code[code][e["event_type"]] = by_code[code].get(e["event_type"], 0) + 1

    # 计算得分（加权）
    scored = []
    weights = {
        "impression": 1, "click": 2, "comment": 3,
        "landing": 5, "assess_start": 8, "assess_done": 10,
        "order_create": 20, "order_pay": 30, "reorder": 25,
    }
    for code, counts in by_code.items():
        score = sum(counts.get(et, 0) * w for et, w in weights.items())
        scored.append({"track_code": code, "score": score, **counts})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_n]


# ========== 4. 自动化投放配置 ==========

def generate_ad_config(product_id, budget_daily=100):
    """生成每日投放配置"""
    from copywriter import PRODUCTS, get_sample

    product = PRODUCTS.get(product_id, {})
    configs = []

    # 从6种钩子类型各选2条，6种风格各选1条
    hook_types = ["焦虑型", "好奇型", "干货型", "种草型", "励志型", "反转型"]
    styles = ["闺蜜体", "专业体", "种草体", "焦虑体", "励志体", "故事体"]

    for hook_type in hook_types:
        copies = get_sample(product_id, count=2)
        for c in copies:
            links = generate_tracking_links({
                "id": c["id"],
                "product_id": product_id,
                "hook_category": c["hook_category"],
            })
            configs.append({
                "copy": c,
                "tracking": links,
                "budget": round(budget_daily / (len(hook_types) * 2), 2),
                "schedule": "daily",
            })

    return {
        "product_id": product_id,
        "product_name": product.get("name", ""),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "total_budget": budget_daily,
        "ads": configs,
        "test_variants": len(configs),
    }


# ========== 5. 引流入口页面 ==========

def generate_redirect_page(track_code):
    """生成带追踪的中间页（微信内打开）"""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MediSlim · 免费健康评估</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,"PingFang SC",sans-serif;background:#f8f8f8;min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:20px}}
.card{{background:#fff;border-radius:20px;padding:40px 30px;max-width:400px;width:100%;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,.08)}}
.emoji{{font-size:60px;margin-bottom:20px}}
.title{{font-size:24px;font-weight:700;color:#1a1a1a;margin-bottom:12px}}
.desc{{font-size:15px;color:#666;line-height:1.6;margin-bottom:30px}}
.btn{{display:block;width:100%;background:linear-gradient(135deg,#07C160,#059B48);color:#fff;font-size:18px;font-weight:600;padding:16px;border-radius:50px;border:none;cursor:pointer;margin-bottom:16px;text-decoration:none}}
.btn:hover{{opacity:.9}}
.btn-secondary{{background:#fff;color:#07C160;border:2px solid #07C160}}
.trust{{font-size:12px;color:#999;margin-top:20px;line-height:1.8}}
input{{width:100%;padding:14px 18px;border:2px solid #eee;border-radius:12px;font-size:16px;margin-bottom:16px;outline:none;transition:border .2s}}
input:focus{{border-color:#07C160}}
</style>
</head>
<body>
<div class="card">
  <div class="emoji">🏥</div>
  <div class="title">免费健康评估</div>
  <div class="desc">填写基本信息，医生为您定制个性化方案<br>全程线上，足不出户</div>
  <input type="tel" placeholder="请输入手机号" id="phone">
  <a href="#" class="btn" onclick="submitLead()">立即免费评估 →</a>
  <a href="#" class="btn btn-secondary" onclick="skipAssess()">先看看方案介绍</a>
  <div class="trust">🔒 信息严格保密 · ✅ 免费评估 · 💊 不满意随时退</div>
</div>
<script>
const ref='{track_code}';
fetch('/api/track',{{
  method:'POST',
  headers:{{'Content-Type':'application/json'}},
  body:JSON.stringify({{track_code:ref,event_type:'landing'}})
}}).catch(()=>{{}});

function submitLead(){{
  const phone=document.getElementById('phone').value;
  if(!phone||phone.length<11){{alert('请输入正确手机号');return;}}
  fetch('/api/track',{{
    method:'POST',
    headers:{{'Content-Type':'application/json'}},
    body:JSON.stringify({{track_code:ref,event_type:'assess_start',extra:{{phone:phone.slice(0,3)+'****'+phone.slice(-4)}}}})
  }}).catch(()=>{{}});
  // 跳转评估页
  window.location.href='/assess?ref='+ref+'&phone='+encodeURIComponent(phone);
}}
function skipAssess(){{
  fetch('/api/track',{{
    method:'POST',
    headers:{{'Content-Type':'application/json'}},
    body:JSON.stringify({{track_code:ref,event_type:'click',extra:{{action:'skip_to_intro'}}}})
  }}).catch(()=>{{}});
  window.location.href='/?ref='+ref;
}}
</script>
</body></html>"""


# ========== HTTP API ==========

class TrackingHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        if path == "/api/funnel":
            hours = int(params.get("hours", [168])[0])
            pid = params.get("product", [None])[0]
            self._json_response(get_funnel(pid, hours))

        elif path == "/api/performance":
            top_n = int(params.get("top", [20])[0])
            self._json_response(get_content_performance(top_n))

        elif path == "/api/events":
            code = params.get("code", [None])[0]
            et = params.get("type", [None])[0]
            hours = int(params.get("hours", [24])[0])
            self._json_response(get_events(code, et, hours))

        elif path == "/api/ad-config":
            pid = params.get("product", ["glp1"])[0]
            budget = int(params.get("budget", [100])[0])
            self._json_response(generate_ad_config(pid, budget))

        elif path.startswith("/r/"):
            # 短链接重定向 /r/{track_code}
            code = path.split("/r/")[1]
            track_event(code, "click")
            page = generate_redirect_page(code)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(page.encode())

        elif path == "/api/dashboard":
            self._serve_dashboard()

        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/track":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            result = track_event(
                body.get("track_code", ""),
                body.get("event_type", ""),
                body.get("extra"),
            )
            self._json_response(result)

        elif path == "/api/generate-links":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            links = generate_tracking_links(body, body.get("platform", "xiaohongshu"))
            self._json_response(links)

        else:
            self.send_error(404)

    def _json_response(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode())

    def _serve_dashboard(self):
        funnel_7d = get_funnel(hours=168)
        performance = get_content_performance(10)

        html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MediSlim · 转化漏斗看板</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,"PingFang SC",sans-serif;background:#f5f5f5;padding:20px}}
.header{{background:linear-gradient(135deg,#07C160,#059B48);color:#fff;padding:24px;border-radius:16px;margin-bottom:20px;text-align:center}}
.header h1{{font-size:24px}}
.funnel{{display:flex;gap:12px;margin-bottom:24px;overflow-x:auto;padding:10px 0}}
.funnel-step{{background:#fff;border-radius:12px;padding:16px;text-align:center;min-width:100px;box-shadow:0 2px 8px rgba(0,0,0,.04);flex-shrink:0}}
.funnel-step .num{{font-size:24px;font-weight:800;color:#07C160}}
.funnel-step .label{{font-size:12px;color:#666;margin-top:4px}}
.funnel-step .rate{{font-size:11px;color:#999;margin-top:2px}}
.arrow{{display:flex;align-items:center;color:#07C160;font-size:20px;flex-shrink:0}}
table{{width:100%;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.04);border-collapse:collapse}}
th{{background:#f8f8f8;padding:12px;text-align:left;font-size:13px;color:#666}}
td{{padding:10px 12px;font-size:13px;border-top:1px solid #f0f0f0}}
.badge{{display:inline-block;padding:2px 8px;border-radius:8px;font-size:11px;background:#E8F5E9;color:#2E7D32}}
h2{{font-size:18px;margin:20px 0 12px;color:#1a1a1a}}
</style></head><body>
<div class="header"><h1>📊 MediSlim 转化漏斗</h1><p>7天数据 · 实时更新</p></div>

<div class="funnel">
{"".join(f'''
  <div class="arrow">→</div>
  <div class="funnel-step">
    <div class="num">{funnel_7d["funnel"].get(et,0)}</div>
    <div class="label">{et}</div>
    <div class="rate">{funnel_7d["rates"].get(et,0)}%</div>
  </div>''' for et in EVENT_TYPES)}
</div>

<h2>🏆 Top 10 高转化内容</h2>
<table>
<tr><th>排名</th><th>追踪码</th><th>得分</th><th>曝光</th><th>点击</th><th>评估</th><th>下单</th></tr>
{"".join(f'''<tr>
  <td>#{i+1}</td>
  <td><span class="badge">{p["track_code"]}</span></td>
  <td><b>{p["score"]}</b></td>
  <td>{p.get("impression",0)}</td>
  <td>{p.get("click",0)}</td>
  <td>{p.get("assess_done",0)}</td>
  <td>{p.get("order_pay",0)}</td>
</tr>''' for i, p in enumerate(performance))}
</table>

<div style="margin-top:20px;text-align:center;color:#999;font-size:12px">
  总事件数: {funnel_7d["total_events"]} · 更新时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}
</div>
</body></html>"""

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())


PORT = 8097

def main():
    server = HTTPServer(("0.0.0.0", PORT), TrackingHandler)
    print(f"📊 转化追踪系统启动: http://0.0.0.0:{PORT}")
    print(f"  漏斗看板: http://localhost:{PORT}/api/dashboard")
    print(f"  漏斗数据: http://localhost:{PORT}/api/funnel")
    print(f"  内容排名: http://localhost:{PORT}/api/performance")
    server.serve_forever()


if __name__ == "__main__":
    main()
