"""
MediSlim 商业落地页 — 微信生态获客系统
专为社交媒体流量（微信/小红书/抖音）设计
零依赖Python HTTP服务
"""
import os
import json
import uuid
import hashlib
import time
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

DATA_DIR = Path("./data")
DATA_DIR.mkdir(exist_ok=True)

def load_db(name):
    f = DATA_DIR / f"{name}.json"
    return json.loads(f.read_text()) if f.exists() else {}

def save_db(name, data):
    (DATA_DIR / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))

# ========== 落地页内容 ==========
LANDING_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>MediSlim · AI健康管家</title>
<meta name="description" content="AI驱动的消费医疗平台，GLP-1科学减重、防脱生发、皮肤管理，足不出户享受专业医疗">
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--g:#07C160;--gd:#06AD56;--r:16px;--bg:#FAFAFA}
body{font-family:-apple-system,"PingFang SC","Helvetica Neue",sans-serif;background:var(--bg);color:#1a1a1a;-webkit-font-smoothing:antialiased;max-width:500px;margin:0 auto;overflow-x:hidden}
.hero{background:linear-gradient(135deg,#07C160 0%,#06AD56 40%,#059B48 100%);padding:60px 20px 40px;color:#fff;text-align:center;position:relative;overflow:hidden}
.hero::after{content:'';position:absolute;bottom:-30px;left:0;right:0;height:60px;background:var(--bg);border-radius:50% 50% 0 0}
.hero h1{font-size:32px;font-weight:800;letter-spacing:2px;text-shadow:0 2px 8px rgba(0,0,0,.15)}
.hero .slogan{font-size:16px;opacity:.95;margin-top:12px;font-weight:500}
.hero .badge{display:inline-block;background:rgba(255,255,255,.2);border-radius:20px;padding:6px 16px;font-size:13px;margin-top:16px}

/* 痛点 */
.pain-section{padding:30px 20px 20px}
.pain-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:16px}
.pain-card{background:#fff;border-radius:var(--r);padding:16px;box-shadow:0 2px 8px rgba(0,0,0,.04)}
.pain-card .icon{font-size:28px;margin-bottom:8px}
.pain-card h4{font-size:14px;font-weight:600;margin-bottom:4px}
.pain-card p{font-size:12px;color:#999;line-height:1.5}

/* 解决方案 */
.solution-section{background:#fff;padding:30px 20px;margin:16px 0}
.solution-title{text-align:center;font-size:20px;font-weight:700;margin-bottom:8px}
.solution-sub{text-align:center;font-size:13px;color:#999;margin-bottom:24px}
.flow{display:flex;align-items:center;justify-content:center;flex-wrap:wrap;gap:8px;margin:20px 0}
.flow-step{background:#F0FFF4;border:2px solid #D1FAE5;border-radius:12px;padding:12px 16px;text-align:center;min-width:70px}
.flow-step .num{font-size:12px;color:var(--g);font-weight:700}
.flow-step .text{font-size:13px;margin-top:4px;font-weight:500}
.flow-arrow{color:var(--g);font-size:20px;font-weight:700}

/* 产品卡 */
.products-section{padding:20px}
.product-card{background:#fff;border-radius:var(--r);padding:20px;margin-bottom:16px;box-shadow:0 2px 8px rgba(0,0,0,.04);position:relative;overflow:hidden}
.product-card.hot::before{content:'🔥爆品';position:absolute;top:0;right:0;background:#FF3B30;color:#fff;font-size:11px;padding:4px 12px;border-radius:0 0 0 12px;font-weight:600}
.product-header{display:flex;align-items:center;gap:16px;margin-bottom:12px}
.product-emoji{width:48px;height:48px;border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:24px}
.pe-glp{background:linear-gradient(135deg,#FF6B6B,#FF8E53)}
.pe-hair{background:linear-gradient(135deg,#A18CD1,#FBC2EB)}
.pe-skin{background:linear-gradient(135deg,#FFD89B,#19547B)}
.product-info h3{font-size:16px;font-weight:600}
.product-info p{font-size:13px;color:#999}
.product-price-row{display:flex;justify-content:space-between;align-items:center;margin-top:12px;padding-top:12px;border-top:1px solid #F5F5F5}
.product-price .first{font-size:22px;font-weight:800;color:#FF3B30}
.product-price .first span{font-size:14px;font-weight:400}
.product-price .renew{font-size:12px;color:#999;margin-top:2px}
.btn-order{background:var(--g);color:#fff;border:none;border-radius:12px;padding:10px 20px;font-size:14px;font-weight:600;cursor:pointer}
.btn-order:hover{background:var(--gd)}

/* 信任 */
.trust-section{background:#fff;padding:30px 20px;margin:16px 0}
.trust-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-top:20px}
.trust-item{text-align:center}
.trust-item .icon{font-size:32px;margin-bottom:8px}
.trust-item h4{font-size:13px;font-weight:600}
.trust-item p{font-size:11px;color:#999;margin-top:4px}

/* 案例 */
.cases-section{padding:20px}
.case-card{background:#fff;border-radius:var(--r);padding:20px;margin-bottom:12px;box-shadow:0 2px 8px rgba(0,0,0,.04)}
.case-header{display:flex;align-items:center;gap:12px;margin-bottom:12px}
.case-avatar{width:40px;height:40px;border-radius:50%;background:linear-gradient(135deg,#667eea,#764ba2);display:flex;align-items:center;justify-content:center;color:#fff;font-size:18px;font-weight:700}
.case-name{font-size:14px;font-weight:600}
.case-time{font-size:12px;color:#999}
.case-result{background:#F0FFF4;border-radius:10px;padding:12px;margin-top:8px}
.case-result .label{font-size:12px;color:var(--g);font-weight:600}
.case-result .value{font-size:20px;font-weight:800;color:var(--g);margin-top:4px}

/* CTA */
.cta-section{background:linear-gradient(135deg,#07C160,#059B48);padding:40px 20px;text-align:center;color:#fff;margin:16px 0}
.cta-section h2{font-size:22px;font-weight:700;margin-bottom:8px}
.cta-section p{font-size:14px;opacity:.9;margin-bottom:20px}
.btn-cta{background:#fff;color:var(--g);border:none;border-radius:14px;padding:16px 40px;font-size:17px;font-weight:700;cursor:pointer;display:inline-block;text-decoration:none}
.btn-cta:hover{background:#F0FFF4}

/* 微信引导 */
.wechat-section{background:#fff;padding:30px 20px;text-align:center}
.wechat-icon{width:80px;height:80px;border-radius:20px;margin:0 auto 16px;background:linear-gradient(135deg,#07C160,#06AD56);display:flex;align-items:center;justify-content:center;font-size:40px}
.wechat-qr{font-size:14px;color:#999;margin-top:12px;line-height:1.8}
.wechat-id{font-size:18px;font-weight:700;color:var(--g);margin:12px 0}
.copy-btn{background:var(--g);color:#fff;border:none;border-radius:10px;padding:10px 24px;font-size:14px;font-weight:600;cursor:pointer;margin-top:8px}

/* 底部 */
.footer{padding:20px;text-align:center;font-size:11px;color:#ccc;line-height:2}
.footer a{color:#999;text-decoration:none}

/* 表单弹窗 */
.modal{display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.6);z-index:100;align-items:center;justify-content:center}
.modal.show{display:flex}
.modal-box{background:#fff;border-radius:20px;padding:24px;width:90%;max-width:400px}
.modal-close{float:right;font-size:24px;cursor:pointer;color:#999}
.form-group{margin-bottom:16px}
.form-group label{font-size:14px;font-weight:600;display:block;margin-bottom:8px}
.form-group input{width:100%;padding:12px;border:2px solid #E5E5EA;border-radius:12px;font-size:16px;outline:none}
.form-group input:focus{border-color:var(--g)}
.form-group select{width:100%;padding:12px;border:2px solid #E5E5EA;border-radius:12px;font-size:16px;outline:none;background:#fff}
.btn-submit{width:100%;padding:16px;background:var(--g);color:#fff;border:none;border-radius:14px;font-size:17px;font-weight:600;cursor:pointer}
.success-msg{text-align:center;padding:30px 0}
.success-msg .icon{font-size:56px}
.success-msg h3{font-size:20px;margin:16px 0}
</style>
</head>
<body>

<!-- Hero -->
<div class="hero">
  <h1>💊 MediSlim</h1>
  <div class="slogan">你的AI健康管家 · 足不出户享受专业医疗</div>
  <div class="badge">✅ 已服务 10,000+ 用户</div>
</div>

<!-- 痛点 -->
<div class="pain-section">
  <h3 style="font-size:18px;font-weight:700;text-align:center">你是不是也有这些困扰？</h3>
  <div class="pain-grid">
    <div class="pain-card">
      <div class="icon">😓</div>
      <h4>减重反复失败</h4>
      <p>节食运动都不管用，越减越胖</p>
    </div>
    <div class="pain-card">
      <div class="icon">😭</div>
      <h4>脱发越来越严重</h4>
      <p>发际线后移，头顶见光</p>
    </div>
    <div class="pain-card">
      <div class="icon">😩</div>
      <h4>皮肤问题反复</h4>
      <p>痘痘、暗沉、斑点去不掉</p>
    </div>
    <div class="pain-card">
      <div class="icon">😴</div>
      <h4>睡眠质量差</h4>
      <p>入睡难、易醒、白天犯困</p>
    </div>
  </div>
</div>

<!-- 解决方案 -->
<div class="solution-section">
  <div class="solution-title">🚀 MediSlim 怎么帮你</div>
  <div class="solution-sub">AI驱动 · 执业医师 · 药品到家</div>
  <div class="flow">
    <div class="flow-step"><div class="num">Step 1</div><div class="text">📝 AI评估</div></div>
    <div class="flow-arrow">→</div>
    <div class="flow-step"><div class="num">Step 2</div><div class="text">👨‍⚕️ 医师审核</div></div>
    <div class="flow-arrow">→</div>
    <div class="flow-step"><div class="num">Step 3</div><div class="text">📦 药品到家</div></div>
    <div class="flow-arrow">→</div>
    <div class="flow-step"><div class="num">Step 4</div><div class="text">💬 跟踪随访</div></div>
  </div>
</div>

<!-- 产品 -->
<div class="products-section">
  <h3 style="font-size:18px;font-weight:700;margin-bottom:16px">🔥 热门产品</h3>
  
  <div class="product-card hot" onclick="openForm('glp1')">
    <div class="product-header">
      <div class="product-emoji pe-glp">🔥</div>
      <div class="product-info">
        <h3>GLP-1 科学减重</h3>
        <p>司美格鲁肽 · 医生指导 · 安全减重</p>
      </div>
    </div>
    <div style="font-size:13px;color:#666;line-height:1.8">
      ✅ 无需节食痛苦 ✅ 不怕运动损伤 ✅ 每月轻松减3-5kg
    </div>
    <div class="product-price-row">
      <div class="product-price">
        <div class="first"><span>¥</span>399 <span>/首月</span></div>
        <div class="renew">续费 ¥599/月 · 随时可取消</div>
      </div>
      <button class="btn-order">立即评估 →</button>
    </div>
  </div>

  <div class="product-card" onclick="openForm('hair')">
    <div class="product-header">
      <div class="product-emoji pe-hair">💇</div>
      <div class="product-info">
        <h3>防脱生发</h3>
        <p>米诺地尔+非那雄胺 · 专业防脱</p>
      </div>
    </div>
    <div class="product-price-row">
      <div class="product-price">
        <div class="first"><span>¥</span>199 <span>/首月</span></div>
        <div class="renew">续费 ¥299/月</div>
      </div>
      <button class="btn-order">立即评估 →</button>
    </div>
  </div>

  <div class="product-card" onclick="openForm('skin')">
    <div class="product-header">
      <div class="product-emoji pe-skin">🧴</div>
      <div class="product-info">
        <h3>皮肤管理</h3>
        <p>祛痘/美白/抗衰 · 皮肤科医生在线</p>
      </div>
    </div>
    <div class="product-price-row">
      <div class="product-price">
        <div class="first"><span>¥</span>299 <span>/首月</span></div>
        <div class="renew">续费 ¥399/月</div>
      </div>
      <button class="btn-order">立即评估 →</button>
    </div>
  </div>
</div>

<!-- 案例 -->
<div class="cases-section">
  <h3 style="font-size:18px;font-weight:700;margin-bottom:16px">💬 真实用户反馈</h3>
  
  <div class="case-card">
    <div class="case-header">
      <div class="case-avatar">L</div>
      <div><div class="case-name">Linda · 32岁</div><div class="case-time">使用3个月</div></div>
    </div>
    <p style="font-size:14px;color:#666;line-height:1.8">生完二胎体重一直下不来，试过各种方法都不行。在MediSlim做了AI评估后，医生给我开了司美格鲁肽，第一个月就瘦了5kg，现在三个月瘦了15kg！终于回到了孕前体重 😭</p>
    <div class="case-result">
      <div class="label">3个月减重</div>
      <div class="value">-15.2 kg</div>
    </div>
  </div>

  <div class="case-card">
    <div class="case-header">
      <div class="case-avatar">王</div>
      <div><div class="case-name">王先生 · 28岁</div><div class="case-time">使用6个月</div></div>
    </div>
    <p style="font-size:14px;color:#666;line-height:1.8">M型发际线越来越严重，试过很多洗发水都没用。在MediSlim开了米诺地尔+非那雄胺，6个月后发际线明显改善，同事都说我年轻了5岁。</p>
    <div class="case-result">
      <div class="label">6个月生发效果</div>
      <div class="value">发际线前移 1.2cm</div>
    </div>
  </div>
</div>

<!-- 信任 -->
<div class="trust-section">
  <div style="text-align:center;font-size:18px;font-weight:700;margin-bottom:4px">🛡️ 为什么选择我们</div>
  <div class="trust-grid">
    <div class="trust-item">
      <div class="icon">👨‍⚕️</div>
      <h4>执业医师</h4>
      <p>持证互联网医院</p>
    </div>
    <div class="trust-item">
      <div class="icon">🤖</div>
      <h4>AI驱动</h4>
      <p>智能评估+方案</p>
    </div>
    <div class="trust-item">
      <div class="icon">📦</div>
      <h4>保密配送</h4>
      <p>顺丰/京东到家</p>
    </div>
    <div class="trust-item">
      <div class="icon">🔒</div>
      <h4>数据安全</h4>
      <p>加密存储</p>
    </div>
    <div class="trust-item">
      <div class="icon">💬</div>
      <h4>24h客服</h4>
      <p>随时在线</p>
    </div>
    <div class="trust-item">
      <div class="icon">🔄</div>
      <h4>随时取消</h4>
      <p>无合约绑定</p>
    </div>
  </div>
</div>

<!-- CTA -->
<div class="cta-section">
  <h2>🎯 限时优惠</h2>
  <p>首月体验价 · 先评估再决定 · 不满意随时退</p>
  <a class="btn-cta" href="javascript:openForm('glp1')">免费AI评估 →</a>
</div>

<!-- 微信 -->
<div class="wechat-section">
  <div class="wechat-icon">💬</div>
  <h3 style="font-size:18px;font-weight:700">添加健康顾问</h3>
  <p style="font-size:14px;color:#999;margin-top:8px">1对1专属服务 · 专业解答 · 限时优惠</p>
  <div class="wechat-id" id="wx-id">MediSlim-Support</div>
  <button class="copy-btn" onclick="copyWx()">📋 复制微信号</button>
  <div class="wechat-qr">👆 长按复制 · 微信搜索添加</div>
</div>

<!-- 底部 -->
<div class="footer">
  MediSlim 轻健康 · AI驱动消费医疗平台<br>
  合作机构持有互联网医院牌照 · 处方药需经医师审核<br>
  <a href="#">用户协议</a> · <a href="#">隐私政策</a> · <a href="#">退款政策</a>
</div>

<!-- 表单弹窗 -->
<div class="modal" id="modal">
  <div class="modal-box">
    <span class="modal-close" onclick="closeForm()">&times;</span>
    <div id="form-content">
      <h3 style="font-size:18px;font-weight:700;margin-bottom:20px;text-align:center" id="form-title">📋 免费AI健康评估</h3>
      <div class="form-group">
        <label>📱 手机号</label>
        <input type="tel" id="phone" placeholder="请输入手机号" maxlength="11">
      </div>
      <div class="form-group">
        <label>👤 称呼</label>
        <input type="text" id="name" placeholder="请输入您的称呼">
      </div>
      <div class="form-group">
        <label>💊 感兴趣的产品</label>
        <select id="product">
          <option value="glp1">🔥 GLP-1 科学减重 (¥399首月)</option>
          <option value="hair">💇 防脱生发 (¥199首月)</option>
          <option value="skin">🧴 皮肤管理 (¥299首月)</option>
          <option value="mens">💪 男性健康 (¥399首月)</option>
          <option value="sleep">😴 助眠调理 (¥199首月)</option>
        </select>
      </div>
      <div class="form-group">
        <label>💬 最想解决的问题</label>
        <input type="text" id="problem" placeholder="简要描述您的困扰">
      </div>
      <button class="btn-submit" onclick="submitForm()">提交 · 免费获取AI评估报告</button>
      <p style="font-size:11px;color:#999;text-align:center;margin-top:12px">提交即同意《用户协议》和《隐私政策》</p>
    </div>
  </div>
</div>

<script>
function openForm(pid){
  document.getElementById('product').value = pid;
  const titles = {glp1:'🔥 GLP-1减重评估',hair:'💇 防脱生发评估',skin:'🧴 皮肤管理评估',mens:'💪 男性健康评估',sleep:'😴 助眠调理评估'};
  document.getElementById('form-title').textContent = titles[pid]||'📋 免费AI健康评估';
  document.getElementById('modal').classList.add('show');
}
function closeForm(){document.getElementById('modal').classList.remove('show')}

function submitForm(){
  const phone = document.getElementById('phone').value;
  const name = document.getElementById('name').value;
  const product = document.getElementById('product').value;
  const problem = document.getElementById('problem').value;
  
  if(!phone || phone.length < 11){alert('请输入正确的手机号');return;}
  
  // 提交到API
  fetch('/api/lead/create',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({phone,name,product,problem})
  }).then(r=>r.json()).then(d=>{
    document.getElementById('form-content').innerHTML = `
      <div class="success-msg">
        <div class="icon">✅</div>
        <h3>提交成功！</h3>
        <p style="font-size:14px;color:#999;margin:12px 0">
          我们的健康顾问将在 <strong style="color:#07C160">30分钟内</strong> 联系您<br>
          为您安排AI健康评估
        </p>
        <div style="background:#F0FFF4;border-radius:12px;padding:16px;margin-top:20px;font-size:13px;line-height:2;text-align:left">
          📋 您的需求已记录<br>
          🤖 AI评估报告将发送到您的手机<br>
          💊 医师将在24小时内审核方案
        </div>
        <button class="btn-submit" style="margin-top:20px" onclick="closeForm()">好的，等待联系</button>
      </div>
    `;
  });
}

function copyWx(){
  navigator.clipboard.writeText('MediSlim-Support').then(()=>{
    alert('微信号已复制！打开微信搜索添加');
  }).catch(()=>{
    prompt('请复制微信号：','MediSlim-Support');
  });
}
</script>
</body>
</html>"""

# ========== API处理器 ==========
class LandingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self._html(LANDING_HTML)
        elif path == "/api/stats":
            leads = load_db("leads")
            self._json({"total_leads": len(leads), "today_leads": sum(1 for l in leads.values() if l.get("created_at","")[:10]==datetime.now().strftime("%Y-%m-%d"))})
        else:
            self._html(LANDING_HTML)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode() if length else "{}"
        try: data = json.loads(body)
        except: data = {}

        if self.path == "/api/lead/create":
            leads = load_db("leads")
            lid = str(uuid.uuid4())[:12]
            lead = {
                "id": lid,
                "phone": data.get("phone",""),
                "name": data.get("name",""),
                "product": data.get("product",""),
                "problem": data.get("problem",""),
                "source": "landing_page",
                "status": "new",
                "created_at": datetime.now().isoformat(),
                "follow_up": [],
            }
            leads[lid] = lead
            save_db("leads", leads)
            self._json({"success": True, "lead_id": lid, "message": "已记录，顾问30分钟内联系"})
        elif self.path == "/api/lead/list":
            leads = load_db("leads")
            self._json(list(leads.values()))
        else:
            self._json({"error": "Not found"}, 404)

    def _html(self, html):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())
    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
    def log_message(self, *a): pass

def main():
    port = int(os.environ.get("PORT", 8091))
    server = HTTPServer(("0.0.0.0", port), LandingHandler)
    print(f"💰 MediSlim 落地页启动: http://localhost:{port}")
    server.serve_forever()

if __name__ == "__main__":
    main()
