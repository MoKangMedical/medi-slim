"""
Partner-facing mock adapters for payment, internet hospital, pharmacy, and logistics.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any

from storage import load_json, save_json, now_iso, short_id


STATE_NAME = "partner_records"


PARTNERS = {
    "payments": {
        "wechat_pay": {"id": "wechat_pay", "name": "微信支付", "type": "payment"},
        "alipay": {"id": "alipay", "name": "支付宝", "type": "payment"},
    },
    "hospitals": {
        "p001": {"id": "p001", "name": "京东健康互联网医院", "specialties": ["glp1", "skin", "mens"]},
        "p002": {"id": "p002", "name": "微医互联网医院", "specialties": ["glp1", "sleep", "hair"]},
        "p003": {"id": "p003", "name": "好大夫在线", "specialties": ["hair", "mens", "sleep"]},
        "p004": {"id": "p004", "name": "丁香园互联网医院", "specialties": ["skin", "sleep", "mens"]},
    },
    "pharmacies": {
        "f001": {"id": "f001", "name": "大参林大药房", "delivery": ["顺丰", "京东物流"]},
        "f002": {"id": "f002", "name": "益丰大药房", "delivery": ["顺丰"]},
    },
    "suppliers": {
        "s001": {"id": "s001", "name": "华东医药", "type": "glp1_supplier", "supports": ["glp1"]},
        "s002": {"id": "s002", "name": "仁会生物", "type": "glp1_supplier", "supports": ["glp1"]},
        "s003": {"id": "s003", "name": "信达生物", "type": "glp1_supplier", "supports": ["glp1"]},
        "s004": {"id": "s004", "name": "三生制药", "type": "hair_supplier", "supports": ["hair", "mens"]},
        "s005": {"id": "s005", "name": "振东制药", "type": "hair_supplier", "supports": ["hair"]},
        "s006": {"id": "s006", "name": "SC食品工厂", "type": "food_factory", "supports": ["sleep"]},
        "s007": {"id": "s007", "name": "保健食品企业", "type": "nutrition_supplier", "supports": ["skin", "sleep"]},
    },
    "logistics": {
        "sf": {"id": "sf", "name": "顺丰", "type": "logistics"},
        "jd": {"id": "jd", "name": "京东物流", "type": "logistics"},
    },
}


def load_state() -> dict[str, Any]:
    state = load_json(STATE_NAME, {})
    return {
        "payments": state.get("payments", {}),
        "consultations": state.get("consultations", {}),
        "prescriptions": state.get("prescriptions", {}),
        "pharmacy_orders": state.get("pharmacy_orders", {}),
        "refunds": state.get("refunds", {}),
    }


def save_state(state: dict[str, Any]) -> None:
    save_json(STATE_NAME, state)


def create_payment_intent(order: dict[str, Any], channel: str = "wechat_pay") -> dict[str, Any]:
    state = load_state()
    existing = _find_one(state["payments"], order["id"])
    if existing and existing.get("status") in {"created", "paid"}:
        return existing

    created_at = now_iso()
    intent = {
        "id": f"pi_{short_id()}",
        "order_id": order["id"],
        "user_id": order.get("user_id", ""),
        "channel": channel,
        "channel_name": PARTNERS["payments"].get(channel, {}).get("name", channel),
        "amount": order.get("price", 0),
        "status": "paid" if order.get("status") in {"paid", "doctor_review", "approved", "pharmacy_processing", "shipped", "delivered", "completed"} else "created",
        "checkout_url": f"/pay/mock/{order['id']}?channel={channel}",
        "checkout_reference": order.get("payment", {}).get("checkout_reference", f"pay_{order['id']}"),
        "trade_no": order.get("payment", {}).get("trade_no", ""),
        "created_at": created_at,
        "paid_at": order.get("payment", {}).get("paid_at", ""),
        "expires_at": _future_iso(days=1),
    }
    state["payments"][intent["id"]] = intent
    save_state(state)
    return intent


def mark_payment_paid(order_id: str, trade_no: str = "", channel: str = "wechat_pay") -> dict[str, Any]:
    state = load_state()
    intent = _find_one(state["payments"], order_id)
    if not intent:
        intent = create_payment_intent({"id": order_id, "price": 0, "payment": {}}, channel)
        state = load_state()
        intent = _find_one(state["payments"], order_id)

    intent["status"] = "paid"
    intent["channel"] = channel or intent.get("channel", "wechat_pay")
    intent["channel_name"] = PARTNERS["payments"].get(intent["channel"], {}).get("name", intent["channel"])
    intent["trade_no"] = trade_no or intent.get("trade_no", f"txn_{order_id}")
    intent["paid_at"] = now_iso()
    state["payments"][intent["id"]] = intent
    save_state(state)
    return intent


def create_refund(order: dict[str, Any], reason: str = "") -> dict[str, Any]:
    state = load_state()
    refund = {
        "id": f"rf_{short_id()}",
        "order_id": order["id"],
        "amount": order.get("price", 0),
        "reason": reason or "用户取消",
        "status": "processed",
        "created_at": now_iso(),
    }
    state["refunds"][refund["id"]] = refund

    payment = _find_one(state["payments"], order["id"])
    if payment:
        payment["status"] = "refunded"
        payment["refunded_at"] = refund["created_at"]
        payment["refund_id"] = refund["id"]
        state["payments"][payment["id"]] = payment

    save_state(state)
    return refund


def ensure_consultation(order: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    consultation = _find_one(state["consultations"], order["id"])
    hospital = _pick_hospital(order.get("product_id", ""))

    if not consultation:
        consultation = {
            "id": f"ih_{short_id()}",
            "order_id": order["id"],
            "user_id": order.get("user_id", ""),
            "hospital_id": hospital["id"],
            "hospital_name": hospital["name"],
            "status": "submitted" if order.get("status") in {"doctor_review", "approved", "rejected", "pharmacy_processing", "shipped", "delivered", "completed"} else "draft",
            "submitted_at": now_iso() if order.get("status") in {"doctor_review", "approved", "rejected", "pharmacy_processing", "shipped", "delivered", "completed"} else "",
            "eta_hours": 24,
            "doctor_name": order.get("doctor_review", {}).get("doctor_name", ""),
            "reviewed_at": order.get("doctor_review", {}).get("reviewed_at", ""),
        }
    else:
        consultation = deepcopy(consultation)

    if order.get("status") in {"doctor_review", "approved", "rejected", "pharmacy_processing", "shipped", "delivered", "completed"}:
        consultation["status"] = {
            "doctor_review": "submitted",
            "approved": "approved",
            "rejected": "rejected",
            "pharmacy_processing": "approved",
            "shipped": "approved",
            "delivered": "approved",
            "completed": "approved",
        }[order["status"]]
        consultation["submitted_at"] = consultation.get("submitted_at") or now_iso()
        consultation["doctor_name"] = order.get("doctor_review", {}).get("doctor_name", consultation.get("doctor_name", "合作医师"))
        consultation["reviewed_at"] = order.get("doctor_review", {}).get("reviewed_at", consultation.get("reviewed_at", ""))

    state["consultations"][consultation["id"]] = consultation
    save_state(state)
    return consultation


def get_consultation(order_id: str) -> dict[str, Any] | None:
    state = load_state()
    return _find_one(state["consultations"], order_id)


def ensure_prescription(order: dict[str, Any]) -> dict[str, Any] | None:
    if order.get("status") not in {"approved", "pharmacy_processing", "shipped", "delivered", "completed"}:
        return None

    state = load_state()
    prescription = _find_one(state["prescriptions"], order["id"])
    consultation = ensure_consultation(order)
    if prescription:
        return prescription

    prescription = {
        "id": f"rx_{short_id()}",
        "order_id": order["id"],
        "consultation_id": consultation["id"],
        "product_id": order.get("product_id", ""),
        "product_name": order.get("product_name", ""),
        "hospital_name": consultation["hospital_name"],
        "doctor_name": order.get("doctor_review", {}).get("doctor_name", "合作医师"),
        "issued_at": order.get("doctor_review", {}).get("reviewed_at", now_iso()),
        "dosage": _dosage_for_product(order.get("product_id", "")),
        "days_supply": 28,
        "notes": "模拟电子处方，用于演示伙伴抽象层。",
    }
    state["prescriptions"][prescription["id"]] = prescription
    save_state(state)
    return prescription


def get_prescription(order_id: str) -> dict[str, Any] | None:
    state = load_state()
    return _find_one(state["prescriptions"], order_id)


def ensure_pharmacy_order(order: dict[str, Any]) -> dict[str, Any] | None:
    if order.get("status") not in {"approved", "pharmacy_processing", "shipped", "delivered", "completed"}:
        return None

    state = load_state()
    pharmacy_order = _find_one(state["pharmacy_orders"], order["id"])
    pharmacy = _pick_pharmacy(order.get("product_id", ""))

    if not pharmacy_order:
        pharmacy_order = {
            "id": f"po_{short_id()}",
            "order_id": order["id"],
            "pharmacy_id": pharmacy["id"],
            "pharmacy_name": order.get("fulfillment", {}).get("pharmacy_name", pharmacy["name"]),
            "status": "processing" if order.get("status") in {"approved", "pharmacy_processing"} else "shipped",
            "created_at": now_iso(),
            "started_at": order.get("fulfillment", {}).get("started_at", ""),
            "tracking_no": order.get("fulfillment", {}).get("tracking_no", ""),
            "carrier": order.get("fulfillment", {}).get("carrier", "顺丰"),
            "shipped_at": order.get("fulfillment", {}).get("shipped_at", ""),
            "delivered_at": order.get("fulfillment", {}).get("delivered_at", ""),
        }
    else:
        pharmacy_order = deepcopy(pharmacy_order)

    fulfillment = order.get("fulfillment", {})
    pharmacy_order["pharmacy_name"] = fulfillment.get("pharmacy_name", pharmacy_order.get("pharmacy_name", pharmacy["name"]))
    pharmacy_order["carrier"] = fulfillment.get("carrier", pharmacy_order.get("carrier", "顺丰"))
    pharmacy_order["tracking_no"] = fulfillment.get("tracking_no", pharmacy_order.get("tracking_no", ""))
    pharmacy_order["started_at"] = fulfillment.get("started_at", pharmacy_order.get("started_at", ""))
    pharmacy_order["shipped_at"] = fulfillment.get("shipped_at", pharmacy_order.get("shipped_at", ""))
    pharmacy_order["delivered_at"] = fulfillment.get("delivered_at", pharmacy_order.get("delivered_at", ""))

    if order.get("status") in {"approved", "pharmacy_processing"}:
        pharmacy_order["status"] = "processing"
    elif order.get("status") == "shipped":
        pharmacy_order["status"] = "shipped"
    elif order.get("status") in {"delivered", "completed"}:
        pharmacy_order["status"] = "delivered"

    state["pharmacy_orders"][pharmacy_order["id"]] = pharmacy_order
    save_state(state)
    return pharmacy_order


def get_pharmacy_order(order_id: str) -> dict[str, Any] | None:
    state = load_state()
    return _find_one(state["pharmacy_orders"], order_id)


def get_tracking(order_id: str) -> dict[str, Any] | None:
    pharmacy_order = get_pharmacy_order(order_id)
    if not pharmacy_order:
        return None
    return {
        "order_id": order_id,
        "tracking_no": pharmacy_order.get("tracking_no", ""),
        "carrier": pharmacy_order.get("carrier", ""),
        "status": pharmacy_order.get("status", "processing"),
        "pharmacy_name": pharmacy_order.get("pharmacy_name", ""),
        "shipped_at": pharmacy_order.get("shipped_at", ""),
        "delivered_at": pharmacy_order.get("delivered_at", ""),
    }


def sync_order_partners(order: dict[str, Any]) -> dict[str, Any]:
    result = {
        "payment": None,
        "consultation": None,
        "prescription": None,
        "pharmacy_order": None,
    }

    if order.get("status") in {"pending_payment", "paid", "doctor_review", "approved", "pharmacy_processing", "shipped", "delivered", "completed"}:
        result["payment"] = create_payment_intent(order, order.get("payment", {}).get("channel", "wechat_pay"))
    if order.get("status") in {"paid", "doctor_review", "approved", "rejected", "pharmacy_processing", "shipped", "delivered", "completed"}:
        result["consultation"] = ensure_consultation(order)
    if order.get("status") in {"approved", "pharmacy_processing", "shipped", "delivered", "completed"}:
        result["prescription"] = ensure_prescription(order)
        result["pharmacy_order"] = ensure_pharmacy_order(order)
    return result


def partner_dashboard() -> dict[str, Any]:
    state = load_state()
    return {
        "partners": PARTNERS,
        "totals": {
            "payments": len(state["payments"]),
            "consultations": len(state["consultations"]),
            "prescriptions": len(state["prescriptions"]),
            "pharmacy_orders": len(state["pharmacy_orders"]),
            "refunds": len(state["refunds"]),
        },
        "latest": {
            "payments": _sorted_values(state["payments"])[:5],
            "consultations": _sorted_values(state["consultations"])[:5],
            "prescriptions": _sorted_values(state["prescriptions"])[:5],
            "pharmacy_orders": _sorted_values(state["pharmacy_orders"])[:5],
            "refunds": _sorted_values(state["refunds"])[:5],
        },
    }


def _pick_hospital(product_id: str) -> dict[str, Any]:
    for hospital in PARTNERS["hospitals"].values():
        if product_id in hospital["specialties"]:
            return hospital
    return next(iter(PARTNERS["hospitals"].values()))


def _pick_pharmacy(product_id: str) -> dict[str, Any]:
    if product_id in {"glp1", "hair"}:
        return PARTNERS["pharmacies"]["f001"]
    return PARTNERS["pharmacies"]["f002"]


def _find_one(records: dict[str, Any], order_id: str) -> dict[str, Any] | None:
    for record in records.values():
        if record.get("order_id") == order_id:
            return deepcopy(record)
    return None


def _sorted_values(mapping: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        (deepcopy(item) for item in mapping.values()),
        key=lambda item: item.get("updated_at") or item.get("paid_at") or item.get("created_at") or item.get("issued_at") or "",
        reverse=True,
    )


def _dosage_for_product(product_id: str) -> str:
    return {
        "glp1": "司美格鲁肽 0.25mg 每周一次，28 天后复评",
        "hair": "米诺地尔外用每日 2 次 + 非那雄胺口服每日 1 次",
        "skin": "按医嘱使用皮肤管理方案，14 天复评",
        "mens": "男性健康综合方案，28 天复诊",
        "sleep": "睡眠干预联合必要时药物支持，14 天随访",
    }.get(product_id, "按医嘱执行，28 天复评")


def _future_iso(days: int = 0, hours: int = 0) -> str:
    return (datetime.now() + timedelta(days=days, hours=hours)).isoformat(timespec="seconds")
