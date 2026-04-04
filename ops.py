"""
MediSlim 商业运营系统
- 线索管理（leads）
- 跟进流程
- 数据统计
- 内容模板
"""
import json
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path("./data")
DATA_DIR.mkdir(exist_ok=True)

def load_db(name):
    f = DATA_DIR / f"{name}.json"
    return json.loads(f.read_text()) if f.exists() else {}

def save_db(name, data):
    (DATA_DIR / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))

# ========== 线索管理 ==========
class LeadManager:
    @staticmethod
    def get_all():
        return load_db("leads")
    
    @staticmethod
    def get_new():
        leads = load_db("leads")
        return [l for l in leads.values() if l.get("status") == "new"]
    
    @staticmethod
    def update_status(lead_id, status, note=""):
        leads = load_db("leads")
        if lead_id in leads:
            leads[lead_id]["status"] = status
            leads[lead_id]["follow_up"].append({
                "time": datetime.now().isoformat(),
                "status": status,
                "note": note,
            })
            save_db("leads", leads)
            return leads[lead_id]
        return None
    
    @staticmethod
    def daily_report():
        leads = load_db("leads").values()
        today = datetime.now().strftime("%Y-%m-%d")
        today_leads = [l for l in leads if l.get("created_at","")[:10] == today]
        
        by_product = {}
        for l in today_leads:
            p = l.get("product", "unknown")
            by_product[p] = by_product.get(p, 0) + 1
        
        return {
            "date": today,
            "total_leads": len(leads),
            "today_leads": len(today_leads),
            "new_leads": sum(1 for l in today_leads if l.get("status") == "new"),
            "contacted": sum(1 for l in today_leads if l.get("status") == "contacted"),
            "converted": sum(1 for l in today_leads if l.get("status") == "converted"),
            "by_product": by_product,
        }

# ========== 跟进流程 ==========
FOLLOW_UP_SCRIPTS = {
    "glp1": {
        "greeting": "您好！我是MediSlim的健康顾问，看到您对GLP-1减重方案感兴趣。请问方便聊几分钟吗？",
        "intro": "我们的GLP-1减重方案是医生指导下的科学减重方法。首月体验价¥399，包含：\n1. 执业医师在线评估\n2. 个性化用药方案\n3. 药品顺丰保密配送\n4. 24小时在线支持\n5. 每月体重管理报告",
        "close": "我现在就可以帮您安排AI健康评估，整个过程大概5分钟，您看可以吗？",
        "objection_1": "关于安全性：GLP-1是全球超过1亿人使用过的药物，副作用可控，我们的医师会在用药前进行禁忌症筛查。",
        "objection_2": "关于价格：首月399元，一杯奶茶的价格就能开始科学减重。不满意随时可以取消，没有合约绑定。",
    },
    "hair": {
        "greeting": "您好！我是MediSlim的健康顾问，看到您关注防脱生发方案。",
        "intro": "我们的防脱方案是：\n1. 毛囊检测评估\n2. 米诺地尔+非那雄胺组合\n3. 每月随访调整\n4. 生发效果跟踪\n\n首月体验价¥199",
        "close": "需要我帮您安排一个简单的脱发评估吗？",
    },
    "skin": {
        "greeting": "您好！我是MediSlim的健康顾问，看到您对皮肤管理感兴趣。",
        "intro": "我们的皮肤管理方案由皮肤科医生在线指导，针对痘痘/色斑/衰老等不同问题制定个性化方案。",
        "close": "方便发几张您的皮肤照片吗？我帮您初步评估一下。",
    },
}

# ========== 内容模板 ==========
CONTENT_TEMPLATES = {
    "xiaohongshu": [
        {
            "title": "🔥 3个月瘦了30斤！我的GLP-1减重日记",
            "content": "分享我的减重经历...\n#减肥 #GLP-1 #司美格鲁肽 #减重日记",
            "type": "experience",
        },
        {
            "title": "💊 司美格鲁肽到底安不安全？医生给你说实话",
            "content": "作为医生，今天给大家科普一下GLP-1...\n#科普 #减重 #健康",
            "type": "education",
        },
        {
            "title": "😭 脱发3年终于长回来了！我的生发方案",
            "content": "从M型发际线到现在...\n#脱发 #生发 #防脱",
            "type": "experience",
        },
    ],
    "douyin": [
        {
            "title": "医生不会告诉你的减重真相",
            "hook": "你知道吗？有一种方法可以让你不用节食就能瘦",
            "duration": "30s",
            "type": "hook",
        },
        {
            "title": "脱发的人一定要看！3个月长出新头发",
            "hook": "我从秃顶到满头浓发只用了3个月",
            "duration": "60s",
            "type": "hook",
        },
    ],
    "wechat_article": [
        {
            "title": "2026年最火的减重方式，竟然是打针？",
            "sections": ["引言", "什么是GLP-1", "安全性分析", "效果数据", "如何开始"],
            "cta": "扫码免费AI评估",
        },
    ],
}

# ========== 运营日历 ==========
def get_daily_tasks():
    """每日运营任务清单"""
    return {
        "morning": [
            "📊 查看昨日数据（leads/转化率）",
            "💬 回复夜间咨询",
            "📝 发布1条小红书笔记",
        ],
        "afternoon": [
            "📞 跟进新leads（30分钟内首次联系）",
            "📱 发布1条抖音短视频",
            "📊 更新运营数据表",
        ],
        "evening": [
            "💬 回复当日咨询",
            "📝 准备次日内容",
            "📊 整理当日leads",
            "🔄 复盘转化率",
        ],
    }

# ========== CLI ==========
if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    
    if cmd == "report":
        report = LeadManager.daily_report()
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif cmd == "leads":
        leads = LeadManager.get_all()
        for l in leads.values():
            print(f"  {'🆕' if l['status']=='new' else '📞'} {l['name']} | {l['phone']} | {l['product']} | {l['status']}")
    elif cmd == "tasks":
        tasks = get_daily_tasks()
        for period, items in tasks.items():
            print(f"\n{'🌅 上午' if period=='morning' else '☀️ 下午' if period=='afternoon' else '🌙 晚上'}:")
            for t in items:
                print(f"  {t}")
    elif cmd == "scripts":
        for product, scripts in FOLLOW_UP_SCRIPTS.items():
            print(f"\n{'🔥' if product=='glp1' else '💇' if product=='hair' else '🧴'} {product.upper()}:")
            print(f"  开场白: {scripts['greeting']}")
            print(f"  介绍: {scripts['intro'][:50]}...")
    else:
        print("""
MediSlim 运营系统
=================
python3 ops.py report   - 每日数据报告
python3 ops.py leads    - 查看所有线索
python3 ops.py tasks    - 今日运营任务
python3 ops.py scripts  - 跟进话术
        """)
