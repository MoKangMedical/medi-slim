"""
MediSlim 智能排期系统
根据转化数据自动选择最佳内容，生成每日发布计划
端口：8100
"""
import os
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

BASE_DIR = Path(__file__).parent.parent
PORT = 8100
CATALOG_PATH = BASE_DIR / "content_engine" / "output" / "catalog.json"
DATA_DIR = BASE_DIR / "content_engine" / "data"
SCHEDULE_FILE = DATA_DIR / "daily_schedule.json"
HISTORY_FILE = DATA_DIR / "post_history.json"


def load_json(path, default=None):
    if path.exists():
        return json.loads(path.read_text())
    return default if default is not None else {}


def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


# ========== 小红书最佳发布时间 ==========
BEST_TIMES = {
    "weekday": [
        {"time": "07:30", "label": "早高峰通勤", "score": 85},
        {"time": "12:00", "label": "午休刷手机", "score": 95},
        {"time": "18:00", "label": "下班通勤", "score": 80},
        {"time": "20:00", "label": "晚间黄金时段", "score": 100},
        {"time": "21:30", "label": "睡前刷手机", "score": 90},
        {"time": "23:00", "label": "深夜emo时段", "score": 70},
    ],
    "weekend": [
        {"time": "09:00", "label": "周末赖床刷手机", "score": 90},
        {"time": "11:00", "label": "周末上午", "score": 85},
        {"time": "14:00", "label": "午休后", "score": 80},
        {"time": "16:00", "label": "下午茶时间", "score": 85},
        {"time": "20:00", "label": "周末黄金时段", "score": 100},
        {"time": "22:00", "label": "周末夜间", "score": 90},
    ],
}


def get_performance_data():
    """从追踪系统获取转化数据"""
    import urllib.request
    try:
        resp = urllib.request.urlopen("http://localhost:8097/api/performance?top=100", timeout=5)
        return json.loads(resp.read())
    except:
        return []


def get_posted_ids():
    """获取已发布内容ID"""
    history = load_json(HISTORY_FILE, [])
    if isinstance(history, list):
        return {h.get("item_id", "") for h in history}
    return set()


def score_content(entry, performance_data):
    """给内容打分（决定是否优先发布）"""
    score = 0

    # 1. 品类权重（减重和防脱最热门）
    product_weights = {"glp1": 100, "hair": 90, "skin": 70, "mens": 60, "sleep": 50}
    score += product_weights.get(entry["product_id"], 50)

    # 2. 钩子类型权重
    hook_weights = {"焦虑型": 95, "好奇型": 90, "反转型": 85, "种草型": 80, "干货型": 70, "励志型": 60}
    score += hook_weights.get(entry.get("hook_category", ""), 50)

    # 3. 风格权重
    style_weights = {"闺蜜体": 90, "焦虑体": 85, "种草体": 80, "故事体": 75, "励志体": 70, "专业体": 60}
    score += style_weights.get(entry.get("style", ""), 50)

    # 4. 如果该品类+钩子组合在历史数据中转化高，加分
    for perf in performance_data[:20]:
        tc = perf.get("track_code", "")
        if entry["product_id"] in tc and entry.get("hook_category", "") in tc:
            score += perf.get("score", 0) // 10
            break

    return score


def generate_schedule(date_str=None, posts_per_day=5):
    """生成某天的发布排期"""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    catalog = load_json(CATALOG_PATH, [])
    if not catalog:
        return {"error": "catalog empty"}

    posted_ids = get_posted_ids()
    performance = get_performance_data()

    # 过滤未发布内容
    available = [e for e in catalog if e.get("id", "") not in posted_ids]

    # 打分排序
    for entry in available:
        entry["_score"] = score_content(entry, performance)

    available.sort(key=lambda x: x["_score"], reverse=True)

    # 选择当天发布内容（确保品类和风格多样化）
    selected = []
    used_products = set()
    used_styles = set()

    for entry in available:
        if len(selected) >= posts_per_day:
            break
        pid = entry["product_id"]
        style = entry.get("style", "")
        # 避免同一品类/风格连续出现
        if pid in used_products and style in used_styles:
            continue
        selected.append(entry)
        used_products.add(pid)
        used_styles.add(style)

    # 如果不够，补充
    if len(selected) < posts_per_day:
        for entry in available:
            if entry not in selected and len(selected) < posts_per_day:
                selected.append(entry)

    # 分配发布时间
    date = datetime.strptime(date_str, "%Y-%m-%d")
    is_weekend = date.weekday() >= 5
    time_slots = BEST_TIMES["weekend" if is_weekend else "weekday"]

    schedule = []
    for i, entry in enumerate(selected[:posts_per_day]):
        slot = time_slots[i % len(time_slots)]
        tc = entry.get("tracking", {})

        schedule.append({
            "slot": i + 1,
            "time": slot["time"],
            "time_label": slot["label"],
            "time_score": slot["score"],
            "product_id": entry["product_id"],
            "hook": entry["hook"],
            "style": entry.get("style", ""),
            "hook_category": entry.get("hook_category", ""),
            "content_score": entry.get("_score", 0),
            "track_code": tc.get("track_code", ""),
            "cta_comment": (tc.get("cta_comments") or [""])[0],
            "content_id": entry.get("id", ""),
            "status": "pending",
        })

    # 保存排期
    all_schedules = load_json(SCHEDULE_FILE, {})
    all_schedules[date_str] = schedule
    save_json(SCHEDULE_FILE, all_schedules)

    return {
        "date": date_str,
        "is_weekend": is_weekend,
        "posts_count": len(schedule),
        "schedule": schedule,
    }


def get_week_schedule(start_date=None):
    """生成一周排期"""
    if start_date is None:
        start_date = datetime.now()

    week = []
    for i in range(7):
        d = start_date + timedelta(days=i)
        date_str = d.strftime("%Y-%m-%d")
        day_schedule = generate_schedule(date_str)
        week.append(day_schedule)

    return week


class ScheduleHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        if path == "/api/schedule/today":
            date = params.get("date", [datetime.now().strftime("%Y-%m-%d")])[0]
            result = generate_schedule(date)
            self._json(result)

        elif path == "/api/schedule/week":
            result = get_week_schedule()
            self._json({"week": result})

        elif path == "/api/schedule/optimal-times":
            self._json({
                "weekday": BEST_TIMES["weekday"],
                "weekend": BEST_TIMES["weekend"],
                "tips": [
                    "午休12:00和晚间20:00是黄金时段",
                    "焦虑型钩子在早高峰效果好",
                    "种草型内容在晚间效果最好",
                    "周末上午11点前发布效果好",
                    "深夜23点发'失眠'相关内容效果翻倍",
                ],
            })

        elif path == "/api/schedule/history":
            schedules = load_json(SCHEDULE_FILE, {})
            self._json({"schedules": schedules})

        else:
            self.send_error(404)

    def _json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode())


def main():
    # 预生成今天和明天的排期
    generate_schedule()
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    generate_schedule(tomorrow)

    server = HTTPServer(("0.0.0.0", PORT), ScheduleHandler)
    print(f"📅 智能排期系统启动: http://0.0.0.0:{PORT}")
    print(f"  今日排期: http://localhost:{PORT}/api/schedule/today")
    print(f"  本周排期: http://localhost:{PORT}/api/schedule/week")
    server.serve_forever()


if __name__ == "__main__":
    main()
