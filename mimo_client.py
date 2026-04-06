"""Xiaomi MiMo integration for user-facing assessment copy."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


WEEKDAY_CN = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
DEFAULT_BASE_URL = "https://api.xiaomimimo.com/v1"
DEFAULT_MODEL = "mimo-v2-flash"


def provider_settings() -> dict[str, Any]:
    return {
        "enabled": os.getenv("MIMO_ENABLED", "1").lower() not in {"0", "false", "off"},
        "api_key": os.getenv("MIMO_API_KEY", "").strip(),
        "base_url": os.getenv("MIMO_API_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
        "model": os.getenv("MIMO_CHAT_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
        "timeout": float(os.getenv("MIMO_TIMEOUT_SECONDS", "20")),
    }


def provider_status() -> dict[str, Any]:
    settings = provider_settings()
    configured = bool(settings["api_key"]) and settings["enabled"]
    return {
        "configured": configured,
        "enabled": settings["enabled"],
        "model": settings["model"],
        "base_url": settings["base_url"],
    }


def enrich_assessment_result(product: dict[str, Any], answers: dict[str, Any], local_result: dict[str, Any]) -> dict[str, Any]:
    status = provider_status()
    if not status["configured"]:
        return {
            **local_result,
            "ai_provider": "local",
            "ai_model": "",
        }

    prompt = {
        "product": {
            "name": product.get("name", ""),
            "category": product.get("category", ""),
            "description": product.get("description", ""),
            "first_price": product.get("first_price", 0),
            "renew_price": product.get("renew_price", 0),
            "includes": product.get("includes", []),
            "requires_prescription": bool(product.get("requires_prescription")),
        },
        "answers": answers,
        "local_result": local_result,
        "task": {
            "goal": "把本地评估结果改写成清楚、克制、适合消费医疗前台直接展示的中文说明",
            "constraints": [
                "不能改变 eligible、estimated_months、estimated_total_cost、first_month_price、bmi、score、contraindications 等硬判定字段",
                "不能输出诊断结论或保证疗效",
                "有禁忌或不适合下单时，语气要谨慎，建议线下或医师进一步评估",
                "输出必须是 JSON",
            ],
            "schema": {
                "summary": "一句话总结，20到48字",
                "plan": "面向用户的建议正文，60到140字",
                "recommendation": "下一步建议，20到60字",
                "cautions": ["最多3条注意事项，每条10到30字"],
                "followups": ["最多3条建议补充确认的问题，每条10到26字"],
            },
        },
    }
    content = _chat_json(
        _base_system_prompt("你负责 MediSlim 的评估结果说明。"),
        json.dumps(prompt, ensure_ascii=False),
        max_completion_tokens=900,
        temperature=0.3,
    )
    if not content:
        return {
            **local_result,
            "ai_provider": "local",
            "ai_model": "",
        }

    enriched = dict(local_result)
    enriched["ai_provider"] = "mimo"
    enriched["ai_model"] = status["model"]
    enriched["ai_summary"] = _clean_text(content.get("summary", ""))
    enriched["ai_cautions"] = _clean_list(content.get("cautions"))
    enriched["ai_followups"] = _clean_list(content.get("followups"))
    if content.get("plan"):
        enriched["plan"] = _clean_text(content["plan"])
    if content.get("recommendation"):
        enriched["recommendation"] = _clean_text(content["recommendation"])
    return enriched


def enrich_constitution_result(raw_answers: dict[str, Any], local_result: dict[str, Any]) -> dict[str, Any]:
    status = provider_status()
    if not status["configured"]:
        local_result["ai_provider"] = "local"
        local_result["ai_model"] = ""
        return local_result

    prompt = {
        "answers": raw_answers,
        "local_result": local_result,
        "task": {
            "goal": "基于当前体质辨识结果，生成更像真人顾问解释的中文说明",
            "constraints": [
                "不能修改 primary.id、primary.label、scores、recommended_products.product_id",
                "不要输出诊断，不要夸大疗效",
                "diet_tips 和 lifestyle_tips 各给 3 条以内，必须简短可执行",
                "输出必须是 JSON",
            ],
            "schema": {
                "primary_summary": "主导体质的一句话解释，20到48字",
                "primary_focus": "当前最需要关注的方向，24到60字",
                "diet_tips": ["最多3条，每条8到20字"],
                "lifestyle_tips": ["最多3条，每条8到20字"],
                "product_reasons": {
                    "glp1": "可选，12到40字",
                    "sleep": "可选，12到40字",
                    "skin": "可选，12到40字",
                    "mens": "可选，12到40字",
                },
            },
        },
    }
    content = _chat_json(
        _base_system_prompt("你负责 MediSlim 的九型体质辨识解释。"),
        json.dumps(prompt, ensure_ascii=False),
        max_completion_tokens=900,
        temperature=0.4,
    )
    if not content:
        local_result["ai_provider"] = "local"
        local_result["ai_model"] = ""
        return local_result

    result = dict(local_result)
    primary = dict(result.get("primary", {}))
    if content.get("primary_summary"):
        primary["summary"] = _clean_text(content["primary_summary"])
    if content.get("primary_focus"):
        primary["focus"] = _clean_text(content["primary_focus"])
    result["primary"] = primary
    diet_tips = _clean_list(content.get("diet_tips"))
    lifestyle_tips = _clean_list(content.get("lifestyle_tips"))
    if diet_tips:
        result["diet_tips"] = diet_tips
    if lifestyle_tips:
        result["lifestyle_tips"] = lifestyle_tips

    product_reasons = content.get("product_reasons", {}) if isinstance(content.get("product_reasons"), dict) else {}
    updated_products = []
    for item in result.get("recommended_products", []):
        reason = product_reasons.get(item.get("product_id", ""), "")
        updated_products.append({
            **item,
            "reason": _clean_text(reason) if reason else item.get("reason", ""),
        })
    result["recommended_products"] = updated_products
    result["ai_provider"] = "mimo"
    result["ai_model"] = status["model"]
    return result


def _base_system_prompt(extra_role: str) -> str:
    today = dt.datetime.now()
    date_label = today.strftime("%Y年%m月%d日")
    weekday_label = WEEKDAY_CN[today.weekday()]
    return (
        "你是MiMo（中文名称也是MiMo），是小米公司研发的AI智能助手。"
        f"今天的日期：{date_label} {weekday_label}，你的知识截止日期是2024年12月。"
        f"{extra_role}"
        "请只输出 JSON，不要输出 Markdown，不要使用代码块。"
    )


def _chat_json(system_prompt: str, user_prompt: str, *, max_completion_tokens: int, temperature: float) -> dict[str, Any] | None:
    settings = provider_settings()
    url = f"{settings['base_url']}/chat/completions"
    payload = {
        "model": settings["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_completion_tokens": max_completion_tokens,
        "temperature": temperature,
        "top_p": 0.95,
        "stream": False,
        "response_format": {"type": "json_object"},
        "thinking": {"type": "disabled"},
    }
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings['api_key']}",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=settings["timeout"]) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None

    content = _extract_message_content(response_data)
    if not content:
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        extracted = _extract_json_blob(content)
        if not extracted:
            return None
        try:
            return json.loads(extracted)
        except json.JSONDecodeError:
            return None


def _extract_message_content(response_data: dict[str, Any]) -> str:
    choices = response_data.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
            elif isinstance(item, str):
                parts.append(item)
        return "".join(parts).strip()
    return ""


def _extract_json_blob(text: str) -> str:
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if fenced:
        return fenced.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return ""
    return text[start:end + 1]


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _clean_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned = []
    for item in value:
        text = _clean_text(item)
        if text:
            cleaned.append(text)
    return cleaned[:3]
