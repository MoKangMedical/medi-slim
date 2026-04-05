"""
MediSlim 小红书发布队列管理
服务器端：管理待发布队列，供本地代理拉取
端口：8099
"""
import os
import json
import time
import shutil
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

PORT = 8099
CATALOG_PATH = Path(__file__).parent / "content_engine" / "output" / "catalog.json"
READY_DIR = Path(__file__).parent / "content_engine" / "output" / "ready_to_post"
DATA_DIR = Path(__file__).parent / "content_engine" / "data"
DATA_DIR.mkdir(exist_ok=True)

QUEUE_FILE = DATA_DIR / "post_queue.json"
HISTORY_FILE = DATA_DIR / "post_history.json"


def load_json(path, default=None):
    if path.exists():
        return json.loads(path.read_text())
    return default if default is not None else []


def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def init_queue():
    """从catalog初始化发布队列"""
    if QUEUE_FILE.exists():
        queue = load_json(QUEUE_FILE, [])
        if queue:
            return queue

    # 从catalog构建队列
    catalog = load_json(CATALOG_PATH, [])
    history = load_json(HISTORY_FILE, [])
    posted_ids = {h["item_id"] for h in history}

    queue = []
    seen_combos = set()

    for entry in catalog:
        item_id = entry.get("id", "")
        if item_id in posted_ids:
            continue

        # 每个品类×钩子×风格只取一条
        combo = f"{entry['product_id']}_{entry['hook_category']}_{entry['style']}"
        if combo in seen_combos:
            continue
        seen_combos.add(combo)

        # 收集图片路径
        image_paths = []
        for p in entry.get("card_paths", []):
            if os.path.exists(p):
                image_paths.append(p)

        tc = entry.get("tracking", {})
        queue.append({
            "id": item_id,
            "product_id": entry["product_id"],
            "hook": entry["hook"],
            "body": entry["body"],
            "style": entry["style"],
            "hook_category": entry["hook_category"],
            "image_paths": image_paths,
            "image_count": len(image_paths),
            "track_code": tc.get("track_code", ""),
            "cta_comment": (tc.get("cta_comments") or [""])[0],
            "tags": [
                f"#{entry['product_id']}",
                "#MediSlim",
                "#AI健康",
                f"#{entry['style']}",
            ],
            "status": "pending",
            "added_at": datetime.now().isoformat(),
        })

    save_json(QUEUE_FILE, queue)
    print(f"📋 初始化队列: {len(queue)} 条待发布")
    return queue


class QueueHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/post-queue":
            # 返回待发布队列（最多5条）
            queue = load_json(QUEUE_FILE, [])
            pending = [q for q in queue if q.get("status") == "pending"][:5]
            self._json({"queue": pending, "total_pending": len([q for q in queue if q.get("status") == "pending"])})

        elif path == "/api/queue-status":
            queue = load_json(QUEUE_FILE, [])
            history = load_json(HISTORY_FILE, [])
            self._json({
                "pending": len([q for q in queue if q.get("status") == "pending"]),
                "posted": len(history),
                "failed": len([q for q in queue if q.get("status") == "failed"]),
                "total": len(queue),
            })

        elif path == "/api/post-history":
            history = load_json(HISTORY_FILE, [])
            self._json({"history": history[-50:]})

        elif path == "/api/reset-queue":
            QUEUE_FILE.unlink(missing_ok=True)
            queue = init_queue()
            self._json({"ok": True, "reset_count": len(queue)})

        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/mark-posted":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            item_id = body.get("item_id", "")

            # 更新队列状态
            queue = load_json(QUEUE_FILE, [])
            for q in queue:
                if q["id"] == item_id:
                    q["status"] = "posted"
                    q["posted_at"] = body.get("posted_at", datetime.now().isoformat())
                    break
            save_json(QUEUE_FILE, queue)

            # 记录发布历史
            history = load_json(HISTORY_FILE, [])
            history.append({
                "item_id": item_id,
                "posted_at": body.get("posted_at", datetime.now().isoformat()),
                "platform": "xiaohongshu",
            })
            save_json(HISTORY_FILE, history)

            self._json({"ok": True})

        elif path == "/api/mark-failed":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            item_id = body.get("item_id", "")

            queue = load_json(QUEUE_FILE, [])
            for q in queue:
                if q["id"] == item_id:
                    q["status"] = "failed"
                    q["fail_reason"] = body.get("reason", "")
                    break
            save_json(QUEUE_FILE, queue)

            self._json({"ok": True})

        elif path == "/api/add-to-queue":
            # 手动添加内容到队列
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            queue = load_json(QUEUE_FILE, [])
            body["status"] = "pending"
            body["added_at"] = datetime.now().isoformat()
            queue.append(body)
            save_json(QUEUE_FILE, queue)
            self._json({"ok": True, "queue_size": len(queue)})

        else:
            self.send_error(404)

    def _json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode())


def main():
    queue = init_queue()
    server = HTTPServer(("0.0.0.0", PORT), QueueHandler)
    print(f"📮 发布队列服务启动: http://0.0.0.0:{PORT}")
    print(f"  队列状态: http://localhost:{PORT}/api/queue-status")
    print(f"  待发布: http://localhost:{PORT}/api/post-queue")
    server.serve_forever()


if __name__ == "__main__":
    main()
