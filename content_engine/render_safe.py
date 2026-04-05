"""
稳健的逐套图片渲染器
每渲染一套就释放浏览器，避免OOM被杀
"""
import json
import gc
import time
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from card_renderer import render_full_set

CATALOG = Path(__file__).parent / "output" / "catalog.json"

def render_all():
    catalog = json.loads(CATALOG.read_text())
    
    # 找没有图片的条目
    to_render = [(i, c) for i, c in enumerate(catalog) 
                 if not c.get("card_paths") or c.get("status") == "copy_only"]
    
    total = len(to_render)
    print(f"🎨 待渲染: {total}套")
    
    done = 0
    errors = 0
    
    for idx, (cat_idx, entry) in enumerate(to_render):
        try:
            pid = entry["product_id"]
            palette = entry["palette_id"]
            copy = {
                "id": entry["id"],
                "product_id": pid,
                "product_name": entry.get("product_name", pid),
                "hook": entry["hook"],
                "body": entry["body"],
                "style": entry.get("style", ""),
                "hook_category": entry.get("hook_category", ""),
                "pain_point": entry.get("pain_point", ""),
                "benefit": entry.get("benefit", ""),
                "call_to_action": entry.get("call_to_action", ""),
                "scene": entry.get("scene", ""),
            }
            
            paths = render_full_set(copy, palette)
            catalog[cat_idx]["card_paths"] = paths
            catalog[cat_idx]["status"] = "rendered"
            done += 1
            
            # 每5套写一次catalog + GC
            if done % 5 == 0:
                CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2))
                gc.collect()
                print(f"  ⏳ {done}/{total} ({errors} errors) - 已保存", flush=True)
            
            # 每套之间等0.5秒让浏览器进程清理
            time.sleep(0.5)
            
        except Exception as e:
            errors += 1
            catalog[cat_idx]["status"] = f"error: {str(e)[:50]}"
            print(f"  ❌ [{idx}] {entry['product_id']}: {str(e)[:60]}", flush=True)
            gc.collect()
            time.sleep(1)
    
    # 最终保存
    CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2))
    
    # 统计
    rendered = sum(1 for c in catalog if c.get("status") == "rendered")
    total_imgs = sum(len(c.get("card_paths", [])) for c in catalog)
    print(f"\n✅ 完成!")
    print(f"   渲染成功: {rendered}/{total}")
    print(f"   图片总数: {total_imgs}")
    print(f"   错误: {errors}")

if __name__ == "__main__":
    render_all()
