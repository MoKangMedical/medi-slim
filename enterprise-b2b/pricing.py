"""MediSlim 企业健康管理 — 定价模型"""

PLANS = {
    "small": {"name": "小微版", "max_employees": 100, "price_per_person": 30},
    "standard": {"name": "标准版", "max_employees": 500, "price_per_person": 25},
    "enterprise": {"name": "企业版", "max_employees": -1, "price_per_person": 20},
}

def calculate_monthly_fee(employee_count):
    for key, plan in PLANS.items():
        if employee_count <= plan["max_employees"] or plan["max_employees"] == -1:
            return {
                "plan": plan["name"],
                "monthly_total": employee_count * plan["price_per_person"],
                "price_per_person": plan["price_per_person"],
                "annual_total": employee_count * plan["price_per_person"] * 12
            }
    return {"error": "No plan found"}

INDUSTRY_ROI = {
    "科技": {"absenteeism_reduction": 0.3, "medical_save_per_person": 3200, "productivity_boost": 0.05},
    "制造业": {"absenteeism_reduction": 0.25, "medical_save_per_person": 2800, "productivity_boost": 0.03},
    "金融": {"absenteeism_reduction": 0.2, "medical_save_per_person": 2500, "productivity_boost": 0.04},
    "default": {"absenteeism_reduction": 0.2, "medical_save_per_person": 2500, "productivity_boost": 0.03},
}

def calculate_roi(employee_count, industry="default"):
    roi = INDUSTRY_ROI.get(industry, INDUSTRY_ROI["default"])
    fee = calculate_monthly_fee(employee_count)
    medical_saved = employee_count * roi["medical_save_per_person"]
    productivity_value = employee_count * 15000 * roi["productivity_boost"]
    total_benefit = medical_saved + productivity_value
    annual_cost = fee.get("annual_total", 0)
    return {
        "employee_count": employee_count,
        "annual_cost": annual_cost,
        "medical_saved": medical_saved,
        "productivity_value": int(productivity_value),
        "total_benefit": int(total_benefit),
        "net_benefit": int(total_benefit - annual_cost),
        "roi_multiple": round(total_benefit / max(annual_cost, 1), 1)
    }
