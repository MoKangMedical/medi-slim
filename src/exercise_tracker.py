"""
MediSlim 运动追踪模块
运动类型库 · 热量消耗计算 · 运动计划生成 · 运动记录追踪
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timedelta
import json
import os
import random


@dataclass
class ExerciseType:
    """运动类型"""
    name: str
    category: str           # 有氧/力量/柔韧/球类/水上/日常
    met: float              # MET 值（代谢当量）
    intensity: str          # 低/中/高
    muscle_groups: list     # 主要锻炼肌群
    equipment: bool = False # 是否需要器械
    description: str = ""


@dataclass
class ExerciseRecord:
    """运动记录"""
    exercise: ExerciseType
    duration_min: float
    calories_burned: float
    date: str
    heart_rate_avg: Optional[int] = None
    notes: str = ""


@dataclass
class ExercisePlan:
    """运动计划"""
    goal: str               # lose / maintain / gain / endurance
    weekly_target_min: int  # 每周目标分钟数
    weekly_target_cal: float # 每周目标消耗热量
    days: list              # [{day: "周一", exercises: [ExercisePlanItem, ...]}]
    warmup: list
    cooldown: list
    tips: list


@dataclass
class ExercisePlanItem:
    """计划中的运动项"""
    exercise: ExerciseType
    duration_min: int
    sets: Optional[int] = None
    reps: Optional[int] = None
    rest_sec: Optional[int] = None
    estimated_calories: float = 0


class ExerciseTracker:
    """运动追踪引擎"""

    # 运动数据库：MET 值参考 Compendium of Physical Activities
    EXERCISE_DB = [
        # 有氧运动
        ExerciseType("慢跑", "有氧", 7.0, "中", ["腿部", "心肺"], False, "6-8km/h配速"),
        ExerciseType("快走", "有氧", 4.5, "低", ["腿部", "心肺"], False, "5-6km/h"),
        ExerciseType("游泳（自由泳）", "有氧", 8.0, "高", ["全身", "心肺"], True, "中等速度"),
        ExerciseType("骑自行车", "有氧", 6.5, "中", ["腿部", "心肺"], True, "15-20km/h"),
        ExerciseType("跳绳", "有氧", 10.0, "高", ["全身", "心肺"], True, "中等速度"),
        ExerciseType("椭圆机", "有氧", 5.0, "中", ["全身", "心肺"], True, "中等阻力"),
        ExerciseType("划船机", "有氧", 7.0, "中", ["背部", "心肺"], True, "中等阻力"),
        ExerciseType("爬楼梯", "有氧", 8.8, "高", ["腿部", "臀部"], False, "持续上楼"),
        ExerciseType("有氧操", "有氧", 6.0, "中", ["全身", "心肺"], False, "中等强度"),
        ExerciseType("舞蹈", "有氧", 5.0, "中", ["全身", "心肺"], False, "社交舞蹈"),
        # 力量训练
        ExerciseType("深蹲", "力量", 5.0, "中", ["腿部", "臀部"], False, "自重深蹲"),
        ExerciseType("硬拉", "力量", 6.0, "高", ["背部", "腿部"], True, "杠铃硬拉"),
        ExerciseType("卧推", "力量", 5.5, "中", ["胸部", "手臂"], True, "杠铃卧推"),
        ExerciseType("引体向上", "力量", 7.0, "高", ["背部", "手臂"], True, "标准引体"),
        ExerciseType("俯卧撑", "力量", 3.8, "中", ["胸部", "手臂"], False, "标准俯卧撑"),
        ExerciseType("哑铃弯举", "力量", 3.5, "低", ["手臂"], True, "二头肌训练"),
        ExerciseType("平板支撑", "力量", 3.0, "低", ["核心"], False, "静态保持"),
        ExerciseType("臀桥", "力量", 3.5, "低", ["臀部", "核心"], False, "自重训练"),
        ExerciseType("波比跳", "力量", 10.0, "高", ["全身"], False, "高强度间歇"),
        ExerciseType("壶铃摆荡", "力量", 8.0, "高", ["全身", "核心"], True, "爆发力训练"),
        # 柔韧/身心
        ExerciseType("瑜伽（哈他）", "柔韧", 3.0, "低", ["全身"], False, "基础体式"),
        ExerciseType("瑜伽（流瑜伽）", "柔韧", 4.5, "中", ["全身"], False, "动态体式"),
        ExerciseType("拉伸", "柔韧", 2.5, "低", ["全身"], False, "静态拉伸"),
        ExerciseType("普拉提", "柔韧", 3.5, "低", ["核心", "全身"], False, "核心控制"),
        ExerciseType("太极拳", "柔韧", 3.0, "低", ["全身", "平衡"], False, "传统武术"),
        # 球类
        ExerciseType("篮球", "球类", 7.5, "高", ["全身", "心肺"], False, "半场比赛"),
        ExerciseType("羽毛球", "球类", 5.5, "中", ["全身", "心肺"], True, "单打"),
        ExerciseType("乒乓球", "球类", 4.0, "低", ["手臂", "反应"], True, "中等强度"),
        ExerciseType("足球", "球类", 8.0, "高", ["腿部", "心肺"], False, "半场比赛"),
        ExerciseType("网球", "球类", 7.0, "高", ["全身", "心肺"], True, "单打"),
        # 日常活动
        ExerciseType("步行（日常）", "日常", 3.0, "低", ["腿部"], False, "正常步速"),
        ExerciseType("做家务", "日常", 3.5, "低", ["全身"], False, "打扫清洁"),
        ExerciseType("园艺", "日常", 4.0, "低", ["手臂", "腿部"], False, "种植修剪"),
        ExerciseType("遛狗", "日常", 3.0, "低", ["腿部"], False, "轻松散步"),
    ]

    # 目标配置
    GOAL_CONFIGS = {
        "lose": {"weekly_min": 300, "focus": "有氧", "intensity": "中", "days": 5},
        "maintain": {"weekly_min": 150, "focus": "有氧", "intensity": "中", "days": 4},
        "gain": {"weekly_min": 200, "focus": "力量", "intensity": "高", "days": 4},
        "endurance": {"weekly_min": 250, "focus": "有氧", "intensity": "中", "days": 5},
        "flexibility": {"weekly_min": 150, "focus": "柔韧", "intensity": "低", "days": 5},
    }

    def __init__(self, data_dir: str = None):
        self.records: list[ExerciseRecord] = []
        if data_dir:
            self._load_custom_exercises(data_dir)

    def _load_custom_exercises(self, data_dir: str):
        """从数据目录加载自定义运动类型"""
        # 预留扩展接口
        pass

    # ── 热量计算 ────────────────────────────────────────
    @staticmethod
    def calc_calories(met: float, weight_kg: float, duration_min: float) -> float:
        """
        热量消耗 = MET × 体重(kg) × 时间(h)
        """
        hours = duration_min / 60
        return round(met * weight_kg * hours, 1)

    # ── 搜索运动 ────────────────────────────────────────
    def search_exercises(
        self,
        category: str = None,
        intensity: str = None,
        muscle_group: str = None,
        no_equipment: bool = False,
    ) -> list:
        """搜索运动类型"""
        results = self.EXERCISE_DB[:]
        if category:
            results = [e for e in results if e.category == category]
        if intensity:
            results = [e for e in results if e.intensity == intensity]
        if muscle_group:
            results = [e for e in results if muscle_group in e.muscle_groups]
        if no_equipment:
            results = [e for e in results if not e.equipment]
        return results

    # ── 记录运动 ────────────────────────────────────────
    def log_exercise(
        self,
        exercise_name: str,
        duration_min: float,
        weight_kg: float,
        date: str = None,
        heart_rate_avg: int = None,
        notes: str = "",
    ) -> ExerciseRecord:
        """记录一次运动"""
        exercise = next((e for e in self.EXERCISE_DB if e.name == exercise_name), None)
        if not exercise:
            raise ValueError(f"未知运动类型: {exercise_name}")

        calories = self.calc_calories(exercise.met, weight_kg, duration_min)
        record = ExerciseRecord(
            exercise=exercise,
            duration_min=duration_min,
            calories_burned=calories,
            date=date or datetime.now().strftime("%Y-%m-%d"),
            heart_rate_avg=heart_rate_avg,
            notes=notes,
        )
        self.records.append(record)
        return record

    def get_records(self, days: int = 7) -> list:
        """获取最近 N 天的运动记录"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        return [r for r in self.records if r.date >= cutoff]

    def get_stats(self, days: int = 7) -> dict:
        """统计最近 N 天的运动数据"""
        records = self.get_records(days)
        if not records:
            return {"total_records": 0}

        total_min = sum(r.duration_min for r in records)
        total_cal = sum(r.calories_burned for r in records)
        categories = {}
        for r in records:
            cat = r.exercise.category
            categories[cat] = categories.get(cat, 0) + r.duration_min

        return {
            "period_days": days,
            "total_records": len(records),
            "total_minutes": round(total_min),
            "total_calories": round(total_cal),
            "avg_minutes_per_day": round(total_min / days, 1),
            "category_breakdown": categories,
        }

    # ── 运动计划生成 ────────────────────────────────────
    def generate_weekly_plan(
        self,
        weight_kg: float,
        goal: str = "lose",
        fitness_level: str = "beginner",
        available_days: list = None,
    ) -> ExercisePlan:
        """
        生成一周运动计划
        fitness_level: beginner / intermediate / advanced
        available_days: 可运动的日子，如 ["周一","周三","周五"]
        """
        config = self.GOAL_CONFIGS.get(goal, self.GOAL_CONFIGS["maintain"])
        if available_days is None:
            day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            available_days = day_names[:config["days"]]

        # 难度系数
        difficulty = {"beginner": 0.7, "intermediate": 1.0, "advanced": 1.3}
        multi = difficulty.get(fitness_level, 1.0)

        # 选择合适的运动
        focus_exercises = self.search_exercises(category=config["focus"])
        support_exercises = self.search_exercises(intensity=config["intensity"])
        all_options = list({e.name: e for e in focus_exercises + support_exercises}.values())

        days_plan = []
        weekly_min = 0
        weekly_cal = 0

        for day in available_days:
            # 每天选 2-3 个运动
            count = random.randint(2, 3)
            selected = random.sample(all_options, min(count, len(all_options)))

            exercises = []
            for ex in selected:
                duration = int(random.choice([20, 30, 40]) * multi)
                cal = self.calc_calories(ex.met, weight_kg, duration)
                exercises.append(ExercisePlanItem(
                    exercise=ex,
                    duration_min=duration,
                    sets=random.choice([3, 4]) if ex.category == "力量" else None,
                    reps=random.choice([8, 10, 12]) if ex.category == "力量" else None,
                    rest_sec=60 if ex.category == "力量" else None,
                    estimated_calories=cal,
                ))
                weekly_min += duration
                weekly_cal += cal

            days_plan.append({"day": day, "exercises": exercises})

        # 热身和放松
        warmup = [
            "原地踏步 2 分钟",
            "关节环绕（颈/肩/腰/膝/踝）各 10 次",
            "动态拉伸 3 分钟",
        ]
        cooldown = [
            "慢走 2 分钟",
            "静态拉伸 5 分钟（重点拉伸训练部位）",
            "深呼吸放松 1 分钟",
        ]

        tips = self._generate_plan_tips(goal, fitness_level, weekly_min)

        return ExercisePlan(
            goal=goal,
            weekly_target_min=config["weekly_min"],
            weekly_target_cal=round(weekly_cal),
            days=days_plan,
            warmup=warmup,
            cooldown=cooldown,
            tips=tips,
        )

    @staticmethod
    def _generate_plan_tips(goal: str, level: str, total_min: int) -> list:
        tips = []
        if goal == "lose":
            tips.append("有氧运动心率维持在最大心率的60-75%效果最佳")
            tips.append("力量训练可增加基础代谢率，帮助持续燃脂")
        elif goal == "gain":
            tips.append("力量训练后 30 分钟内补充蛋白质")
            tips.append("每个肌群训练后至少休息 48 小时")
        if level == "beginner":
            tips.append("新手前两周以适应为主，不要追求高强度")
            tips.append("感到不适立即停止，循序渐进最重要")
        tips.append(f"本周计划运动 {total_min} 分钟，加油！💪")
        tips.append("运动前后注意补水，每 15 分钟喝 150-200ml")
        return tips

    # ── 格式化输出 ──────────────────────────────────────
    def format_plan(self, plan: ExercisePlan) -> str:
        lines = ["=" * 50, "🏃 本周运动计划", "=" * 50]
        lines.append(f"目标: {plan.goal} | 每周 {plan.weekly_target_min} 分钟")
        lines.append(f"预计消耗: {plan.weekly_target_cal} kcal\n")

        lines.append("🔥 热身（每次运动前）:")
        for w in plan.warmup:
            lines.append(f"  • {w}")

        for day_plan in plan.days:
            lines.append(f"\n📅 {day_plan['day']}")
            lines.append("-" * 30)
            for item in day_plan["exercises"]:
                sets_info = ""
                if item.sets:
                    sets_info = f" ({item.sets}组×{item.reps}次)"
                lines.append(
                    f"  {item.exercise.name}{sets_info} — "
                    f"{item.duration_min}分钟 | ~{item.estimated_calories:.0f} kcal"
                )

        lines.append("\n🧊 放松（每次运动后）:")
        for c in plan.cooldown:
            lines.append(f"  • {c}")

        lines.append("\n💡 小贴士:")
        for tip in plan.tips:
            lines.append(f"  • {tip}")

        return "\n".join(lines)

    def to_dict(self, plan: ExercisePlan) -> dict:
        return {
            "goal": plan.goal,
            "weekly_target_min": plan.weekly_target_min,
            "weekly_target_cal": plan.weekly_target_cal,
            "days": [{
                "day": d["day"],
                "exercises": [{
                    "name": e.exercise.name,
                    "category": e.exercise.category,
                    "duration_min": e.duration_min,
                    "sets": e.sets,
                    "reps": e.reps,
                    "estimated_calories": e.estimated_calories,
                } for e in d["exercises"]]
            } for d in plan.days],
            "warmup": plan.warmup,
            "cooldown": plan.cooldown,
            "tips": plan.tips,
        }


# ── 便捷函数 ────────────────────────────────────────────
def quick_exercise_plan(
    weight_kg: float,
    goal: str = "lose",
    fitness_level: str = "beginner",
) -> dict:
    """快速生成运动计划"""
    tracker = ExerciseTracker()
    plan = tracker.generate_weekly_plan(weight_kg, goal, fitness_level)
    return tracker.to_dict(plan)
