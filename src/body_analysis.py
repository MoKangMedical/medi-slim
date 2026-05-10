"""
MediSlim 身体分析模块
BMI / 体脂率 / 基础代谢率 / 理想体重 计算
"""

from dataclasses import dataclass
from typing import Optional
import math


@dataclass
class BodyMetrics:
    """身体指标数据"""
    height_cm: float
    weight_kg: float
    age: int
    gender: str  # "male" / "female"
    waist_cm: Optional[float] = None
    hip_cm: Optional[float] = None
    neck_cm: Optional[float] = None
    activity_level: str = "moderate"  # sedentary / light / moderate / active / very_active


@dataclass
class BodyAnalysisResult:
    """身体分析结果"""
    bmi: float
    bmi_category: str
    body_fat_pct: float
    body_fat_category: str
    bmr: float  # 基础代谢率 kcal/day
    tdee: float  # 每日总消耗
    ideal_weight_min: float
    ideal_weight_max: float
    waist_hip_ratio: Optional[float]
    health_risk: str
    recommendations: list


class BodyAnalyzer:
    """身体分析引擎"""

    ACTIVITY_MULTIPLIERS = {
        "sedentary": 1.2,       # 久坐不动
        "light": 1.375,         # 轻度活动（每周1-3次）
        "moderate": 1.55,       # 中度活动（每周3-5次）
        "active": 1.725,        # 高度活动（每周6-7次）
        "very_active": 1.9,     # 极高活动（体力劳动/专业运动）
    }

    def analyze(self, metrics: BodyMetrics) -> BodyAnalysisResult:
        """执行完整身体分析"""
        bmi = self.calc_bmi(metrics.height_cm, metrics.weight_kg)
        bmi_cat = self.bmi_category(bmi)
        body_fat = self.calc_body_fat(metrics)
        body_fat_cat = self.body_fat_category(body_fat, metrics.gender)
        bmr = self.calc_bmr(metrics)
        tdee = self.calc_tdee(bmr, metrics.activity_level)
        ideal_min, ideal_max = self.ideal_weight_range(metrics.height_cm)
        whr = self.calc_waist_hip_ratio(metrics.waist_cm, metrics.hip_cm)
        risk = self.health_risk_assessment(bmi, body_fat, metrics.age, metrics.gender)
        recs = self.generate_recommendations(bmi, body_fat, bmr, tdee, metrics)

        return BodyAnalysisResult(
            bmi=round(bmi, 1),
            bmi_category=bmi_cat,
            body_fat_pct=round(body_fat, 1),
            body_fat_category=body_fat_cat,
            bmr=round(bmr),
            tdee=round(tdee),
            ideal_weight_min=round(ideal_min, 1),
            ideal_weight_max=round(ideal_max, 1),
            waist_hip_ratio=round(whr, 3) if whr else None,
            health_risk=risk,
            recommendations=recs,
        )

    # ── BMI ──────────────────────────────────────────────
    @staticmethod
    def calc_bmi(height_cm: float, weight_kg: float) -> float:
        h_m = height_cm / 100
        return weight_kg / (h_m ** 2)

    @staticmethod
    def bmi_category(bmi: float) -> str:
        if bmi < 18.5:
            return "偏瘦"
        elif bmi < 24:
            return "正常"
        elif bmi < 28:
            return "偏胖"
        else:
            return "肥胖"

    # ── 体脂率 ──────────────────────────────────────────
    @staticmethod
    def calc_body_fat(metrics: BodyMetrics) -> float:
        """
        美国海军体脂率公式（需要腰围、颈围）
        若缺少测量数据，回退到 BMI 估算公式
        """
        if metrics.waist_cm and metrics.neck_cm:
            h = metrics.height_cm
            if metrics.gender == "male":
                # 男性: 495/(1.0324-0.19077*log10(腰-颈)+0.15456*log10(身高))-450
                return 495 / (
                    1.0324
                    - 0.19077 * math.log10(metrics.waist_cm - metrics.neck_cm)
                    + 0.15456 * math.log10(h)
                ) - 450
            else:
                # 女性: 495/(1.29579-0.35004*log10(腰+臀-颈)+0.22100*log10(身高))-450
                hip = metrics.hip_cm or metrics.waist_cm * 1.1
                return 495 / (
                    1.29579
                    - 0.35004 * math.log10(metrics.waist_cm + hip - metrics.neck_cm)
                    + 0.22100 * math.log10(h)
                ) - 450
        else:
            # BMI 估算体脂率（Deurenberg 公式）
            bmi = metrics.weight_kg / ((metrics.height_cm / 100) ** 2)
            gender_factor = 1 if metrics.gender == "male" else 0
            return 1.2 * bmi + 0.23 * metrics.age - 10.8 * gender_factor - 5.4

    @staticmethod
    def body_fat_category(pct: float, gender: str) -> str:
        if gender == "male":
            if pct < 6:
                return "必需脂肪"
            elif pct < 14:
                return "运动员"
            elif pct < 18:
                return "健康"
            elif pct < 25:
                return "一般"
            else:
                return "肥胖"
        else:
            if pct < 14:
                return "必需脂肪"
            elif pct < 21:
                return "运动员"
            elif pct < 25:
                return "健康"
            elif pct < 32:
                return "一般"
            else:
                return "肥胖"

    # ── 基础代谢率 BMR ──────────────────────────────────
    @staticmethod
    def calc_bmr(metrics: BodyMetrics) -> float:
        """
        Mifflin-St Jeor 公式（最准确）
        男: 10*体重 + 6.25*身高 - 5*年龄 + 5
        女: 10*体重 + 6.25*身高 - 5*年龄 - 161
        """
        base = 10 * metrics.weight_kg + 6.25 * metrics.height_cm - 5 * metrics.age
        return base + 5 if metrics.gender == "male" else base - 161

    @classmethod
    def calc_tdee(cls, bmr: float, activity_level: str) -> float:
        """每日总能量消耗 = BMR × 活动系数"""
        multiplier = cls.ACTIVITY_MULTIPLIERS.get(activity_level, 1.55)
        return bmr * multiplier

    # ── 理想体重 ────────────────────────────────────────
    @staticmethod
    def ideal_weight_range(height_cm: float) -> tuple:
        """BMI 18.5~24 对应的理想体重范围"""
        h_m = height_cm / 100
        return (18.5 * h_m ** 2, 24 * h_m ** 2)

    # ── 腰臀比 ──────────────────────────────────────────
    @staticmethod
    def calc_waist_hip_ratio(waist: Optional[float], hip: Optional[float]) -> Optional[float]:
        if waist and hip and hip > 0:
            return waist / hip
        return None

    # ── 健康风险评估 ────────────────────────────────────
    @staticmethod
    def health_risk_assessment(bmi: float, body_fat: float, age: int, gender: str) -> str:
        """综合健康风险评级"""
        score = 0
        # BMI 风险
        if bmi < 18.5 or bmi >= 28:
            score += 3
        elif bmi >= 24:
            score += 1
        # 体脂风险
        threshold = 25 if gender == "male" else 32
        if body_fat > threshold + 5:
            score += 3
        elif body_fat > threshold:
            score += 1
        # 年龄风险
        if age > 50:
            score += 1

        if score >= 4:
            return "高风险 — 建议尽快咨询医生"
        elif score >= 2:
            return "中等风险 — 建议调整生活方式"
        else:
            return "低风险 — 保持良好习惯"

    # ── 个性化建议 ──────────────────────────────────────
    @staticmethod
    def generate_recommendations(
        bmi: float, body_fat: float, bmr: float, tdee: float, metrics: BodyMetrics
    ) -> list:
        recs = []

        if bmi < 18.5:
            recs.append("体重偏低，建议增加优质蛋白摄入，每日热量目标 {:.0f} kcal".format(tdee + 300))
            recs.append("推荐力量训练增肌，避免过度有氧")
        elif bmi < 24:
            recs.append("体重正常，维持当前饮食和运动习惯")
            recs.append("每日热量维持在 {:.0f} kcal 左右".format(tdee))
        elif bmi < 28:
            recs.append("体重偏高，建议每日减少 300-500 kcal 摄入")
            recs.append("每日热量目标 {:.0f} kcal".format(tdee - 400))
            recs.append("增加有氧运动，每周 150 分钟以上")
        else:
            recs.append("肥胖范围，强烈建议咨询营养师制定专业方案")
            recs.append("每日热量目标 {:.0f} kcal，循序渐进".format(tdee - 500))

        threshold = 25 if metrics.gender == "male" else 32
        if body_fat > threshold:
            recs.append("体脂率偏高，重点降低体脂而非单纯减重")

        if metrics.age > 40:
            recs.append("40岁以上建议增加蛋白质摄入，防止肌肉流失")

        recs.append("每日饮水 2000-2500ml")
        recs.append("保证 7-8 小时充足睡眠")

        return recs

    def to_dict(self, result: BodyAnalysisResult) -> dict:
        """转为字典，方便 JSON 序列化"""
        return {
            "bmi": result.bmi,
            "bmi_category": result.bmi_category,
            "body_fat_pct": result.body_fat_pct,
            "body_fat_category": result.body_fat_category,
            "bmr": result.bmr,
            "tdee": result.tdee,
            "ideal_weight_range_kg": [result.ideal_weight_min, result.ideal_weight_max],
            "waist_hip_ratio": result.waist_hip_ratio,
            "health_risk": result.health_risk,
            "recommendations": result.recommendations,
        }


# ── 便捷函数 ────────────────────────────────────────────
def quick_bmi(height_cm: float, weight_kg: float) -> dict:
    """快速 BMI 计算"""
    analyzer = BodyAnalyzer()
    bmi = analyzer.calc_bmi(height_cm, weight_kg)
    return {"bmi": round(bmi, 1), "category": analyzer.bmi_category(bmi)}


def quick_body_analysis(
    height_cm: float,
    weight_kg: float,
    age: int,
    gender: str,
    waist_cm: float = None,
    activity_level: str = "moderate",
) -> dict:
    """快速完整分析"""
    metrics = BodyMetrics(
        height_cm=height_cm,
        weight_kg=weight_kg,
        age=age,
        gender=gender,
        waist_cm=waist_cm,
        activity_level=activity_level,
    )
    analyzer = BodyAnalyzer()
    result = analyzer.analyze(metrics)
    return analyzer.to_dict(result)
