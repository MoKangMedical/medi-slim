"""
MediSlim — 中国版Medvi消费医疗平台
完全复刻Medvi极简架构：只做流量层，医疗合规全外包
技术栈：Python原生HTTP + 微信小程序风格前端
"""
import os
import json
import urllib.parse
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

from constitution_engine import get_questionnaire, analyze_constitution
from order_flow import create_order_record, apply_order_action, decorate_order
from partner_hub import (
    PARTNERS,
    create_payment_intent,
    mark_payment_paid,
    create_refund,
    ensure_consultation,
    get_consultation,
    ensure_prescription,
    get_prescription,
    ensure_pharmacy_order,
    get_pharmacy_order,
    get_tracking,
    sync_order_partners,
    partner_dashboard,
)
from storage import BASE_DIR, load_json, save_json, load_orders, save_orders, migrate_legacy_orders, now_iso, short_id
from subscription_engine import (
    list_subscriptions,
    get_subscription,
    sync_subscription_with_order,
    apply_subscription_action,
    create_renewal_order,
    due_subscriptions,
)
from wecom_handoff import (
    list_threads,
    upsert_thread,
    assign_thread,
    apply_thread_action,
    add_thread_message,
    queue_summary,
)

try:
    from content_engine.tracking import track_event, get_funnel, get_content_performance
except Exception:  # pragma: no cover - optional integration
    track_event = None
    get_funnel = None
    get_content_performance = None

# ========== 配置 ==========
class Config:
    APP_NAME = "MediSlim 轻健康"
    VERSION = "1.0.0"

    PRODUCTS = {
        "glp1": {
            "name": "GLP-1 科学减重",
            "emoji": "🔥",
            "description": "司美格鲁肽/替尔泊肽，医生指导，科学减重",
            "image": "/static/media/products/glp1.svg",
            "image_alt": "GLP-1 科学减重产品展示图",
            "first_price": 399,
            "renew_price": 599,
            "unit": "月",
            "includes": ["医师评估", "个性化方案", "药品配送", "24h在线支持", "体重管理报告"],
            "requires_prescription": True,
            "category": "减肥",
        },
        "hair": {
            "name": "防脱生发",
            "emoji": "💇",
            "description": "米诺地尔/非那雄胺，专业防脱方案",
            "image": "/static/media/products/hair.svg",
            "image_alt": "防脱生发产品展示图",
            "first_price": 199,
            "renew_price": 299,
            "unit": "月",
            "includes": ["毛囊检测评估", "药物方案", "每月随访", "生发跟踪"],
            "requires_prescription": True,
            "category": "脱发",
        },
        "skin": {
            "name": "皮肤管理",
            "emoji": "🧴",
            "description": "祛痘/美白/抗衰，皮肤科医生在线诊疗",
            "image": "/static/media/products/skin.svg",
            "image_alt": "皮肤管理产品展示图",
            "first_price": 299,
            "renew_price": 399,
            "unit": "月",
            "includes": ["皮肤评估", "个性化方案", "药品/护肤品配送", "定期随访"],
            "requires_prescription": False,
            "category": "皮肤",
        },
        "mens": {
            "name": "男性健康",
            "emoji": "💪",
            "description": "精力管理/睾酮/前列腺，专业男性健康",
            "image": "/static/media/products/mens.svg",
            "image_alt": "男性健康产品展示图",
            "first_price": 399,
            "renew_price": 599,
            "unit": "月",
            "includes": ["健康评估", "检验建议", "药物方案", "隐私配送"],
            "requires_prescription": True,
            "category": "男性",
        },
        "sleep": {
            "name": "助眠调理",
            "emoji": "😴",
            "description": "失眠/焦虑/褪黑素，科学改善睡眠",
            "image": "/static/media/products/sleep.svg",
            "image_alt": "助眠调理产品展示图",
            "first_price": 199,
            "renew_price": 299,
            "unit": "月",
            "includes": ["睡眠评估", "行为指导", "必要时药物", "睡眠日记跟踪"],
            "requires_prescription": False,
            "category": "睡眠",
        },
    }

    ASSESSMENT_QUESTIONS = {
        "glp1": [
            {"id": 1, "text": "您的身高是多少(cm)？", "type": "input", "field": "height"},
            {"id": 2, "text": "您的体重是多少(kg)？", "type": "input", "field": "weight"},
            {"id": 3, "text": "您的目标体重是多少(kg)？", "type": "input", "field": "target_weight"},
            {"id": 4, "text": "是否有糖尿病或糖尿病前期？", "type": "choice", "options": ["是", "否", "不确定"]},
            {"id": 5, "text": "是否尝试过其他减肥方法？", "type": "choice", "options": ["节食", "运动", "减肥药", "均未尝试"]},
            {"id": 6, "text": "是否有甲状腺疾病？", "type": "choice", "options": ["是", "否"]},
            {"id": 7, "text": "是否有胰腺炎病史？", "type": "choice", "options": ["是", "否"]},
            {"id": 8, "text": "是否怀孕或备孕中？", "type": "choice", "options": ["是", "否", "不适用"]},
            {"id": 9, "text": "是否有进食障碍史？", "type": "choice", "options": ["是", "否"]},
            {"id": 10, "text": "希望多久达到目标？", "type": "choice", "options": ["3个月", "6个月", "1年", "不急"]},
        ],
        "hair": [
            {"id": 1, "text": "脱发类型？", "type": "choice", "options": ["M型发际线", "头顶稀疏", "整体稀疏", "斑秃"]},
            {"id": 2, "text": "脱发持续多长时间？", "type": "choice", "options": ["不到半年", "半年~2年", "2年以上"]},
            {"id": 3, "text": "家族是否有脱发史？", "type": "choice", "options": ["父亲", "母亲", "双方", "无"]},
            {"id": 4, "text": "是否使用过防脱产品？", "type": "choice", "options": ["米诺地尔", "非那雄胺", "其他", "未使用"]},
            {"id": 5, "text": "是否有药物过敏？", "type": "choice", "options": ["是", "否"]},
            {"id": 6, "text": "是否有肝脏疾病？", "type": "choice", "options": ["是", "否"]},
        ],
        "skin": [
            {"id": 1, "text": "主要皮肤问题？", "type": "choice", "options": ["痘痘/痤疮", "色斑/暗沉", "皱纹/松弛", "敏感/红血丝"]},
            {"id": 2, "text": "皮肤类型？", "type": "choice", "options": ["油性", "干性", "混合", "敏感"]},
            {"id": 3, "text": "问题持续时间？", "type": "choice", "options": ["不到1个月", "1-6个月", "6个月以上"]},
            {"id": 4, "text": "是否使用过处方药？", "type": "choice", "options": ["维A酸", "抗生素", "激素类", "未使用"]},
            {"id": 5, "text": "是否有药物过敏？", "type": "choice", "options": ["是", "否"]},
        ],
        "mens": [
            {"id": 1, "text": "主要困扰？", "type": "choice", "options": ["精力不足", "性功能", "前列腺", "其他"]},
            {"id": 2, "text": "年龄？", "type": "input", "field": "age"},
            {"id": 3, "text": "是否有心血管疾病？", "type": "choice", "options": ["是", "否"]},
            {"id": 4, "text": "是否检测过睾酮水平？", "type": "choice", "options": ["是（偏低）", "是（正常）", "未检测"]},
            {"id": 5, "text": "是否有药物过敏？", "type": "choice", "options": ["是", "否"]},
        ],
        "sleep": [
            {"id": 1, "text": "失眠类型？", "type": "choice", "options": ["入睡困难", "易醒", "早醒", "多梦"]},
            {"id": 2, "text": "失眠持续时间？", "type": "choice", "options": ["不到1周", "1-4周", "1-3个月", "3个月以上"]},
            {"id": 3, "text": "是否伴有焦虑/抑郁？", "type": "choice", "options": ["是", "否", "不确定"]},
            {"id": 4, "text": "是否使用过助眠药物？", "type": "choice", "options": ["褪黑素", "安定类", "中成药", "未使用"]},
            {"id": 5, "text": "每天睡眠时长？", "type": "choice", "options": ["不到4小时", "4-6小时", "6-8小时"]},
        ],
    }

    PARTNER_HOSPITALS = [
        {
            "id": "p001",
            "name": "京东健康互联网医院",
            "specialties": ["全科", "皮肤科", "男科"],
            "type": "互联网医院",
            "logo": "/static/media/partners/jd-health.svg",
            "logo_alt": "京东健康互联网医院标识",
        },
        {
            "id": "p002",
            "name": "微医互联网医院",
            "specialties": ["全科", "内分泌", "皮肤科"],
            "type": "互联网医院",
            "logo": "/static/media/partners/wedoctor.svg",
            "logo_alt": "微医互联网医院标识",
        },
        {
            "id": "p003",
            "name": "好大夫在线",
            "specialties": ["全科", "脱发", "减重"],
            "type": "互联网医院",
            "logo": "/static/media/partners/haodf.svg",
            "logo_alt": "好大夫在线标识",
        },
        {
            "id": "p004",
            "name": "丁香园互联网医院",
            "specialties": ["全科", "睡眠", "皮肤科"],
            "type": "互联网医院",
            "logo": "/static/media/partners/dxy.svg",
            "logo_alt": "丁香园互联网医院标识",
        },
    ]

    PARTNER_PHARMACIES = [
        {
            "id": "f001",
            "name": "大参林大药房",
            "type": "连锁药房",
            "delivery": "顺丰/京东",
            "logo": "/static/media/partners/dashenlin.svg",
            "logo_alt": "大参林大药房标识",
        },
        {
            "id": "f002",
            "name": "益丰大药房",
            "type": "连锁药房",
            "delivery": "顺丰",
            "logo": "/static/media/partners/yifeng.svg",
            "logo_alt": "益丰大药房标识",
        },
    ]

    PARTNER_PRODUCT_SUPPLIERS = [
        {
            "id": "s001",
            "name": "华东医药",
            "type": "GLP-1 药品方",
            "supports": ["GLP-1减重", "处方减重"],
            "logo": "/static/media/partners/huadong.svg",
            "logo_alt": "华东医药标识",
        },
        {
            "id": "s002",
            "name": "仁会生物",
            "type": "GLP-1 药品方",
            "supports": ["GLP-1减重", "代谢管理"],
            "logo": "/static/media/partners/renhui.svg",
            "logo_alt": "仁会生物标识",
        },
        {
            "id": "s003",
            "name": "信达生物",
            "type": "GLP-1 药品方",
            "supports": ["GLP-1减重", "代谢管理"],
            "logo": "/static/media/partners/innovent.svg",
            "logo_alt": "信达生物标识",
        },
        {
            "id": "s004",
            "name": "三生制药",
            "type": "脱发药品方",
            "supports": ["防脱生发", "男性健康"],
            "logo": "/static/media/partners/3sbio.svg",
            "logo_alt": "三生制药标识",
        },
        {
            "id": "s005",
            "name": "振东制药",
            "type": "脱发药品方",
            "supports": ["防脱生发", "处方药供应"],
            "logo": "/static/media/partners/zhendong.svg",
            "logo_alt": "振东制药标识",
        },
        {
            "id": "s006",
            "name": "SC 食品工厂",
            "type": "药食同源工厂",
            "supports": ["祛湿轻体", "气血调养", "助眠调理"],
            "logo": "/static/media/partners/sc-food.svg",
            "logo_alt": "SC 食品工厂标识",
        },
        {
            "id": "s007",
            "name": "保健食品企业",
            "type": "蓝帽子供应方",
            "supports": ["益生菌", "胶原蛋白", "营养补充"],
            "logo": "/static/media/partners/nutrition-gmp.svg",
            "logo_alt": "保健食品企业标识",
        },
    ]

# ========== 数据存储 ==========
TEMPLATES_DIR = BASE_DIR / "templates"
CONTENT_CATALOG_PATH = BASE_DIR / "content_engine" / "output" / "catalog.json"
STATIC_CONTENT_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".wav": "audio/wav",
    ".webp": "image/webp",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
}


def load_data(name):
    return load_json(name, {})


def save_data(name, data):
    save_json(name, data)


def static_content_type(filepath):
    return STATIC_CONTENT_TYPES.get(Path(filepath).suffix.lower(), "application/octet-stream")


ATTRIBUTION_KEYS = [
    "ref",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_term",
    "source",
    "landing_path",
]


def extract_attribution(data):
    attribution = {}
    for key in ATTRIBUTION_KEYS:
        value = data.get(key, "")
        if isinstance(value, str):
            value = value.strip()
        if value:
            attribution[key] = value
    return attribution


def source_from_attribution(attribution, fallback="direct"):
    return (
        attribution.get("source")
        or attribution.get("utm_source")
        or attribution.get("ref")
        or fallback
    )


def track_attribution_event(attribution, event_type, extra=None):
    ref = (attribution or {}).get("ref", "")
    if not ref or not track_event:
        return None

    try:
        return track_event(ref, event_type, extra or {})
    except Exception:
        return None


def sync_subscription_state(order):
    product = Config.PRODUCTS.get(order.get("product_id", ""), {})
    return sync_subscription_with_order(order, product)


def create_wecom_task_for_lead(lead):
    return upsert_thread(
        phone=lead.get("phone", ""),
        name=lead.get("name", ""),
        product_id=lead.get("product_id", ""),
        source=lead.get("source", "direct"),
        scenario="lead",
        note="新线索进入企微承接队列",
        attribution=lead.get("attribution", {}),
    )


def create_wecom_task_for_order(order, scenario="order", note=""):
    return upsert_thread(
        phone=order.get("phone", ""),
        name=order.get("name", ""),
        product_id=order.get("product_id", ""),
        source=source_from_attribution(order.get("attribution", {}), "direct"),
        scenario=scenario,
        user_id=order.get("user_id", ""),
        order_id=order.get("id", ""),
        note=note,
        attribution=order.get("attribution", {}),
    )


def sync_crm_user(user):
    crm_users = load_data("crm_users")
    existing_id = next(
        (crm_id for crm_id, crm_user in crm_users.items() if crm_user.get("phone") == user.get("phone")),
        None,
    )

    crm_id = existing_id or user["id"]
    current = crm_users.get(crm_id, {})
    current.update({
        "id": crm_id,
        "name": user.get("name", current.get("name", "用户")),
        "phone": user.get("phone", current.get("phone", "")),
        "channel": current.get("channel", "direct"),
        "tags": current.get("tags", []),
        "lifecycle": current.get("lifecycle", "lead"),
        "health_profile": current.get("health_profile", {}),
        "orders": current.get("orders", []),
        "interactions": current.get("interactions", []),
        "value_score": current.get("value_score", 0),
        "created_at": current.get("created_at", user.get("created_at", now_iso())),
        "updated_at": now_iso(),
        "attribution": current.get("attribution", {}),
    })
    crm_users[crm_id] = current
    save_data("crm_users", crm_users)


def attach_order_to_user(user_id, phone, order_id, order_status="pending_payment"):
    users = load_data("users")
    user = users.get(user_id)
    if user:
        user.setdefault("orders", [])
        if order_id not in user["orders"]:
            user["orders"].append(order_id)
        user["latest_order_status"] = order_status
        users[user_id] = user
        save_data("users", users)

    crm_users = load_data("crm_users")
    crm_match_id = next(
        (crm_id for crm_id, crm_user in crm_users.items() if crm_user.get("phone") == phone or crm_user.get("id") == user_id),
        None,
    )
    if crm_match_id:
        crm_user = crm_users[crm_match_id]
        crm_user.setdefault("orders", [])
        if order_id not in crm_user["orders"]:
            crm_user["orders"].append(order_id)
        lifecycle_rank = {
            "lead": 0,
            "assessed": 1,
            "first_order": 2,
            "active": 3,
            "vip": 4,
            "churned": 5,
        }
        current_stage = crm_user.get("lifecycle", "lead")
        target_stage = current_stage
        if order_status in {"pending_payment", "paid", "doctor_review", "approved", "pharmacy_processing", "shipped"}:
            target_stage = "first_order"
        elif order_status in {"delivered", "completed"}:
            target_stage = "vip" if len(crm_user["orders"]) >= 2 else "active"
        if lifecycle_rank.get(current_stage, 0) < lifecycle_rank.get(target_stage, 0):
            crm_user["lifecycle"] = target_stage
        crm_user["updated_at"] = now_iso()
        crm_users[crm_match_id] = crm_user
        save_data("crm_users", crm_users)


def mark_lead_converted(phone, order_id, user_id=""):
    leads = load_data("leads")
    candidates = [
        lead
        for lead in leads.values()
        if lead.get("phone") == phone
    ]
    if not candidates:
        return

    candidates.sort(key=lambda lead: lead.get("updated_at") or lead.get("created_at") or "", reverse=True)
    latest = candidates[0]
    latest["status"] = "converted"
    latest["order_id"] = order_id
    latest["user_id"] = user_id or latest.get("user_id", "")
    latest["converted_at"] = now_iso()
    latest["updated_at"] = now_iso()
    leads[latest["id"]] = latest
    save_data("leads", leads)
    sync_lead_to_crm(latest)


def sync_lead_to_crm(lead):
    crm_users = load_data("crm_users")
    crm_match_id = next(
        (crm_id for crm_id, crm_user in crm_users.items() if crm_user.get("phone") == lead.get("phone")),
        None,
    )

    crm_id = crm_match_id or short_id()
    crm_user = crm_users.get(crm_id, {})
    merged_tags = [tag for tag in crm_user.get("tags", []) + [lead.get("product_id", "")] if tag]
    crm_user.update({
        "id": crm_id,
        "name": lead.get("name") or crm_user.get("name", "潜在线索"),
        "phone": lead.get("phone", crm_user.get("phone", "")),
        "channel": lead.get("source", crm_user.get("channel", "direct")),
        "tags": sorted(set(merged_tags)),
        "lifecycle": crm_user.get("lifecycle", "lead"),
        "health_profile": crm_user.get("health_profile", {}),
        "orders": crm_user.get("orders", []),
        "interactions": crm_user.get("interactions", []),
        "value_score": crm_user.get("value_score", 0),
        "created_at": crm_user.get("created_at", lead.get("created_at", now_iso())),
        "updated_at": now_iso(),
        "latest_lead_id": lead["id"],
        "attribution": {**crm_user.get("attribution", {}), **lead.get("attribution", {})},
    })
    crm_users[crm_id] = crm_user
    save_data("crm_users", crm_users)


class LeadManager:
    @staticmethod
    def create_lead(name, phone, product_id="", source="homepage", note="", attribution=None):
        leads = load_data("leads")
        attribution = attribution or {}
        normalized_source = source_from_attribution(attribution, source or "homepage")
        existing = next(
            (
                lead
                for lead in leads.values()
                if lead.get("phone") == phone and lead.get("product_id") == product_id and lead.get("source") == normalized_source
            ),
            None,
        )

        if existing:
            existing.update({
                "name": name or existing.get("name", "潜在线索"),
                "note": note or existing.get("note", ""),
                "attribution": {**existing.get("attribution", {}), **attribution},
                "updated_at": now_iso(),
            })
            leads[existing["id"]] = existing
            save_data("leads", leads)
            sync_lead_to_crm(existing)
            create_wecom_task_for_lead(existing)
            return existing

        lead = {
            "id": short_id(),
            "name": name or "潜在线索",
            "phone": phone,
            "product_id": product_id,
            "source": normalized_source,
            "note": note,
            "status": "new",
            "attribution": attribution,
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        leads[lead["id"]] = lead
        save_data("leads", leads)
        sync_lead_to_crm(lead)
        create_wecom_task_for_lead(lead)
        track_attribution_event(attribution, "landing", {
            "phone": phone[-4:],
            "product_id": product_id,
            "source": normalized_source,
        })
        return lead


def reconcile_records():
    for user in load_data("users").values():
        sync_crm_user(user)

    for lead in load_data("leads").values():
        sync_lead_to_crm(lead)
        try:
            create_wecom_task_for_lead(lead)
        except Exception:
            pass

    for order in load_orders().values():
        attach_order_to_user(order.get("user_id", ""), order.get("phone", ""), order["id"], order.get("status", "pending_payment"))
        mark_lead_converted(order.get("phone", ""), order["id"], order.get("user_id", ""))
        sync_order_partners(order)
        sync_subscription_state(order)

# ========== AI引擎 ==========
class SlimAIEngine:
    @staticmethod
    def analyze(product_id, answers):
        product = Config.PRODUCTS.get(product_id, {})
        questions = Config.ASSESSMENT_QUESTIONS.get(product_id, [])
        if not product:
            return {
                "eligible": False,
                "reason": "产品不存在",
            }

        if product_id == "glp1":
            return SlimAIEngine._analyze_glp1(product, answers, questions)
        elif product_id == "hair":
            return SlimAIEngine._analyze_hair(product, answers, questions)
        else:
            return SlimAIEngine._analyze_generic(product, product_id, answers, questions)

    @staticmethod
    def _analyze_glp1(product, answers, questions):
        try:
            height = float(answers.get("1", "170")) / 100
            weight = float(answers.get("2", "80"))
            target = float(answers.get("3", "70"))
        except (TypeError, ValueError):
            height, weight, target = 1.70, 80.0, 70.0

        bmi = round(weight / (height ** 2), 1)
        need = round(weight - target, 1)

        # 禁忌症筛查
        contraindications = []
        if answers.get("4") == "是":
            contraindications.append("糖尿病（需医师评估用药方案）")
        if answers.get("6") == "是":
            contraindications.append("甲状腺疾病（需排除MTC风险）")
        if answers.get("7") == "是":
            contraindications.append("胰腺炎病史（GLP-1相对禁忌）")
        if answers.get("8") == "是":
            contraindications.append("怀孕/备孕（禁用GLP-1）")
        if answers.get("9") == "是":
            contraindications.append("进食障碍史（需心理评估）")

        if contraindications:
            return {
                "product": product["name"],
                "eligible": False,
                "reason": "存在用药禁忌，建议线下就诊",
                "contraindications": contraindications,
                "recommendation": "请前往三甲医院内分泌科进行详细评估",
            }

        # BMI评估
        if bmi >= 28:
            urgency = "high"
            plan = "强烈推荐GLP-1治疗 + 饮食运动指导"
        elif bmi >= 24:
            urgency = "medium"
            plan = "推荐GLP-1辅助减重 + 生活方式干预"
        elif bmi >= 18.5:
            urgency = "low"
            plan = "BMI正常，如确有减重需求建议先尝试生活方式干预"
        else:
            return {
                "product": product["name"],
                "eligible": False,
                "reason": f"BMI {bmi} 已偏瘦，不建议药物减重",
                "recommendation": "如有身体形象困扰，建议心理咨询",
            }

        # 估算方案
        months = max(3, min(12, round(need / 3)))  # 每月约减3kg
        est_cost = product["first_price"] + product["renew_price"] * (months - 1)

        return {
            "product": product["name"],
            "eligible": True,
            "bmi": bmi,
            "weight_to_lose": need,
            "urgency": urgency,
            "plan": plan,
            "estimated_months": months,
            "estimated_total_cost": est_cost,
            "first_month_price": product["first_price"],
            "includes": product["includes"],
            "next_step": "order",
        }

    @staticmethod
    def _analyze_hair(product, answers, questions):
        severity_map = {
            "不到半年": "early",
            "半年~2年": "moderate",
            "2年以上": "advanced",
        }
        severity = severity_map.get(answers.get("2", ""), "unknown")

        family_history = answers.get("3", "无") != "无"
        prior_treatment = answers.get("4") not in ["未使用", None]
        has_liver = answers.get("6") == "是"

        if has_liver:
            return {
                "product": product["name"],
                "eligible": False,
                "reason": "肝脏疾病患者不建议使用口服非那雄胺",
                "recommendation": "可考虑外用米诺地尔（无需口服）",
            }

        if severity == "early":
            plan = "外用米诺地尔 + 口服非那雄胺（6个月疗程）"
            months = 6
        elif severity == "moderate":
            plan = "外用米诺地尔 + 口服非那雄胺 + 微针辅助（12个月疗程）"
            months = 12
        else:
            plan = "综合治疗方案（含口服+外用+辅助），12个月起"
            months = 12

        return {
            "product": product["name"],
            "eligible": True,
            "severity": severity,
            "family_history": family_history,
            "prior_treatment": prior_treatment,
            "plan": plan,
            "estimated_months": months,
            "estimated_total_cost": product["first_price"] + product["renew_price"] * (months - 1),
            "first_month_price": product["first_price"],
            "includes": product["includes"],
            "next_step": "order",
        }

    @staticmethod
    def _analyze_generic(product, product_id, answers, questions):
        positive = sum(1 for k, v in answers.items() if v in ["是", "严重", "经常"])
        total = len(questions)
        score = round(positive / max(total, 1) * 100, 1)

        if score >= 60:
            urgency, plan = "high", f"建议立即开始{product.get('name', '治疗')}方案"
        elif score >= 30:
            urgency, plan = "medium", f"推荐{product.get('name', '调理')}方案"
        else:
            urgency, plan = "low", "症状较轻，可先尝试生活方式调整"

        return {
            "product": product.get("name", ""),
            "eligible": True,
            "urgency": urgency,
            "score": score,
            "plan": plan,
            "estimated_months": 3,
            "estimated_total_cost": product.get("first_price", 0) + product.get("renew_price", 0) * 2,
            "first_month_price": product.get("first_price", 0),
            "includes": product.get("includes", []),
            "next_step": "order",
        }

# ========== 订单管理 ==========
class OrderManager:
    @staticmethod
    def create_order(user_id, product_id, assessment_result, name, phone, address, attribution=None, order_kind="", subscription_id=""):
        orders_db = load_orders()
        product = Config.PRODUCTS.get(product_id, {})
        order = create_order_record(
            user_id,
            product_id,
            product.get("name", ""),
            product.get("first_price", 0),
            name,
            phone,
            address,
            assessment_result,
            attribution=attribution,
        )
        if order_kind:
            order["order_kind"] = order_kind
        if subscription_id:
            order["subscription_id"] = subscription_id
        orders_db[order["id"]] = order
        save_orders(orders_db)
        attach_order_to_user(user_id, phone, order["id"], order["status"])
        mark_lead_converted(phone, order["id"], user_id)
        sync_order_partners(order)
        sync_subscription_state(order)
        create_wecom_task_for_order(order, scenario="renewal" if order_kind == "renewal" else "order", note="新订单进入运营跟进链路")
        track_attribution_event(attribution or {}, "order_create", {
            "order_id": order["id"],
            "product_id": product_id,
            "price": order.get("price", 0),
            "order_kind": order_kind or "initial",
        })
        return decorate_order(order)

    @staticmethod
    def get_order(order_id):
        order = load_orders().get(order_id)
        return decorate_order(order) if order else None

    @staticmethod
    def apply_action(order_id, action, operator="system", note="", extra=None):
        orders_db = load_orders()
        order = orders_db.get(order_id)
        if not order:
            raise KeyError("订单不存在")

        updated = apply_order_action(order, action, operator=operator, note=note, extra=extra)
        orders_db[order_id] = updated
        save_orders(orders_db)
        attach_order_to_user(updated.get("user_id", ""), updated.get("phone", ""), order_id, updated.get("status", "pending_payment"))
        sync_order_partners(updated)
        subscription = sync_subscription_state(updated)

        if action == "mark_paid":
            mark_payment_paid(order_id, (extra or {}).get("trade_no", ""), (extra or {}).get("channel", "wechat_pay"))
            track_attribution_event(updated.get("attribution", {}), "order_pay", {
                "order_id": order_id,
                "product_id": updated.get("product_id", ""),
                "order_kind": updated.get("order_kind", "initial"),
            })
            if updated.get("order_kind") == "renewal" and subscription:
                create_wecom_task_for_order(updated, scenario="renewal", note="续费订单支付完成，等待顾问确认")
        elif action in {"approve", "reject"}:
            ensure_consultation(updated)
            ensure_prescription(updated)
        elif action in {"start_fulfillment", "ship", "deliver", "complete"}:
            ensure_pharmacy_order(updated)
            if action in {"deliver", "complete"}:
                create_wecom_task_for_order(updated, scenario="aftercare", note="订单履约完成，进入用药指导/复购跟进")
        elif action == "cancel":
            create_wecom_task_for_order(updated, scenario="order", note="订单已取消，需要确认取消原因")

        return decorate_order(updated)

# ========== HTTP处理器 ==========
class MediSlimHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self._send_common_headers("application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        if path in ("/", "/index.html"):
            self._serve("templates/index.html", "text/html; charset=utf-8")
        elif path == "/assess":
            self._serve("templates/assess.html", "text/html; charset=utf-8")
        elif path == "/constitution":
            self._serve("templates/constitution.html", "text/html; charset=utf-8")
        elif path == "/flow":
            self._serve("templates/flow.html", "text/html; charset=utf-8")
        elif path == "/demo-film":
            self._serve("templates/demo_film.html", "text/html; charset=utf-8")
        elif path == "/admin":
            self._serve("templates/admin2.html", "text/html; charset=utf-8")
        elif path.startswith("/static/"):
            self._serve(path[1:], static_content_type(path))
        elif path == "/api/products":
            self._json(Config.PRODUCTS)
        elif path == "/api/hospitals":
            self._json(Config.PARTNER_HOSPITALS)
        elif path == "/api/pharmacies":
            self._json(Config.PARTNER_PHARMACIES)
        elif path == "/api/product-partners":
            self._json(Config.PARTNER_PRODUCT_SUPPLIERS)
        elif path == "/api/partners":
            self._json(PARTNERS)
        elif path == "/api/partner/dashboard":
            self._json(partner_dashboard())
        elif path == "/api/constitution/questions":
            self._json(get_questionnaire())
        elif path == "/api/subscriptions":
            self._json(list_subscriptions())
        elif path == "/api/wecom/queue":
            self._json(queue_summary())
        elif path == "/api/stats":
            users = load_data("users")
            orders = load_orders()
            leads = load_data("leads")
            subscriptions = list_subscriptions()
            self._json({
                "total_users": len(users),
                "total_orders": len(orders),
                "total_leads": len(leads),
                "total_subscriptions": len(subscriptions),
                "products": len(Config.PRODUCTS),
                "hospitals": len(Config.PARTNER_HOSPITALS),
                "pharmacies": len(Config.PARTNER_PHARMACIES),
                "product_partners": len(Config.PARTNER_PRODUCT_SUPPLIERS),
            })
        elif path == "/api/leads":
            self._json(list(load_data("leads").values()))
        elif path == "/api/orders":
            orders = sorted(
                (decorate_order(order) for order in load_orders().values()),
                key=lambda item: item.get("updated_at") or item.get("created_at") or "",
                reverse=True,
            )
            self._json(orders)
        elif path == "/api/user/tracking":
            order_id = params.get("order_id", [""])[0]
            if not order_id:
                self._json({"error": "order_id 不能为空"}, 400)
                return
            tracking = get_tracking(order_id)
            if not tracking:
                self._json({"error": "暂无物流信息"}, 404)
                return
            self._json(tracking)
        elif path == "/api/content/funnel":
            if not get_funnel:
                self._json({"error": "内容追踪模块不可用"}, 503)
                return
            hours = int(params.get("hours", ["168"])[0])
            self._json(get_funnel(hours=hours))
        elif path == "/api/content/performance":
            if not get_content_performance:
                self._json({"error": "内容追踪模块不可用"}, 503)
                return
            top = int(params.get("top", ["10"])[0])
            self._json(get_content_performance(top))
        elif path == "/api/content/catalog":
            if CONTENT_CATALOG_PATH.exists():
                catalog = json.loads(CONTENT_CATALOG_PATH.read_text(encoding="utf-8"))
            else:
                catalog = []
            self._json(catalog)
        elif path == "/api/health":
            self._json({
                "status": "ok",
                "service": Config.APP_NAME,
                "version": Config.VERSION,
            })
        else:
            self._json({"error": "Not found"}, 404)

    def do_POST(self):
        try:
            data = self._read_json_body()
        except ValueError as exc:
            self._json({"error": str(exc)}, 400)
            return

        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/user/register":
            users = load_data("users")
            phone = data.get("phone", "")
            existing = next((user for user in users.values() if user.get("phone") == phone and phone), None)
            if existing:
                sync_crm_user(existing)
                self._json(existing)
                return
            crm_match = next(
                (crm_user for crm_user in load_data("crm_users").values() if crm_user.get("phone") == phone and phone),
                None,
            )
            uid = crm_match.get("id") if crm_match else short_id()
            users[uid] = {
                "id": uid,
                "phone": phone,
                "name": data.get("name", "用户"),
                "created_at": now_iso(),
                "orders": [],
            }
            save_data("users", users)
            sync_crm_user(users[uid])
            self._json(users[uid])

        elif path == "/api/assessment/start":
            pid = data.get("product_id", "")
            questions = Config.ASSESSMENT_QUESTIONS.get(pid, [])
            product = Config.PRODUCTS.get(pid, {})
            if not questions:
                self._json({"error": "产品不存在"}, 400)
                return
            track_attribution_event(extract_attribution(data), "assess_start", {
                "product_id": pid,
            })
            self._json({
                "product_id": pid,
                "product_name": product.get("name", ""),
                "questions": questions,
                "total": len(questions),
            })

        elif path == "/api/assessment/analyze":
            pid = data.get("product_id", "")
            if pid not in Config.PRODUCTS:
                self._json({"error": "产品不存在"}, 400)
                return
            answers = data.get("answers", {})
            result = SlimAIEngine.analyze(pid, answers)
            track_attribution_event(extract_attribution(data), "assess_done", {
                "product_id": pid,
                "eligible": result.get("eligible", False),
            })
            self._json(result)

        elif path == "/api/constitution/analyze":
            result = analyze_constitution(data.get("answers", {}))
            track_attribution_event(extract_attribution(data), "assess_done", {
                "assessment_type": "constitution",
                "primary": result.get("primary", {}).get("id", ""),
            })
            self._json(result)

        elif path == "/api/lead/create":
            phone = data.get("phone", "").strip()
            if not phone:
                self._json({"error": "手机号不能为空"}, 400)
                return
            attribution = extract_attribution(data)

            lead = LeadManager.create_lead(
                data.get("name", "").strip(),
                phone,
                data.get("product_id", "").strip(),
                data.get("source", "homepage").strip() or "homepage",
                data.get("note", "").strip(),
                attribution=attribution,
            )
            self._json(lead)

        elif path == "/api/order/create":
            uid = data.get("user_id", "")
            pid = data.get("product_id", "")
            if pid not in Config.PRODUCTS:
                self._json({"error": "产品不存在"}, 400)
                return
            result = data.get("assessment", {})
            order = OrderManager.create_order(
                uid, pid, result,
                data.get("name", ""),
                data.get("phone", ""),
                data.get("address", ""),
                attribution=extract_attribution(data),
                order_kind=data.get("order_kind", ""),
                subscription_id=data.get("subscription_id", ""),
            )
            self._json(order)

        elif path == "/api/pay/create":
            oid = data.get("order_id", "")
            order = OrderManager.get_order(oid)
            if not order:
                self._json({"error": "订单不存在"}, 404)
                return
            intent = create_payment_intent(order, data.get("channel", "wechat_pay"))
            self._json(intent)

        elif path == "/api/order/status":
            oid = data.get("order_id", "")
            order = OrderManager.get_order(oid)
            if not order:
                self._json({"error": "订单不存在"}, 404)
                return
            self._json(order)

        elif path == "/api/order/action":
            oid = data.get("order_id", "")
            action = data.get("action", "")
            if not oid or not action:
                self._json({"error": "order_id 和 action 不能为空"}, 400)
                return
            try:
                order = OrderManager.apply_action(
                    oid,
                    action,
                    operator=data.get("operator", "ops"),
                    note=data.get("note", ""),
                    extra=data.get("extra", {}),
                )
            except KeyError as exc:
                self._json({"error": str(exc)}, 404)
                return
            except ValueError as exc:
                self._json({"error": str(exc)}, 400)
                return
            self._json(order)

        elif path in {"/api/pay/callback", "/api/callback/payment"}:
            oid = data.get("order_id", "")
            if not oid:
                self._json({"error": "order_id 不能为空"}, 400)
                return
            try:
                order = OrderManager.apply_action(
                    oid,
                    "mark_paid",
                    operator="payment_callback",
                    note=data.get("note", ""),
                    extra={
                        "trade_no": data.get("trade_no", ""),
                        "channel": data.get("channel", "mock_gateway"),
                    },
                )
                if any(item["action"] == "submit_doctor_review" for item in order.get("available_actions", [])):
                    order = OrderManager.apply_action(
                        oid,
                        "submit_doctor_review",
                        operator="workflow",
                        extra={"case_id": data.get("case_id", "")},
                    )
            except (KeyError, ValueError) as exc:
                self._json({"error": str(exc)}, 400)
                return
            self._json(order)

        elif path == "/api/pay/refund":
            oid = data.get("order_id", "")
            order = OrderManager.get_order(oid)
            if not order:
                self._json({"error": "订单不存在"}, 404)
                return
            if any(item["action"] == "cancel" for item in order.get("available_actions", [])):
                order = OrderManager.apply_action(
                    oid,
                    "cancel",
                    operator="payment_ops",
                    note=data.get("reason", "退款取消"),
                )
            refund = create_refund(order, data.get("reason", "用户申请退款"))
            self._json({"order": order, "refund": refund})

        elif path == "/api/ih/create_consultation":
            oid = data.get("order_id", "")
            order = OrderManager.get_order(oid)
            if not order:
                self._json({"error": "订单不存在"}, 404)
                return
            if any(item["action"] == "submit_doctor_review" for item in order.get("available_actions", [])):
                order = OrderManager.apply_action(
                    oid,
                    "submit_doctor_review",
                    operator="ih_adapter",
                    extra={"case_id": data.get("case_id", "")},
                )
            consultation = ensure_consultation(order)
            self._json({"order": order, "consultation": consultation})

        elif path == "/api/ih/check_status":
            oid = data.get("order_id", "")
            order = OrderManager.get_order(oid)
            consultation = get_consultation(oid)
            if not order or not consultation:
                self._json({"error": "暂无问诊记录"}, 404)
                return
            self._json({"order": order, "consultation": consultation})

        elif path == "/api/ih/get_prescription":
            oid = data.get("order_id", "")
            order = OrderManager.get_order(oid)
            if not order:
                self._json({"error": "订单不存在"}, 404)
                return
            prescription = ensure_prescription(order)
            if not prescription:
                self._json({"error": "当前订单尚未形成处方"}, 400)
                return
            self._json({"order": order, "prescription": prescription})

        elif path == "/api/callback/doctor-review":
            oid = data.get("order_id", "")
            result = data.get("result", "").strip().lower()
            action = "approve" if result == "approved" else "reject" if result == "rejected" else ""
            if not oid or not action:
                self._json({"error": "需要 order_id 和 result=approved|rejected"}, 400)
                return
            try:
                order = OrderManager.apply_action(
                    oid,
                    action,
                    operator="doctor_callback",
                    note=data.get("note", ""),
                    extra={"doctor_name": data.get("doctor_name", "")},
                )
            except (KeyError, ValueError) as exc:
                self._json({"error": str(exc)}, 400)
                return
            self._json(order)

        elif path == "/api/pharmacy/submit_order":
            oid = data.get("order_id", "")
            order = OrderManager.get_order(oid)
            if not order:
                self._json({"error": "订单不存在"}, 404)
                return
            if any(item["action"] == "start_fulfillment" for item in order.get("available_actions", [])):
                order = OrderManager.apply_action(
                    oid,
                    "start_fulfillment",
                    operator="pharmacy_adapter",
                    extra={"pharmacy_name": data.get("pharmacy_name", "")},
                )
            pharmacy_order = ensure_pharmacy_order(order)
            self._json({"order": order, "pharmacy_order": pharmacy_order})

        elif path == "/api/pharmacy/check_status":
            oid = data.get("order_id", "")
            order = OrderManager.get_order(oid)
            pharmacy_order = get_pharmacy_order(oid)
            if not order or not pharmacy_order:
                self._json({"error": "暂无药房订单"}, 404)
                return
            self._json({"order": order, "pharmacy_order": pharmacy_order})

        elif path == "/api/pharmacy/get_tracking":
            oid = data.get("order_id", "")
            tracking = get_tracking(oid)
            if not tracking:
                self._json({"error": "暂无物流信息"}, 404)
                return
            self._json(tracking)

        elif path == "/api/callback/logistics":
            oid = data.get("order_id", "")
            event = data.get("event", "").strip().lower()
            if not oid or event not in {"shipped", "delivered"}:
                self._json({"error": "需要 order_id 和 event=shipped|delivered"}, 400)
                return
            try:
                order = OrderManager.get_order(oid)
                if not order:
                    self._json({"error": "订单不存在"}, 404)
                    return
                if event == "shipped":
                    if any(item["action"] == "start_fulfillment" for item in order.get("available_actions", [])):
                        order = OrderManager.apply_action(
                            oid,
                            "start_fulfillment",
                            operator="pharmacy_callback",
                            extra={"pharmacy_name": data.get("pharmacy_name", "")},
                        )
                    order = OrderManager.apply_action(
                        oid,
                        "ship",
                        operator="logistics_callback",
                        extra={
                            "carrier": data.get("carrier", "顺丰"),
                            "tracking_no": data.get("tracking_no", ""),
                        },
                    )
                else:
                    order = OrderManager.apply_action(
                        oid,
                        "deliver",
                        operator="logistics_callback",
                        extra={"carrier": data.get("carrier", "顺丰")},
                    )
            except (KeyError, ValueError) as exc:
                self._json({"error": str(exc)}, 400)
                return
            self._json(order)

        elif path == "/api/user/refill":
            subscription_id = data.get("subscription_id", "")
            try:
                order = create_renewal_order(subscription_id, Config.PRODUCTS)
            except (KeyError, ValueError) as exc:
                self._json({"error": str(exc)}, 400)
                return
            attach_order_to_user(order.get("user_id", ""), order.get("phone", ""), order["id"], order.get("status", "pending_payment"))
            sync_order_partners(order)
            track_attribution_event(order.get("attribution", {}), "reorder", {
                "order_id": order["id"],
                "subscription_id": subscription_id,
                "product_id": order.get("product_id", ""),
            })
            create_wecom_task_for_order(order, scenario="renewal", note="生成续费订单，等待支付")
            self._json({"subscription": get_subscription(subscription_id), "order": decorate_order(order)})

        elif path == "/api/subscription/action":
            subscription_id = data.get("subscription_id", "")
            action = data.get("action", "")
            if not subscription_id or not action:
                self._json({"error": "subscription_id 和 action 不能为空"}, 400)
                return
            if action == "renew":
                try:
                    order = create_renewal_order(subscription_id, Config.PRODUCTS)
                except (KeyError, ValueError) as exc:
                    self._json({"error": str(exc)}, 400)
                    return
                attach_order_to_user(order.get("user_id", ""), order.get("phone", ""), order["id"], order.get("status", "pending_payment"))
                sync_order_partners(order)
                create_wecom_task_for_order(order, scenario="renewal", note="后台生成续费订单")
                self._json({"subscription": get_subscription(subscription_id), "order": decorate_order(order)})
                return

            try:
                subscription = apply_subscription_action(
                    subscription_id,
                    action,
                    operator=data.get("operator", "ops"),
                    note=data.get("note", ""),
                )
            except (KeyError, ValueError) as exc:
                self._json({"error": str(exc)}, 400)
                return

            if action == "remind":
                create_wecom_task_for_order(
                    {
                        "id": subscription.get("current_order_id", ""),
                        "user_id": subscription.get("user_id", ""),
                        "phone": subscription.get("phone", ""),
                        "name": subscription.get("name", ""),
                        "product_id": subscription.get("product_id", ""),
                        "attribution": {"source": "subscription_reminder"},
                    },
                    scenario="renewal",
                    note="订阅已触发续费提醒，请顾问跟进",
                )
            self._json(subscription)

        elif path == "/api/wecom/handoff":
            try:
                thread = upsert_thread(
                    phone=data.get("phone", "").strip(),
                    name=data.get("name", "").strip(),
                    product_id=data.get("product_id", "").strip(),
                    source=data.get("source", "direct").strip() or "direct",
                    scenario=data.get("scenario", "lead").strip() or "lead",
                    user_id=data.get("user_id", "").strip(),
                    order_id=data.get("order_id", "").strip(),
                    note=data.get("note", "").strip(),
                    attribution=extract_attribution(data),
                )
            except ValueError as exc:
                self._json({"error": str(exc)}, 400)
                return
            self._json(thread)

        elif path == "/api/wecom/action":
            thread_id = data.get("thread_id", "")
            action = data.get("action", "")
            if action == "assign":
                try:
                    thread = assign_thread(thread_id, data.get("consultant_id", ""))
                except (KeyError, ValueError) as exc:
                    self._json({"error": str(exc)}, 400)
                    return
                self._json(thread)
                return
            try:
                thread = apply_thread_action(
                    thread_id,
                    action,
                    operator=data.get("operator", "ops"),
                    note=data.get("note", ""),
                )
            except (KeyError, ValueError) as exc:
                self._json({"error": str(exc)}, 400)
                return
            self._json(thread)

        elif path == "/api/wecom/message":
            try:
                thread = add_thread_message(
                    data.get("thread_id", ""),
                    data.get("sender", "consultant"),
                    data.get("content", ""),
                )
            except (KeyError, ValueError) as exc:
                self._json({"error": str(exc)}, 400)
                return
            self._json(thread)

        elif path == "/api/content/track":
            attribution = extract_attribution(data)
            result = track_attribution_event(attribution, data.get("event_type", ""), data.get("extra", {}))
            if result is None:
                self._json({"ok": False, "message": "缺少 ref 或追踪模块不可用"}, 400)
                return
            self._json(result)

        else:
            self._json({"error": "Not found"}, 404)

    def _json(self, data, status=200):
        payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self._write_response(status, "application/json; charset=utf-8", payload)

    def _serve(self, filepath, content_type):
        full = BASE_DIR / filepath
        if full.exists():
            self.send_response(200)
            self._send_common_headers(content_type)
            self.send_header("Content-Length", str(full.stat().st_size))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(full.read_bytes())
        else:
            self._json({"error": "Not found"}, 404)

    def _write_response(self, status, content_type, payload):
        self.send_response(status)
        self._send_common_headers(content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    def _send_common_headers(self, content_type):
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}

        try:
            body = self.rfile.read(length).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("请求体编码必须是 UTF-8") from exc

        if not body.strip():
            return {}

        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise ValueError("请求体不是合法 JSON") from exc

    def log_message(self, *a):
        pass

# ========== 启动 ==========
def main():
    migrate_legacy_orders()
    reconcile_records()
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8090))
    server = ThreadingHTTPServer((host, port), MediSlimHandler)
    print(f"💰 MediSlim 轻健康平台启动成功")
    print(f"📱 访问: http://{host}:{port}")
    print(f"📊 统计: http://localhost:{port}/api/stats")
    print(f"💚 健康检查: http://localhost:{port}/api/health")
    server.serve_forever()

if __name__ == "__main__":
    main()
