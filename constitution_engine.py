"""
Nine-constitution assessment helpers for MediSlim.
"""
from __future__ import annotations

from typing import Any


QUESTION_OPTIONS = [
    {"label": "完全没有", "value": 1},
    {"label": "偶尔", "value": 2},
    {"label": "有时", "value": 3},
    {"label": "经常", "value": 4},
    {"label": "非常明显", "value": 5},
]


CONSTITUTIONS = {
    "balanced": {
        "label": "平和质",
        "summary": "整体状态较平衡，适合做轻干预和长期维持。",
        "focus": "维持作息、饮食平衡和体重管理节奏。",
        "products": ["glp1", "skin", "sleep"],
        "diet_tips": ["规律三餐", "控制过量零食", "保持蛋白质和膳食纤维稳定摄入"],
        "lifestyle_tips": ["每周运动 3-4 次", "固定入睡时间", "每月复盘体重和精神状态"],
    },
    "qi_deficiency": {
        "label": "气虚质",
        "summary": "容易疲劳、气短、恢复慢，更适合先补基础体能。",
        "focus": "先把精力和恢复力拉起来，再推进减重或男科方案。",
        "products": ["sleep", "mens", "glp1"],
        "diet_tips": ["增加优质蛋白", "减少生冷", "早餐尽量吃热食"],
        "lifestyle_tips": ["避免过度熬夜", "优先低到中强度训练", "午后减少高糖波动"],
    },
    "yang_deficiency": {
        "label": "阳虚质",
        "summary": "怕冷、手脚凉、代谢偏慢，适合温和拉高代谢活性。",
        "focus": "先改善基础循环，再做体重、睡眠和男性健康管理。",
        "products": ["glp1", "sleep", "mens"],
        "diet_tips": ["少冰冷饮食", "增加温热食材", "晚餐不过饱不过晚"],
        "lifestyle_tips": ["固定晨起时间", "增加晒太阳和步行", "减少久坐受凉"],
    },
    "yin_deficiency": {
        "label": "阴虚质",
        "summary": "容易口干、烦躁、睡眠浅，适合先修复睡眠和刺激阈值。",
        "focus": "优先处理睡眠、皮肤屏障和夜间情绪性进食。",
        "products": ["sleep", "skin", "glp1"],
        "diet_tips": ["提高饮水量", "减少辛辣酒精", "增加高水分蔬果"],
        "lifestyle_tips": ["减少夜间屏幕刺激", "控制咖啡因时间", "用舒缓运动代替极限训练"],
    },
    "phlegm_dampness": {
        "label": "痰湿质",
        "summary": "更容易体重上升、身体困重和饭后犯困，是减重高潜人群。",
        "focus": "优先做体重、饮食结构和作息管理。",
        "products": ["glp1", "sleep", "skin"],
        "diet_tips": ["控制精制碳水", "减少高油高糖", "提高膳食纤维比例"],
        "lifestyle_tips": ["饭后轻活动", "保持日步数", "连续记录体重和围度"],
    },
    "damp_heat": {
        "label": "湿热质",
        "summary": "容易长痘、口苦、油脂旺盛，适合先控炎和降低代谢压力。",
        "focus": "皮肤管理与体重控制适合联动推进。",
        "products": ["skin", "glp1", "sleep"],
        "diet_tips": ["减少辛辣油炸", "减少含糖饮料", "增加蔬菜和水分摄入"],
        "lifestyle_tips": ["规律作息", "增加出汗频率", "减少长期外卖高盐高油"],
    },
    "blood_stasis": {
        "label": "血瘀质",
        "summary": "循环偏弱、恢复慢，常见暗沉、僵硬或局部不适。",
        "focus": "适合把皮肤、恢复和慢性健康管理结合起来看。",
        "products": ["skin", "mens", "sleep"],
        "diet_tips": ["减少反式脂肪", "增加深色蔬菜", "保持足量饮水"],
        "lifestyle_tips": ["避免久坐", "坚持低强度有氧", "定期复查关键指标"],
    },
    "qi_stagnation": {
        "label": "气郁质",
        "summary": "压力和情绪波动会明显影响睡眠、食欲和执行力。",
        "focus": "先降低波动，再推进减重和皮肤方案更稳。",
        "products": ["sleep", "glp1", "skin"],
        "diet_tips": ["减少情绪性进食", "固定进餐时间", "避免夜间暴食"],
        "lifestyle_tips": ["建立减压习惯", "选择可持续计划", "减少社交性熬夜"],
    },
    "special_diathesis": {
        "label": "特禀质",
        "summary": "过敏、敏感或特殊体质倾向更强，安全边界要放在第一位。",
        "focus": "优先明确过敏史和禁忌，再进入具体方案。",
        "products": ["skin", "sleep"],
        "diet_tips": ["记录触发食物", "减少补剂叠加", "保持饮食简单稳定"],
        "lifestyle_tips": ["先小剂量尝试", "保留既往过敏史", "重要方案优先人工复核"],
    },
}


QUESTIONS = [
    {
        "id": "q1",
        "text": "平时是否容易疲劳、懒得说话或运动后恢复慢？",
        "weights": {"qi_deficiency": 3, "yang_deficiency": 1},
    },
    {
        "id": "q2",
        "text": "是否经常怕冷、手脚发凉，尤其在空调房更明显？",
        "weights": {"yang_deficiency": 3, "qi_deficiency": 1},
    },
    {
        "id": "q3",
        "text": "是否常有口干、咽干、心烦、睡眠浅或容易上火？",
        "weights": {"yin_deficiency": 3, "damp_heat": 1},
    },
    {
        "id": "q4",
        "text": "是否容易体重增加、饭后犯困、身体困重或舌苔偏厚？",
        "weights": {"phlegm_dampness": 3, "qi_deficiency": 1},
    },
    {
        "id": "q5",
        "text": "是否容易长痘、口苦口黏、油脂旺盛或大便黏滞？",
        "weights": {"damp_heat": 3, "phlegm_dampness": 1},
    },
    {
        "id": "q6",
        "text": "是否容易情绪压着、烦闷叹气，压力大时失眠或暴食？",
        "weights": {"qi_stagnation": 3, "yin_deficiency": 1},
    },
    {
        "id": "q7",
        "text": "是否常觉得肤色暗沉、身体固定部位不适或恢复慢？",
        "weights": {"blood_stasis": 3},
    },
    {
        "id": "q8",
        "text": "是否有明显过敏、鼻炎、皮肤敏感或多种食物药物不耐受？",
        "weights": {"special_diathesis": 3, "yin_deficiency": 1},
    },
    {
        "id": "q9",
        "text": "是否整体状态平稳，睡眠、食欲和精力都比较均衡？",
        "weights": {"balanced": 3},
        "reverse": True,
    },
    {
        "id": "q10",
        "text": "是否经常早上起床困难、白天脑雾明显、执行力偏低？",
        "weights": {"qi_deficiency": 2, "phlegm_dampness": 2},
    },
    {
        "id": "q11",
        "text": "是否经常夜间燥热、入睡慢、睡着后易醒？",
        "weights": {"yin_deficiency": 2, "qi_stagnation": 2},
    },
    {
        "id": "q12",
        "text": "是否吃得不多也容易长胖，减重后又容易反弹？",
        "weights": {"phlegm_dampness": 3, "yang_deficiency": 1},
    },
    {
        "id": "q13",
        "text": "是否久坐后肩颈僵硬、末梢循环差、运动后酸胀恢复慢？",
        "weights": {"blood_stasis": 2, "yang_deficiency": 1},
    },
    {
        "id": "q14",
        "text": "是否情绪一波动就会明显影响睡眠、皮肤或食欲？",
        "weights": {"qi_stagnation": 3, "damp_heat": 1},
    },
    {
        "id": "q15",
        "text": "是否更适应温和、规律、少刺激的生活节奏，否则身体反应明显？",
        "weights": {"special_diathesis": 2, "balanced": 1, "yin_deficiency": 1},
    },
]


def get_questionnaire() -> dict[str, Any]:
    return {
        "title": "AI 九型体质辨识",
        "description": "15 题快速识别当前偏向体质，用于推荐更稳妥的干预方向。",
        "total": len(QUESTIONS),
        "questions": [{**question, "options": QUESTION_OPTIONS} for question in QUESTIONS],
    }


def analyze_constitution(raw_answers: dict[str, Any]) -> dict[str, Any]:
    scores = {constitution_id: 0 for constitution_id in CONSTITUTIONS}

    for question in QUESTIONS:
        value = _normalize_answer(raw_answers.get(question["id"], 1))
        if question.get("reverse"):
            value = 6 - value
        for constitution_id, weight in question["weights"].items():
            scores[constitution_id] += value * weight

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    primary_id, primary_score = ranked[0]
    normalized = _normalize_scores(scores)
    profile = CONSTITUTIONS[primary_id]

    return {
        "primary": {
            "id": primary_id,
            "label": profile["label"],
            "score": primary_score,
            "normalized_score": normalized[primary_id],
            "summary": profile["summary"],
            "focus": profile["focus"],
        },
        "secondary": [
            {
                "id": constitution_id,
                "label": CONSTITUTIONS[constitution_id]["label"],
                "score": score,
                "normalized_score": normalized[constitution_id],
            }
            for constitution_id, score in ranked[1:3]
        ],
        "scores": [
            {
                "id": constitution_id,
                "label": CONSTITUTIONS[constitution_id]["label"],
                "score": score,
                "normalized_score": normalized[constitution_id],
            }
            for constitution_id, score in ranked
        ],
        "diet_tips": profile["diet_tips"],
        "lifestyle_tips": profile["lifestyle_tips"],
        "recommended_products": [
            {
                "product_id": product_id,
                "reason": _product_reason(primary_id, product_id),
            }
            for product_id in profile["products"]
        ],
        "disclaimer": "体质辨识仅用于健康管理分层，不替代医师诊断或处方决策。",
    }


def _normalize_answer(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 1
    return max(1, min(5, parsed))


def _normalize_scores(scores: dict[str, int]) -> dict[str, float]:
    max_score = max(scores.values()) if scores else 1
    return {
        constitution_id: round(score / max_score * 100, 1) if max_score else 0.0
        for constitution_id, score in scores.items()
    }


def _product_reason(constitution_id: str, product_id: str) -> str:
    reasons = {
        "glp1": {
            "phlegm_dampness": "痰湿偏重时，更适合先做体重与代谢管理。",
            "yang_deficiency": "阳虚伴代谢低活性时，减重方案更需要节奏化推进。",
            "qi_stagnation": "压力型进食和睡眠波动会直接影响减重执行。",
            "default": "体重和代谢管理是这一体质的重要抓手。",
        },
        "sleep": {
            "yin_deficiency": "阴虚和心烦型人群，往往先把睡眠修复好更稳。",
            "qi_stagnation": "气郁型压力最先体现在入睡和睡眠质量上。",
            "qi_deficiency": "气虚恢复慢时，睡眠和精力管理是基础工程。",
            "default": "睡眠管理有助于降低后续方案执行阻力。",
        },
        "skin": {
            "damp_heat": "湿热偏重时，皮肤炎症和油脂问题更容易反复。",
            "blood_stasis": "血瘀型常见肤色和恢复速度问题，皮肤管理收益较高。",
            "special_diathesis": "敏感体质需要更谨慎的皮肤与药物方案。",
            "default": "皮肤状态是当前体质外显的关键窗口。",
        },
        "mens": {
            "qi_deficiency": "气虚或阳虚时，精力和男性健康体验往往同步受影响。",
            "yang_deficiency": "阳虚型代谢和活力偏弱，适合做男性健康综合干预。",
            "blood_stasis": "循环和恢复问题会拉低男性健康方案效果。",
            "default": "适合作为体能、精力和恢复能力的延伸管理。",
        },
    }
    product_reasons = reasons.get(product_id, {})
    return product_reasons.get(constitution_id, product_reasons.get("default", "建议结合完整评估结果进一步确认。"))
