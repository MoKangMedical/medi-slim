"""
MediSlim 小红书配色系统
8套配色方案 × 5个品类 = 40种视觉风格
"""

# ========== 主题配色方案 ==========
PALETTES = {
    "清新薄荷": {
        "id": "mint",
        "bg": "#F0FFF4",
        "primary": "#07C160",
        "secondary": "#06AD56",
        "accent": "#059B48",
        "text": "#1a1a1a",
        "text_sub": "#666666",
        "card_bg": "#FFFFFF",
        "gradient": "linear-gradient(135deg, #07C160 0%, #059B48 100%)",
        "mood": "健康、自然、清新",
    },
    "浪漫桃粉": {
        "id": "pink",
        "bg": "#FFF5F5",
        "primary": "#FF6B8A",
        "secondary": "#FF4D6D",
        "accent": "#E8384F",
        "text": "#2D1F2D",
        "text_sub": "#8C6B7A",
        "card_bg": "#FFFFFF",
        "gradient": "linear-gradient(135deg, #FF6B8A 0%, #FF4D6D 100%)",
        "mood": "温柔、女性化、亲切",
    },
    "高级灰蓝": {
        "id": "slate",
        "bg": "#F8FAFC",
        "primary": "#3B82F6",
        "secondary": "#2563EB",
        "accent": "#1D4ED8",
        "text": "#1E293B",
        "text_sub": "#64748B",
        "card_bg": "#FFFFFF",
        "gradient": "linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%)",
        "mood": "专业、可信赖、权威",
    },
    "暖阳橘橙": {
        "id": "sunset",
        "bg": "#FFFBEB",
        "primary": "#F59E0B",
        "secondary": "#D97706",
        "accent": "#B45309",
        "text": "#1C1917",
        "text_sub": "#78716C",
        "card_bg": "#FFFFFF",
        "gradient": "linear-gradient(135deg, #F59E0B 0%, #D97706 100%)",
        "mood": "活力、温暖、正能量",
    },
    "神秘暗夜": {
        "id": "dark",
        "bg": "#18181B",
        "primary": "#A78BFA",
        "secondary": "#8B5CF6",
        "accent": "#7C3AED",
        "text": "#F4F4F5",
        "text_sub": "#A1A1AA",
        "card_bg": "#27272A",
        "gradient": "linear-gradient(135deg, #A78BFA 0%, #7C3AED 100%)",
        "mood": "高级、酷、小众",
    },
    "法式奶油": {
        "id": "cream",
        "bg": "#FEFCE8",
        "primary": "#92400E",
        "secondary": "#78350F",
        "accent": "#451A03",
        "text": "#1C1917",
        "text_sub": "#57534E",
        "card_bg": "#FFFBEB",
        "gradient": "linear-gradient(135deg, #D97706 0%, #92400E 100%)",
        "mood": "高级感、法式、文艺",
    },
    "氧气蓝绿": {
        "id": "teal",
        "bg": "#F0FDFA",
        "primary": "#14B8A6",
        "secondary": "#0D9488",
        "accent": "#0F766E",
        "text": "#134E4A",
        "text_sub": "#5F9EA0",
        "card_bg": "#FFFFFF",
        "gradient": "linear-gradient(135deg, #14B8A6 0%, #0F766E 100%)",
        "mood": "清爽、专业医疗、信任",
    },
    "极简黑白": {
        "id": "mono",
        "bg": "#FAFAFA",
        "primary": "#18181B",
        "secondary": "#27272A",
        "accent": "#3F3F46",
        "text": "#18181B",
        "text_sub": "#71717A",
        "card_bg": "#FFFFFF",
        "gradient": "linear-gradient(135deg, #27272A 0%, #18181B 100%)",
        "mood": "极简、高级、克制",
    },
}

# ========== 品类推荐配色 ==========
PRODUCT_PALETTES = {
    "glp1": ["mint", "sunset", "slate", "teal", "dark", "mono", "pink", "cream"],
    "hair": ["pink", "cream", "dark", "mint", "slate", "teal", "sunset", "mono"],
    "skin": ["pink", "cream", "teal", "mint", "dark", "slate", "sunset", "mono"],
    "mens": ["slate", "dark", "teal", "mono", "mint", "sunset", "cream", "pink"],
    "sleep": ["teal", "dark", "slate", "mint", "cream", "pink", "sunset", "mono"],
}

# ========== 字体配置 ==========
FONTS = {
    "default": "'PingFang SC', 'Helvetica Neue', 'Microsoft YaHei', sans-serif",
    "title": "'PingFang SC', 'Noto Sans SC', sans-serif",
    "mono": "'SF Mono', 'Menlo', monospace",
}


def get_palette(palette_id):
    """获取配色方案"""
    return PALETTES.get(palette_id, PALETTES["清新薄荷"])


def get_product_palettes(product_id):
    """获取品类推荐配色列表"""
    return PRODUCT_PALETTES.get(product_id, list(PALETTES.keys()))


def get_all_combinations():
    """获取所有品类×配色组合"""
    combos = []
    for product_id, palette_ids in PRODUCT_PALETTES.items():
        for pid in palette_ids:
            combos.append({
                "product_id": product_id,
                "palette_id": pid,
                "palette": PALETTES[pid],
            })
    return combos


if __name__ == "__main__":
    print(f"🎨 配色方案数: {len(PALETTES)}")
    print(f"📦 品类数: {len(PRODUCT_PALETTES)}")
    total = sum(len(v) for v in PRODUCT_PALETTES.values())
    print(f"🔗 品类×配色组合: {total}")
    for name, p in PALETTES.items():
        print(f"  {name} ({p['id']}): {p['gradient'][:40]}... | {p['mood']}")
