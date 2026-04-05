"""
MediSlim 小红书爆款文案引擎
钩子公式 × 品类 × 风格 = 1000+ 变体自动组合
零依赖，纯Python
"""
import json
import random
import hashlib
from itertools import product as iterproduct

# ========== 产品数据 ==========
PRODUCTS = {
    "glp1": {
        "name": "GLP-1科学减重",
        "emoji": "🔥",
        "pain": ["节食反弹", "越减越肥", "喝水都胖", "运动没效果", "减不下来"],
        "benefit": ["7天瘦3斤", "不挨饿不反弹", "躺着也能瘦", "医生方案安全有效", "BMI回归正常"],
        "scene": ["体检被说超重", "衣服越来越紧", "爬楼梯气喘", "拍照不敢露全身", "前任婚礼在即"],
        "trust": ["三甲医生在线评估", "司美格鲁肽/替尔泊肽", "已帮助10万+用户", "不满意随时退"],
        "price_hook": "首月仅¥399",
        "target": "想减肥但没时间的人",
    },
    "hair": {
        "name": "防脱生发",
        "emoji": "💇",
        "pain": ["发际线后移", "洗头掉一把", "头顶越来越稀", "年纪轻轻秃了", "不敢梳头"],
        "benefit": ["28天见新发", "发缝变窄了", "洗头不再堵下水道", "发量回来了", "终于敢扎马尾"],
        "scene": ["被同事说秃了", "风吹头皮凉", "自拍要P发际线", "相亲被嫌老", "枕头上全是头发"],
        "trust": ["皮肤科医生处方", "FDA认证药物", "毛囊检测精准评估", "30天无效退款"],
        "price_hook": "首月仅¥199",
        "target": "脱发焦虑的年轻人",
    },
    "skin": {
        "name": "皮肤管理",
        "emoji": "🧴",
        "pain": ["痘痘反复长", "毛孔粗到能种田", "色斑越来越深", "皮肤暗沉发黄", "敏感泛红"],
        "benefit": ["14天肉眼可见改善", "素颜也敢出门", "皮肤嫩到发光", "同事以为我打了水光", "告别滤镜"],
        "scene": ["合照永远最丑", "粉底遮不住瑕疵", "相亲前紧急护肤", "被叫阿姨/叔叔", "护肤品用了一堆没效果"],
        "trust": ["皮肤科医生在线诊断", "个性化方案非千人一方", "药物+护肤联合方案", "定期随访调整"],
        "price_hook": "首月仅¥299",
        "target": "皮肤困扰的精致人群",
    },
    "mens": {
        "name": "男性健康",
        "emoji": "💪",
        "pain": ["精力不够用", "体力大不如前", "工作到下午就萎", "那方面力不从心", "体检指标飘红"],
        "benefit": ["精力充沛一整天", "重回巅峰状态", "工作效率翻倍", "夫妻关系改善", "体检指标变好"],
        "scene": ["加班后回家倒头就睡", "被老婆嫌弃", "体检报告一堆箭头", "爬两层楼就喘", "开会走神"],
        "trust": ["泌尿外科/内分泌医生", "隐私保护全程加密", "药品隐私包装配送", "检验建议+用药指导"],
        "price_hook": "首月仅¥399",
        "target": "中年危机男性",
    },
    "sleep": {
        "name": "助眠调理",
        "emoji": "😴",
        "pain": ["翻来覆去睡不着", "凌晨3点还醒着", "白天困晚上精神", "睡眠浅容易醒", "安眠药不敢吃"],
        "benefit": ["躺下15分钟入睡", "一觉到天亮", "白天精力充沛", "不吃安眠药也能睡好", "告别数羊"],
        "scene": ["第二天有重要会议", "越想睡越清醒", "刷手机到凌晨", "室友打呼被吵醒", "长期靠褪黑素"],
        "trust": ["睡眠医学专科医生", "行为+药物联合方案", "睡眠日记精准追踪", "不依赖药物方案"],
        "price_hook": "首月仅¥199",
        "target": "失眠焦虑的打工人",
    },
}

# ========== 钩子公式（小红书爆款开头）==========
HOOK_FORMULAS = [
    # 焦虑型
    "姐妹们！{pain}的救星来了！",
    "千万别再{pain}了！我的血泪教训😭",
    "{pain}？！看完这篇你就懂了",
    "救命！{pain}终于有救了😱",
    "谁懂啊！{pain}太难受了",
    "如果你也{pain}，请一定要看完",
    "被{pain}折磨了X年，终于找到解法",
    "别再交智商税了！{pain}这样做才对",
    "{pain}的姐妹看过来👀这篇超有用",
    "停！别再{pain}了！试试这个方法",
    # 好奇型
    "我试了X天后，{benefit}！",
    "偷偷告诉你，{benefit}的秘密",
    "没想到{benefit}这么简单！",
    "闺蜜问我怎么{benefit}的",
    "同事以为我{benefit}，其实我只做了这一件事",
    "这个方法让我{benefit}，姐妹们冲！",
    "坚持了X天，{benefit}！效果惊了",
    "原来{benefit}的关键是这个！",
    "不节食不运动，居然{benefit}！",
    "医生朋友推荐的方法，{benefit}！",
    # 干货型
    "3个方法帮你解决{pain}",
    "亲测有效！{benefit}的完整攻略",
    "X年{pain}总结出的经验，全在这了",
    "医生教我的方法，{benefit}不反弹",
    "从{pain}到{benefit}，我只用了X天",
    "手把手教你{benefit}，小白也能学会",
    "这份{benefit}指南，建议收藏⭐",
    "专业医生科普：{pain}的真正原因",
    "不想{pain}？这X件事一定要做",
    "科学证明：{benefit}其实不难",
    # 种草型
    "安利一个让我{benefit}的宝藏",
    "后悔没早点发现！{benefit}太香了",
    "用过的都说好！{benefit}神器",
    "被种草了！{benefit}真的有用",
    "姐妹安利的{benefit}方法，绝了！",
    "这个{benefit}方案也太靠谱了吧",
    "不允许还有人不知道！{benefit}秘籍",
    "吹爆这个{benefit}方法！效果炸裂",
    "全网都在推的{benefit}方案，试了才知道",
    "朋友推荐的{benefit}方法，后悔没早试",
    # 励志型
    "从{pain}到自信，我的蜕变日记",
    "记录一下{benefit}的过程💪",
    "自律X天后，{benefit}！",
    "我的{benefit}故事，希望能帮到你",
    "坚持就是胜利！{benefit}全记录",
    "曾经{pain}，现在{benefit}✨",
    "X天逆袭！{benefit}真实经历",
    "给自己一个改变的机会，{benefit}",
    "不将就的人生，从{benefit}开始",
    "记录我的{benefit}之路，加油！",
    # 反转型
    "之前{pain}，现在{benefit}！就因为做了这件事",
    "差点放弃的时候发现了这个，{benefit}！",
    "试了无数方法都没用，直到遇到它——{benefit}",
    "从{pain}到{benefit}，只差这一步",
    "所有人都说我没救了，直到{benefit}",
    "被骗了X年！真正{benefit}的方法是这个",
    "走了X年弯路，终于{benefit}了",
    "后悔没早知道！{benefit}原来这么简单",
    "被坑了无数次，终于找到{benefit}的正解",
    "停！别再乱试了！{benefit}只需要这一招",
]

# ========== 语言风格 ==========
STYLES = {
    "闺蜜体": {
        "tone": "亲切、口语化、像闺蜜聊天",
        "particles": ["姐妹！", "宝子们~", "真的绝了！", "超好用！", "爱了爱了！"],
        "emoji_density": "high",
        "example_end": "姐妹们冲就完了！🏃‍♀️",
    },
    "专业体": {
        "tone": "医学专业、数据说话、权威可信",
        "particles": ["研究表明", "临床数据显示", "医生建议", "科学方案"],
        "emoji_density": "low",
        "example_end": "科学减重，从了解自己开始。",
    },
    "种草体": {
        "tone": "安利推荐、真实体验、对比明显",
        "particles": ["安利！", "强推！", "回购N次", "闭眼入", "yyds"],
        "emoji_density": "medium",
        "example_end": "姐妹们闭眼入就对了！💕",
    },
    "焦虑体": {
        "tone": "制造紧迫感、FOMO、痛点放大",
        "particles": ["别再拖了！", "再不行动就晚了！", "你还在等什么？"],
        "emoji_density": "high",
        "example_end": "别再犹豫了，行动起来！⚡",
    },
    "励志体": {
        "tone": "正能量、蜕变、自律打卡",
        "particles": ["加油💪", "冲！", "自律即自由", "遇见更好的自己"],
        "emoji_density": "medium",
        "example_end": "每天进步一点点，遇见更好的自己✨",
    },
    "故事体": {
        "tone": "第一人称叙事、时间线、情感起伏",
        "particles": ["说实话", "一开始我也不信", "直到…", "结果让我震惊"],
        "emoji_density": "medium",
        "example_end": "如果你也有同样的困扰，可以试试看。",
    },
}

# ========== 正文模板 ==========
BODY_TEMPLATES = [
    # 干货型正文
    """📝 我的情况：
{scene}，{pain}已经好几年了。

🔍 尝试过的方法：
❌ 节食 → 坚持不了几天就暴食
❌ 运动 → 太忙根本没时间
❌ 网红产品 → 交了一堆智商税

✅ 真正有效的方法：
后来经朋友推荐，尝试了MediSlim的{benefit}方案。

整个过程很简单：
1️⃣ 在线填写评估问卷
2️⃣ 医生根据我的情况定制方案
3️⃣ 药品直接寄到家
4️⃣ 全程有医生指导和随访

💡 效果：
{benefit}！而且完全没有{pain}的困扰了。

{price_hook}就能开始，姐妹们冲！🏃‍♀️""",

    # 对比型正文
    """⏰ 时间线记录：

Day 1：{scene}，抱着试试看的心态开始
Day 7：有点感觉了，{benefit_short}
Day 14：明显变化！{benefit}
Day 28：效果稳定，整个人都不一样了

📊 关键数据：
• 之前：{pain}
• 现在：{benefit}

为什么选MediSlim？
✅ {trust[0]}
✅ {trust[1]}
✅ 全程线上，不用跑医院
✅ {price_hook}

有问题评论区问我～💬""",

    # 种草型正文
    """姐妹们我真的要安利这个！！

之前{scene}，{pain}困扰了我好久。

各种方法都试过了，差点就放弃了…

直到发现了MediSlim的{name}方案！

整个体验：
🌟 医生在线评估，不用排队挂号
🌟 方案完全个性化，不是千人一方
🌟 药品快递到家，超方便
🌟 价格：{price_hook}！性价比绝了

关键是真的有效！{benefit}

💡 适合人群：
{target}

有同款困扰的姐妹可以去看看～
评论区告诉我你们的情况！👇""",

    # 医生科普型正文
    """🏥 医学科普时间

关于{pain}，很多人存在误区：

❌ 误区一：{pain}只能靠意志力
→ 错！这可能涉及代谢/激素等生理因素

❌ 误区二：随便买点药吃就行
→ 错！需要专业评估+个性化方案

❌ 误区三：{pain}不影响健康
→ 错！长期可能引发更多问题

✅ 正确做法：
1. 先做专业评估（了解根本原因）
2. 医生制定个性化方案
3. 定期随访调整
4. 药物+行为联合干预

MediSlim就是按这个流程来的：
• {trust[0]}
• {trust[1]}
• {trust[2]}

{price_hook}，建议有{pain}困扰的朋友先做个评估。
评估是免费的，不亏。""",

    # 痛点放大+解决方案
    """💀 {pain}的痛苦谁懂啊！！

{scene}的时候真的太尴尬了…

以前总觉得{pain}是小事，忍忍就过去了。

直到有一天{scene}，我才意识到真的要重视了。

🏥 去医院：排队2小时，看诊5分钟
💊 买药：不知道该买啥，药店瞎推荐
📱 网上查：各种说法矛盾，越查越焦虑

直到朋友推荐了MediSlim 👇

✅ 线上评估 → 医生1v1方案
✅ 不用出门 → 药品送到家
✅ 全程指导 → 不是买了药就没人管
✅ {price_hook}

现在的我：{benefit}！
真心推荐给有同款困扰的姐妹 ❤️""",
]


def generate_all_copies():
    """生成所有文案组合（1000+变体）"""
    copies = []
    for product_id, product in PRODUCTS.items():
        for hook_idx, hook in enumerate(HOOK_FORMULAS):
            for style_name, style in STYLES.items():
                for body_idx, body_template in enumerate(BODY_TEMPLATES):
                    # 填充钩子
                    pain = random.choice(product["pain"])
                    benefit = random.choice(product["benefit"])
                    scene = random.choice(product["scene"])

                    filled_hook = hook.format(pain=pain, benefit=benefit)

                    # 填充正文
                    try:
                        filled_body = body_template.format(
                            name=product["name"],
                            pain=pain,
                            benefit=benefit,
                            benefit_short=benefit.split('，')[0] if '，' in benefit else benefit,
                            scene=scene,
                            trust=product["trust"],
                            price_hook=product["price_hook"],
                            target=product["target"],
                        )
                    except (KeyError, IndexError):
                        filled_body = body_template.replace("{name}", product["name"]) \
                            .replace("{pain}", pain) \
                            .replace("{benefit_short}", benefit.split('，')[0] if '，' in benefit else benefit) \
                            .replace("{benefit}", benefit) \
                            .replace("{scene}", scene) \
                            .replace("{price_hook}", product["price_hook"]) \
                            .replace("{target}", product["target"])
                        for i, t in enumerate(product["trust"]):
                            filled_body = filled_body.replace(f"{{trust[{i}]}}", t)

                    # 生成唯一ID
                    raw = f"{product_id}_{hook_idx}_{style_name}_{body_idx}"
                    copy_id = hashlib.md5(raw.encode()).hexdigest()[:10]

                    copy = {
                        "id": copy_id,
                        "product_id": product_id,
                        "product_name": product["name"],
                        "hook": filled_hook,
                        "body": filled_body,
                        "style": style_name,
                        "style_tone": style["tone"],
                        "call_to_action": style["example_end"],
                        "pain_point": pain,
                        "benefit": benefit,
                        "scene": scene,
                        "hook_category": _get_hook_category(hook_idx),
                    }
                    copies.append(copy)

    return copies


def _get_hook_category(idx):
    if idx < 10: return "焦虑型"
    if idx < 20: return "好奇型"
    if idx < 30: return "干货型"
    if idx < 40: return "种草型"
    if idx < 50: return "励志型"
    return "反转型"


def get_sample(product_id=None, style=None, count=5):
    """获取指定条件的样本文案"""
    all_copies = generate_all_copies()
    filtered = all_copies
    if product_id:
        filtered = [c for c in filtered if c["product_id"] == product_id]
    if style:
        filtered = [c for c in filtered if c["style"] == style]
    return random.sample(filtered, min(count, len(filtered)))


def get_stats():
    """生成统计信息"""
    all_copies = generate_all_copies()
    stats = {
        "total": len(all_copies),
        "by_product": {},
        "by_style": {},
        "by_hook_category": {},
    }
    for c in all_copies:
        pid = c["product_id"]
        stats["by_product"][pid] = stats["by_product"].get(pid, 0) + 1
        s = c["style"]
        stats["by_style"][s] = stats["by_style"].get(s, 0) + 1
        h = c["hook_category"]
        stats["by_hook_category"][h] = stats["by_hook_category"].get(h, 0) + 1
    return stats


if __name__ == "__main__":
    stats = get_stats()
    print(f"📊 文案引擎总变体数: {stats['total']}")
    print(f"\n按品类分布:")
    for k, v in stats["by_product"].items():
        print(f"  {k}: {v} 条")
    print(f"\n按风格分布:")
    for k, v in stats["by_style"].items():
        print(f"  {k}: {v} 条")
    print(f"\n按钩子类型分布:")
    for k, v in stats["by_hook_category"].items():
        print(f"  {k}: {v} 条")

    print("\n--- 样本文案 (GLP-1 × 闺蜜体) ---")
    samples = get_sample("glp1", "闺蜜体", 2)
    for s in samples:
        print(f"\n【{s['hook_category']}】{s['hook']}")
        print(f"风格: {s['style']} | ID: {s['id']}")
        print(s["body"][:200] + "...")
        print("---")
