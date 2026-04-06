"""
Recurring subscription helpers for MediSlim.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any

from order_flow import create_order_record
from storage import load_json, save_json, load_orders, save_orders, now_iso, short_id


STATUS_META = {
    "pending_activation": {"label": "待激活", "desc": "首单已创建，等待履约完成后进入活跃订阅"},
    "active": {"label": "活跃", "desc": "处于正常续费周期内"},
    "paused": {"label": "已暂停", "desc": "订阅暂停，不自动续费"},
    "cancelled": {"label": "已取消", "desc": "订阅已终止"},
    "past_due": {"label": "待处理", "desc": "续费节点已到，需要人工跟进"},
}


def load_subscriptions() -> dict[str, Any]:
    return load_json("subscriptions", {})


def save_subscriptions(data: dict[str, Any]) -> None:
    save_json("subscriptions", data)


def decorate_subscription(subscription: dict[str, Any] | None) -> dict[str, Any] | None:
    if not subscription:
        return None

    decorated = deepcopy(subscription)
    status = decorated.get("status", "pending_activation")
    meta = STATUS_META.get(status, {"label": status, "desc": ""})
    decorated["status_label"] = meta["label"]
    decorated["status_description"] = meta["desc"]
    decorated["days_until_billing"] = _days_until(decorated.get("next_billing_at", ""))
    decorated["available_actions"] = available_actions(decorated)
    return decorated


def list_subscriptions() -> list[dict[str, Any]]:
    return sorted(
        (decorate_subscription(subscription) for subscription in load_subscriptions().values()),
        key=lambda item: item.get("updated_at") or item.get("created_at") or "",
        reverse=True,
    )


def get_subscription(subscription_id: str) -> dict[str, Any] | None:
    return decorate_subscription(load_subscriptions().get(subscription_id))


def sync_subscription_with_order(order: dict[str, Any], product_config: dict[str, Any]) -> dict[str, Any] | None:
    if not order.get("user_id") and not order.get("phone"):
        return None

    subscriptions = load_subscriptions()
    subscription = _find_matching_subscription(subscriptions, order)

    if not subscription:
        subscription = {
            "id": order.get("subscription_id") or f"sub_{short_id()}",
            "user_id": order.get("user_id", ""),
            "phone": order.get("phone", ""),
            "name": order.get("name", ""),
            "product_id": order.get("product_id", ""),
            "product_name": order.get("product_name", ""),
            "status": "pending_activation",
            "cycle_days": 28,
            "renew_price": product_config.get("renew_price", order.get("price", 0)),
            "start_order_id": order["id"],
            "current_order_id": order["id"],
            "latest_order_status": order.get("status", "pending_payment"),
            "renewal_orders": [],
            "last_reminded_at": "",
            "next_billing_at": "",
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "timeline": [],
        }

    subscription = deepcopy(subscription)
    subscription["user_id"] = order.get("user_id", subscription.get("user_id", ""))
    subscription["phone"] = order.get("phone", subscription.get("phone", ""))
    subscription["name"] = order.get("name", subscription.get("name", ""))
    subscription["product_id"] = order.get("product_id", subscription.get("product_id", ""))
    subscription["product_name"] = order.get("product_name", subscription.get("product_name", ""))
    subscription["renew_price"] = product_config.get("renew_price", subscription.get("renew_price", order.get("price", 0)))
    subscription["updated_at"] = now_iso()
    subscription["latest_order_status"] = order.get("status", subscription.get("latest_order_status", "pending_payment"))

    if order.get("order_kind") == "renewal" and order["id"] not in subscription["renewal_orders"]:
        subscription["renewal_orders"].append(order["id"])
        _push_timeline(subscription, "renewal_created", f"生成续费订单 {order['id']}")

    if order.get("status") in {"pending_payment", "paid", "doctor_review", "approved", "pharmacy_processing", "shipped"}:
        if subscription.get("status") not in {"paused", "cancelled"}:
            subscription["status"] = "pending_activation"
    elif order.get("status") in {"delivered", "completed"}:
        was_status = subscription.get("status")
        was_order_id = subscription.get("current_order_id")
        subscription["status"] = "active" if subscription.get("status") != "paused" else "paused"
        subscription["current_order_id"] = order["id"]
        base_time = (
            order.get("completed_at")
            or order.get("fulfillment", {}).get("delivered_at")
            or order.get("updated_at")
            or order.get("created_at")
            or now_iso()
        )
        subscription["next_billing_at"] = _shift_time(base_time, days=subscription.get("cycle_days", 28))
        if was_status != subscription["status"] or was_order_id != order["id"]:
            _push_timeline(subscription, "activated", f"订单 {order['id']} 履约完成，订阅进入 {subscription['status']}")
    elif order.get("status") in {"rejected", "cancelled"} and not subscription.get("renewal_orders"):
        if subscription.get("status") != "cancelled":
            subscription["status"] = "cancelled"
            _push_timeline(subscription, "cancelled", f"订单 {order['id']} 终止，订阅关闭")

    subscriptions[subscription["id"]] = subscription
    save_subscriptions(subscriptions)
    return decorate_subscription(subscription)


def apply_subscription_action(subscription_id: str, action: str, operator: str = "ops", note: str = "") -> dict[str, Any]:
    subscriptions = load_subscriptions()
    subscription = subscriptions.get(subscription_id)
    if not subscription:
        raise KeyError("订阅不存在")

    subscription = deepcopy(subscription)
    if action == "pause":
        if subscription.get("status") not in {"active", "pending_activation", "past_due"}:
            raise ValueError("当前订阅不可暂停")
        subscription["status"] = "paused"
        _push_timeline(subscription, "paused", note or f"{operator} 暂停订阅")
    elif action == "resume":
        if subscription.get("status") != "paused":
            raise ValueError("当前订阅不在暂停状态")
        subscription["status"] = "active" if subscription.get("next_billing_at") else "pending_activation"
        _push_timeline(subscription, "resumed", note or f"{operator} 恢复订阅")
    elif action == "cancel":
        if subscription.get("status") == "cancelled":
            raise ValueError("订阅已取消")
        subscription["status"] = "cancelled"
        _push_timeline(subscription, "cancelled", note or f"{operator} 取消订阅")
    elif action == "remind":
        subscription["last_reminded_at"] = now_iso()
        _push_timeline(subscription, "reminded", note or f"{operator} 发送续费提醒")
    elif action == "mark_due":
        subscription["status"] = "past_due"
        _push_timeline(subscription, "past_due", note or f"{operator} 标记为待处理")
    else:
        raise ValueError("未知订阅动作")

    subscription["updated_at"] = now_iso()
    subscriptions[subscription_id] = subscription
    save_subscriptions(subscriptions)
    return decorate_subscription(subscription)


def create_renewal_order(subscription_id: str, products: dict[str, Any]) -> dict[str, Any]:
    subscriptions = load_subscriptions()
    subscription = subscriptions.get(subscription_id)
    if not subscription:
        raise KeyError("订阅不存在")
    if subscription.get("status") in {"paused", "cancelled"}:
        raise ValueError("当前订阅不可续费")

    orders = load_orders()
    previous_order = orders.get(subscription.get("current_order_id")) or orders.get(subscription.get("start_order_id"))
    if not previous_order:
        raise ValueError("缺少可用于续费的历史订单")

    product = products.get(subscription.get("product_id"), {})
    renewed = create_order_record(
        subscription.get("user_id", ""),
        subscription.get("product_id", ""),
        subscription.get("product_name", product.get("name", "")),
        product.get("renew_price", subscription.get("renew_price", previous_order.get("price", 0))),
        subscription.get("name", previous_order.get("name", "续费用户")),
        subscription.get("phone", previous_order.get("phone", "")),
        previous_order.get("address", ""),
        previous_order.get("assessment", {}),
        attribution={
            **previous_order.get("attribution", {}),
            "source": "subscription_renewal",
        },
    )
    renewed["subscription_id"] = subscription_id
    renewed["order_kind"] = "renewal"
    renewed["price"] = product.get("renew_price", renewed.get("price", 0))

    orders[renewed["id"]] = renewed
    save_orders(orders)

    subscription = deepcopy(subscription)
    subscription["renewal_orders"].append(renewed["id"])
    subscription["current_order_id"] = renewed["id"]
    subscription["status"] = "pending_activation"
    subscription["updated_at"] = now_iso()
    _push_timeline(subscription, "renewal_created", f"生成续费订单 {renewed['id']}")
    subscriptions[subscription_id] = subscription
    save_subscriptions(subscriptions)
    return renewed


def due_subscriptions(within_days: int = 7) -> list[dict[str, Any]]:
    rows = []
    for subscription in list_subscriptions():
        days_until = subscription.get("days_until_billing")
        if subscription.get("status") in {"active", "past_due"} and days_until is not None and days_until <= within_days:
            rows.append(subscription)
    return rows


def available_actions(subscription: dict[str, Any]) -> list[dict[str, Any]]:
    status = subscription.get("status", "pending_activation")
    actions = [{"action": "remind", "label": "发送提醒"}]
    if status in {"active", "pending_activation", "past_due"}:
        actions.append({"action": "pause", "label": "暂停订阅"})
        actions.append({"action": "mark_due", "label": "标记待处理"})
    if status == "paused":
        actions.append({"action": "resume", "label": "恢复订阅"})
    if status != "cancelled":
        actions.append({"action": "cancel", "label": "取消订阅"})
    if status in {"active", "pending_activation", "past_due"}:
        actions.append({"action": "renew", "label": "生成续费订单"})
    return actions


def _find_matching_subscription(subscriptions: dict[str, Any], order: dict[str, Any]) -> dict[str, Any] | None:
    explicit_id = order.get("subscription_id")
    if explicit_id and subscriptions.get(explicit_id):
        return subscriptions[explicit_id]

    for subscription in subscriptions.values():
        if subscription.get("phone") == order.get("phone") and subscription.get("product_id") == order.get("product_id"):
            if order["id"] == subscription.get("start_order_id") or order["id"] in subscription.get("renewal_orders", []):
                return subscription
            if subscription.get("status") in {"active", "pending_activation", "paused", "past_due"}:
                return subscription
    return None


def _push_timeline(subscription: dict[str, Any], status: str, note: str) -> None:
    subscription.setdefault("timeline", []).append({
        "time": now_iso(),
        "status": status,
        "note": note,
    })


def _days_until(iso_time: str) -> int | None:
    if not iso_time:
        return None
    try:
        delta = datetime.fromisoformat(iso_time) - datetime.now()
    except ValueError:
        return None
    return delta.days


def _shift_time(iso_time: str, days: int) -> str:
    try:
        base = datetime.fromisoformat(iso_time)
    except ValueError:
        base = datetime.now()
    return (base + timedelta(days=days)).isoformat(timespec="seconds")
