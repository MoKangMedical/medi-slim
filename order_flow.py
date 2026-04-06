"""
Order lifecycle helpers shared by the app and admin services.
"""
from __future__ import annotations

from copy import deepcopy

from storage import now_iso, short_id

ORDER_STATUS_META = {
    "pending_payment": {"label": "待支付", "desc": "订单已创建，等待支付确认"},
    "paid": {"label": "已支付", "desc": "支付已确认，等待提交医师审核"},
    "doctor_review": {"label": "医师审核中", "desc": "合作医师正在审核"},
    "approved": {"label": "审核通过", "desc": "医师审核通过，等待药房履约"},
    "rejected": {"label": "审核未通过", "desc": "医师审核未通过"},
    "pharmacy_processing": {"label": "药房配货中", "desc": "药房已接单，准备发货"},
    "shipped": {"label": "已发货", "desc": "药品已交给物流"},
    "delivered": {"label": "已签收", "desc": "用户已签收"},
    "completed": {"label": "已完成", "desc": "本次服务已完成"},
    "cancelled": {"label": "已取消", "desc": "订单已取消"},
}

ORDER_ACTIONS = {
    "mark_paid": {
        "label": "确认支付",
        "from": ["pending_payment"],
        "to": "paid",
        "desc": "支付成功",
        "actor": "payment",
    },
    "submit_doctor_review": {
        "label": "提交医审",
        "from": ["paid"],
        "to": "doctor_review",
        "desc": "已提交医师审核",
        "actor": "system",
    },
    "approve": {
        "label": "审核通过",
        "from": ["doctor_review"],
        "to": "approved",
        "desc": "医师审核通过",
        "actor": "doctor",
    },
    "reject": {
        "label": "审核拒绝",
        "from": ["doctor_review"],
        "to": "rejected",
        "desc": "医师审核未通过",
        "actor": "doctor",
    },
    "start_fulfillment": {
        "label": "开始配货",
        "from": ["approved"],
        "to": "pharmacy_processing",
        "desc": "药房开始配货",
        "actor": "pharmacy",
    },
    "ship": {
        "label": "标记发货",
        "from": ["approved", "pharmacy_processing"],
        "to": "shipped",
        "desc": "药品已发货",
        "actor": "logistics",
    },
    "deliver": {
        "label": "标记签收",
        "from": ["shipped"],
        "to": "delivered",
        "desc": "药品已签收",
        "actor": "logistics",
    },
    "complete": {
        "label": "完成服务",
        "from": ["delivered"],
        "to": "completed",
        "desc": "本次服务已完成",
        "actor": "system",
    },
    "cancel": {
        "label": "取消订单",
        "from": ["pending_payment", "paid", "doctor_review", "approved"],
        "to": "cancelled",
        "desc": "订单已取消",
        "actor": "ops",
    },
}


def create_order_record(user_id, product_id, product_name, price, name, phone, address, assessment, attribution=None):
    created_at = now_iso()
    order_id = short_id()
    order = {
        "id": order_id,
        "user_id": user_id,
        "product_id": product_id,
        "product_name": product_name,
        "status": "pending_payment",
        "price": price,
        "name": name,
        "phone": phone,
        "address": address,
        "assessment": assessment,
        "created_at": created_at,
        "updated_at": created_at,
        "payment": {
            "status": "pending",
            "checkout_reference": f"pay_{order_id}",
        },
        "doctor_review": {},
        "fulfillment": {},
        "attribution": attribution or {},
        "timeline": [
            _event("created", "订单创建", actor="user"),
        ],
    }
    return decorate_order(order)


def apply_order_action(order, action, operator="system", note="", extra=None):
    definition = ORDER_ACTIONS.get(action)
    if not definition:
        raise ValueError("未知订单动作")

    current_status = order.get("status", "pending_payment")
    if current_status not in definition["from"]:
        raise ValueError(f"当前状态 {current_status} 不能执行 {action}")

    updated = deepcopy(order)
    next_status = definition["to"]
    timestamp = now_iso()
    extra = extra or {}

    updated["status"] = next_status
    updated["updated_at"] = timestamp
    updated.setdefault("timeline", []).append(
        _event(next_status, definition["desc"], actor=operator or definition["actor"], note=note, extra=extra)
    )

    if action == "mark_paid":
        updated["payment"] = {
            **updated.get("payment", {}),
            "status": "paid",
            "paid_at": timestamp,
            "trade_no": extra.get("trade_no") or updated.get("payment", {}).get("trade_no") or f"txn_{updated['id']}",
            "channel": extra.get("channel", "mock_gateway"),
        }
    elif action in {"approve", "reject"}:
        updated["doctor_review"] = {
            **updated.get("doctor_review", {}),
            "status": next_status,
            "doctor_name": extra.get("doctor_name", ""),
            "reviewed_at": timestamp,
            "note": note or extra.get("note", ""),
        }
    elif action == "submit_doctor_review":
        updated["doctor_review"] = {
            **updated.get("doctor_review", {}),
            "status": "doctor_review",
            "submitted_at": timestamp,
            "case_id": extra.get("case_id") or updated.get("doctor_review", {}).get("case_id") or f"doc_{updated['id']}",
        }
    elif action == "start_fulfillment":
        updated["fulfillment"] = {
            **updated.get("fulfillment", {}),
            "status": "processing",
            "started_at": timestamp,
            "pharmacy_name": extra.get("pharmacy_name", ""),
        }
    elif action == "ship":
        updated["fulfillment"] = {
            **updated.get("fulfillment", {}),
            "status": "shipped",
            "carrier": extra.get("carrier", updated.get("fulfillment", {}).get("carrier", "顺丰")),
            "tracking_no": extra.get("tracking_no") or updated.get("fulfillment", {}).get("tracking_no") or f"SF{updated['id'].upper()}",
            "shipped_at": timestamp,
        }
    elif action == "deliver":
        updated["fulfillment"] = {
            **updated.get("fulfillment", {}),
            "status": "delivered",
            "delivered_at": timestamp,
        }
    elif action == "complete":
        updated["completed_at"] = timestamp
    elif action == "cancel":
        updated["cancelled_at"] = timestamp
        updated["cancel_reason"] = note or extra.get("reason", "")

    return decorate_order(updated)


def decorate_order(order):
    decorated = deepcopy(order)
    status = decorated.get("status", "pending_payment")
    meta = ORDER_STATUS_META.get(status, {"label": status, "desc": ""})
    decorated["status_label"] = meta["label"]
    decorated["status_description"] = meta["desc"]
    decorated["available_actions"] = available_actions(decorated)
    return decorated


def available_actions(order):
    current_status = order.get("status", "pending_payment")
    actions = []
    for action, definition in ORDER_ACTIONS.items():
        if current_status in definition["from"]:
            actions.append({
                "action": action,
                "label": definition["label"],
                "next_status": definition["to"],
                "next_label": ORDER_STATUS_META.get(definition["to"], {}).get("label", definition["to"]),
            })
    return actions


def _event(status, desc, actor="system", note="", extra=None):
    payload = {
        "time": now_iso(),
        "status": status,
        "desc": desc,
        "actor": actor,
    }
    if note:
        payload["note"] = note
    if extra:
        payload["extra"] = extra
    return payload
