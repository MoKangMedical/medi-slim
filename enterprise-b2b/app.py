"""MediSlim 企业健康管理MVP — 主应用"""
from flask import Flask, render_template, jsonify, request
from models import init_db, seed_demo_data, get_db, CONSTITUTIONS
from health_engine import get_health_score, get_dept_stats, get_company_summary, assess_constitution, RECOMMENDATIONS
from pricing import calculate_monthly_fee, calculate_roi

app = Flask(__name__)

@app.before_request
def setup():
    if not hasattr(app, '_initialized'):
        init_db()
        seed_demo_data()
        app._initialized = True

@app.route("/")
def index():
    return render_template("admin_dashboard.html")

@app.route("/admin")
def admin():
    return render_template("admin_dashboard.html")

@app.route("/employee")
def employee():
    return render_template("employee_portal.html")

@app.route("/api/company/<int:cid>/summary")
def api_summary(cid):
    return jsonify(get_company_summary(cid))

@app.route("/api/company/<int:cid>/departments")
def api_departments(cid):
    return jsonify(get_dept_stats(cid))

@app.route("/api/company/<int:cid>/employees")
def api_employees(cid):
    db = get_db()
    rows = db.execute("SELECT * FROM employee WHERE company_id=? ORDER BY health_score", (cid,)).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/employee/<emp_id>/score")
def api_emp_score(emp_id):
    score = get_health_score(emp_id)
    db = get_db()
    emp = db.execute("SELECT * FROM employee WHERE emp_id=?", (emp_id,)).fetchone()
    db.close()
    return jsonify({"emp_id": emp_id, "health_score": score, "constitution": emp["constitution_type"] if emp else "未评估"})

@app.route("/api/employee/<emp_id>/checkin", methods=["POST"])
def api_checkin(emp_id):
    data = request.json
    db = get_db()
    from datetime import datetime
    db.execute("INSERT INTO health_checkin(emp_id,date,sleep_hours,exercise_min,water_ml,mood) VALUES(?,?,?,?,?,?)",
               (emp_id, datetime.now().strftime("%Y-%m-%d"),
                data.get("sleep", 7), data.get("exercise", 0),
                data.get("water", 1500), data.get("mood", 3)))
    db.commit()
    db.close()
    return jsonify({"status": "ok", "message": "打卡成功！坚持就是胜利 💪"})

@app.route("/api/assess", methods=["POST"])
def api_assess():
    data = request.json
    answers = data.get("answers", [1]*9)
    primary, scores = assess_constitution(answers)
    return jsonify({
        "primary_constitution": primary,
        "scores": scores,
        "recommendation": RECOMMENDATIONS.get(primary, "请咨询专业中医师"),
        "detail": f"您属于{primary}，{RECOMMENDATIONS.get(primary, '')}"
    })

@app.route("/api/ai_chat", methods=["POST"])
def api_ai_chat():
    data = request.json
    q = data.get("question", "")
    responses = {
        "减肥": "GLP-1类药物（如司美格鲁肽）是目前最有效的减重方式之一。建议先做体质评估，我们会为您匹配最合适的方案。请回复「评估」开始。",
        "失眠": "睡眠问题很常见。建议：1. 固定作息时间 2. 睡前1小时不看手机 3. 适量运动但不要太晚 4. 避免咖啡因。如需助眠产品推荐，请联系健康顾问。",
        "脱发": "脱发可能与压力、营养、激素有关。建议先检查甲状腺功能和铁蛋白。外用米诺地尔+口服非那雄胺是经典方案，但需医生处方。",
        "体检": "年度体检建议包含：血常规、肝肾功能、血脂血糖、甲状腺、肿瘤标志物。40岁以上建议加做肠镜。",
    }
    answer = "感谢您的咨询！我是MediSlim AI健康助手。您可以问我关于：减重、睡眠、脱发、体检、饮食、运动等健康话题。"
    for k, v in responses.items():
        if k in q:
            answer = v
            break
    return jsonify({"question": q, "answer": answer})

@app.route("/api/pricing")
def api_pricing():
    emp_count = int(request.args.get("employees", 100))
    industry = request.args.get("industry", "default")
    return jsonify({
        "fee": calculate_monthly_fee(emp_count),
        "roi": calculate_roi(emp_count, industry)
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
