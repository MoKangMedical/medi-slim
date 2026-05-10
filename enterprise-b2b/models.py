"""MediSlim 企业健康管理 — 数据模型"""
import sqlite3
from datetime import datetime, timedelta
import random

DB_PATH = "enterprise_b2b.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS company (
        id INTEGER PRIMARY KEY, name TEXT, industry TEXT, employee_count INTEGER,
        plan_type TEXT, monthly_fee REAL, created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS employee (
        id INTEGER PRIMARY KEY, emp_id TEXT, company_id INTEGER, name TEXT,
        department TEXT, health_score REAL DEFAULT 0, constitution_type TEXT,
        last_active TEXT, created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS health_checkin (
        id INTEGER PRIMARY KEY, emp_id TEXT, date TEXT,
        sleep_hours REAL, exercise_min INTEGER, water_ml INTEGER, mood INTEGER
    );
    CREATE TABLE IF NOT EXISTS health_assessment (
        id INTEGER PRIMARY KEY, emp_id TEXT, date TEXT,
        constitution_type TEXT, scores TEXT, recommendations TEXT
    );
    CREATE TABLE IF NOT EXISTS ai_chat (
        id INTEGER PRIMARY KEY, emp_id TEXT, question TEXT, answer TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """)
    conn.commit()
    conn.close()

CONSTITUTIONS = ["平和质","气虚质","阳虚质","阴虚质","痰湿质","湿热质","血瘀质","气郁质","特禀质"]
DEPARTMENTS = ["研发部","市场部","销售部","财务部","HR","运营部","产品部"]
NAMES = ["张伟","李娜","王磊","刘洋","陈静","杨帆","赵敏","黄强","周杰","吴芳","徐明","孙丽","马超","朱婷","胡涛","林燕","郭亮","何雪","罗勇","谢芳"]

def seed_demo_data():
    conn = get_db()
    if conn.execute("SELECT COUNT(*) FROM company").fetchone()[0] > 0:
        conn.close()
        return
    companies = [
        ("字节跳动","科技",200,"enterprise",4000),
        ("比亚迪","制造业",500,"enterprise",10000),
        ("招商银行","金融",150,"standard",3750),
    ]
    for c in companies:
        conn.execute("INSERT INTO company(name,industry,employee_count,plan_type,monthly_fee) VALUES(?,?,?,?,?)", c)
    
    emp_counter = 0
    for cid in range(1, 4):
        count = [200, 500, 150][cid-1]
        for i in range(min(count, 60)):
            emp_counter += 1
            dept = DEPARTMENTS[i % len(DEPARTMENTS)]
            name = random.choice(NAMES)
            const = random.choice(CONSTITUTIONS)
            score = round(random.uniform(45, 95), 1)
            last = (datetime.now() - timedelta(days=random.randint(0, 10))).strftime("%Y-%m-%d")
            conn.execute("INSERT INTO employee(emp_id,company_id,name,department,health_score,constitution_type,last_active) VALUES(?,?,?,?,?,?,?)",
                         (f"EMP{str(emp_counter).zfill(4)}", cid, name, dept, score, const, last))
            for d in range(30):
                date = (datetime.now() - timedelta(days=d)).strftime("%Y-%m-%d")
                conn.execute("INSERT INTO health_checkin(emp_id,date,sleep_hours,exercise_min,water_ml,mood) VALUES(?,?,?,?,?,?)",
                             (f"EMP{str(emp_counter).zfill(4)}", date,
                              round(random.uniform(5, 9), 1), random.randint(0, 60),
                              random.randint(500, 2500), random.randint(1, 5)))
    
    conn.commit()
    conn.close()
    print("✅ Demo data seeded: 3 companies, 180 employees, 5400+ checkins")
