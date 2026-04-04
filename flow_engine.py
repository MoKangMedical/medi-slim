"""
MediSlim 完整业务流引擎
Medvi模式中国版 — 端到端业务流自动化
"""
import os
import json
import uuid
import time
from datetime import datetime, timedelta
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

DATA_DIR = Path("./data")
DATA_DIR.mkdir(exist_ok=True)

def load_db(name):
    f = DATA_DIR / f"{name}.json"
    return json.loads(f.read_text()) if f.exists() else {}

def save_db(name, data):
    (DATA_DIR / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))

def now():
    return datetime.now().isoformat()

def gen_id():
    return str(uuid.uuid4())[:12]

# ========== 状态机 ==========
ORDER_STATES = {
    "new_lead":        {"next": "contacted",      "timeout_hours": 0.5, "action": "顾问联系"},
    "contacted":       {"next": "assessed",       "timeout_hours": 24,  "action": "完成AI评估"},
    "assessed":        {"next": "paid",           "timeout_hours": 48,  "action": "引导付费"},
    "paid":            {"next": "ih_submitted",   "timeout_hours": 1,   "action": "推送互联网医院"},
    "ih_submitted":    {"next": "doctor_review",  "timeout_hours": 2,   "action": "医师接诊"},
    "doctor_review":   {"next": "prescribed",     "timeout_hours": 24,  "action": "医师开方"},
    "prescribed":      {"next": "pharmacy_order", "timeout_hours": 2,   "action": "推送药房"},
    "pharmacy_order":  {"next": "dispensing",     "timeout_hours": 12,  "action": "药房配药"},
    "dispensing":      {"next": "shipped",        "timeout_hours": 12,  "action": "发货"},
    "shipped":         {"next": "delivered",      "timeout_hours": 72,  "action": "签收"},
    "delivered":       {"next": "in_use",         "timeout_hours": 24,  "action": "开始用药"},
    "in_use":          {"next": "refill_reminder","timeout_hours": 504, "action": "用药中(21天)"},
    "refill_reminder": {"next": "refill_paid",    "timeout_hours": 168, "action": "续费窗口(7天)"},
    "refill_paid":     {"next": "pharmacy_order", "timeout_hours": 1,   "action": "复购发货"},
    "cancelled":       {"next": None,             "timeout_hours": 0,   "action": "已取消"},
}

# ========== 互联网医院模拟API ==========
class InternetHospitalAPI:
    """模拟互联网医院API（对接微医/好大夫/京东健康）"""
    
    @staticmethod
    def create_consultation(order_id, patient_info, assessment):
        """创建远程问诊"""
        consult_id = gen_id()
        return {
            "consult_id": consult_id,
            "order_id": order_id,
            "status": "submitted",
            "estimated_review_time": "2小时内",
            "hospital": "合作互联网医院",
            "created_at": now(),
        }
    
    @staticmethod
    def check_status(consult_id):
        """查询问诊状态（模拟自动通过）"""
        return {
            "consult_id": consult_id,
            "status": "approved",
            "doctor": "王医生（执业医师）",
            "license": "医师执业证书编号 XXXXXX",
            "review_time": now(),
            "prescription": {
                "drug": "司美格鲁肽注射液",
                "spec": "1.5ml:2.01mg",
                "dosage": "起始剂量0.25mg/周，4周后增至0.5mg/周",
                "quantity": 1,
                "instructions": "皮下注射，每周一次，腹部或大腿",
                "refills": 3,
            }
        }

# ========== 药房模拟API ==========
class PharmacyAPI:
    """模拟药房API（对接大参林/益丰/老百姓）"""
    
    @staticmethod
    def submit_order(prescription, shipping_address):
        """提交配药订单"""
        order_id = gen_id()
        return {
            "pharmacy_order_id": order_id,
            "status": "received",
            "pharmacy": "合作连锁药房",
            "estimated_dispense_time": "12小时内",
            "created_at": now(),
        }
    
    @staticmethod
    def check_status(order_id):
        """查询配药状态"""
        return {
            "order_id": order_id,
            "status": "dispensed",
            "qc_passed": True,
            "tracking_no": f"SF{gen_id().upper()}",
            "carrier": "顺丰速运",
            "estimated_delivery": "1-2个工作日",
        }

# ========== 支付模拟API ==========
class PaymentAPI:
    """模拟支付API（对接微信支付/支付宝）"""
    
    @staticmethod
    def create_payment(order_id, amount, product_name):
        """创建支付"""
        return {
            "pay_id": gen_id(),
            "order_id": order_id,
            "amount": amount,
            "product": product_name,
            "status": "pending",
            "pay_url": f"https://pay.example.com/{gen_id()}",
            "expires_at": (datetime.now() + timedelta(minutes=30)).isoformat(),
        }
    
    @staticmethod
    def callback(pay_id):
        """支付回调（模拟成功）"""
        return {
            "pay_id": pay_id,
            "status": "success",
            "paid_at": now(),
            "transaction_id": f"wx_{gen_id()}",
        }

# ========== 订单管理 ==========
class OrderEngine:
    """完整订单生命周期管理"""
    
    @staticmethod
    def create_from_lead(lead_id, product_id, assessment, name, phone, address):
        """从线索创建订单"""
        orders = load_db("orders")
        products_db = load_db("products")
        product = products_db.get("products", {}).get(product_id, {})
        
        order = {
            "id": gen_id(),
            "lead_id": lead_id,
            "product_id": product_id,
            "product_name": product.get("name", product_id),
            "state": "new_lead",
            "state_history": [{"state": "new_lead", "time": now(), "note": "线索创建"}],
            "assessment": assessment,
            "patient": {"name": name, "phone": phone, "address": address},
            "price": product.get("first_price", 0),
            "prescription": None,
            "tracking": None,
            "refill_count": 0,
            "next_refill_date": None,
            "created_at": now(),
            "updated_at": now(),
        }
        
        orders[order["id"]] = order
        save_db("orders", orders)
        return order
    
    @staticmethod
    def advance_state(order_id, note=""):
        """推进订单状态"""
        orders = load_db("orders")
        order = orders.get(order_id)
        if not order:
            return None
        
        current = order["state"]
        next_state = ORDER_STATES.get(current, {}).get("next")
        
        if not next_state:
            return order  # 已终态
        
        # 执行状态转换的副作用
        result = OrderEngine._execute_transition(order, current, next_state)
        
        order["state"] = next_state
        order["state_history"].append({
            "state": next_state,
            "time": now(),
            "note": note or ORDER_STATES.get(next_state, {}).get("action", ""),
            "result": result,
        })
        order["updated_at"] = now()
        
        orders[order_id] = order
        save_db("orders", orders)
        return order
    
    @staticmethod
    def _execute_transition(order, from_state, to_state):
        """执行状态转换的副作用"""
        
        if to_state == "paid":
            # 模拟支付成功
            return {"payment": "success", "amount": order["price"]}
        
        elif to_state == "ih_submitted":
            # 推送互联网医院
            ih_result = InternetHospitalAPI.create_consultation(
                order["id"], order["patient"], order["assessment"]
            )
            order["ih_consult_id"] = ih_result["consult_id"]
            return ih_result
        
        elif to_state == "prescribed":
            # 获取处方
            presc = InternetHospitalAPI.check_status(order.get("ih_consult_id", ""))
            order["prescription"] = presc.get("prescription")
            return presc
        
        elif to_state == "pharmacy_order":
            # 推送药房
            pharma = PharmacyAPI.submit_order(
                order.get("prescription"), order["patient"].get("address")
            )
            order["pharmacy_order_id"] = pharma["pharmacy_order_id"]
            return pharma
        
        elif to_state == "shipped":
            # 获取物流信息
            tracking = PharmacyAPI.check_status(order.get("pharmacy_order_id", ""))
            order["tracking"] = tracking
            return tracking
        
        elif to_state == "refill_reminder":
            # 设置复购日期
            order["next_refill_date"] = (datetime.now() + timedelta(days=7)).isoformat()
            return {"reminder": "已推送续费提醒", "deadline": order["next_refill_date"]}
        
        elif to_state == "refill_paid":
            # 复购成功
            order["refill_count"] = order.get("refill_count", 0) + 1
            return {"refill": f"第{order['refill_count']}次复购", "amount": order["price"]}
        
        return {}
    
    @staticmethod
    def auto_advance(order_id):
        """自动推进到下一步（用于自动化流程）"""
        return OrderEngine.advance_state(order_id, "系统自动推进")
    
    @staticmethod
    def process_all():
        """批量处理所有可推进的订单"""
        orders = load_db("orders")
        results = []
        for oid, order in orders.items():
            current = order.get("state")
            next_state = ORDER_STATES.get(current, {}).get("next")
            if next_state and next_state not in ("refill_paid",):
                # 自动推进（除复购外）
                result = OrderEngine.auto_advance(oid)
                results.append({"order_id": oid, "from": current, "to": order["state"]})
        return results
    
    @staticmethod
    def get_dashboard():
        """运营看板数据"""
        orders = load_db("orders").values()
        
        by_state = {}
        for o in orders:
            s = o.get("state", "unknown")
            by_state[s] = by_state.get(s, 0) + 1
        
        today = datetime.now().strftime("%Y-%m-%d")
        today_orders = [o for o in orders if o.get("created_at", "")[:10] == today]
        
        revenue = sum(o.get("price", 0) for o in orders if o.get("state") not in ("new_lead", "contacted", "assessed", "cancelled"))
        
        return {
            "total_orders": len(list(orders)),
            "today_orders": len(today_orders),
            "total_revenue": revenue,
            "by_state": by_state,
            "states": list(ORDER_STATES.keys()),
        }

# ========== HTTP API ==========
class FlowHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        
        if path == "/api/flow/dashboard":
            self._json(OrderEngine.get_dashboard())
        elif path == "/api/flow/orders":
            orders = load_db("orders")
            self._json(list(orders.values()))
        elif path == "/api/flow/process":
            result = OrderEngine.process_all()
            self._json({"processed": len(result), "results": result})
        elif path == "/api/flow/states":
            self._json(ORDER_STATES)
        else:
            self._json({"error": "Not found"}, 404)
    
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode() if length else "{}"
        try: data = json.loads(body)
        except: data = {}
        
        path = self.path
        
        if path == "/api/flow/order/create":
            order = OrderEngine.create_from_lead(
                data.get("lead_id", gen_id()),
                data.get("product_id", "glp1"),
                data.get("assessment", {}),
                data.get("name", ""),
                data.get("phone", ""),
                data.get("address", ""),
            )
            self._json(order)
        
        elif path == "/api/flow/order/advance":
            order = OrderEngine.advance_state(
                data.get("order_id", ""),
                data.get("note", "")
            )
            self._json(order if order else {"error": "Order not found"}, 404 if not order else 200)
        
        elif path == "/api/flow/order/process-all":
            result = OrderEngine.process_all()
            self._json({"processed": len(result), "results": result})
        
        elif path == "/api/flow/simulate-full":
            # 模拟完整业务流
            order = OrderEngine.create_from_lead(
                gen_id(), "glp1", {},
                data.get("name", "测试用户"),
                data.get("phone", "13800001234"),
                data.get("address", "北京市朝阳区XX路XX号"),
            )
            oid = order["id"]
            
            # 自动推进全流程
            steps = []
            while True:
                current = order["state"]
                order = OrderEngine.auto_advance(oid)
                if order["state"] == current:
                    break
                steps.append({"from": current, "to": order["state"]})
                if order["state"] in ("in_use", "cancelled"):
                    break
            
            self._json({
                "order_id": oid,
                "final_state": order["state"],
                "steps": steps,
                "prescription": order.get("prescription"),
                "tracking": order.get("tracking"),
            })
        
        else:
            self._json({"error": "Not found"}, 404)
    
    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode())
    def log_message(self, *a): pass

# 初始化产品数据
products = {
    "products": {
        "glp1": {"name": "GLP-1 科学减重", "first_price": 399, "renew_price": 599, "emoji": "🔥"},
        "hair": {"name": "防脱生发", "first_price": 199, "renew_price": 299, "emoji": "💇"},
        "skin": {"name": "皮肤管理", "first_price": 299, "renew_price": 399, "emoji": "🧴"},
        "mens": {"name": "男性健康", "first_price": 399, "renew_price": 599, "emoji": "💪"},
        "sleep": {"name": "助眠调理", "first_price": 199, "renew_price": 299, "emoji": "😴"},
    }
}
if not (DATA_DIR / "products.json").exists():
    save_db("products", products)

def main():
    port = int(os.environ.get("PORT", 8092))
    server = HTTPServer(("0.0.0.0", port), FlowHandler)
    print(f"🔄 MediSlim 业务流引擎启动: http://localhost:{port}")
    print(f"📊 看板: http://localhost:{port}/api/flow/dashboard")
    print(f"🧪 模拟: POST http://localhost:{port}/api/flow/simulate-full")
    server.serve_forever()

if __name__ == "__main__":
    main()
