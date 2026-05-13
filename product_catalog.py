"""Extended product catalog and dashboard helpers.

The orderable products remain in app.Config.PRODUCTS. This catalog captures the
broader three-circle product strategy for product-side planning and reporting.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


PRODUCT_CATALOG = {
    "glp1": {"name": "GLP-1 科学减重", "circle": "处方药", "price": 399, "renewal": 599, "category": "prescription", "cost_pct": 0.45, "status": "active"},
    "hair": {"name": "防脱生发", "circle": "处方药", "price": 199, "renewal": 299, "category": "prescription", "cost_pct": 0.40, "status": "active"},
    "mens": {"name": "男性健康", "circle": "处方药", "price": 399, "renewal": 599, "category": "prescription", "cost_pct": 0.38, "status": "active"},
    "sleep": {"name": "助眠调理", "circle": "轻处方/OTC", "price": 199, "renewal": 299, "category": "prescription", "cost_pct": 0.35, "status": "active"},
    "skin": {"name": "皮肤管理", "circle": "轻处方/功效护肤", "price": 299, "renewal": 399, "category": "prescription", "cost_pct": 0.42, "status": "active"},
    "damp": {"name": "祛湿轻体", "circle": "药食同源", "price": 168, "renewal": 168, "category": "tcm_food", "cost_pct": 0.21, "status": "planning"},
    "blood": {"name": "气血调养", "circle": "药食同源", "price": 198, "renewal": 198, "category": "tcm_food", "cost_pct": 0.23, "status": "planning"},
    "liver": {"name": "护肝养生", "circle": "药食同源", "price": 168, "renewal": 168, "category": "tcm_food", "cost_pct": 0.25, "status": "planning"},
    "warm": {"name": "暖宫驱寒", "circle": "药食同源", "price": 158, "renewal": 158, "category": "tcm_food", "cost_pct": 0.22, "status": "planning"},
    "spleen": {"name": "健脾养胃", "circle": "药食同源", "price": 148, "renewal": 148, "category": "tcm_food", "cost_pct": 0.24, "status": "planning"},
    "lung": {"name": "润肺清燥", "circle": "药食同源", "price": 138, "renewal": 138, "category": "tcm_food", "cost_pct": 0.20, "status": "planning"},
    "probiotic": {"name": "益生菌", "circle": "保健品", "price": 198, "renewal": 198, "category": "supplement", "cost_pct": 0.23, "status": "planning"},
    "collagen": {"name": "胶原蛋白", "circle": "保健品", "price": 228, "renewal": 228, "category": "supplement", "cost_pct": 0.25, "status": "planning"},
    "vd": {"name": "维生素 D", "circle": "保健品", "price": 98, "renewal": 98, "category": "supplement", "cost_pct": 0.18, "status": "planning"},
    "omega": {"name": "Omega-3 鱼油", "circle": "保健品", "price": 168, "renewal": 168, "category": "supplement", "cost_pct": 0.22, "status": "planning"},
    "q10": {"name": "辅酶 Q10", "circle": "保健品", "price": 188, "renewal": 188, "category": "supplement", "cost_pct": 0.24, "status": "planning"},
    "lutein": {"name": "叶黄素", "circle": "保健品", "price": 128, "renewal": 128, "category": "supplement", "cost_pct": 0.20, "status": "planning"},
    "protein": {"name": "蛋白粉", "circle": "保健品", "price": 188, "renewal": 188, "category": "supplement", "cost_pct": 0.28, "status": "planning"},
    "multiv": {"name": "综合维生素", "circle": "保健品", "price": 128, "renewal": 128, "category": "supplement", "cost_pct": 0.19, "status": "planning"},
}

ACTIVE_STATUSES = {"paid", "doctor_review", "approved", "pharmacy_processing", "shipped", "delivered", "completed"}


def list_product_catalog() -> list[dict[str, Any]]:
    return [
        {"id": product_id, **product}
        for product_id, product in sorted(PRODUCT_CATALOG.items(), key=lambda item: (item[1]["category"], item[0]))
    ]


def product_catalog_summary() -> dict[str, Any]:
    items = list_product_catalog()
    by_circle: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for item in items:
        by_circle[item["circle"]] = by_circle.get(item["circle"], 0) + 1
        by_status[item["status"]] = by_status.get(item["status"], 0) + 1
    return {
        "total": len(items),
        "by_circle": by_circle,
        "by_status": by_status,
        "items": items,
    }


def product_performance_dashboard(orders: dict[str, Any]) -> list[dict[str, Any]]:
    order_rows = [order for order in orders.values() if isinstance(order, dict)]
    rows = []
    for product_id, product in PRODUCT_CATALOG.items():
        related = [
            order for order in order_rows
            if order.get("product_id") == product_id or order.get("product") == product_id
        ]
        revenue = sum(float(order.get("price") or order.get("amount") or 0) for order in related)
        active = sum(1 for order in related if order.get("status") in ACTIVE_STATUSES or order.get("state") in ACTIVE_STATUSES)
        rows.append({
            "id": product_id,
            "name": product["name"],
            "circle": product["circle"],
            "category": product["category"],
            "status": product["status"],
            "price": product["price"],
            "renewal": product["renewal"],
            "orders": len(related),
            "active_orders": active,
            "revenue": round(revenue, 2),
            "gross_profit": round(revenue * (1 - product["cost_pct"]), 2),
            "gross_margin": round((1 - product["cost_pct"]) * 100, 1),
        })
    rows.sort(key=lambda item: (item["revenue"], item["orders"], item["status"] == "active"), reverse=True)
    return rows


def revenue_dashboard(orders: dict[str, Any], leads: dict[str, Any] | None = None) -> dict[str, Any]:
    now = datetime.now()
    today = now.date().isoformat()
    month = now.strftime("%Y-%m")
    start = now.date() - timedelta(days=29)
    daily = {(start + timedelta(days=offset)).isoformat(): 0.0 for offset in range(30)}
    by_product: dict[str, float] = {}
    by_channel: dict[str, float] = {}
    by_circle: dict[str, float] = {}

    order_rows = [order for order in orders.values() if isinstance(order, dict)]
    total_revenue = 0.0
    today_revenue = 0.0
    month_revenue = 0.0
    for order in order_rows:
        amount = float(order.get("price") or order.get("amount") or 0)
        total_revenue += amount
        created_at = str(order.get("created_at") or order.get("date") or "")
        date_key = created_at[:10]
        if date_key == today:
            today_revenue += amount
        if created_at[:7] == month:
            month_revenue += amount
        if date_key in daily:
            daily[date_key] += amount

        product_id = order.get("product_id") or order.get("product") or "unknown"
        product = PRODUCT_CATALOG.get(product_id, {})
        by_product[product_id] = by_product.get(product_id, 0.0) + amount
        by_circle[product.get("circle", "未归类")] = by_circle.get(product.get("circle", "未归类"), 0.0) + amount

        attribution = order.get("attribution", {}) if isinstance(order.get("attribution"), dict) else {}
        channel = attribution.get("utm_source") or attribution.get("source") or order.get("channel") or "direct"
        by_channel[channel] = by_channel.get(channel, 0.0) + amount

    lead_count = len(leads or {})
    return {
        "total_revenue": round(total_revenue, 2),
        "today_revenue": round(today_revenue, 2),
        "month_revenue": round(month_revenue, 2),
        "total_orders": len(order_rows),
        "total_leads": lead_count,
        "conversion": round(len(order_rows) / max(lead_count, 1) * 100, 1) if lead_count else 0.0,
        "by_product": _round_map(by_product),
        "by_channel": _round_map(by_channel),
        "by_circle": _round_map(by_circle),
        "daily": _round_map(daily),
        "mrr": round(month_revenue, 2),
    }


def _round_map(values: dict[str, float]) -> dict[str, float]:
    return {key: round(value, 2) for key, value in values.items()}
