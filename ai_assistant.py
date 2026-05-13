"""DeepSeek-backed AI assistant utilities for MediSlim.

The production app keeps deterministic medical eligibility checks in app.py.
This module only handles user-facing guidance, recommendation explanations,
and lightweight nutrition lookup copy.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from mimo_client import _base_system_prompt, _chat_json, _clean_text, provider_status


CONSTITUTIONS = {
    "气虚": {"features": "易疲劳、气短、自汗", "focus": ["补气", "健脾", "规律作息"]},
    "阳虚": {"features": "怕冷、手脚凉、精神不足", "focus": ["温阳", "保暖", "减少寒凉"]},
    "阴虚": {"features": "口干、手足心热、睡眠浅", "focus": ["滋阴", "降燥", "睡眠修复"]},
    "痰湿": {"features": "体重上升、困倦、油腻感", "focus": ["控糖控脂", "祛湿", "增加活动"]},
    "湿热": {"features": "口苦、油脂多、易长痘", "focus": ["清淡饮食", "规律排便", "皮肤管理"]},
    "血瘀": {"features": "面色暗、疼痛固定、循环差", "focus": ["改善循环", "运动", "睡眠"]},
    "气郁": {"features": "情绪紧绷、胸闷、睡眠受影响", "focus": ["舒压", "规律运动", "睡眠"]},
    "特禀": {"features": "过敏倾向、皮肤或呼吸道敏感", "focus": ["避敏", "温和护理", "记录诱因"]},
    "平和": {"features": "状态稳定、精力较均衡", "focus": ["维持习惯", "预防管理", "周期复查"]},
}


@dataclass
class UserProfile:
    user_id: str
    nickname: str = "用户"
    age: int = 0
    gender: str = ""
    constitution_type: str = ""
    health_goals: list[str] = field(default_factory=list)
    purchase_history: list[dict[str, Any]] = field(default_factory=list)


class AIHealthAssistant:
    """Non-diagnostic assistant for product education and next-step guidance."""

    def assess_constitution(self, answers: dict[str, Any] | list[str]) -> dict[str, Any]:
        scores = {key: 0 for key in CONSTITUTIONS}
        values: list[str]
        if isinstance(answers, dict):
            values = [str(value) for value in answers.values()]
            values.extend(str(key) for key in answers.keys())
        else:
            values = [str(value) for value in answers]

        joined = " ".join(values)
        rules = {
            "气虚": ["疲劳", "气短", "乏力", "精力"],
            "阳虚": ["怕冷", "手脚凉", "阳虚"],
            "阴虚": ["口干", "手足心热", "失眠", "助眠"],
            "痰湿": ["减重", "肥胖", "体重", "痰湿", "困倦"],
            "湿热": ["长痘", "油", "口苦", "皮肤", "湿热"],
            "血瘀": ["脱发", "循环", "血瘀", "疼痛"],
            "气郁": ["焦虑", "压力", "情绪", "胸闷"],
            "特禀": ["过敏", "敏感", "鼻炎"],
        }
        for constitution, keywords in rules.items():
            scores[constitution] += sum(2 for keyword in keywords if keyword in joined)

        primary = max(scores, key=scores.get)
        if scores[primary] == 0:
            primary = "平和"

        profile = CONSTITUTIONS[primary]
        return {
            "main_type": primary,
            "characteristics": profile["features"],
            "recommendations": profile["focus"],
            "scores": scores,
        }

    def recommend_products(self, constitution: str, goals: list[str], products: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        goal_text = " ".join(goals)
        matches: list[dict[str, Any]] = []
        for product_id, product in products.items():
            score = 20
            category = product.get("category", "")
            name = product.get("name", "")
            description = product.get("description", "")
            if category and category in goal_text:
                score += 35
            if any(token in goal_text for token in [category, name, description]):
                score += 25
            if constitution in {"痰湿", "湿热"} and product_id == "glp1":
                score += 35
            if constitution in {"血瘀", "气虚"} and product_id == "hair":
                score += 25
            if constitution in {"湿热", "特禀"} and product_id == "skin":
                score += 25
            if constitution in {"气郁", "阴虚"} and product_id == "sleep":
                score += 25
            if constitution in {"阳虚", "气虚"} and product_id == "mens":
                score += 20
            if score >= 45:
                matches.append({
                    "product_id": product_id,
                    "name": name,
                    "price_first_month": product.get("first_price", 0),
                    "ai_score": min(score, 100),
                    "reason": f"匹配{constitution}体质与当前目标，建议先完成正式评估。",
                })
        return sorted(matches, key=lambda item: item["ai_score"], reverse=True)[:3]

    def generate_health_plan(self, user: UserProfile, products: dict[str, dict[str, Any]]) -> dict[str, Any]:
        constitution = user.constitution_type or self.assess_constitution(user.health_goals)["main_type"]
        recommendations = self.recommend_products(constitution, user.health_goals, products)
        return {
            "user_id": user.user_id,
            "constitution": constitution,
            "recommended_products": recommendations,
            "ai_advice": self._deepseek_plan(user, constitution, recommendations) or self._local_plan(constitution, recommendations),
        }

    def smart_chat(self, message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        message = _clean_text(message)
        if not message:
            return {"reply": "请先告诉我你主要想改善的问题，例如减重、脱发、皮肤、睡眠或男性健康。", "source": "local"}

        ai_reply = self._deepseek_chat(message, context or {})
        if ai_reply:
            return {"reply": ai_reply, "source": provider_status()["provider"], "model": provider_status()["model"]}
        return {"reply": self._local_chat(message), "source": "local"}

    def _deepseek_chat(self, message: str, context: dict[str, Any]) -> str:
        status = provider_status()
        if not status["configured"]:
            return ""
        payload = {
            "message": message,
            "context": context,
            "constraints": [
                "不能诊断疾病，不能承诺疗效",
                "处方药相关问题必须提示先做评估并由医生确认",
                "回答要短，80字以内，给出明确下一步",
            ],
            "schema": {"reply": "中文回复"},
        }
        content = _chat_json(
            _base_system_prompt("你负责 MediSlim 官网 AI 助手对话。"),
            json.dumps(payload, ensure_ascii=False),
            max_completion_tokens=500,
            temperature=0.35,
        )
        if not content:
            return ""
        return _clean_text(content.get("reply", ""))[:240]

    def _deepseek_plan(self, user: UserProfile, constitution: str, recommendations: list[dict[str, Any]]) -> str:
        status = provider_status()
        if not status["configured"]:
            return ""
        payload = {
            "user": {
                "age": user.age,
                "gender": user.gender,
                "goals": user.health_goals,
                "constitution": constitution,
            },
            "recommendations": recommendations,
            "schema": {"advice": "60到120字中文建议"},
        }
        content = _chat_json(
            _base_system_prompt("你负责 MediSlim 健康方案解释。"),
            json.dumps(payload, ensure_ascii=False),
            max_completion_tokens=600,
            temperature=0.35,
        )
        if not content:
            return ""
        return _clean_text(content.get("advice", ""))

    def _local_chat(self, message: str) -> str:
        if "减重" in message or "减肥" in message or "glp" in message.lower():
            return "可以先做 GLP-1 减重评估，系统会先筛查 BMI、禁忌症和目标周期，再决定是否进入医生确认。"
        if "脱发" in message or "掉发" in message:
            return "防脱方案需要先确认脱发类型、持续时间、用药史和禁忌情况，建议从在线评估开始。"
        if "皮肤" in message or "痘" in message:
            return "皮肤管理会先区分痤疮、敏感、暗沉或抗衰需求，再匹配皮肤科方案。"
        if "睡" in message or "失眠" in message:
            return "助眠调理建议先记录入睡、早醒、焦虑和用药情况，再判断是否需要医生介入。"
        if "价格" in message or "多少钱" in message:
            return "当前首月价从199到399元不等，具体取决于品类和评估结果。"
        return "我可以帮你了解产品、评估流程、费用和下一步。请告诉我你最想改善的问题。"

    def _local_plan(self, constitution: str, recommendations: list[dict[str, Any]]) -> str:
        names = "、".join(item["name"] for item in recommendations[:2]) or "体质评估"
        return f"当前更接近{constitution}体质，建议先完成正式评估，再结合{names}做医生确认和后续跟进。"


ASSISTANT = AIHealthAssistant()


def get_ai_assistant_status() -> dict[str, Any]:
    status = provider_status()
    return {
        "available": True,
        "provider_configured": status["configured"],
        "provider": status["provider"],
        "provider_label": status["provider_label"],
        "model": status["model"],
        "fallback": "local",
    }


def smart_chat(message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    return ASSISTANT.smart_chat(message, context)


def generate_health_plan(payload: dict[str, Any], products: dict[str, dict[str, Any]]) -> dict[str, Any]:
    user = UserProfile(
        user_id=str(payload.get("user_id") or "guest"),
        nickname=str(payload.get("nickname") or payload.get("name") or "用户"),
        age=int(payload.get("age") or 0),
        gender=str(payload.get("gender") or ""),
        constitution_type=str(payload.get("constitution_type") or ""),
        health_goals=[str(item) for item in payload.get("health_goals", []) if str(item).strip()],
    )
    return ASSISTANT.generate_health_plan(user, products)
