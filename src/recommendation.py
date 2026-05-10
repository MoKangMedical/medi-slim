"""
MediSlim AI 推荐引擎
基于用户画像和医美项目数据，提供个性化推荐
"""

import json
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class UserProfile:
    """用户画像"""
    age: int
    gender: str  # "male" / "female"
    budget_min: int = 0
    budget_max: int = 100000
    concerns: list = None  # ["抗衰", "祛斑", "瘦脸"]
    skin_type: str = ""  # "dry" / "oily" / "combination" / "sensitive"
    pain_tolerance: str = "medium"  # "low" / "medium" / "high"
    recovery_days: int = 7  # 可接受的恢复天数

    def __post_init__(self):
        if self.concerns is None:
            self.concerns = []


class RecommendationEngine:
    """AI 医美推荐引擎"""

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        self.data_dir = data_dir
        self.products = self._load_json("products.json")
        self.clinics = self._load_json("clinics.json")

    def _load_json(self, filename: str) -> list:
        filepath = os.path.join(self.data_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def recommend(
        self,
        profile: UserProfile,
        top_k: int = 5,
        city: Optional[str] = None,
    ) -> list:
        """
        根据用户画像推荐医美项目

        Args:
            profile: 用户画像
            top_k: 返回数量
            city: 城市筛选

        Returns:
            推荐项目列表，按匹配度降序
        """
        scored = []
        for product in self.products:
            score = self._score_product(product, profile)
            if score > 0:
                scored.append({"product": product, "score": score})

        # 按分数降序
        scored.sort(key=lambda x: x["score"], reverse=True)

        results = []
        for item in scored[:top_k]:
            product = item["product"]
            matched_clinics = self._find_clinics(product, city)
            results.append({
                "product": product,
                "match_score": round(item["score"], 2),
                "recommended_clinics": matched_clinics[:3],
            })

        return results

    def _score_product(self, product: dict, profile: UserProfile) -> float:
        """计算产品与用户画像的匹配分数"""
        score = 0.0

        # 1. 预算匹配 (0-30分)
        price_min = product["price_range"]["min"]
        price_max = product["price_range"]["max"]
        if price_max < profile.budget_min or price_min > profile.budget_max:
            return 0  # 预算不匹配，直接排除
        budget_overlap = min(price_max, profile.budget_max) - max(price_min, profile.budget_min)
        budget_range = profile.budget_max - profile.budget_min
        if budget_range > 0:
            score += 30 * (budget_overlap / budget_range)

        # 2. 需求匹配 (0-40分)
        if profile.concerns:
            product_tags = set(product.get("tags", []) + product.get("suitable_for", []))
            concern_matches = sum(
                1 for c in profile.concerns
                if any(c in tag for tag in product_tags)
            )
            score += 40 * (concern_matches / len(profile.concerns))
        else:
            score += 20  # 无明确需求，给基础分

        # 3. 恢复时间匹配 (0-15分)
        recovery = product.get("recovery_days", 0)
        if recovery <= profile.recovery_days:
            score += 15
        elif recovery <= profile.recovery_days * 2:
            score += 7

        # 4. 风险偏好匹配 (0-15分)
        risk = product.get("risk_level", "low")
        risk_scores = {"low": 15, "medium": 10, "high": 5}
        if profile.pain_tolerance == "high":
            risk_scores = {"low": 10, "medium": 15, "high": 15}
        elif profile.pain_tolerance == "low":
            risk_scores = {"low": 15, "medium": 5, "high": 0}
        score += risk_scores.get(risk, 10)

        return score

    def _find_clinics(self, product: dict, city: Optional[str] = None) -> list:
        """找到能提供该产品的机构"""
        product_tags = set(product.get("tags", []) + product.get("suitable_for", []))
        matched = []

        for clinic in self.clinics:
            if city and clinic.get("city") != city:
                continue

            # 检查机构专长是否匹配
            specialties = clinic.get("specialties", [])
            clinic_tags = set(specialties)
            overlap = product_tags & clinic_tags

            if overlap or any(
                s in product.get("subcategory", "") for s in specialties
            ):
                matched.append({
                    "id": clinic["id"],
                    "name": clinic["name"],
                    "city": clinic["city"],
                    "rating": clinic.get("rating", 0),
                    "review_count": clinic.get("review_count", 0),
                })

        # 按评分排序
        matched.sort(key=lambda x: x["rating"], reverse=True)
        return matched


def demo():
    """演示推荐引擎"""
    engine = RecommendationEngine()

    # 示例用户：28岁女性，预算5000-20000，关注抗衰和祛斑
    profile = UserProfile(
        age=28,
        gender="female",
        budget_min=5000,
        budget_max=20000,
        concerns=["抗衰", "祛斑", "紧致"],
        skin_type="combination",
        pain_tolerance="medium",
        recovery_days=5,
    )

    results = engine.recommend(profile, top_k=3)

    print("🎯 MediSlim AI 推荐结果")
    print("=" * 50)
    for i, item in enumerate(results, 1):
        p = item["product"]
        print(f"\n{i}. {p['name']} (匹配度: {item['match_score']})")
        print(f"   价格: ¥{p['price_range']['min']:,} - ¥{p['price_range']['max']:,}")
        print(f"   恢复期: {p['recovery_days']}天")
        print(f"   适合: {', '.join(p['suitable_for'][:3])}")
        if item["recommended_clinics"]:
            print(f"   推荐机构: {item['recommended_clinics'][0]['name']}")


if __name__ == "__main__":
    demo()
