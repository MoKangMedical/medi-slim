"""
MediSlim 饮食计划模块
热量计算 · 营养素分配 · 食谱推荐 · 饮食计划生成
"""

from dataclasses import dataclass, field
from typing import Optional
import json
import os
import random


@dataclass
class NutritionTarget:
    """每日营养目标"""
    calories: float        # kcal
    protein_g: float       # 蛋白质 g
    carbs_g: float         # 碳水化合物 g
    fat_g: float           # 脂肪 g
    fiber_g: float = 25    # 膳食纤维 g
    water_ml: float = 2000 # 饮水量 ml


@dataclass
class FoodItem:
    """食物项"""
    name: str
    category: str          # 谷物/蔬菜/水果/肉类/蛋奶/豆制品/坚果/调味品/饮品
    calories_per_100g: float
    protein_per_100g: float
    carbs_per_100g: float
    fat_per_100g: float
    fiber_per_100g: float = 0
    unit_weight: float = 100  # 一份的克数
    tags: list = field(default_factory=list)  # 低脂/高蛋白/低GI/素食


@dataclass
class MealItem:
    """一餐中的一道食物"""
    food: FoodItem
    grams: float
    calories: float
    protein: float
    carbs: float
    fat: float


@dataclass
class MealPlan:
    """一日饮食计划"""
    target: NutritionTarget
    breakfast: list   # [MealItem, ...]
    lunch: list
    dinner: list
    snacks: list
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
    summary: str
    tips: list


class DietPlanner:
    """饮食计划引擎"""

    # 宏量素分配比例 (protein/carbs/fat)
    DIET_PROFILES = {
        "balanced":    {"protein": 0.20, "carbs": 0.50, "fat": 0.30},
        "low_carb":    {"protein": 0.30, "carbs": 0.30, "fat": 0.40},
        "high_protein": {"protein": 0.35, "carbs": 0.40, "fat": 0.25},
        "keto":        {"protein": 0.25, "carbs": 0.05, "fat": 0.70},
        "muscle_gain": {"protein": 0.30, "carbs": 0.45, "fat": 0.25},
        "fat_loss":    {"protein": 0.35, "carbs": 0.35, "fat": 0.30},
    }

    # 餐次热量分配
    MEAL_SPLIT = {
        "breakfast": 0.25,
        "lunch": 0.35,
        "dinner": 0.30,
        "snacks": 0.10,
    }

    def __init__(self, data_dir: str = None):
        self.foods: list[FoodItem] = []
        if data_dir:
            self._load_foods(data_dir)

    def _load_foods(self, data_dir: str):
        """从 JSON 加载食物数据库"""
        path = os.path.join(data_dir, "nutrition-data.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for item in raw.get("foods", []):
                self.foods.append(FoodItem(
                    name=item["name"],
                    category=item["category"],
                    calories_per_100g=item["calories"],
                    protein_per_100g=item["protein"],
                    carbs_per_100g=item["carbs"],
                    fat_per_100g=item["fat"],
                    fiber_per_100g=item.get("fiber", 0),
                    unit_weight=item.get("unit_weight", 100),
                    tags=item.get("tags", []),
                ))

    # ── 营养目标计算 ────────────────────────────────────
    def calc_nutrition_target(
        self,
        tdee: float,
        goal: str = "maintain",
        diet_profile: str = "balanced",
    ) -> NutritionTarget:
        """
        根据 TDEE 和目标计算每日营养目标
        goal: lose / maintain / gain
        """
        goal_adj = {"lose": -400, "maintain": 0, "gain": 300}
        target_cal = tdee + goal_adj.get(goal, 0)
        target_cal = max(target_cal, 1200)  # 最低安全摄入

        ratios = self.DIET_PROFILES.get(diet_profile, self.DIET_PROFILES["balanced"])

        protein_g = target_cal * ratios["protein"] / 4   # 4 kcal/g
        carbs_g = target_cal * ratios["carbs"] / 4
        fat_g = target_cal * ratios["fat"] / 9           # 9 kcal/g

        return NutritionTarget(
            calories=round(target_cal),
            protein_g=round(protein_g),
            carbs_g=round(carbs_g),
            fat_g=round(fat_g),
        )

    # ── 一日食谱生成 ────────────────────────────────────
    def generate_daily_plan(
        self,
        target: NutritionTarget,
        preferences: list = None,
        allergies: list = None,
    ) -> MealPlan:
        """
        生成一日饮食计划
        preferences: 偏好标签如 ["高蛋白", "低脂"]
        allergies: 过敏食物类别如 ["坚果", "海鲜"]
        """
        available = self._filter_foods(preferences, allergies)

        breakfast = self._build_meal(available, "breakfast", target, target.calories * self.MEAL_SPLIT["breakfast"])
        lunch = self._build_meal(available, "lunch", target, target.calories * self.MEAL_SPLIT["lunch"])
        dinner = self._build_meal(available, "dinner", target, target.calories * self.MEAL_SPLIT["dinner"])
        snacks = self._build_meal(available, "snacks", target, target.calories * self.MEAL_SPLIT["snacks"])

        all_meals = breakfast + lunch + dinner + snacks
        total_cal = sum(m.calories for m in all_meals)
        total_pro = sum(m.protein for m in all_meals)
        total_carb = sum(m.carbs for m in all_meals)
        total_fat = sum(m.fat for m in all_meals)

        summary = self._generate_summary(target, total_cal, total_pro, total_carb, total_fat)
        tips = self._generate_tips(target, total_cal, total_pro)

        return MealPlan(
            target=target,
            breakfast=breakfast,
            lunch=lunch,
            dinner=dinner,
            snacks=snacks,
            total_calories=round(total_cal),
            total_protein=round(total_pro, 1),
            total_carbs=round(total_carb, 1),
            total_fat=round(total_fat, 1),
            summary=summary,
            tips=tips,
        )

    def _filter_foods(self, preferences: list = None, allergies: list = None) -> list:
        """过滤食物列表"""
        foods = self.foods[:]
        if allergies:
            foods = [f for f in foods if not any(a in f.category or a in f.name for a in allergies)]
        if preferences:
            # 优先保留匹配标签的食物
            preferred = [f for f in foods if any(p in f.tags for p in preferences)]
            if len(preferred) >= 10:
                return preferred
        return foods

    def _build_meal(
        self,
        available: list,
        meal_type: str,
        target: NutritionTarget,
        calorie_budget: float,
    ) -> list:
        """为某一餐选择食物并计算分量"""
        # 按餐次筛选合适的食物
        category_map = {
            "breakfast": ["谷物", "蛋奶", "水果", "豆制品"],
            "lunch":     ["谷物", "蔬菜", "肉类", "豆制品"],
            "dinner":    ["谷物", "蔬菜", "肉类", "鱼类"],
            "snacks":    ["水果", "坚果", "饮品"],
        }
        preferred_cats = category_map.get(meal_type, [])
        candidates = [f for f in available if f.category in preferred_cats]
        if len(candidates) < 2:
            candidates = available

        # 随机选择 2-4 道菜
        count = min(random.randint(2, 4), len(candidates))
        selected = random.sample(candidates, count)

        items = []
        budget_per_item = calorie_budget / count

        for food in selected:
            # 根据热量预算反算克数
            if food.calories_per_100g > 0:
                grams = (budget_per_item / food.calories_per_100g) * 100
                grams = round(min(max(grams, 30), 400) / 10) * 10  # 限制30-400g，取整10
            else:
                grams = food.unit_weight

            cal = food.calories_per_100g * grams / 100
            items.append(MealItem(
                food=food,
                grams=grams,
                calories=round(cal, 1),
                protein=round(food.protein_per_100g * grams / 100, 1),
                carbs=round(food.carbs_per_100g * grams / 100, 1),
                fat=round(food.fat_per_100g * grams / 100, 1),
            ))

        return items

    def _generate_summary(self, target, cal, pro, carb, fat) -> str:
        cal_diff = cal - target.calories
        pct = abs(cal_diff) / target.calories * 100
        if pct < 5:
            status = "热量达标 ✅"
        elif cal_diff < 0:
            status = f"热量偏低 {abs(cal_diff):.0f} kcal"
        else:
            status = f"热量偏高 {cal_diff:.0f} kcal"
        return f"总计 {cal:.0f} kcal | 蛋白质 {pro:.0f}g | 碳水 {carb:.0f}g | 脂肪 {fat:.0f}g — {status}"

    @staticmethod
    def _generate_tips(target, cal, pro) -> list:
        tips = []
        if pro < target.protein_g * 0.8:
            tips.append("蛋白质摄入不足，建议增加鸡蛋、鸡胸肉或豆腐")
        if cal > target.calories * 1.1:
            tips.append("今日热量超标，晚餐可适当减少主食")
        tips.append("餐前喝水 300ml，增加饱腹感")
        tips.append("细嚼慢咽，每餐 20 分钟以上")
        return tips

    # ── 格式化输出 ──────────────────────────────────────
    def format_plan(self, plan: MealPlan) -> str:
        """格式化为可读文本"""
        lines = ["=" * 50, "📋 今日饮食计划", "=" * 50]

        for meal_name, items in [
            ("🌅 早餐", plan.breakfast),
            ("☀️ 午餐", plan.lunch),
            ("🌙 晚餐", plan.dinner),
            ("🍪 加餐", plan.snacks),
        ]:
            lines.append(f"\n{meal_name}")
            lines.append("-" * 30)
            for item in items:
                lines.append(
                    f"  {item.food.name} ({item.grams}g) — "
                    f"{item.calories} kcal | P:{item.protein}g C:{item.carbs}g F:{item.fat}g"
                )

        lines.append("\n" + "=" * 50)
        lines.append(plan.summary)
        lines.append("\n💡 小贴士：")
        for tip in plan.tips:
            lines.append(f"  • {tip}")

        return "\n".join(lines)

    def to_dict(self, plan: MealPlan) -> dict:
        """转为字典"""
        def meal_to_dict(items):
            return [{
                "name": i.food.name,
                "grams": i.grams,
                "calories": i.calories,
                "protein": i.protein,
                "carbs": i.carbs,
                "fat": i.fat,
            } for i in items]

        return {
            "target": {
                "calories": plan.target.calories,
                "protein_g": plan.target.protein_g,
                "carbs_g": plan.target.carbs_g,
                "fat_g": plan.target.fat_g,
            },
            "breakfast": meal_to_dict(plan.breakfast),
            "lunch": meal_to_dict(plan.lunch),
            "dinner": meal_to_dict(plan.dinner),
            "snacks": meal_to_dict(plan.snacks),
            "total": {
                "calories": plan.total_calories,
                "protein": plan.total_protein,
                "carbs": plan.total_carbs,
                "fat": plan.total_fat,
            },
            "summary": plan.summary,
            "tips": plan.tips,
        }


# ── 便捷函数 ────────────────────────────────────────────
def quick_meal_plan(
    tdee: float,
    goal: str = "lose",
    diet_profile: str = "balanced",
    data_dir: str = None,
) -> dict:
    """快速生成一日饮食计划"""
    planner = DietPlanner(data_dir=data_dir)
    target = planner.calc_nutrition_target(tdee, goal, diet_profile)
    plan = planner.generate_daily_plan(target)
    return planner.to_dict(plan)
