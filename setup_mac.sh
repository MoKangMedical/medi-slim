#!/bin/bash
# MediSlim 小红书自动发布 — Mac一键安装脚本
# 用法：bash setup_mac.sh

set -e

echo "╔══════════════════════════════════════════════╗"
echo "║   MediSlim 小红书自动发布代理 — Mac安装       ║"
echo "╚══════════════════════════════════════════════╝"

# 检查Python3
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到Python3，正在安装..."
    if command -v brew &> /dev/null; then
        brew install python3
    else
        echo "请先安装Python3: https://www.python.org/downloads/"
        exit 1
    fi
fi
echo "✅ Python3: $(python3 --version)"

# 安装依赖
echo "📦 安装依赖..."
pip3 install --user playwright requests 2>/dev/null || pip3 install playwright requests

# 安装浏览器
echo "🌐 安装Chromium浏览器（首次约200MB）..."
python3 -m playwright install chromium

# 创建工作目录
mkdir -p ~/medislim_xhs

# 下载发布脚本
echo "📝 创建发布脚本..."
cat > ~/medislim_xhs/xhs_poster.py << 'PYEOF'
"""
MediSlim 小红书本地发布代理 — Mac版
用法：python3 xhs_poster.py
"""
import os, sys, json, time, requests
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright

# ========== 配置（请修改SERVER_IP）==========
SERVER_IP = "43.128.114.201"  # ← 改成服务器公网IP
SERVER_URL = f"http://{SERVER_IP}:8099"
BROWSER_DATA = Path.home() / ".medislim_xhs_browser"
POST_INTERVAL = 90   # 发布间隔秒数
MAX_PER_DAY = 15     # 每天上限

XHS_CREATOR = "https://creator.xiaohongshu.com/publish/publish"
XHS_LOGIN = "https://creator.xiaohongshu.com/login"


class XHSPoster:
    def __init__(self):
        self.pw = None
        self.ctx = None
        self.page = None
        self.count = 0

    def start(self):
        self.pw = sync_playwright().start()
        BROWSER_DATA.mkdir(exist_ok=True)
        self.ctx = self.pw.chromium.launch_persistent_context(
            str(BROWSER_DATA), headless=False,
            viewport={"width": 1280, "height": 900},
            locale="zh-CN",
        )
        self.page = self.ctx.new_page()
        print("✅ 浏览器已启动")

    def login(self):
        self.page.goto(XHS_CREATOR)
        self.page.wait_for_timeout(3000)
        if "login" in self.page.url:
            print("\n🔐 请在浏览器窗口扫码登录小红书...")
            self.page.goto(XHS_LOGIN)
            for i in range(120):
                self.page.wait_for_timeout(2000)
                if "creator" in self.page.url and "login" not in self.page.url:
                    print("✅ 登录成功！")
                    return True
            return False
        print("✅ 已登录")
        return True

    def fetch(self):
        try:
            r = requests.get(f"{SERVER_URL}/api/post-queue", timeout=10)
            if r.status_code == 200:
                return r.json().get("queue", [])
        except Exception as e:
            print(f"⚠️ 拉取失败: {e}")
        return []

    def post(self, item):
        self.page.goto(XHS_CREATOR)
        self.page.wait_for_timeout(3000)

        # 上传图片
        imgs = [p for p in item.get("image_paths", []) if os.path.exists(p)]
        if imgs:
            fi = self.page.query_selector('input[type="file"]')
            if fi:
                fi.set_input_files(imgs)
                print(f"   📸 上传 {len(imgs)} 张图片")
                self.page.wait_for_timeout(6000)

        # 标题
        title = item.get("hook", "")[:20]
        ti = self.page.query_selector('input[placeholder*="标题"]') or \
             self.page.query_selector('[data-placeholder="添加标题"]')
        if ti:
            ti.click()
            ti.fill(title)
            print(f"   📝 标题: {title}")

        # 正文
        body = item.get("body", "")
        ed = self.page.query_selector('[contenteditable="true"]')
        if ed:
            ed.click()
            ed.fill(body)
            print(f"   📝 正文: {len(body)}字")

        self.page.wait_for_timeout(1000)

        # 发布
        btn = self.page.query_selector('button:has-text("发布")')
        if btn:
            btn.click()
            self.page.wait_for_timeout(3000)
            print("   ✅ 已发布！")
            return True
        else:
            self.page.screenshot(path=str(Path.home() / "medislim_xhs/debug.png"))
            print("   ❌ 未找到发布按钮，已截图到 ~/medislim_xhs/debug.png")
            return False

    def mark(self, item_id):
        try:
            requests.post(f"{SERVER_URL}/api/mark-posted", json={
                "item_id": item_id,
                "posted_at": datetime.now().isoformat(),
            }, timeout=5)
        except: pass

    def run(self):
        print("""
╔══════════════════════════════════════════════╗
║   MediSlim 小红书自动发布                     ║
║   Ctrl+C 退出                                 ║
╚══════════════════════════════════════════════╝
        """)
        self.start()
        if not self.login():
            print("❌ 登录失败")
            return

        print(f"\n🚀 开始发布循环... (间隔{POST_INTERVAL}s, 每日上限{MAX_PER_DAY})")

        while self.count < MAX_PER_DAY:
            queue = self.fetch()
            if not queue:
                print(f"📭 队列空，{POST_INTERVAL}s后重试...")
                time.sleep(POST_INTERVAL)
                continue

            for item in queue:
                if self.count >= MAX_PER_DAY:
                    break
                print(f"\n📤 [{self.count+1}/{MAX_PER_DAY}] {item['product_id']} | {item['hook'][:30]}...")
                if self.post(item):
                    self.mark(item["id"])
                    self.count += 1
                    print(f"   ⏳ 等待{POST_INTERVAL}s...")
                    time.sleep(POST_INTERVAL)
                else:
                    print("   ⏳ 失败，60s后重试...")
                    time.sleep(60)

        print(f"\n✅ 今日完成: {self.count}条")
        self.ctx.close()
        self.pw.stop()

    def cleanup(self):
        try:
            self.ctx.close()
            self.pw.stop()
        except: pass


if __name__ == "__main__":
    poster = XHSPoster()
    try:
        poster.run()
    except KeyboardInterrupt:
        print("\n👋 用户退出")
        poster.cleanup()
PYEOF

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   ✅ 安装完成！                               ║"
echo "╠══════════════════════════════════════════════╣"
echo "║                                              ║"
echo "║   下一步：                                    ║"
echo "║   1. 编辑脚本配置：                           ║"
echo "║      open -e ~/medislim_xhs/xhs_poster.py    ║"
echo "║   2. 把 SERVER_IP 改成服务器公网IP             ║"
echo "║   3. 运行发布：                               ║"
echo "║      python3 ~/medislim_xhs/xhs_poster.py     ║"
echo "║                                              ║"
echo "║   首次运行会弹出浏览器，扫码登录即可            ║"
echo "║                                              ║"
echo "╚══════════════════════════════════════════════╝"
