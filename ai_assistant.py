"""
MediSlim v5.0 — AI驱动消费医疗平台
核心升级：AI健康助手 + 个性化推荐 + 智能客服 + 数据分析
"""
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class UserProfile:
    """用户档案"""
    user_id: str
    nickname: str
    age: int
    gender: str
    constitution_type: str  # 九种体质
    health_goals: List[str]
    purchase_history: List[Dict] = field(default_factory=list)
    ai_recommendations: List[Dict] = field(default_factory=list)


@dataclass
class Product:
    """产品"""
    product_id: str
    name: str
    category: str  # prescription / tcm / supplement
    subcategory: str
    price_first_month: float
    price_monthly: float
    target_constitutions: List[str]
    description: str
    ingredients: List[str] = field(default_factory=list)
    ai_score: float = 0.0


class AIHealthAssistant:
    """AI健康助手 v5.0"""

    # 九种体质
    CONSTITUTIONS = {
        "气虚": {"特征": "易疲劳、气短", "推荐": ["补气", "健脾"]},
        "阳虚": {"特征": "怕冷、手脚凉", "推荐": ["温阳", "补肾"]},
        "阴虚": {"特征": "手足心热、口干", "推荐": ["滋阴", "润燥"]},
        "痰湿": {"特征": "体胖、痰多", "推荐": ["祛湿", "化痰"]},
        "湿热": {"特征": "口苦、大便粘", "推荐": ["清热", "利湿"]},
        "血瘀": {"特征": "面色暗、易瘀伤", "推荐": ["活血", "化瘀"]},
        "气郁": {"特征": "情绪低落、胸闷", "推荐": ["疏肝", "理气"]},
        "特禀": {"特征": "过敏体质", "推荐": ["抗敏", "调理"]},
        "平和": {"特征": "体质平衡", "推荐": ["养生", "保健"]},
    }

    # 产品库
    PRODUCTS = {
        "glp1": Product(
            "GLP1-001", "GLP-1减重方案", "prescription", "减重",
            399, 599, ["痰湿", "湿热"],
            "司美格鲁肽/替尔泊肽，GLP-1受体激动剂",
            ["司美格鲁肽", "替尔泊肽"]
        ),
        "hair": Product(
            "HAIR-001", "防脱生发方案", "prescription", "防脱",
            199, 299, ["气虚", "血瘀"],
            "米诺地尔+非那雄胺，促进毛发生长",
            ["米诺地尔", "非那雄胺"]
        ),
        "skin": Product(
            "SKIN-001", "皮肤管理方案", "prescription", "护肤",
            299, 399, ["湿热", "阴虚"],
            "祛痘/美白/抗衰三合一方案",
            ["维A酸", "烟酰胺", "透明质酸"]
        ),
        "male": Product(
            "MALE-001", "男性健康方案", "prescription", "男性",
            399, 599, ["阳虚", "气虚"],
            "精力/睾酮管理方案",
            ["睾酮补充剂", "复合维生素"]
        ),
        "sleep": Product(
            "SLEEP-001", "助眠调理方案", "prescription", "助眠",
            199, 299, ["阴虚", "气郁"],
            "失眠/褪黑素调理方案",
            ["褪黑素", "酸枣仁"]
        ),
    }

    def __init__(self):
        self.users: Dict[str, UserProfile] = {}
        self.recommendations: List[Dict] = []

    def assess_constitution(self, answers) -> Dict:
        """AI体质评估"""
        # 根据答案计算体质得分
        scores = {k: 0 for k in self.CONSTITUTIONS}
        
        # 支持dict和list两种输入
        if isinstance(answers, dict):
            for q, a in answers.items():
                if a == "是":
                    # 简化计分逻辑
                    if "疲劳" in q or "气短" in q:
                        scores["气虚"] += 1
                    if "怕冷" in q or "手脚凉" in q:
                        scores["阳虚"] += 1
                    if "口干" in q or "手足心热" in q:
                        scores["阴虚"] += 1
                    if "体胖" in q or "痰多" in q:
                        scores["痰湿"] += 1
        elif isinstance(answers, list):
            # 根据健康目标推断体质
            for goal in answers:
                if "减重" in goal or "肥胖" in goal:
                    scores["痰湿"] += 2
                if "精力" in goal or "疲劳" in goal:
                    scores["气虚"] += 2
                if "脱发" in goal:
                    scores["血瘀"] += 1
                if "助眠" in goal or "失眠" in goal:
                    scores["阴虚"] += 1
        
        # 找出得分最高的体质
        main_type = max(scores, key=scores.get)
        
        return {
            "main_type": main_type,
            "characteristics": self.CONSTITUTIONS[main_type]["特征"],
            "recommendations": self.CONSTITUTIONS[main_type]["推荐"],
            "scores": scores,
        }

    def recommend_products(self, constitution: str, 
                          goals: List[str]) -> List[Dict]:
        """AI个性化产品推荐"""
        recommendations = []
        
        for pid, product in self.PRODUCTS.items():
            score = 0
            
            # 体质匹配
            if constitution in product.target_constitutions:
                score += 50
            
            # 目标匹配
            for goal in goals:
                if goal in product.subcategory or goal in product.description:
                    score += 30
            
            # 添加随机因子模拟AI
            score += 10
            
            if score > 40:
                product.ai_score = score
                recommendations.append({
                    "product_id": product.product_id,
                    "name": product.name,
                    "category": product.category,
                    "price_first_month": product.price_first_month,
                    "ai_score": score,
                    "reason": f"匹配{constitution}体质，适合您的需求",
                })
        
        # 按分数排序
        recommendations.sort(key=lambda x: x["ai_score"], reverse=True)
        return recommendations[:3]

    def generate_health_plan(self, user: UserProfile) -> Dict:
        """生成AI健康方案"""
        # 体质评估
        constitution_data = self.assess_constitution(user.health_goals)
        
        # 产品推荐
        products = self.recommend_products(
            user.constitution_type,
            user.health_goals
        )
        
        return {
            "user_id": user.user_id,
            "constitution": constitution_data,
            "recommended_products": products,
            "ai_advice": f"根据您的{user.constitution_type}体质，建议优先选择{'/'.join([p['name'] for p in products[:2]])}",
            "generated_at": datetime.now().isoformat(),
        }

    def smart_chat(self, message: str, context: Dict = None) -> str:
        """AI智能客服"""
        msg = message.lower()
        
        if "减重" in msg or "减肥" in msg:
            return "我们的GLP-1减重方案通过司美格鲁肽/替尔泊肽实现科学减重，首月仅¥399。是否需要我帮您做个体质评估？"
        elif "脱发" in msg or "掉发" in msg:
            return "防脱生发方案包含米诺地尔+非那雄胺，针对不同脱发原因定制方案。首月¥199起，需要了解详情吗？"
        elif "价格" in msg or "多少钱" in msg:
            return "我们有5个品类，价格从¥199-599/月不等。具体取决于您的需求和体质。是否需要我帮您推荐？"
        elif "体质" in msg:
            return "我们提供AI体质评估，通过九种体质分析为您推荐最适合的方案。是否立即开始评估？"
        elif "开始" in msg or "购买" in msg:
            return "好的，请先完成体质评估（3分钟），然后我为您定制专属方案。"
        else:
            return "我是MediSlim AI健康助手，可以帮您了解我们的产品和服务。请问有什么需要帮助的吗？"


class DataAnalytics:
    """数据分析引擎"""

    def __init__(self):
        self.metrics = {
            "total_users": 0,
            "active_users": 0,
            "total_orders": 0,
            "total_revenue": 0,
            "avg_order_value": 0,
        }

    def update_metrics(self, data: Dict):
        """更新指标"""
        self.metrics.update(data)

    def get_dashboard(self) -> Dict:
        """获取仪表盘数据"""
        return {
            "metrics": self.metrics,
            "trends": {
                "users_growth": "+15%",
                "revenue_growth": "+25%",
                "order_growth": "+20%",
            },
            "top_products": [
                {"name": "GLP-1减重", "sales": 156, "revenue": 62344},
                {"name": "防脱生发", "sales": 98, "revenue": 19402},
                {"name": "皮肤管理", "sales": 67, "revenue": 20033},
            ],
            "constitution_distribution": {
                "痰湿": 35,
                "湿热": 25,
                "气虚": 15,
                "阳虚": 10,
                "阴虚": 8,
                "其他": 7,
            },
        }


# ========== 测试 ==========
if __name__ == "__main__":
    assistant = AIHealthAssistant()
    analytics = DataAnalytics()
    
    print("=" * 60)
    print("💊 MediSlim v5.0 AI健康助手测试")
    print("=" * 60)
    
    # 创建测试用户
    user = UserProfile(
        user_id="U001",
        nickname="测试用户",
        age=35,
        gender="male",
        constitution_type="痰湿",
        health_goals=["减重", "精力"]
    )
    
    # 生成健康方案
    plan = assistant.generate_health_plan(user)
    
    print(f"\n📋 AI健康方案:")
    print(f"   用户: {user.nickname}")
    print(f"   体质: {plan['constitution']['main_type']}")
    print(f"   特征: {plan['constitution']['characteristics']}")
    
    print(f"\n🎯 推荐产品:")
    for p in plan['recommended_products']:
        print(f"   {p['name']}: ¥{p['price_first_month']}/首月 (AI评分: {p['ai_score']})")
    
    print(f"\n💬 AI建议: {plan['ai_advice']}")
    
    # 测试智能客服
    print(f"\n🤖 AI客服测试:")
    test_messages = ["我想减肥", "脱发怎么办", "多少钱", "体质评估"]
    for msg in test_messages:
        response = assistant.smart_chat(msg)
        print(f"   用户: {msg}")
        print(f"   AI: {response}\n")
    
    # 仪表盘
    dashboard = analytics.get_dashboard()
    print(f"📊 仪表盘:")
    print(f"   总用户: {dashboard['metrics']['total_users']}")
    print(f"   总订单: {dashboard['metrics']['total_orders']}")
