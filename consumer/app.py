"""MediSlim 消费医疗产品页 — 直接产生现金流"""
from flask import Flask, render_template_string, jsonify, request

app = Flask(__name__)

PRODUCTS = [
    {"id": "glp1", "name": "GLP-1减重方案", "icon": "🔥", "subtitle": "司美格鲁肽/替尔泊肽",
     "first_month": 399, "renewal": 599, "market": "500亿+",
     "desc": "通过GLP-1受体激动剂实现科学减重，平均减重15-20%。包含：在线问诊+处方+药品配送+AI随访",
     "features": ["在线医师问诊", "个性化处方", "药品冷链配送", "AI体重管理", "月度复查提醒"]},
    {"id": "hair", "name": "防脱生发方案", "icon": "💇", "subtitle": "米诺地尔+非那雄胺",
     "first_month": 199, "renewal": 299, "market": "200亿+",
     "desc": "FDA认证的防脱方案，3个月见效。包含：头皮检测+用药指导+效果追踪",
     "features": ["AI头皮分析", "处方开具", "药品配送", "效果追踪", "生发打卡"]},
    {"id": "skin", "name": "皮肤管理方案", "icon": "🧴", "subtitle": "祛痘/美白/抗衰",
     "first_month": 299, "renewal": 399, "market": "300亿+",
     "desc": "根据肤质定制护肤方案。包含：AI肤质检测+产品推荐+使用指导",
     "features": ["AI肤质检测", "个性化方案", "产品配送", "效果记录", "护肤顾问"]},
    {"id": "male", "name": "男性健康方案", "icon": "💪", "subtitle": "精力/睾酮管理",
     "first_month": 399, "renewal": 599, "market": "150亿+",
     "desc": "男性精力管理方案。包含：健康评估+营养补充+运动指导",
     "features": ["健康评估", "营养方案", "运动指导", "精力追踪", "医师咨询"]},
    {"id": "sleep", "name": "助眠调理方案", "icon": "😴", "subtitle": "失眠/褪黑素",
     "first_month": 199, "renewal": 299, "market": "100亿+",
     "desc": "科学助眠方案。包含：睡眠评估+行为干预+必要时用药",
     "features": ["睡眠评估", "行为干预", "产品推荐", "睡眠打卡", "AI助眠"]},
]

HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MediSlim — AI驱动消费医疗</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:-apple-system,sans-serif;background:#f5f7fa;color:#333;max-width:420px;margin:0 auto}
.hdr{background:linear-gradient(135deg,#43a047,#2e7d32);color:#fff;padding:24px 20px;text-align:center;border-radius:0 0 20px 20px}
.hdr h1{font-size:20px}.hdr p{font-size:13px;opacity:.8;margin-top:6px}
.wrap{padding:16px}
.product{background:#fff;border-radius:14px;padding:16px;margin-bottom:14px;box-shadow:0 2px 8px rgba(0,0,0,.05)}
.product .head{display:flex;align-items:center;gap:12px;margin-bottom:10px}
.product .icon{font-size:32px}
.product .title{font-size:16px;font-weight:700}
.product .subtitle{font-size:12px;color:#888}
.product .desc{font-size:13px;color:#555;line-height:1.6;margin-bottom:10px}
.product .features{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}
.product .feat{font-size:11px;padding:3px 8px;background:#f1f8e9;border-radius:8px;color:#2e7d32}
.product .price{display:flex;justify-content:space-between;align-items:center;padding-top:10px;border-top:1px solid #f0f0f0}
.product .price .first{font-size:22px;font-weight:800;color:#e65100}
.product .price .renew{font-size:12px;color:#888}
.product .price .market{font-size:11px;color:#43a047;background:#e8f5e9;padding:2px 8px;border-radius:8px}
.buy-btn{display:block;width:100%;padding:12px;background:#43a047;color:#fff;border:none;border-radius:10px;font-size:15px;font-weight:600;cursor:pointer;margin-top:10px}
.buy-btn:active{background:#2e7d32}
.trust{background:#fff;border-radius:14px;padding:16px;margin-bottom:14px;text-align:center}
.trust h3{font-size:14px;margin-bottom:10px}
.trust .stats{display:flex;justify-content:space-around}
.trust .stat{text-align:center}.trust .stat .num{font-size:22px;font-weight:700;color:#43a047}.trust .stat .label{font-size:11px;color:#888}
.b2b{background:linear-gradient(135deg,#e3f2fd,#bbdefb);border-radius:14px;padding:16px;text-align:center}
.b2b h3{font-size:14px;color:#1565c0;margin-bottom:6px}.b2b p{font-size:12px;color:#555}
.b2b-btn{display:inline-block;padding:10px 20px;background:#1565c0;color:#fff;border-radius:10px;font-size:13px;text-decoration:none;margin-top:8px}
</style></head><body>
<div class="hdr">
  <h1>🌿 MediSlim</h1>
  <p>AI驱动的消费医疗平台 · 在线问诊+药品直达</p>
</div>
<div class="wrap">
  <div class="trust">
    <h3>📊 平台数据</h3>
    <div class="stats">
      <div class="stat"><div class="num">10,000+</div><div class="label">服务用户</div></div>
      <div class="stat"><div class="num">98%</div><div class="label">满意度</div></div>
      <div class="stat"><div class="num">3天</div><div class="label">药品送达</div></div>
    </div>
  </div>

  {% for p in products %}
  <div class="product">
    <div class="head">
      <div class="icon">{{ p.icon }}</div>
      <div><div class="title">{{ p.name }}</div><div class="subtitle">{{ p.subtitle }}</div></div>
    </div>
    <div class="desc">{{ p.desc }}</div>
    <div class="features">
      {% for f in p.features %}<span class="feat">✓ {{ f }}</span>{% endfor %}
    </div>
    <div class="price">
      <div><span class="first">¥{{ p.first_month }}</span><span class="renew">首月价 · 续费¥{{ p.renewal }}/月</span></div>
      <span class="market">{{ p.market }}市场</span>
    </div>
    <button class="buy-btn" onclick="order('{{ p.id }}')">立即购买 · ¥{{ p.first_month }}</button>
  </div>
  {% endfor %}

  <div class="b2b">
    <h3>🏢 企业健康管理</h3>
    <p>为企业员工提供健康管理服务<br>HR付费 · 员工免费 · ROI 8.2x</p>
    <a class="b2b-btn" href="/admin">了解企业方案 →</a>
  </div>
</div>

<script>
function order(id){
  alert('✅ 订单已提交！\\n\\n我们将在24小时内安排医师在线问诊，确认处方后3天内药品送达。\\n\\n产品ID: '+id);
}
</script>
</body></html>"""

@app.route("/")
def index():
    return render_template_string(HTML, products=PRODUCTS)

@app.route("/api/products")
def api_products():
    return jsonify(PRODUCTS)

@app.route("/api/order", methods=["POST"])
def api_order():
    data = request.json
    return jsonify({"status": "ok", "order_id": f"MS{data.get('product_id','').upper()}20260426001", "message": "订单已提交，24h内安排问诊"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=True)
