"""
MediSlim A/B测试分析面板
分析哪类钩子、风格、品类、配色组合转化最好
端口：8101
"""
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

PORT = 8101
DATA_DIR = Path(__file__).parent / "data"


def load_json(name, default=None):
    p = DATA_DIR / f"{name}.json"
    if p.exists():
        return json.loads(p.read_text())
    return default if default is not None else {}


def analyze_ab():
    """全面A/B测试分析"""
    events = load_json("tracking_events", [])
    if not events:
        return {"error": "no data"}

    # 按track_code解析内容属性
    # track_code格式: xhs_{product_id}_{content_id}
    content_stats = defaultdict(lambda: {
        "impression": 0, "click": 0, "comment": 0,
        "landing": 0, "assess_start": 0, "assess_done": 0,
        "order_create": 0, "order_pay": 0, "reorder": 0,
    })

    for e in events:
        code = e.get("track_code", "")
        et = e.get("event_type", "")
        if code and et in content_stats[code]:
            content_stats[code][et] += 1

    # 从track_code提取品类
    def extract_product(code):
        parts = code.split("_")
        return parts[1] if len(parts) > 1 else "unknown"

    # 品类维度分析
    by_product = defaultdict(lambda: defaultdict(int))
    for code, stats in content_stats.items():
        pid = extract_product(code)
        for et, count in stats.items():
            by_product[pid][et] += count

    # 转化率计算
    def calc_rates(stats):
        imp = stats.get("impression", 1)
        return {
            "ctr": round(stats.get("click", 0) / imp * 100, 2),
            "landing_rate": round(stats.get("landing", 0) / max(stats.get("click", 1), 1) * 100, 2),
            "assess_rate": round(stats.get("assess_done", 0) / max(stats.get("landing", 1), 1) * 100, 2),
            "conversion_rate": round(stats.get("order_pay", 0) / max(stats.get("assess_done", 1), 1) * 100, 2),
            "full_funnel": round(stats.get("order_pay", 0) / imp * 100, 4),
        }

    # Top/Bottom内容
    scored = []
    for code, stats in content_stats.items():
        score = (stats["click"] * 2 + stats["landing"] * 5 +
                 stats["assess_done"] * 10 + stats["order_pay"] * 30)
        scored.append({
            "track_code": code,
            "product": extract_product(code),
            "score": score,
            **stats,
            "rates": calc_rates(stats),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)

    # 品类对比
    product_comparison = {}
    for pid, stats in by_product.items():
        product_comparison[pid] = {
            **stats,
            "rates": calc_rates(stats),
            "content_count": len([c for c in content_stats if extract_product(c) == pid]),
        }

    return {
        "total_contents": len(content_stats),
        "total_events": len(events),
        "product_comparison": product_comparison,
        "top_10": scored[:10],
        "bottom_10": scored[-10:] if len(scored) > 10 else [],
        "insights": generate_insights(product_comparison, scored),
    }


def generate_insights(product_comp, scored):
    """自动生成洞察建议"""
    insights = []

    # 最佳品类
    if product_comp:
        best_pid = max(product_comp.keys(), key=lambda p: product_comp[p].get("order_pay", 0))
        insights.append(f"🏆 品类冠军: {best_pid}，支付转化最高")

    # 最佳内容
    if scored:
        best = scored[0]
        insights.append(f"⭐ 最佳内容: {best['track_code']}，得分{best['score']}")

    # CTR分析
    ctrs = [(c["track_code"], c["rates"]["ctr"]) for c in scored if c["impression"] > 10]
    if ctrs:
        ctrs.sort(key=lambda x: x[1], reverse=True)
        avg_ctr = sum(c[1] for c in ctrs) / len(ctrs)
        insights.append(f"📊 平均CTR: {avg_ctr:.1f}%，最高: {ctrs[0][1]}% ({ctrs[0][0][:20]})")

    # 全漏斗转化
    if scored:
        full_funnels = [(c["track_code"], c["rates"]["full_funnel"]) for c in scored if c["impression"] > 10]
        if full_funnels:
            full_funnels.sort(key=lambda x: x[1], reverse=True)
            insights.append(f"🔄 最高全漏斗转化: {full_funnels[0][1]}% ({full_funnels[0][0][:20]})")

    return insights


class ABHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/ab/analysis":
            result = analyze_ab()
            self._json(result)

        elif path == "/api/ab/compare":
            params = urllib.parse.parse_qs(parsed.query)
            # 对比两个track_code
            code_a = params.get("a", [""])[0]
            code_b = params.get("b", [""])[0]
            events = load_json("tracking_events", [])
            # ... simplified
            self._json({"a": code_a, "b": code_b, "status": "compare endpoint"})

        elif path == "/api/ab/dashboard":
            result = analyze_ab()
            html = render_dashboard(result)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode())

        else:
            self.send_error(404)

    def _json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode())


def render_dashboard(data):
    """渲染A/B测试看板"""
    pc = data.get("product_comparison", {})
    top = data.get("top_10", [])
    insights = data.get("insights", [])

    # 品类对比表格
    product_rows = ""
    for pid, stats in sorted(pc.items(), key=lambda x: x[1].get("order_pay", 0), reverse=True):
        rates = stats.get("rates", {})
        product_rows += f"""<tr>
            <td><b>{pid}</b></td>
            <td>{stats.get('impression',0):,}</td>
            <td>{stats.get('click',0):,}</td>
            <td>{rates.get('ctr',0)}%</td>
            <td>{stats.get('landing',0):,}</td>
            <td>{stats.get('assess_done',0)}</td>
            <td>{stats.get('order_pay',0)}</td>
            <td><b>{rates.get('full_funnel',0)}%</b></td>
            <td>{stats.get('content_count',0)}</td>
        </tr>"""

    # Top内容表格
    top_rows = ""
    for i, c in enumerate(top):
        rates = c.get("rates", {})
        top_rows += f"""<tr>
            <td>#{i+1}</td>
            <td><span class="badge">{c['track_code'][:25]}</span></td>
            <td><b>{c['score']}</b></td>
            <td>{c['impression']}</td>
            <td>{c['click']}</td>
            <td>{rates.get('ctr',0)}%</td>
            <td>{c['assess_done']}</td>
            <td>{c['order_pay']}</td>
            <td>{rates.get('full_funnel',0)}%</td>
        </tr>"""

    # 洞察
    insight_html = "".join(f"<li>{i}</li>" for i in insights)

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MediSlim · A/B测试分析</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,"PingFang SC",sans-serif;background:#f5f5f5;padding:20px}}
.header{{background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;padding:24px;border-radius:16px;margin-bottom:20px;text-align:center}}
.header h1{{font-size:24px}}
.stats-bar{{display:flex;gap:20px;margin-bottom:20px;flex-wrap:wrap}}
.stat-card{{background:#fff;border-radius:12px;padding:16px;flex:1;min-width:120px;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,.04)}}
.stat-card .num{{font-size:24px;font-weight:800;color:#667eea}}
.stat-card .label{{font-size:12px;color:#999;margin-top:4px}}
.section{{background:#fff;border-radius:12px;padding:20px;margin-bottom:20px;box-shadow:0 2px 8px rgba(0,0,0,.04)}}
.section h2{{font-size:18px;margin-bottom:16px;color:#1a1a1a}}
table{{width:100%;border-collapse:collapse}}
th{{background:#f8f8f8;padding:10px;text-align:left;font-size:12px;color:#666;border-bottom:2px solid #eee}}
td{{padding:8px 10px;font-size:13px;border-bottom:1px solid #f5f5f5}}
.badge{{display:inline-block;padding:2px 8px;border-radius:8px;font-size:11px;background:#E8EAF6;color:#3F51B5}}
.insights{{list-style:none;padding:0}}
.insights li{{padding:10px;margin-bottom:8px;background:#F3E5F5;border-radius:8px;font-size:14px;color:#4A148C}}
</style></head><body>
<div class="header"><h1>🧪 A/B测试分析面板</h1><p>数据驱动的内容优化</p></div>
<div class="stats-bar">
  <div class="stat-card"><div class="num">{data.get('total_contents',0)}</div><div class="label">测试内容数</div></div>
  <div class="stat-card"><div class="num">{data.get('total_events',0):,}</div><div class="label">总事件数</div></div>
  <div class="stat-card"><div class="num">{len(pc)}</div><div class="label">品类数</div></div>
</div>

<div class="section">
  <h2>💡 AI洞察</h2>
  <ul class="insights">{insight_html}</ul>
</div>

<div class="section">
  <h2>📊 品类对比</h2>
  <table>
  <tr><th>品类</th><th>曝光</th><th>点击</th><th>CTR</th><th>落地</th><th>评估</th><th>支付</th><th>全漏斗</th><th>内容数</th></tr>
  {product_rows}
  </table>
</div>

<div class="section">
  <h2>🏆 Top 10 高转化内容</h2>
  <table>
  <tr><th>#</th><th>追踪码</th><th>得分</th><th>曝光</th><th>点击</th><th>CTR</th><th>评估</th><th>支付</th><th>转化率</th></tr>
  {top_rows}
  </table>
</div>

<div style="text-align:center;color:#999;font-size:12px;margin-top:20px">
  更新: {datetime.now().strftime("%Y-%m-%d %H:%M")} · MediSlim A/B测试引擎
</div>
</body></html>"""


def main():
    server = HTTPServer(("0.0.0.0", PORT), ABHandler)
    print(f"🧪 A/B测试分析面板: http://0.0.0.0:{PORT}")
    print(f"  看板: http://localhost:{PORT}/api/ab/dashboard")
    print(f"  数据: http://localhost:{PORT}/api/ab/analysis")
    server.serve_forever()


if __name__ == "__main__":
    main()
