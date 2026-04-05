"""
MediSlim 小红书本地发布代理
在你电脑上运行，用本机IP登录小红书，自动发布内容
依赖：pip install playwright requests
用法：python3 xhs_poster.py

流程：
  1. 启动 → 打开小红书 → 扫码登录（首次）
  2. 从服务器拉取待发布内容
  3. 自动填写标题/正文/上传图片
  4. 发布 → 回传状态到服务器
  5. 循环直到队列清空
"""
import os
import sys
import json
import time
import hashlib
import requests
from pathlib import Path
from datetime import datetime

# ========== 配置 ==========
SERVER_URL = os.environ.get("MEDISLIM_SERVER", "http://YOUR_SERVER_IP:8096")
BROWSER_DATA_DIR = Path.home() / ".medislim_xhs_browser"
POST_INTERVAL = 60  # 两条发布间隔（秒），防封
MAX_POSTS_PER_DAY = 20  # 每天上限

# 小红书创作平台URL
XHS_CREATOR = "https://creator.xiaohongshu.com/publish/publish"
XHS_LOGIN = "https://creator.xiaohongshu.com/login"


class XHSPoster:
    def __init__(self, headless=False):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.pw = None
        self.posted_today = 0

    def start(self):
        """启动浏览器"""
        from playwright.sync_api import sync_playwright
        self.pw = sync_playwright().start()

        BROWSER_DATA_DIR.mkdir(exist_ok=True)
        self.context = self.pw.chromium.launch_persistent_context(
            str(BROWSER_DATA_DIR),
            headless=self.headless,
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/131.0.0.0 Safari/537.36",
        )
        self.page = self.context.new_page()
        print("✅ 浏览器已启动")

    def ensure_login(self):
        """确保已登录小红书"""
        self.page.goto(XHS_CREATOR)
        self.page.wait_for_timeout(3000)

        # 检查是否需要登录
        if "login" in self.page.url or "creator" not in self.page.url:
            print("\n" + "=" * 50)
            print("🔐 需要扫码登录小红书")
            print("   请在弹出的浏览器窗口中用手机小红书扫码")
            print("=" * 50)

            self.page.goto(XHS_LOGIN)
            self.page.wait_for_timeout(2000)

            # 等待登录成功（最多120秒）
            for i in range(60):
                self.page.wait_for_timeout(2000)
                if "creator" in self.page.url and "login" not in self.page.url:
                    print("✅ 登录成功！")
                    return True
                if i % 10 == 0:
                    print(f"   等待登录中... ({i*2}s)")

            print("❌ 登录超时，请重试")
            return False
        else:
            print("✅ 已登录状态")
            return True

    def fetch_queue(self):
        """从服务器拉取待发布队列"""
        try:
            resp = requests.get(f"{SERVER_URL}/api/post-queue", timeout=10)
            if resp.status_code == 200:
                return resp.json().get("queue", [])
        except Exception as e:
            print(f"⚠️ 拉取队列失败: {e}")
        return []

    def post_content(self, item):
        """发布一条内容到小红书"""
        try:
            # 进入发布页
            self.page.goto(XHS_CREATOR)
            self.page.wait_for_timeout(2000)

            # 选择上传图文
            upload_tab = self.page.query_selector('text=上传图文')
            if upload_tab:
                upload_tab.click()
                self.page.wait_for_timeout(1000)

            # 上传图片
            image_paths = item.get("image_paths", [])
            if image_paths:
                # 找到文件上传input
                file_input = self.page.query_selector('input[type="file"]')
                if file_input:
                    # Playwright支持多文件上传
                    existing = [p for p in image_paths if os.path.exists(p)]
                    if existing:
                        file_input.set_input_files(existing)
                        print(f"   📸 上传 {len(existing)} 张图片")
                        self.page.wait_for_timeout(5000)  # 等待上传

            # 填写标题（取钩子前20字）
            title = item.get("hook", "")[:20]
            title_input = self.page.query_selector('input[placeholder*="标题"]') or \
                          self.page.query_selector('#title') or \
                          self.page.query_selector('[data-placeholder="添加标题"]')
            if title_input:
                title_input.click()
                title_input.fill(title)
                print(f"   📝 标题: {title}")

            # 填写正文
            body = item.get("body", "")
            body_editor = self.page.query_selector('[contenteditable="true"]') or \
                          self.page.query_selector('textarea') or \
                          self.page.query_selector('#content')
            if body_editor:
                body_editor.click()
                body_editor.fill(body)
                print(f"   📝 正文: {len(body)}字")

            # 添加话题标签
            tags = item.get("tags", ["#MediSlim", "#AI健康"])
            # 标签通常在正文末尾添加

            self.page.wait_for_timeout(1000)

            # 点击发布
            publish_btn = self.page.query_selector('button:has-text("发布")') or \
                          self.page.query_selector('text=发布')
            if publish_btn:
                publish_btn.click()
                self.page.wait_for_timeout(3000)
                print(f"   ✅ 已发布!")
                return True
            else:
                print(f"   ❌ 未找到发布按钮")
                # 截图以便调试
                self.page.screenshot(path="/tmp/xhs_debug.png")
                return False

        except Exception as e:
            print(f"   ❌ 发布异常: {e}")
            return False

    def mark_posted(self, item_id):
        """通知服务器已发布"""
        try:
            requests.post(f"{SERVER_URL}/api/mark-posted", json={
                "item_id": item_id,
                "posted_at": datetime.now().isoformat(),
            }, timeout=5)
        except:
            pass

    def run(self):
        """主循环"""
        print("""
╔══════════════════════════════════════════════╗
║   MediSlim 小红书自动发布代理                 ║
║   用本机IP自动发布，绕过服务器风控              ║
╚══════════════════════════════════════════════╝
        """)

        self.start()

        if not self.ensure_login():
            print("❌ 登录失败，退出")
            return

        print(f"\n🚀 开始拉取发布队列...")
        print(f"   服务器: {SERVER_URL}")
        print(f"   每日上限: {MAX_POSTS_PER_DAY}条")
        print(f"   发布间隔: {POST_INTERVAL}秒")

        while self.posted_today < MAX_POSTS_PER_DAY:
            queue = self.fetch_queue()

            if not queue:
                print(f"\n📭 队列为空，{POST_INTERVAL}秒后重试...")
                time.sleep(POST_INTERVAL)
                continue

            for item in queue:
                if self.posted_today >= MAX_POSTS_PER_DAY:
                    print("📊 今日已达上限，停止发布")
                    break

                item_id = item.get("id", "unknown")
                hook = item.get("hook", "")[:40]
                product = item.get("product_id", "")

                print(f"\n📤 [{self.posted_today + 1}/{MAX_POSTS_PER_DAY}] 发布中...")
                print(f"   品类: {product} | 钩子: {hook}...")

                success = self.post_content(item)

                if success:
                    self.mark_posted(item_id)
                    self.posted_today += 1
                    print(f"   ⏳ 等待 {POST_INTERVAL}秒 后发布下一条...")
                    time.sleep(POST_INTERVAL)
                else:
                    print(f"   ⚠️ 发布失败，跳过，60秒后重试...")
                    time.sleep(60)

        print(f"\n✅ 今日发布完成: {self.posted_today}条")
        self.cleanup()

    def cleanup(self):
        if self.context:
            self.context.close()
        if self.pw:
            self.pw.stop()


def main():
    headless = "--headless" in sys.argv
    poster = XHSPoster(headless=headless)
    poster.run()


if __name__ == "__main__":
    main()
