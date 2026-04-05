"""
MediSlim 智能落地页 — 基于来源个性化
读取UTM参数 → 匹配内容 → 展示对应首屏 → 全程埋点
端口：8098
零依赖
"""
import os
import json
import uuid
import time
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

PORT = 8098
CATALOG_PATH = Path(__file__).parent / "content_engine" / "output" / "catalog.json"
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# ========== 产品配置 ==========
PRODUCTS = {
    "glp1": {
        "name": "GLP-1科学减重",
        "emoji": "🔥",
        "hero_gradient": "linear-gradient(135deg, #FF6B6B 0%, #FF8E53 100%)",
        "hero_badge": "🔥 爆款 · 首月仅¥399",
        "hero_slogan": "不挨饿不运动，科学减重",
        "pains": ["节食反弹越减越肥", "太忙没时间运动", "试了各种方法都没用"],
        "benefits": ["医生个性化方案", "药品直接寄到家", "7天不满意可退"],
        "price": 399,
        "price_unit": "首月",
        "assess_title": "免费减重评估",
        "assess_desc": "30秒填写，获取专属减重方案",
    },
    "hair": {
        "name": "防脱生发",
        "emoji": "💇",
        "hero_gradient": "linear-gradient(135deg, #A18CD1 0%, #FBC2EB 100%)",
        "hero_badge": "💇 热门 · 首月仅¥199",
        "hero_slogan": "28天见证发量回归",
        "pains": ["发际线越来越后移", "洗头掉一大把", "头顶越来越稀疏"],
        "benefits": ["皮肤科医生处方", "FDA认证药物", "毛囊精准检测"],
        "price": 199,
        "price_unit": "首月",
        "assess_title": "免费脱发评估",
        "assess_desc": "了解脱发原因，获取生发方案",
    },
    "skin": {
        "name": "皮肤管理",
        "emoji": "🧴",
        "hero_gradient": "linear-gradient(135deg, #FFD89B 0%, #19547B 100%)",
        "hero_badge": "🧴 爆款 · 首月仅¥299",
        "hero_slogan": "14天肉眼可见的改变",
        "pains": ["痘痘反复不见好", "毛孔粗大暗沉", "色斑越来越深"],
        "benefits": ["皮肤科在线诊断", "个性化护肤方案", "药品/护肤品配送"],
        "price": 299,
        "price_unit": "首月",
        "assess_title": "免费皮肤评估",
        "assess_desc": "上传照片，医生在线诊断",
    },
    "mens": {
        "name": "男性健康",
        "emoji": "💪",
        "hero_gradient": "linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%)",
        "hero_badge": "💪 专属 · 首月仅¥399",
        "hero_slogan": "重回巅峰状态",
        "pains": ["精力大不如前", "工作到下午就萎", "体检指标飘红"],
        "benefits": ["泌尿/内分泌医生", "隐私保护配送", "检验+用药指导"],
        "price": 399,
        "price_unit": "首月",
        "assess_title": "免费男性健康评估",
        "assess_desc": "隐私保护，专业评估",
    },
    "sleep": {
        "name": "助眠调理",
        "emoji": "😴",
        "hero_gradient": "linear-gradient(135deg, #14B8A6 0%, #0F766E 100%)",
        "hero_badge": "😴 热门 · 首月仅¥199",
        "hero_slogan": "告别失眠，一觉到天亮",
        "pains": ["翻来覆去睡不着", "凌晨醒了就难入睡", "白天困晚上精神"],
        "benefits": ["睡眠专科医生", "行为+药物联合", "睡眠日记追踪"],
        "price": 199,
        "price_unit": "首月",
        "assess_title": "免费睡眠评估",
        "assess_desc": "了解失眠原因，获取改善方案",
    },
}

# 不同风格的首屏文案变体
STYLE_VARIANTS = {
    "闺蜜体": {
        "cta": "姐妹们冲！先做评估不花钱～",
        "tone_color": "#FF6B8A",
    },
    "专业体": {
        "cta": "专业评估 · 科学方案 · 立即开始",
        "tone_color": "#3B82F6",
    },
    "种草体": {
        "cta": "闭眼入！评估免费不满意随时退～",
        "tone_color": "#14B8A6",
    },
    "焦虑体": {
        "cta": "别再拖了！免费评估立即行动⚡",
        "tone_color": "#F59E0B",
    },
    "励志体": {
        "cta": "遇见更好的自己，从这一步开始💪",
        "tone_color": "#07C160",
    },
    "故事体": {
        "cta": "看看适合你的方案，免费评估～",
        "tone_color": "#8B5CF6",
    },
}


def load_catalog():
    if CATALOG_PATH.exists():
        return json.loads(CATALOG_PATH.read_text())
    return []


def find_content(ref=None, utm_campaign=None, utm_content=None):
    """根据追踪码或UTM参数匹配内容"""
    catalog = load_catalog()

    # 优先匹配追踪码
    if ref:
        for entry in catalog:
            tc = entry.get("tracking", {}).get("track_code", "")
            if ref in tc or ref == entry.get("id", ""):
                return entry

    # 匹配utm_campaign中的品类
    if utm_campaign:
        pid = utm_campaign.replace("medislim_", "")
        if pid in PRODUCTS:
            # 返回该品类的任意一条内容
            for entry in catalog:
                if entry.get("product_id") == pid:
                    return entry

    return None


def track_event(track_code, event_type, extra=None):
    """调用追踪系统的事件接口"""
    import urllib.request
    try:
        data = json.dumps({
            "track_code": track_code,
            "event_type": event_type,
            "extra": extra or {},
        }).encode()
        req = urllib.request.Request(
            "http://localhost:8097/api/track",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=3)
    except Exception:
        pass  # 静默失败


def render_landing(product_id="glp1", content=None, style=None, ref=None):
    """渲染个性化落地页"""
    p = PRODUCTS.get(product_id, PRODUCTS["glp1"])
    sv = STYLE_VARIANTS.get(style, STYLE_VARIANTS["励志体"])

    # 如果有具体内容，用它的钩子作为标题
    hook = ""
    body_preview = ""
    if content:
        hook = content.get("hook", "")
        body_preview = content.get("body", "")[:200]

    hero_title = hook if hook else f"{p['emoji']} {p['assess_title']}"
    hero_sub = body_preview if body_preview else p["assess_desc"]
    track_code = ref or ""

    # 痛点卡片
    pain_cards = "".join(
        f'<div class="pain-card"><div class="pain-icon">😣</div><div class="pain-text">{pain}</div></div>'
        for pain in p["pains"]
    )

    # 好处卡片
    benefit_items = "".join(
        f'<div class="benefit-item">✓ {b}</div>'
        for b in p["benefits"]
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>MediSlim · {p['name']}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,"PingFang SC",sans-serif;background:#f8f8f8;color:#1a1a1a;max-width:500px;margin:0 auto}}

/* Hero */
.hero{{background:{p['hero_gradient']};padding:50px 24px 60px;color:#fff;text-align:center;position:relative}}
.hero::after{{content:'';position:absolute;bottom:-24px;left:0;right:0;height:48px;background:#f8f8f8;border-radius:50% 50% 0 0}}
.hero-badge{{display:inline-block;background:rgba(255,255,255,.25);border-radius:20px;padding:6px 16px;font-size:13px;margin-bottom:20px;font-weight:500}}
.hero-title{{font-size:26px;font-weight:800;line-height:1.4;margin-bottom:12px;text-shadow:0 2px 8px rgba(0,0,0,.1)}}
.hero-sub{{font-size:15px;opacity:.9;line-height:1.6}}

/* Pain */
.section{{padding:24px 20px}}
.section-title{{font-size:18px;font-weight:700;margin-bottom:16px;text-align:center}}
.pain-grid{{display:flex;flex-direction:column;gap:10px}}
.pain-card{{background:#fff;border-radius:14px;padding:16px;display:flex;align-items:center;gap:12px;box-shadow:0 2px 8px rgba(0,0,0,.04)}}
.pain-icon{{font-size:24px}}
.pain-text{{font-size:14px;color:#666}}

/* Solution */
.solution{{background:#fff;margin:16px;border-radius:16px;padding:24px;box-shadow:0 2px 12px rgba(0,0,0,.05)}}
.solution-title{{font-size:18px;font-weight:700;text-align:center;margin-bottom:16px}}
.benefit-item{{font-size:15px;padding:10px 0;border-bottom:1px solid #f5f5f5;color:#333}}
.benefit-item:last-child{{border:none}}

/* Price */
.price-box{{background:#fff;margin:16px;border-radius:16px;padding:24px;text-align:center;box-shadow:0 2px 12px rgba(0,0,0,.05)}}
.price-label{{font-size:14px;color:#999}}
.price{{font-size:48px;font-weight:800;color:#FF3B30;margin:8px 0}}
.price span{{font-size:18px;font-weight:400;color:#999}}
.price-note{{font-size:12px;color:#999}}

/* CTA */
.cta-section{{padding:16px}}
.cta-btn{{display:block;width:100%;background:{p['hero_gradient']};color:#fff;font-size:18px;font-weight:700;padding:18px;border-radius:50px;border:none;cursor:pointer;text-align:center;text-decoration:none;box-shadow:0 4px 16px rgba(0,0,0,.15)}}
.cta-btn:active{{opacity:.9}}
.cta-sub{{text-align:center;font-size:12px;color:#999;margin-top:12px}}

/* Trust */
.trust-bar{{display:flex;justify-content:center;gap:24px;padding:20px;font-size:12px;color:#999}}
.trust-bar span{{display:flex;align-items:center;gap:4px}}

/* Form */
.form-section{{background:#fff;margin:16px;border-radius:16px;padding:24px;box-shadow:0 2px 12px rgba(0,0,0,.05)}}
.form-section input{{width:100%;padding:14px 18px;border:2px solid #eee;border-radius:12px;font-size:16px;margin-bottom:12px;outline:none;transition:border .2s}}
.form-section input:focus{{border-color:{sv['tone_color']}}}
</style>
</head>
<body>

<!-- Hero -->
<div class="hero">
  <div class="hero-badge">{p['hero_badge']}</div>
  <div class="hero-title">{hero_title}</div>
  <div class="hero-sub">{hero_sub}</div>
</div>

<!-- 痛点 -->
<div class="section">
  <div class="section-title">你是不是也遇到了这些问题？</div>
  <div class="pain-grid">{pain_cards}</div>
</div>

<!-- 解决方案 -->
<div class="solution">
  <div class="section-title">MediSlim {p['name']}方案</div>
  {benefit_items}
</div>

<!-- 价格 -->
<div class="price-box">
  <div class="price-label">{p['price_unit']}体验价</div>
  <div class="price">¥{p['price']}<span>/{p['price_unit']}</span></div>
  <div class="price-note">✅ 免费评估 · 不满意随时退 · 隐私保护</div>
</div>

<!-- 表单 -->
<div class="form-section" id="lead-form">
  <div class="section-title">{p['assess_title']}</div>
  <input type="text" placeholder="您的姓名（可选）" id="name">
  <input type="tel" placeholder="手机号码" id="phone">
  <button class="cta-btn" onclick="submitLead()">{sv['cta']}</button>
  <div class="cta-sub">提交后医生将在24小时内联系您</div>
</div>

<!-- 信任 -->
<div class="trust-bar">
  <span>🔒 隐私保护</span>
  <span>👨‍⚕️ 专业医生</span>
  <span>💊 正品药品</span>
  <span>↩️ 不满意退</span>
</div>

<script>
const ref='{track_code}';
const product='{product_id}';

// 页面浏览埋点
fetch('http://localhost:8097/api/track',{{
  method:'POST',
  headers:{{'Content-Type':'application/json'}},
  body:JSON.stringify({{track_code:ref,event_type:'landing',extra:{{product:product,source:document.referrer}}}})
}}).catch(()=>{{}});

function submitLead(){{
  const phone=document.getElementById('phone').value;
  const name=document.getElementById('name').value||'';
  if(!phone||phone.length<11){{alert('请输入正确的手机号码');return;}}

  fetch('http://localhost:8097/api/track',{{
    method:'POST',
    headers:{{'Content-Type':'application/json'}},
    body:JSON.stringify({{
      track_code:ref,
      event_type:'assess_start',
      extra:{{phone:phone.slice(0,3)+'****'+phone.slice(-4),name:name}}
    }})
  }}).catch(()=>{{}});

  // 跳转评估页
  const params=new URLSearchParams({{ref:ref,phone:phone,name:name,product:product}});
  window.location.href='/assess?'+params.toString();
}}
</script>
</body></html>"""


class SmartLandingHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            # 读取追踪参数
            ref = params.get("ref", [None])[0]
            utm_campaign = params.get("utm_campaign", [None])[0]
            utm_content = params.get("utm_content", [None])[0]
            style = params.get("style", [None])[0]

            # 匹配内容
            content = find_content(ref, utm_campaign, utm_content)
            product_id = "glp1"
            if content:
                product_id = content.get("product_id", "glp1")
                style = style or content.get("style")
            elif utm_campaign:
                product_id = utm_campaign.replace("medislim_", "")

            # 渲染个性化页面
            html = render_landing(product_id, content, style, ref)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode())

        elif path == "/assess":
            # 评估页（简化版）
            html = self._render_assess(params)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode())

        elif path.startswith("/r/"):
            # 短链接 → 追踪点击 → 重定向到落地页
            code = path.split("/r/")[1]
            track_event(code, "click")
            # 重定向到首页带ref参数
            self.send_response(302)
            self.send_header("Location", f"/?ref={code}")
            self.end_headers()

        elif path == "/api/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')

        else:
            self.send_error(404)

    def _render_assess(self, params):
        ref = params.get("ref", [""])[0]
        phone = params.get("phone", [""])[0]
        name = params.get("name", [""])[0]
        product = params.get("product", ["glp1"])[0]
        p = PRODUCTS.get(product, PRODUCTS["glp1"])

        track_event(ref, "assess_start", {"phone": phone[:3] + "****" if phone else ""})

        return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{p['assess_title']}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,"PingFang SC",sans-serif;background:#f8f8f8;max-width:500px;margin:0 auto;padding:20px}}
.card{{background:#fff;border-radius:16px;padding:24px;margin-bottom:16px;box-shadow:0 2px 8px rgba(0,0,0,.04)}}
.card h3{{font-size:18px;font-weight:700;margin-bottom:16px}}
.q{{margin-bottom:16px}}
.q label{{font-size:14px;font-weight:600;display:block;margin-bottom:8px}}
.q input,.q select{{width:100%;padding:12px;border:2px solid #eee;border-radius:10px;font-size:15px;outline:none}}
.q input:focus,.q select:focus{{border-color:#07C160}}
.btn{{display:block;width:100%;background:linear-gradient(135deg,#07C160,#059B48);color:#fff;font-size:17px;font-weight:700;padding:16px;border-radius:50px;border:none;cursor:pointer;text-align:center;margin-top:20px}}
.progress{{height:4px;background:#eee;border-radius:2px;margin-bottom:20px}}
.progress-bar{{height:100%;background:#07C160;border-radius:2px;transition:width .3s}}
</style></head><body>
<div class="progress"><div class="progress-bar" style="width:33%"></div></div>
<div class="card">
  <h3>{p['emoji']} {p['assess_title']}</h3>
  <div class="q"><label>您的年龄？</label><input type="number" placeholder="请输入" id="age"></div>
  <div class="q"><label>您的性别？</label><select id="gender"><option value="">请选择</option><option>男</option><option>女</option></select></div>
  <div class="q"><label>主要困扰是什么？</label><input type="text" placeholder="简要描述" id="concern"></div>
  <button class="btn" onclick="submit()">下一步 →</button>
</div>
<script>
const ref='{ref}';const product='{product}';
function submit(){{window.location.href='/assess?step=2&ref='+ref+'&product='+product;}}
</script></body></html>"""


def main():
    server = HTTPServer(("0.0.0.0", PORT), SmartLandingHandler)
    print(f"🌐 智能落地页启动: http://0.0.0.0:{PORT}")
    print(f"  短链接: http://localhost:{PORT}/r/{{track_code}}")
    print(f"  评估页: http://localhost:{PORT}/assess")
    server.serve_forever()


if __name__ == "__main__":
    main()
