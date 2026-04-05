"""
MediSlim 小红书自动发布 — 调试版
每步都有输出，方便排查问题
用法：python3 xhs_poster_v2.py
"""
import os, sys, json, time, requests
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright

# ========== 配置 ==========
SERVER = "http://43.128.114.201:8099"
BROWSER_DATA = Path.home() / ".medislim_xhs_browser"
INTERVAL = 90
MAX_PER_DAY = 15

XHS_CREATOR = "https://creator.xiaohongshu.com/publish/publish"
XHS_LOGIN = "https://creator.xiaohongshu.com/login"


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def main():
    print("""
╔══════════════════════════════════════╗
║  MediSlim 小红书自动发布 v2          ║
║  Ctrl+C 退出                         ║
╚══════════════════════════════════════╝
    """)

    # Step 1: 测试服务器连接
    log("🔌 测试服务器连接...")
    try:
        r = requests.get(f"{SERVER}/api/queue-status", timeout=10)
        status = r.json()
        log(f"   ✅ 服务器OK: {status['pending']}条待发布")
    except Exception as e:
        log(f"   ❌ 连不上服务器: {e}")
        log(f"   请检查SERVER地址: {SERVER}")
        return

    # Step 2: 拉取队列
    log("📥 拉取发布队列...")
    try:
        r = requests.get(f"{SERVER}/api/post-queue", timeout=10)
        queue = r.json().get("queue", [])
        log(f"   ✅ 获取到 {len(queue)} 条内容")
        if not queue:
            log("   队列为空，退出")
            return
        for i, item in enumerate(queue):
            log(f"   [{i+1}] {item['product_id']} | {item['hook'][:30]}... | {item['image_count']}图")
    except Exception as e:
        log(f"   ❌ 拉取失败: {e}")
        return

    # Step 3: 启动浏览器
    log("🌐 启动浏览器...")
    pw = sync_playwright().start()
    BROWSER_DATA.mkdir(exist_ok=True)
    ctx = pw.chromium.launch_persistent_context(
        str(BROWSER_DATA), headless=False,
        viewport={"width": 1280, "height": 900}, locale="zh-CN",
    )
    page = ctx.new_page()
    log("   ✅ 浏览器已启动")

    # Step 4: 检查登录状态
    log("🔐 检查登录状态...")
    page.goto(XHS_CREATOR)
    page.wait_for_timeout(3000)
    
    if "login" in page.url:
        log("   需要登录，跳转到登录页...")
        page.goto(XHS_LOGIN)
        page.wait_for_timeout(2000)
        log("   请在浏览器窗口扫码登录！")
        log("   等待最多120秒...")
        
        for i in range(60):
            page.wait_for_timeout(2000)
            if "creator" in page.url and "login" not in page.url:
                log("   ✅ 登录成功！")
                break
            if i % 15 == 0:
                log(f"   等待中... ({i*2}s)")
        else:
            log("   ❌ 登录超时")
            ctx.close(); pw.stop(); return
    else:
        log("   ✅ 已登录")

    # Step 5: 逐条发布
    posted = 0
    for idx, item in enumerate(queue):
        if posted >= MAX_PER_DAY:
            log(f"📊 今日上限({MAX_PER_DAY})，停止")
            break

        hook = item.get("hook", "")[:30]
        product = item.get("product_id", "")
        item_id = item.get("id", "")
        log(f"\n📤 [{posted+1}/{MAX_PER_DAY}] 发布: {product} | {hook}...")

        # 5.1 进入发布页
        log("   → 打开发布页...")
        page.goto(XHS_CREATOR)
        page.wait_for_timeout(3000)

        # 截图看看当前状态
        page.screenshot(path=f"/tmp/xhs_debug_{idx}.png")
        log(f"   → 截图: /tmp/xhs_debug_{idx}.png")

        # 5.2 尝试切换到图文模式
        log("   → 尝试切换到图文模式...")
        try:
            # 尝试多种选择器
            selectors = [
                'div:has-text("上传图文")',
                'span:has-text("上传图文")',
                'text=上传图文',
                '[class*="tab"]:has-text("图文")',
            ]
            clicked = False
            for sel in selectors:
                try:
                    el = page.query_selector(sel)
                    if el:
                        el.click()
                        page.wait_for_timeout(1000)
                        log(f"   ✅ 已切换 (selector: {sel[:20]})")
                        clicked = True
                        break
                except:
                    continue
            
            if not clicked:
                # 打印所有可点击元素帮助调试
                elements = page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('*'))
                        .filter(e => e.textContent.trim().length > 0 && e.textContent.trim().length < 30)
                        .slice(0, 30)
                        .map(e => e.textContent.trim());
                }''')
                log(f"   页面文本: {elements[:10]}")
        except Exception as e:
            log(f"   ⚠️ 切换失败: {e}")

        # 5.3 上传图片
        log("   → 上传图片...")
        imgs = [p for p in item.get("image_paths", []) if os.path.exists(p) and p.endswith('.png')]
        if imgs:
            try:
                file_input = page.query_selector('input[type="file"]')
                if file_input:
                    file_input.set_input_files(imgs[:3])  # 先传3张
                    log(f"   ✅ 已选择 {len(imgs[:3])} 张图片，等待上传...")
                    page.wait_for_timeout(8000)
                else:
                    log("   ⚠️ 未找到文件上传控件")
            except Exception as e:
                log(f"   ❌ 上传失败: {e}")
        else:
            log("   ⚠️ 无可用图片")

        # 5.4 填写标题
        title = item.get("hook", "")[:20]
        log(f"   → 填写标题: {title}")
        try:
            title_el = page.query_selector('input[placeholder*="标题"]') or \
                       page.query_selector('[data-placeholder="添加标题"]')
            if title_el:
                title_el.click()
                title_el.fill(title)
                log("   ✅ 标题已填")
            else:
                log("   ⚠️ 未找到标题输入框")
        except Exception as e:
            log(f"   ❌ 标题填写失败: {e}")

        # 5.5 填写正文
        body = item.get("body", "")
        log(f"   → 填写正文 ({len(body)}字)...")
        try:
            editor = page.query_selector('[contenteditable="true"]')
            if editor:
                editor.click()
                editor.fill(body)
                log("   ✅ 正文已填")
            else:
                log("   ⚠️ 未找到正文编辑器")
        except Exception as e:
            log(f"   ❌ 正文填写失败: {e}")

        page.wait_for_timeout(1000)
        page.screenshot(path=f"/tmp/xhs_debug_{idx}_filled.png")
        log(f"   → 发布前截图: /tmp/xhs_debug_{idx}_filled.png")

        # 5.6 点击发布
        log("   → 点击发布...")
        try:
            pub_btn = page.query_selector('button:has-text("发布")')
            if pub_btn:
                pub_btn.click()
                page.wait_for_timeout(3000)
                log("   ✅ 已点击发布！")
                
                # 回传状态
                requests.post(f"{SERVER}/api/mark-posted", json={
                    "item_id": item_id,
                    "posted_at": datetime.now().isoformat(),
                }, timeout=5)
                posted += 1
                log(f"   📊 已发布: {posted}条")
            else:
                log("   ❌ 未找到发布按钮")
                page.screenshot(path=f"/tmp/xhs_debug_{idx}_nopub.png")
        except Exception as e:
            log(f"   ❌ 发布失败: {e}")
            requests.post(f"{SERVER}/api/mark-failed", json={
                "item_id": item_id, "reason": str(e),
            }, timeout=5)

        # 等待
        if posted < len(queue):
            log(f"   ⏳ 等待 {INTERVAL}秒...")
            time.sleep(INTERVAL)

    log(f"\n✅ 完成！本次发布 {posted} 条")
    ctx.close()
    pw.stop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 用户退出")
