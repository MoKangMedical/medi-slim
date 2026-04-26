"""MediSlim 消费医疗产品页 — 完整购物流程"""
from flask import Flask, render_template_string, jsonify, request
import json, os, time
from datetime import datetime

app = Flask(__name__)
DB_FILE = os.path.join(os.path.dirname(__file__), "orders.json")

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

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE) as f: return json.load(f)
    return {"orders": [], "assessments": [], "revenue": 0}
def save_db(db):
    with open(DB_FILE, "w") as f: json.dump(db, f, ensure_ascii=False, indent=2)

@app.before_request
def ensure_db():
    if not hasattr(app, '_db'): app._db = load_db()
def get_db(): return app._db
def commit(): save_db(app._db)

HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MediSlim — AI驱动消费医疗</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:-apple-system,sans-serif;background:#f5f7fa;color:#333;max-width:420px;margin:0 auto}
.hdr{background:linear-gradient(135deg,#43a047,#2e7d32);color:#fff;padding:24px 20px;text-align:center;border-radius:0 0 20px 20px}
.hdr h1{font-size:20px}.hdr p{font-size:13px;opacity:.8;margin-top:6px}
.nav{display:flex;gap:8px;justify-content:center;margin-top:8px}
.nav a{color:rgba(255,255,255,.85);text-decoration:none;font-size:11px;padding:3px 8px;border-radius:4px;background:rgba(255,255,255,.15)}
.wrap{padding:16px}
.card{background:#fff;border-radius:14px;padding:16px;margin-bottom:14px;box-shadow:0 2px 8px rgba(0,0,0,.05)}
.card h3{font-size:14px;color:#2e7d32;margin-bottom:10px}
.product .head{display:flex;align-items:center;gap:12px;margin-bottom:10px}
.product .icon{font-size:32px}.product .title{font-size:16px;font-weight:700}.product .subtitle{font-size:12px;color:#888}
.product .desc{font-size:13px;color:#555;line-height:1.6;margin-bottom:10px}
.product .features{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}
.product .feat{font-size:11px;padding:3px 8px;background:#f1f8e9;border-radius:8px;color:#2e7d32}
.product .price{display:flex;justify-content:space-between;align-items:center;padding-top:10px;border-top:1px solid #f0f0f0}
.product .price .first{font-size:22px;font-weight:800;color:#e65100}
.product .price .renew{font-size:12px;color:#888}
.product .price .market{font-size:11px;color:#43a047;background:#e8f5e9;padding:2px 8px;border-radius:8px}
.buy-btn{display:block;width:100%;padding:12px;background:#43a047;color:#fff;border:none;border-radius:10px;font-size:15px;font-weight:600;cursor:pointer;margin-top:10px}
.buy-btn:active{background:#2e7d32}
.btn{padding:10px 20px;border:none;border-radius:8px;cursor:pointer;font-size:13px}
.btn.green{background:#43a047;color:#fff}.btn.outline{background:#fff;color:#43a047;border:1px solid #43a047}
.tag{display:inline-block;padding:2px 8px;border-radius:8px;font-size:11px}
.tag.green{background:#e0f2f1;color:#00695c}.tag.orange{background:#fff3e0;color:#e65100}
.assess-q{margin:10px 0;padding:12px;background:#f5f5f5;border-radius:10px;font-size:13px}
.assess-q label{display:block;padding:8px;margin:4px 0;border:1px solid #ddd;border-radius:8px;cursor:pointer;font-size:13px}
.assess-q label.selected{border-color:#43a047;background:#e8f5e9}
.assess-q input[type=radio]{margin-right:6px}
.checkout{background:#fff;border-radius:14px;padding:16px}
.checkout .row{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #f0f0f0;font-size:13px}
.checkout .row.total{font-size:16px;font-weight:700;color:#e65100;border:none}
.progress-step{display:flex;gap:8px;margin:10px 0}
.progress-step .step{flex:1;text-align:center;font-size:11px;padding:8px;border-radius:8px}
.progress-step .step.done{background:#e0f2f1;color:#00695c}
.progress-step .step.active{background:#fff3e0;color:#e65100;font-weight:700}
.progress-step .step.pending{background:#f5f5f5;color:#888}
.order-item{display:flex;justify-content:space-between;align-items:center;padding:10px;border-bottom:1px solid #f0f0f0;font-size:13px}
.order-item .oid{font-weight:700;color:#43a047}.order-item .status{font-size:11px}
.tab-bar{display:flex;background:#fff;border-bottom:2px solid #e0e0e0;margin-bottom:12px}
.tab-bar button{flex:1;padding:12px;border:none;background:none;font-size:13px;font-weight:600;color:#888;cursor:pointer;border-bottom:3px solid transparent}
.tab-bar button.active{color:#43a047;border-bottom-color:#43a047}
.tab{display:none}.tab.active{display:block}
</style></head><body>
<div class="hdr">
  <h1>🌿 MediSlim</h1>
  <p>AI驱动的消费医疗平台 · 在线问诊+药品直达</p>
  <div class="nav">
    <a href="http://localhost:5002/admin">🏢 企业健康</a>
    <a href="/" onclick="showTab('products',this)">🛒 购买</a>
    <a href="#" onclick="showTab('assess',this)">🧬 体质测试</a>
    <a href="#" onclick="showTab('orders',this)">📦 我的订单</a>
  </div>
</div>

<div class="tab-bar">
  <button class="active" onclick="showTab('products',this)">🛒 产品</button>
  <button onclick="showTab('assess',this)">🧬 体质测试</button>
  <button onclick="showTab('orders',this)">📦 订单</button>
</div>

<div class="wrap">
  <!-- 产品列表 -->
  <div id="tab-products" class="tab active">
    <div class="card" style="text-align:center">
      <h3>📊 平台数据</h3>
      <div style="display:flex;justify-content:space-around">
        <div><div style="font-size:22px;font-weight:700;color:#43a047">10,000+</div><div style="font-size:11px;color:#888">服务用户</div></div>
        <div><div style="font-size:22px;font-weight:700;color:#43a047">98%</div><div style="font-size:11px;color:#888">满意度</div></div>
        <div><div style="font-size:22px;font-weight:700;color:#43a047">3天</div><div style="font-size:11px;color:#888">药品送达</div></div>
      </div>
    </div>
    {% for p in products %}
    <div class="card product">
      <div class="head"><div class="icon">{{ p.icon }}</div><div><div class="title">{{ p.name }}</div><div class="subtitle">{{ p.subtitle }}</div></div></div>
      <div class="desc">{{ p.desc }}</div>
      <div class="features">{% for f in p.features %}<span class="feat">✓ {{ f }}</span>{% endfor %}</div>
      <div class="price">
        <div><span class="first">¥{{ p.first_month }}</span><span class="renew">首月 · 续费¥{{ p.renewal }}/月</span></div>
        <span class="market">{{ p.market }}市场</span>
      </div>
      <button class="buy-btn" onclick="addToCart('{{ p.id }}')">🛒 立即购买 · ¥{{ p.first_month }}</button>
    </div>
    {% endfor %}
  </div>

  <!-- 体质测试 -->
  <div id="tab-assess" class="tab">
    <div class="card">
      <h3>🧬 AI体质评估</h3>
      <p style="font-size:12px;color:#888;margin-bottom:10px">回答5个问题，AI帮你找到最适合的健康方案</p>
      <div id="assessForm">
        <div class="assess-q" data-q="0">
          <strong>1. 你的主要健康诉求？</strong>
          <label onclick="selectOpt(this,0,0)"><input type="radio" name="q0"> 🏃 减重瘦身</label>
          <label onclick="selectOpt(this,0,1)"><input type="radio" name="q0"> 💇 防脱生发</label>
          <label onclick="selectOpt(this,0,2)"><input type="radio" name="q0"> 🧴 皮肤改善</label>
          <label onclick="selectOpt(this,0,3)"><input type="radio" name="q0"> 💪 精力提升</label>
          <label onclick="selectOpt(this,0,4)"><input type="radio" name="q0"> 😴 改善睡眠</label>
        </div>
        <div class="assess-q" data-q="1">
          <strong>2. 你尝试过什么方法？</strong>
          <label onclick="selectOpt(this,1,0)"><input type="radio" name="q1"> 节食/运动但效果不佳</label>
          <label onclick="selectOpt(this,1,1)"><input type="radio" name="q1"> 用过药物/保健品</label>
          <label onclick="selectOpt(this,1,2)"><input type="radio" name="q1"> 完全没有尝试过</label>
          <label onclick="selectOpt(this,1,3)"><input type="radio" name="q1"> 看过医生但没坚持</label>
        </div>
        <div class="assess-q" data-q="2">
          <strong>3. 你的预算范围？</strong>
          <label onclick="selectOpt(this,2,0)"><input type="radio" name="q2"> ¥200以内/月</label>
          <label onclick="selectOpt(this,2,1)"><input type="radio" name="q2"> ¥200-500/月</label>
          <label onclick="selectOpt(this,2,2)"><input type="radio" name="q2"> ¥500-1000/月</label>
          <label onclick="selectOpt(this,2,3)"><input type="radio" name="q2"> 不限预算</label>
        </div>
        <div class="assess-q" data-q="3">
          <strong>4. 你能坚持的时间？</strong>
          <label onclick="selectOpt(this,3,0)"><input type="radio" name="q3"> 1个月试试看</label>
          <label onclick="selectOpt(this,3,1)"><input type="radio" name="q3"> 3个月认真做</label>
          <label onclick="selectOpt(this,3,2)"><input type="radio" name="q3"> 6个月以上</label>
        </div>
        <div class="assess-q" data-q="4">
          <strong>5. 你期望的结果？</strong>
          <label onclick="selectOpt(this,4,0)"><input type="radio" name="q4"> 快速见效</label>
          <label onclick="selectOpt(this,4,1)"><input type="radio" name="q4"> 稳步改善</label>
          <label onclick="selectOpt(this,4,2)"><input type="radio" name="q4"> 彻底改变生活方式</label>
        </div>
        <button class="btn green" onclick="submitAssess()" style="width:100%;margin-top:10px">📊 获取AI推荐方案</button>
      </div>
      <div id="assessResult" style="display:none"></div>
    </div>
  </div>

  <!-- 我的订单 -->
  <div id="tab-orders" class="tab">
    <div class="card">
      <h3>📦 我的订单</h3>
      <div style="font-size:12px;color:#888;margin-bottom:10px">查看您的订单状态和配送进度</div>
      <div id="orderList">
        <div style="text-align:center;padding:20px;color:#888;font-size:13px">暂无订单，选择产品立即购买</div>
      </div>
    </div>
  </div>

  <!-- 结算弹窗 -->
  <div id="checkoutModal" style="display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.5);z-index:100;display:none;align-items:center;justify-content:center">
    <div class="checkout" style="width:90%;max-width:380px">
      <h3 style="color:#2e7d32;margin-bottom:12px">🛒 确认订单</h3>
      <div id="checkoutContent"></div>
      <div style="margin-top:8px">
        <label style="font-size:12px;color:#888">收货地址</label>
        <input id="address" placeholder="请输入详细地址" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:8px;margin:4px 0 8px">
        <label style="font-size:12px;color:#888">联系电话</label>
        <input id="phone" placeholder="请输入手机号" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:8px;margin:4px 0 8px">
      </div>
      <div class="row total"><span>应付金额</span><span id="totalAmount">¥0</span></div>
      <button class="btn green" onclick="confirmOrder()" style="width:100%;margin-top:10px;padding:14px;font-size:15px">💳 确认支付</button>
      <button class="btn outline" onclick="closeCheckout()" style="width:100%;margin-top:6px">取消</button>
    </div>
  </div>
</div>

<script>
let cart=null;
let assessAnswers=[null,null,null,null,null];
let orders=[];

const productMap={
  {% for p in products %}'{{ p.id }}':{name:'{{ p.name }}',icon:'{{ p.icon }}',price:{{ p.first_month }},renewal:{{ p.renewal }}},{% endfor %}
};

function showTab(id,el){
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.getElementById('tab-'+id).classList.add('active');
  document.querySelectorAll('.tab-bar button').forEach(b=>b.classList.remove('active'));
  if(el)el.classList.add('active');
}

function selectOpt(el,qi,oi){
  el.parentElement.querySelectorAll('label').forEach(l=>l.classList.remove('selected'));
  el.classList.add('selected');
  assessAnswers[qi]=oi;
}

function submitAssess(){
  const filled=assessAnswers.filter(a=>a!==null).length;
  if(filled<5){alert('请回答所有问题');return;}
  // 根据答案推荐产品
  const products=['glp1','hair','skin','male','sleep'];
  const recommended=products[assessAnswers[0]];
  const p=productMap[recommended];
  const reasons=['你的减重需求最适合GLP-1方案','你的脱发问题适合药物+AI追踪方案','你的皮肤问题适合定制护肤方案','你的精力问题适合营养+运动方案','你的睡眠问题适合行为干预方案'];
  document.getElementById('assessForm').style.display='none';
  document.getElementById('assessResult').style.display='block';
  document.getElementById('assessResult').innerHTML=`
    <div style="text-align:center;padding:10px;background:#e8f5e9;border-radius:10px;margin-bottom:10px">
      <div style="font-size:28px">${p.icon}</div>
      <div style="font-size:16px;font-weight:700;color:#2e7d32">${p.name}</div>
      <div style="font-size:12px;color:#888;margin:4px 0">AI推荐匹配度：92%</div>
    </div>
    <p style="font-size:13px;color:#555;line-height:1.8">${reasons[assessAnswers[0]]}</p>
    <p style="font-size:13px;color:#555;margin-top:8px">基于你的预算和时间偏好，首月仅需 <strong style="color:#e65100">¥${p.price}</strong>，续费¥${p.renewal}/月</p>
    <button class="btn green" onclick="addToCart('${recommended}')" style="width:100%;margin-top:10px;padding:14px">🛒 立即购买推荐方案 · ¥${p.price}</button>
  `;
  // 保存评估
  fetch('/api/assess',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({answers:assessAnswers,recommended})});
}

function addToCart(id){
  const p=productMap[id];
  cart={...p,id};
  showCheckout();
}

function showCheckout(){
  const m=document.getElementById('checkoutModal');
  m.style.display='flex';
  document.getElementById('checkoutContent').innerHTML=`
    <div class="row"><span>${cart.icon} ${cart.name}</span><span>¥${cart.price}</span></div>
    <div class="row"><span>首月优惠</span><span style="color:#e65100">已包含</span></div>
    <div class="row"><span>配送费</span><span style="color:#43a047">包邮</span></div>
  `;
  document.getElementById('totalAmount').textContent='¥'+cart.price;
}

function closeCheckout(){
  document.getElementById('checkoutModal').style.display='none';
}

function confirmOrder(){
  const addr=document.getElementById('address').value;
  const phone=document.getElementById('phone').value;
  if(!addr||!phone){alert('请填写完整信息');return;}
  fetch('/api/order',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({product_id:cart.id,address:addr,phone:phone})})
    .then(r=>r.json()).then(data=>{
      closeCheckout();
      orders.unshift({id:data.order_id,product:cart.name,icon:cart.icon,price:cart.price,status:'问诊中',time:new Date().toLocaleString('zh-CN')});
      renderOrders();
      alert('✅ 订单提交成功！\\n\\n订单号：'+data.order_id+'\\n我们将在24小时内安排医师在线问诊。');
      showTab('orders',document.querySelectorAll('.tab-bar button')[2]);
    });
}

function renderOrders(){
  const el=document.getElementById('orderList');
  if(orders.length===0){el.innerHTML='<div style="text-align:center;padding:20px;color:#888">暂无订单</div>';return;}
  el.innerHTML=orders.map(o=>`
    <div class="order-item">
      <div><div class="oid">${o.id}</div><div style="font-size:12px;color:#888">${o.icon} ${o.product} · ${o.time}</div></div>
      <div style="text-align:right"><div style="font-weight:700;color:#e65100">¥${o.price}</div><div class="status tag orange">${o.status}</div></div>
    </div>
  `).join('');
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
    db = get_db()
    oid = f"MS{int(time.time())}"
    product = next((p for p in PRODUCTS if p["id"] == data.get("product_id")), PRODUCTS[0])
    db["orders"].append({"id": oid, "product_id": data.get("product_id"), "address": data.get("address"), "phone": data.get("phone"), "price": product["first_month"], "created": datetime.now().isoformat()})
    db["revenue"] = db.get("revenue", 0) + product["first_month"]
    commit()
    return jsonify({"order_id": oid, "product": product["name"], "price": product["first_month"]})

@app.route("/api/assess", methods=["POST"])
def api_assess():
    data = request.json
    db = get_db()
    db["assessments"].append({"answers": data.get("answers"), "recommended": data.get("recommended"), "created": datetime.now().isoformat()})
    commit()
    return jsonify({"status": "ok"})

@app.route("/api/stats")
def api_stats():
    db = get_db()
    return jsonify({"orders": len(db["orders"]), "assessments": len(db["assessments"]), "revenue": db.get("revenue", 0)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=True)
