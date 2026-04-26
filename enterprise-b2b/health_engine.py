"""健康引擎 — 体质评估/评分/统计"""
from models import get_db, CONSTITUTIONS

QUESTIONS = [
    ("您容易疲劳吗？", {"很少":0,"有时":1,"经常":2}),
    ("您睡眠质量如何？", {"很好":0,"一般":1,"很差":2}),
    ("您容易感冒吗？", {"很少":0,"有时":1,"经常":2}),
    ("您手脚容易发凉吗？", {"不会":0,"有时":1,"经常":2}),
    ("您容易口干舌燥吗？", {"不会":0,"有时":1,"经常":2}),
    ("您体型偏胖吗？", {"标准":0,"微胖":1,"肥胖":2}),
    ("您容易长痘/出油吗？", {"不会":0,"有时":1,"经常":2}),
    ("您容易情绪低落吗？", {"不会":0,"有时":1,"经常":2}),
    ("您容易过敏吗？", {"不会":0,"有时":1,"经常":2}),
]

def assess_constitution(answers):
    scores = {c: 0 for c in CONSTITUTIONS}
    score_map = [
        [("气虚质",2),("阳虚质",1)],
        [("阴虚质",2),("气虚质",1)],
        [("气虚质",2),("阳虚质",1)],
        [("阳虚质",2),("血瘀质",1)],
        [("阴虚质",2),("湿热质",1)],
        [("痰湿质",2),("湿热质",1)],
        [("湿热质",2),("痰湿质",1)],
        [("气郁质",2),("血瘀质",1)],
        [("特禀质",2),("气虚质",1)],
    ]
    for i, ans in enumerate(answers):
        if i < len(score_map):
            for const, weight in score_map[i]:
                scores[const] += ans * weight
    primary = max(scores, key=scores.get)
    return primary, scores

RECOMMENDATIONS = {
    "平和质": "保持规律作息，均衡饮食，适量运动。推荐：每日30分钟有氧运动。",
    "气虚质": "补气养血，避免过劳。推荐：黄芪泡水，八段锦，早睡。",
    "阳虚质": "温阳散寒，注意保暖。推荐：生姜红枣茶，艾灸关元穴。",
    "阴虚质": "滋阴润燥，避免熬夜。推荐：银耳百合汤，少吃辛辣。",
    "痰湿质": "健脾化湿，控制饮食。推荐：薏米红豆粥，少甜少油。",
    "湿热质": "清热利湿，清淡饮食。推荐：冬瓜汤，绿豆粥，忌酒。",
    "血瘀质": "活血化瘀，多运动。推荐：山楂茶，快走，按摩。",
    "气郁质": "疏肝理气，调节情绪。推荐：玫瑰花茶，瑜伽，倾诉。",
    "特禀质": "避免过敏原，增强免疫。推荐：远离过敏源，规律作息。",
}

def get_health_score(emp_id):
    db = get_db()
    rows = db.execute("""SELECT AVG(sleep_hours) as sleep, AVG(exercise_min) as exercise,
                        AVG(water_ml) as water, AVG(mood) as mood 
                        FROM health_checkin WHERE emp_id=? AND date > date('now','-7 days')""", (emp_id,)).fetchone()
    if not rows or rows["sleep"] is None:
        return 0
    sleep_score = min(rows["sleep"] / 8 * 30, 30)
    exercise_score = min(rows["exercise"] / 30 * 25, 25)
    water_score = min(rows["water"] / 2000 * 25, 25)
    mood_score = rows["mood"] / 5 * 20
    total = round(sleep_score + exercise_score + water_score + mood_score, 1)
    db.close()
    return total

def get_dept_stats(company_id):
    db = get_db()
    rows = db.execute("""
        SELECT department, COUNT(*) as cnt, ROUND(AVG(health_score),1) as avg_score
        FROM employee WHERE company_id=? GROUP BY department ORDER BY avg_score DESC
    """, (company_id,)).fetchall()
    db.close()
    return [dict(r) for r in rows]

def get_company_summary(company_id):
    db = get_db()
    emp = db.execute("SELECT COUNT(*) as cnt, AVG(health_score) as avg, COUNT(DISTINCT department) as depts FROM employee WHERE company_id=?", (company_id,)).fetchone()
    active_7d = db.execute("SELECT COUNT(DISTINCT emp_id) FROM health_checkin WHERE emp_id IN (SELECT emp_id FROM employee WHERE company_id=?) AND date > date('now','-7 days')", (company_id,)).fetchone()[0]
    total = emp["cnt"] or 1
    avg_medical_save = 2800
    saved = int(total * (emp["avg"] or 60) / 100 * avg_medical_save)
    db.close()
    return {
        "employee_count": emp["cnt"],
        "avg_health_score": emp["avg"] or 0,
        "departments": emp["depts"],
        "active_7d": active_7d,
        "coverage": round(active_7d / total * 100, 1),
        "estimated_medical_saved": saved
    }
