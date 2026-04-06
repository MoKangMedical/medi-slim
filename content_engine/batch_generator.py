"""
MediSlim 小红书爆款内容批量生成器
文案 × 配色 × 图组 = 1000+套完整内容
"""
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime
from itertools import product as iterproduct

from copywriter import generate_all_copies, get_stats, PRODUCTS
from palettes import get_product_palettes, PALETTES
from card_renderer import render_hero_card, render_content_card, render_cta_card, render_full_set
from tracking import generate_tracking_links

OUTPUT_DIR = Path(__file__).parent / "output"
CATALOG_PATH = OUTPUT_DIR / "catalog.json"


def batch_generate(
    products=None,
    palettes_per_product=3,
    copies_per_combo=5,
    max_total=1000,
    render_cards=True,
):
    """
    批量生成内容

    参数:
        products: 品类列表，None=全部
        palettes_per_product: 每个品类使用几个配色
        copies_per_combo: 每个文案×配色组合生成几套图
        max_total: 最大生成总数
        render_cards: 是否渲染PNG（False则只生成文案数据）
    """
    if products is None:
        products = list(PRODUCTS.keys())

    print(f"🚀 开始批量生成小红书爆款内容")
    print(f"📦 品类: {', '.join(products)}")
    print(f"🎨 每品类配色数: {palettes_per_product}")
    print(f"📝 每组合文案数: {copies_per_combo}")
    print(f"🎯 最大总数: {max_total}")
    print(f"🖼️ 渲染PNG: {render_cards}")
    print("=" * 60)

    start_time = time.time()
    all_copies = generate_all_copies()
    catalog = []
    total_generated = 0

    for product_id in products:
        if total_generated >= max_total:
            break

        product_copies = [c for c in all_copies if c["product_id"] == product_id]
        palette_ids = get_product_palettes(product_id)[:palettes_per_product]

        print(f"\n📦 {PRODUCTS[product_id]['name']} ({product_id})")
        print(f"   文案库: {len(product_copies)} 条")
        print(f"   配色: {', '.join(palette_ids)}")

        for palette_id in palette_ids:
            if total_generated >= max_total:
                break

            # 从不同钩子类型和风格中采样
            sampled = _diverse_sample(product_copies, copies_per_combo)

            for copy in sampled:
                if total_generated >= max_total:
                    break

                entry = {
                    "id": f"{copy['id']}_{palette_id}",
                    "copy_id": copy["id"],
                    "product_id": product_id,
                    "palette_id": palette_id,
                    "hook": copy["hook"],
                    "hook_category": copy["hook_category"],
                    "style": copy["style"],
                    "body": copy["body"],
                    "call_to_action": copy["call_to_action"],
                    "pain_point": copy["pain_point"],
                    "benefit": copy["benefit"],
                    "generated_at": datetime.now().isoformat(),
                    "card_paths": [],
                }

                if render_cards:
                    try:
                        paths = render_full_set(copy, palette_id)
                        entry["card_paths"] = paths
                        entry["status"] = "rendered"
                    except Exception as e:
                        entry["status"] = f"error: {str(e)}"
                        print(f"   ❌ 渲染失败: {copy['id']}: {e}")
                else:
                    entry["status"] = "copy_only"

                # 生成追踪链接
                entry["tracking"] = generate_tracking_links(entry)

                catalog.append(entry)
                total_generated += 1

                # 每50条增量写入目录（防中断丢失）
                if total_generated % 50 == 0:
                    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
                        json.dump(catalog, f, ensure_ascii=False, indent=2)
                    elapsed = time.time() - start_time
                    rate = total_generated / elapsed
                    print(f"   ⏳ 进度: {total_generated}/{max_total} ({rate:.1f}条/秒)")

    # 保存目录
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"✅ 生成完成!")
    print(f"📊 总数: {total_generated}")
    print(f"⏱️ 耗时: {elapsed:.1f}秒")
    print(f"📁 目录: {OUTPUT_DIR}")
    print(f"📋 目录文件: {CATALOG_PATH}")

    # 统计
    _print_stats(catalog)

    return catalog


def _diverse_sample(copies, count):
    """从不同钩子类型和风格中均匀采样"""
    # 按钩子类型分组
    by_hook = {}
    for c in copies:
        cat = c["hook_category"]
        by_hook.setdefault(cat, []).append(c)

    # 按风格分组
    by_style = {}
    for c in copies:
        s = c["style"]
        by_style.setdefault(s, []).append(c)

    # 交替从不同组采样
    import random
    result = []
    categories = list(by_hook.keys())
    styles = list(by_style.keys())

    for i in range(count):
        # 轮换钩子类型和风格
        cat = categories[i % len(categories)]
        style = styles[i % len(styles)]
        # 找同时满足的
        pool = [c for c in copies if c["hook_category"] == cat and c["style"] == style]
        if pool:
            result.append(random.choice(pool))
        else:
            # fallback: 只按钩子类型
            pool2 = by_hook.get(cat, copies)
            result.append(random.choice(pool2))

    return result


def _print_stats(catalog):
    """打印生成统计"""
    by_product = {}
    by_palette = {}
    by_hook = {}
    by_style = {}
    by_status = {}

    for entry in catalog:
        by_product[entry["product_id"]] = by_product.get(entry["product_id"], 0) + 1
        by_palette[entry["palette_id"]] = by_palette.get(entry["palette_id"], 0) + 1
        by_hook[entry["hook_category"]] = by_hook.get(entry["hook_category"], 0) + 1
        by_style[entry["style"]] = by_style.get(entry["style"], 0) + 1
        by_status[entry["status"]] = by_status.get(entry["status"], 0) + 1

    print(f"\n📊 生成统计:")
    print(f"  按品类: {json.dumps(by_product, ensure_ascii=False)}")
    print(f"  按配色: {json.dumps(by_palette, ensure_ascii=False)}")
    print(f"  按钩子: {json.dumps(by_hook, ensure_ascii=False)}")
    print(f"  按风格: {json.dumps(by_style, ensure_ascii=False)}")
    print(f"  按状态: {json.dumps(by_status, ensure_ascii=False)}")


def quick_generate(product_id="glp1", palette_id="mint", count=3):
    """快速生成少量测试内容"""
    from copywriter import get_sample
    copies = get_sample(product_id, count=count)
    results = []
    for copy in copies:
        paths = render_full_set(copy, palette_id)
        results.append({
            "hook": copy["hook"],
            "style": copy["style"],
            "paths": paths,
        })
        print(f"✅ {copy['style']} | {copy['hook'][:40]}...")
    return results


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]

    if "--quick" in args:
        # 快速测试：每个品类1条
        print("⚡ 快速测试模式")
        quick_generate("glp1", "mint", 3)
    elif "--full" in args:
        # 全量生成：1000套
        batch_generate(max_total=1000, render_cards=True)
    else:
        # 默认：少量预览
        batch_generate(
            products=["glp1"],
            palettes_per_product=2,
            copies_per_combo=5,
            max_total=30,
            render_cards=True,
        )
