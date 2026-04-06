"""
MediSlim 小红书配图渲染引擎
HTML模板 + Playwright截图 = 高质量PNG
小红书标准尺寸：1080×1440（3:4竖版）
"""
import os
import json
from pathlib import Path
from palettes import get_palette, PALETTES, FONTS

# 小红书标准尺寸
CARD_WIDTH = 1080
CARD_HEIGHT = 1440

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def render_hero_card(copy, palette_id="mint", output_path=None):
    """
    渲染主图卡片（封面图）
    大字钩子 + 品类标识 + 配色
    """
    p = get_palette(palette_id)
    hook = copy["hook"]
    product_name = copy["product_name"]
    product_emoji = _get_emoji(copy["product_id"])
    style = copy["style"]

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:{CARD_WIDTH}px;height:{CARD_HEIGHT}px;background:{p['bg']};font-family:{FONTS['default']};overflow:hidden;position:relative}}
.gradient-bar{{position:absolute;top:0;left:0;right:0;height:12px;background:{p['gradient']}}}
.content{{padding:80px 60px;height:100%;display:flex;flex-direction:column;justify-content:center}}
.tag{{display:inline-block;background:{p['primary']};color:#fff;font-size:18px;padding:8px 24px;border-radius:30px;font-weight:600;margin-bottom:40px;letter-spacing:1px}}
.emoji-big{{font-size:80px;margin-bottom:30px}}
.hook{{font-size:48px;font-weight:800;color:{p['text']};line-height:1.4;margin-bottom:40px;letter-spacing:1px}}
.hook::first-line{{color:{p['primary']}}}
.divider{{width:80px;height:6px;background:{p['gradient']};border-radius:3px;margin-bottom:30px}}
.product-name{{font-size:28px;color:{p['text_sub']};font-weight:500;margin-bottom:20px}}
.style-badge{{display:inline-block;border:2px solid {p['primary']};color:{p['primary']};font-size:16px;padding:6px 18px;border-radius:20px;font-weight:500}}
.brand{{position:absolute;bottom:60px;left:60px;right:60px;display:flex;justify-content:space-between;align-items:center}}
.brand-name{{font-size:24px;font-weight:700;color:{p['primary']}}}
.brand-slogan{{font-size:16px;color:{p['text_sub']}}}
.watermark{{position:absolute;bottom:60px;right:60px;font-size:14px;color:{p['text_sub']};opacity:0.5}}
.corner-deco{{position:absolute;top:0;right:0;width:200px;height:200px;background:{p['gradient']};opacity:0.06;border-radius:0 0 0 200px}}
.corner-deco-2{{position:absolute;bottom:0;left:0;width:300px;height:300px;background:{p['gradient']};opacity:0.04;border-radius:0 300px 0 0}}
</style></head><body>
<div class="gradient-bar"></div>
<div class="corner-deco"></div>
<div class="corner-deco-2"></div>
<div class="content">
  <span class="tag">{product_emoji} {product_name}</span>
  <div class="emoji-big">{product_emoji}</div>
  <div class="hook">{hook}</div>
  <div class="divider"></div>
  <div class="product-name">MediSlim · AI驱动的消费医疗平台</div>
  <span class="style-badge">{style}</span>
</div>
<div class="brand">
  <div><div class="brand-name">MediSlim</div><div class="brand-slogan">AI健康管家 · 足不出户享受专业医疗</div></div>
</div>
</body></html>"""

    if output_path is None:
        output_path = OUTPUT_DIR / copy["product_id"] / f"hero_{copy['id']}_{palette_id}.png"

    return _html_to_png(html, output_path)


def render_content_card(copy, palette_id="mint", page=1, output_path=None):
    """
    渲染正文卡片（多页内容图）
    """
    p = get_palette(palette_id)
    body = copy["body"]
    product_emoji = _get_emoji(copy["product_id"])

    # 分段渲染
    paragraphs = [line.strip() for line in body.split("\n") if line.strip()]

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:{CARD_WIDTH}px;height:{CARD_HEIGHT}px;background:{p['bg']};font-family:{FONTS['default']};overflow:hidden;position:relative}}
.gradient-bar{{position:absolute;top:0;left:0;right:0;height:8px;background:{p['gradient']}}}
.content{{padding:60px 56px}}
.page-tag{{display:inline-block;background:{p['primary']};color:#fff;font-size:14px;padding:4px 14px;border-radius:15px;font-weight:600;margin-bottom:30px}}
.body-text{{font-size:26px;color:{p['text']};line-height:1.9;letter-spacing:0.5px}}
.body-text p{{margin-bottom:16px}}
.highlight{{color:{p['primary']};font-weight:600}}
.brand{{position:absolute;bottom:40px;left:56px;right:56px;text-align:center}}
.brand-line{{height:2px;background:{p['gradient']};margin-bottom:16px;border-radius:1px}}
.brand-text{{font-size:16px;color:{p['text_sub']};font-weight:500}}
</style></head><body>
<div class="gradient-bar"></div>
<div class="content">
  <span class="page-tag">{product_emoji} 第{page}页</span>
  <div class="body-text">
    {''.join(f'<p>{_format_line(line, p)}</p>' for line in paragraphs)}
  </div>
</div>
<div class="brand">
  <div class="brand-line"></div>
  <div class="brand-text">MediSlim · AI健康管家</div>
</div>
</body></html>"""

    if output_path is None:
        output_path = OUTPUT_DIR / copy["product_id"] / f"content_{copy['id']}_{palette_id}_p{page}.png"

    return _html_to_png(html, output_path)


def render_cta_card(copy, palette_id="mint", output_path=None):
    """
    渲染CTA引导卡片（最后一页，引导加微信/下单）
    """
    p = get_palette(palette_id)
    product_name = copy["product_name"]
    product_emoji = _get_emoji(copy["product_id"])
    benefit = copy["benefit"]
    price = _get_price(copy["product_id"])

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:{CARD_WIDTH}px;height:{CARD_HEIGHT}px;background:{p['bg']};font-family:{FONTS['default']};overflow:hidden;position:relative;display:flex;align-items:center;justify-content:center}}
.gradient-bar{{position:absolute;top:0;left:0;right:0;height:8px;background:{p['gradient']}}}
.card{{text-align:center;padding:80px 60px}}
.emoji{{font-size:100px;margin-bottom:30px}}
.title{{font-size:42px;font-weight:800;color:{p['text']};margin-bottom:20px;line-height:1.3}}
.title span{{color:{p['primary']}}}
.subtitle{{font-size:24px;color:{p['text_sub']};margin-bottom:50px;line-height:1.6}}
.benefits{{margin-bottom:50px}}
.benefit-item{{font-size:22px;color:{p['text']};margin-bottom:16px;display:flex;align-items:center;justify-content:center;gap:12px}}
.check{{color:{p['primary']};font-size:26px;font-weight:bold}}
.price-box{{background:{p['card_bg']};border:3px solid {p['primary']};border-radius:20px;padding:30px 40px;margin-bottom:40px;display:inline-block}}
.price-label{{font-size:18px;color:{p['text_sub']};margin-bottom:8px}}
.price{{font-size:56px;font-weight:800;color:{p['primary']}}}
.price span{{font-size:24px;font-weight:400}}
.cta{{background:{p['gradient']};color:#fff;font-size:28px;font-weight:700;padding:20px 60px;border-radius:50px;border:none;letter-spacing:2px;margin-bottom:30px}}
.trust{{font-size:16px;color:{p['text_sub']};margin-top:20px}}
.brand{{position:absolute;bottom:50px;left:0;right:0;text-align:center}}
.brand-text{{font-size:18px;color:{p['text_sub']};font-weight:600}}
</style></head><body>
<div class="gradient-bar"></div>
<div class="card">
  <div class="emoji">{product_emoji}</div>
  <div class="title">{product_name}<br><span>{benefit}</span></div>
  <div class="subtitle">专业医生在线评估，足不出户享受专业医疗</div>
  <div class="benefits">
    <div class="benefit-item"><span class="check">✓</span> 三甲医生在线评估</div>
    <div class="benefit-item"><span class="check">✓</span> 个性化治疗方案</div>
    <div class="benefit-item"><span class="check">✓</span> 药品直接寄到家</div>
    <div class="benefit-item"><span class="check">✓</span> 全程医生随访指导</div>
  </div>
  <div class="price-box">
    <div class="price-label">首月体验价</div>
    <div class="price">¥{price}<span>/月</span></div>
  </div>
  <br>
  <button class="cta">立即免费评估 →</button>
  <div class="trust">✅ 免费评估 · 不满意随时退 · 隐私保护</div>
</div>
<div class="brand">
  <div class="brand-text">MediSlim · AI健康管家</div>
</div>
</body></html>"""

    if output_path is None:
        output_path = OUTPUT_DIR / copy["product_id"] / f"cta_{copy['id']}_{palette_id}.png"

    return _html_to_png(html, output_path)


def render_full_set(copy, palette_id="mint"):
    """渲染完整图组：主图 + 正文 + CTA"""
    product_dir = OUTPUT_DIR / copy["product_id"]
    product_dir.mkdir(exist_ok=True)

    paths = []
    # 主图
    hero_path = render_hero_card(copy, palette_id)
    paths.append(hero_path)

    # 正文（分页）
    body_lines = [l.strip() for l in copy["body"].split("\n") if l.strip()]
    page_size = 12
    pages = [body_lines[i:i+page_size] for i in range(0, len(body_lines), page_size)]
    for i, page_lines in enumerate(pages):
        page_copy = dict(copy)
        page_copy["body"] = "\n".join(page_lines)
        p = render_content_card(page_copy, palette_id, i+1)
        paths.append(p)

    # CTA
    cta = render_cta_card(copy, palette_id)
    paths.append(cta)

    return paths


def _html_to_png(html, output_path):
    """Playwright截图"""
    from playwright.sync_api import sync_playwright

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 写临时HTML
    tmp_html = output_path.with_suffix(".html")
    tmp_html.write_text(html, encoding="utf-8")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": CARD_WIDTH, "height": CARD_HEIGHT},
            device_scale_factor=1,
        )
        page.goto(f"file://{tmp_html.resolve()}")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=str(output_path), type="png")
        browser.close()

    # 清理临时HTML
    tmp_html.unlink(missing_ok=True)
    return str(output_path)


def _get_emoji(product_id):
    emojis = {"glp1": "🔥", "hair": "💇", "skin": "🧴", "mens": "💪", "sleep": "😴"}
    return emojis.get(product_id, "💊")


def _get_price(product_id):
    prices = {"glp1": 399, "hair": 199, "skin": 299, "mens": 399, "sleep": 199}
    return prices.get(product_id, 299)


def _format_line(line, palette):
    """格式化正文行，高亮关键信息"""
    if line.startswith("✅"):
        return f'<span class="highlight">{line}</span>'
    if line.startswith("❌"):
        return f'<span style="color:#FF3B30">{line}</span>'
    if line.startswith("📊") or line.startswith("⏰") or line.startswith("🔍") or line.startswith("💡") or line.startswith("📝") or line.startswith("🏥"):
        return f'<span class="highlight" style="font-weight:700">{line}</span>'
    return line


if __name__ == "__main__":
    # 测试渲染
    from copywriter import get_sample
    test_copy = get_sample("glp1", "闺蜜体", 1)[0]
    print(f"测试文案: {test_copy['hook']}")
    paths = render_full_set(test_copy, "mint")
    print(f"生成文件: {paths}")
