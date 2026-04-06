"""
Simple WeCom handoff queue for consultant follow-up.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from storage import load_json, save_json, now_iso, short_id


CONSULTANTS = [
    {"id": "c01", "name": "顾问 A"},
    {"id": "c02", "name": "顾问 B"},
    {"id": "c03", "name": "顾问 C"},
]


def load_queue() -> dict[str, Any]:
    return load_json("wecom_queue", {})


def save_queue(data: dict[str, Any]) -> None:
    save_json("wecom_queue", data)


def list_threads() -> list[dict[str, Any]]:
    return sorted(
        (decorate_thread(thread) for thread in load_queue().values()),
        key=lambda item: item.get("updated_at") or item.get("created_at") or "",
        reverse=True,
    )


def get_thread(thread_id: str) -> dict[str, Any] | None:
    return decorate_thread(load_queue().get(thread_id))


def upsert_thread(
    *,
    phone: str,
    name: str,
    product_id: str = "",
    source: str = "direct",
    scenario: str = "lead",
    user_id: str = "",
    order_id: str = "",
    note: str = "",
    attribution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not phone:
        raise ValueError("手机号不能为空")

    queue = load_queue()
    thread = _find_open_thread(queue, phone, scenario, product_id)
    created = False
    if not thread:
        created = True
        thread = {
            "id": f"wq_{short_id()}",
            "phone": phone,
            "name": name or "待跟进用户",
            "product_id": product_id,
            "source": source,
            "scenario": scenario,
            "user_id": user_id,
            "order_id": order_id,
            "consultant_id": "",
            "consultant_name": "",
            "status": "pending",
            "priority": _priority_for_scenario(scenario),
            "attribution": attribution or {},
            "messages": [],
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
    else:
        thread = deepcopy(thread)

    thread["name"] = name or thread.get("name", "待跟进用户")
    thread["product_id"] = product_id or thread.get("product_id", "")
    thread["source"] = source or thread.get("source", "direct")
    thread["user_id"] = user_id or thread.get("user_id", "")
    thread["order_id"] = order_id or thread.get("order_id", "")
    thread["priority"] = max(thread.get("priority", 1), _priority_for_scenario(scenario))
    thread["attribution"] = {**thread.get("attribution", {}), **(attribution or {})}
    thread["updated_at"] = now_iso()

    if created:
        _append_message(thread, "system", note or f"新建企微承接任务：{scenario}")
        queue[thread["id"]] = thread
        if scenario in {"lead", "assessment", "renewal"}:
            assign_thread(thread["id"], queue=queue)
            thread = queue[thread["id"]]
    elif note:
        _append_message(thread, "system", note)

    queue[thread["id"]] = thread
    save_queue(queue)
    return decorate_thread(thread)


def assign_thread(thread_id: str, consultant_id: str = "", queue: dict[str, Any] | None = None) -> dict[str, Any]:
    owned_queue = queue is None
    queue = queue or load_queue()
    thread = deepcopy(queue.get(thread_id))
    if not thread:
        raise KeyError("企微任务不存在")

    consultant = _pick_consultant(queue, consultant_id)
    thread["consultant_id"] = consultant["id"]
    thread["consultant_name"] = consultant["name"]
    thread["status"] = "assigned"
    thread["updated_at"] = now_iso()
    _append_message(thread, "system", f"已分配给 {consultant['name']}")
    queue[thread_id] = thread
    if owned_queue:
        save_queue(queue)
    return decorate_thread(thread)


def apply_thread_action(thread_id: str, action: str, operator: str = "ops", note: str = "") -> dict[str, Any]:
    queue = load_queue()
    thread = deepcopy(queue.get(thread_id))
    if not thread:
        raise KeyError("企微任务不存在")

    if action == "start_followup":
        thread["status"] = "following_up"
        _append_message(thread, operator, note or "开始跟进")
    elif action == "close":
        thread["status"] = "closed"
        _append_message(thread, operator, note or "关闭企微任务")
    elif action == "reopen":
        thread["status"] = "assigned" if thread.get("consultant_id") else "pending"
        _append_message(thread, operator, note or "重新打开企微任务")
    elif action == "assign":
        consultant_id = note or ""
        return assign_thread(thread_id, consultant_id=consultant_id)
    else:
        raise ValueError("未知企微动作")

    thread["updated_at"] = now_iso()
    queue[thread_id] = thread
    save_queue(queue)
    return decorate_thread(thread)


def add_thread_message(thread_id: str, sender: str, content: str) -> dict[str, Any]:
    queue = load_queue()
    thread = deepcopy(queue.get(thread_id))
    if not thread:
        raise KeyError("企微任务不存在")
    _append_message(thread, sender, content)
    thread["updated_at"] = now_iso()
    queue[thread_id] = thread
    save_queue(queue)
    return decorate_thread(thread)


def queue_summary() -> dict[str, Any]:
    threads = list_threads()
    by_status = {}
    for thread in threads:
        by_status[thread.get("status", "pending")] = by_status.get(thread.get("status", "pending"), 0) + 1
    return {
        "consultants": CONSULTANTS,
        "total": len(threads),
        "by_status": by_status,
        "items": threads,
    }


def decorate_thread(thread: dict[str, Any] | None) -> dict[str, Any] | None:
    if not thread:
        return None
    item = deepcopy(thread)
    item["available_actions"] = available_actions(item)
    return item


def available_actions(thread: dict[str, Any]) -> list[dict[str, str]]:
    status = thread.get("status", "pending")
    actions = []
    if status in {"pending", "assigned"}:
        actions.append({"action": "start_followup", "label": "开始跟进"})
    if status != "closed":
        actions.append({"action": "close", "label": "关闭任务"})
    if status == "closed":
        actions.append({"action": "reopen", "label": "重新打开"})
    return actions


def _find_open_thread(queue: dict[str, Any], phone: str, scenario: str, product_id: str) -> dict[str, Any] | None:
    for thread in queue.values():
        if thread.get("phone") == phone and thread.get("scenario") == scenario and thread.get("product_id") == product_id:
            if thread.get("status") != "closed":
                return thread
    return None


def _append_message(thread: dict[str, Any], sender: str, content: str) -> None:
    thread.setdefault("messages", []).append({
        "time": now_iso(),
        "sender": sender,
        "content": content,
    })


def _priority_for_scenario(scenario: str) -> int:
    return {
        "lead": 1,
        "assessment": 2,
        "order": 3,
        "renewal": 4,
        "aftercare": 2,
    }.get(scenario, 1)


def _pick_consultant(queue: dict[str, Any], requested_id: str = "") -> dict[str, str]:
    if requested_id:
        for consultant in CONSULTANTS:
            if consultant["id"] == requested_id or consultant["name"] == requested_id:
                return consultant

    loads = {consultant["id"]: 0 for consultant in CONSULTANTS}
    for thread in queue.values():
        if thread.get("status") != "closed" and thread.get("consultant_id") in loads:
            loads[thread["consultant_id"]] += 1

    consultant_id = min(loads, key=loads.get)
    return next(consultant for consultant in CONSULTANTS if consultant["id"] == consultant_id)
