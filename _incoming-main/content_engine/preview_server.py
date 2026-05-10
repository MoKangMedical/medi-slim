"""
MediSlim 小红书爆款内容预览服务器
端口：8094
功能：浏览/筛选/预览所有生成的文案和配图
零依赖，Python标准库
"""
import os
import json
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

CONTENT_DIR = Path(__file__).parent
CATALOG_PATH = CONTENT_DIR / "output" / "catalog.json"
PORT = 8096

# 产品名称映射
PRODUCT_NAMES = {
    "glp1": "🔥 GLP-1科学减重",
    "hair": "💇 防脱生发",
    "skin": "🧴 皮肤管理",
    "mens": "💪 男性健康",
    "sleep": "😴 助眠调理",
}

STYLE_EMOJI = {
    "闺蜜体": "👯‍♀️",
    "专业体": "👨‍⚕️",
    "种草体": "🌿",
    "焦虑体": "😰",
    "励志体": "💪",
    "故事体": "📖",
}

HOOK_EMOJI = {
    "焦虑型": "😱",
    "好奇型": "🤔",
    "干货型": "📝",
    "种草型": "🌱",
    "励志型": "🔥",
    "反转型": "🔄",
}


class PreviewHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # 静默日志

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self._serve_index()
        elif path == "/api/catalog":
            self._serve_catalog(params)
        elif path == "/api/stats":
            self._serve_stats()
        elif path.startswith("/output/"):
            self._serve_image(path)
        elif path == "/api/regenerate":
            self._regenerate(params)
        else:
            self.send_error(404)

    def _serve_index(self):
        html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MediSlim · 小红书爆款内容工厂</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,"PingFang SC",sans-serif;background:#f5f5f5;color:#1a1a1a}
.header{background:linear-gradient(135deg,#07C160,#059B48);color:#fff;padding:30px;text-align:center}
.header h1{font-size:28px;font-weight:800}
.header p{font-size:14px;opacity:.8;margin-top:8px}
.stats-bar{display:flex;justify-content:center;gap:40px;padding:20px;background:#fff;box-shadow:0 2px 8px rgba(0,0,0,.06)}
.stat{text-align:center}
.stat .num{font-size:28px;font-weight:800;color:#07C160}
.stat .label{font-size:12px;color:#999;margin-top:4px}
.filters{padding:20px;background:#fff;margin:16px;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.04)}
.filter-group{margin-bottom:12px}
.filter-group label{font-size:13px;font-weight:600;color:#666;margin-right:12px}
.filter-btn{display:inline-block;padding:6px 16px;border-radius:20px;border:1px solid #ddd;background:#fff;font-size:13px;cursor:pointer;margin:4px;transition:all .2s}
.filter-btn:hover,.filter-btn.active{background:#07C160;color:#fff;border-color:#07C160}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px;padding:0 16px 30px}
.card{background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.06);transition:transform .2s}
.card:hover{transform:translateY(-2px);box-shadow:0 4px 16px rgba(0,0,0,.1)}
.card-img{width:100%;aspect-ratio:3/4;object-fit:cover;cursor:pointer}
.card-info{padding:12px 16px}
.card-hook{font-size:14px;font-weight:600;line-height:1.4;margin-bottom:8px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.card-meta{display:flex;gap:8px;flex-wrap:wrap}
.badge{font-size:11px;padding:2px 8px;border-radius:10px;background:#f0f0f0;color:#666}
.badge-product{background:#E8F5E9;color:#2E7D32}
.badge-style{background:#E3F2FD;color:#1565C0}
.badge-hook{background:#FFF3E0;color:#E65100}
.badge-palette{background:#F3E5F5;color:#7B1FA2}
.modal{display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.8);z-index:100;overflow-y:auto;padding:40px 20px}
.modal.active{display:block}
.modal-content{max-width:600px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden}
.modal-img{width:100%}
.modal-info{padding:20px}
.modal-hook{font-size:18px;font-weight:700;margin-bottom:12px}
.modal-body{font-size:14px;color:#666;line-height:1.8;white-space:pre-line}
.modal-close{position:fixed;top:20px;right:20px;color:#fff;font-size:32px;cursor:pointer;z-index:101}
.loading{text-align:center;padding:40px;color:#999}
</style>
</head>
<body>
<div class="header">
  <h1>🎨 小红书爆款内容工厂</h1>
  <p>9000文案变体 × 8配色方案 × 5品类 = 1000+套完整内容</p>
</div>
<div class="stats-bar" id="stats"></div>
<div class="filters" id="filters">
  <div class="filter-group">
    <label>📦 品类：</label>
    <button class="filter-btn active" onclick="filterProduct('all')">全部</button>
    <button class="filter-btn" onclick="filterProduct('glp1')">🔥 减重</button>
    <button class="filter-btn" onclick="filterProduct('hair')">💇 防脱</button>
    <button class="filter-btn" onclick="filterProduct('skin')">🧴 皮肤</button>
    <button class="filter-btn" onclick="filterProduct('mens')">💪 男性</button>
    <button class="filter-btn" onclick="filterProduct('sleep')">😴 助眠</button>
  </div>
  <div class="filter-group">
    <label>✍️ 风格：</label>
    <button class="filter-btn active" onclick="filterStyle('all')">全部</button>
    <button class="filter-btn" onclick="filterStyle('闺蜜体')">👯‍♀️ 闺蜜体</button>
    <button class="filter-btn" onclick="filterStyle('专业体')">👨‍⚕️ 专业体</button>
    <button class="filter-btn" onclick="filterStyle('种草体')">🌿 种草体</button>
    <button class="filter-btn" onclick="filterStyle('焦虑体')">😰 焦虑体</button>
    <button class="filter-btn" onclick="filterStyle('励志体')">💪 励志体</button>
    <button class="filter-btn" onclick="filterStyle('故事体')">📖 故事体</button>
  </div>
</div>
<div class="grid" id="grid">
  <div class="loading">⏳ 加载中...</div>
</div>

<div class="modal" id="modal" onclick="if(event.target===this)closeModal()">
  <div class="modal-close" onclick="closeModal()">✕</div>
  <div class="modal-content" id="modal-content"></div>
</div>

<script>
let catalog=[];
let currentProduct='all',currentStyle='all';

async function init(){
  const r=await fetch('/api/stats');
  const s=await r.json();
  document.getElementById('stats').innerHTML=
    `<div class="stat"><div class="num">${s.total||0}</div><div class="label">总套数</div></div>`+
    `<div class="stat"><div class="num">${s.products||5}</div><div class="label">品类</div></div>`+
    `<div class="stat"><div class="num">${s.palettes||8}</div><div class="label">配色</div></div>`+
    `<div class="stat"><div class="num">${s.styles||6}</div><div class="label">风格</div></div>`;

  const r2=await fetch('/api/catalog');
  catalog=await r2.json();
  render();
}

function render(){
  const filtered=catalog.filter(c=>
    (currentProduct==='all'||c.product_id===currentProduct)&&
    (currentStyle==='all'||c.style===currentStyle)
  );
  document.getElementById('grid').innerHTML=filtered.map(c=>{
    const heroImg=c.card_paths&&c.card_paths[0]?c.card_paths[0].replace('/root/medi-slim/content_engine/','/output/'):'';
    return `<div class="card" onclick='showDetail(${JSON.stringify(c).replace(/'/g,"&#39;")})'>
      ${heroImg?`<img class="card-img" src="${heroImg}" loading="lazy" onerror="this.style.display='none'">`:''}
      <div class="card-info">
        <div class="card-hook">${c.hook}</div>
        <div class="card-meta">
          <span class="badge badge-product">${c.product_id}</span>
          <span class="badge badge-style">${c.style}</span>
          <span class="badge badge-hook">${c.hook_category}</span>
          <span class="badge badge-palette">${c.palette_id}</span>
        </div>
      </div>
    </div>`;
  }).join('')||'<div class="loading">暂无内容，生成中...</div>';
}

function filterProduct(p){currentProduct=p;render();
  document.querySelectorAll('.filter-group:first-child .filter-btn').forEach(b=>b.classList.remove('active'));
  event.target.classList.add('active');
}
function filterStyle(s){currentStyle=s;render();
  document.querySelectorAll('.filter-group:nth-child(2) .filter-btn').forEach(b=>b.classList.remove('active'));
  event.target.classList.add('active');
}

function showDetail(c){
  const imgs=c.card_paths?c.card_paths.map(p=>
    `<img class="modal-img" src="${p.replace('/root/medi-slim/content_engine/','/output/')}" onerror="this.style.display='none'">`
  ).join(''):'';
  document.getElementById('modal-content').innerHTML=
    `<div class="modal-info"><div class="modal-hook">${c.hook}</div>
     <div class="card-meta" style="margin-bottom:16px">
       <span class="badge badge-product">${c.product_id}</span>
       <span class="badge badge-style">${c.style}</span>
       <span class="badge badge-hook">${c.hook_category}</span>
     </div>
     <div class="modal-body">${c.body}</div>
    </div>${imgs}`;
  document.getElementById('modal').classList.add('active');
}
function closeModal(){document.getElementById('modal').classList.remove('active')}

init();
</script>
</body></html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

    def _serve_catalog(self, params):
        if CATALOG_PATH.exists():
            with open(CATALOG_PATH, "r", encoding="utf-8") as f:
                catalog = json.load(f)
        else:
            catalog = []

        product = params.get("product", [None])[0]
        style = params.get("style", [None])[0]

        if product:
            catalog = [c for c in catalog if c["product_id"] == product]
        if style:
            catalog = [c for c in catalog if c["style"] == style]

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(catalog[:200], ensure_ascii=False).encode())

    def _serve_stats(self):
        if CATALOG_PATH.exists():
            with open(CATALOG_PATH, "r", encoding="utf-8") as f:
                catalog = json.load(f)
        else:
            catalog = []

        stats = {
            "total": len(catalog),
            "products": len(set(c["product_id"] for c in catalog)) if catalog else 0,
            "palettes": len(set(c["palette_id"] for c in catalog)) if catalog else 0,
            "styles": len(set(c["style"] for c in catalog)) if catalog else 0,
        }

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(stats).encode())

    def _serve_image(self, path):
        # /output/glp1/hero_xxx.png -> content_engine/output/glp1/hero_xxx.png
        file_path = CONTENT_DIR / path.lstrip("/")
        if file_path.exists():
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Cache-Control", "public, max-age=3600")
            self.end_headers()
            self.wfile.write(file_path.read_bytes())
        else:
            self.send_error(404, f"Image not found: {file_path}")


def main():
    server = HTTPServer(("0.0.0.0", PORT), PreviewHandler)
    print(f"🎨 小红书爆款内容预览服务器启动: http://0.0.0.0:{PORT}")
    print(f"📊 目录文件: {CATALOG_PATH}")
    server.serve_forever()


if __name__ == "__main__":
    main()
