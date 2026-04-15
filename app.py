"""
MediSlim — 中国版Medvi消费医疗平台
完全复刻Medvi极简架构：只做流量层，医疗合规全外包
技术栈：Python原生HTTP + 微信小程序风格前端
"""
import os
import json
import uuid
import time
import logging
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

# ========== 决策检查点 ==========
from decision_checkpoint import (
    validate_phone, validate_address, validate_product_exists,
    validate_order_preview, validate_prescription_check,
    validate_data_save, get_audit_log, get_checkpoint_registry,
)

# ========== 日志配置 ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("MediSlim")

# ========== 配置 ==========
class Config:
    APP_NAME = "MediSlim 轻健康"
    VERSION = "1.0.0"

    PRODUCTS = {
        "glp1": {
            "name": "GLP-1 科学减重",
            "emoji": "🔥",
            "description": "司美格鲁肽/替尔泊肽，医生指导，科学减重",
            "first_price": 399,
            "renew_price": 599,
            "unit": "月",
            "includes": ["医师评估", "个性化方案", "药品配送", "24h在线支持", "体重管理报告"],
            "requires_prescription": True,
            "category": "减肥",
        },
        "hair": {
            "name": "防脱生发",
            "emoji": "💇",
            "description": "米诺地尔/非那雄胺，专业防脱方案",
            "first_price": 199,
            "renew_price": 299,
            "unit": "月",
            "includes": ["毛囊检测评估", "药物方案", "每月随访", "生发跟踪"],
            "requires_prescription": True,
            "category": "脱发",
        },
        "skin": {
            "name": "皮肤管理",
            "emoji": "🧴",
            "description": "祛痘/美白/抗衰，皮肤科医生在线诊疗",
            "first_price": 299,
            "renew_price": 399,
            "unit": "月",
            "includes": ["皮肤评估", "个性化方案", "药品/护肤品配送", "定期随访"],
            "requires_prescription": False,
            "category": "皮肤",
        },
        "mens": {
            "name": "男性健康",
            "emoji": "💪",
            "description": "精力管理/睾酮/前列腺，专业男性健康",
            "first_price": 399,
            "renew_price": 599,
            "unit": "月",
            "includes": ["健康评估", "检验建议", "药物方案", "隐私配送"],
            "requires_prescription": True,
            "category": "男性",
        },
        "sleep": {
            "name": "助眠调理",
            "emoji": "😴",
            "description": "失眠/焦虑/褪黑素，科学改善睡眠",
            "first_price": 199,
            "renew_price": 299,
            "unit": "月",
            "includes": ["睡眠评估", "行为指导", "必要时药物", "睡眠日记跟踪"],
            "requires_prescription": False,
            "category": "睡眠",
        },
    }

    ASSESSMENT_QUESTIONS = {
        "glp1": [
            {"id": 1, "text": "您的身高是多少(cm)？", "type": "input", "field": "height"},
            {"id": 2, "text": "您的体重是多少(kg)？", "type": "input", "field": "weight"},
            {"id": 3, "text": "您的目标体重是多少(kg)？", "type": "input", "field": "target_weight"},
            {"id": 4, "text": "是否有糖尿病或糖尿病前期？", "type": "choice", "options": ["是", "否", "不确定"]},
            {"id": 5, "text": "是否尝试过其他减肥方法？", "type": "choice", "options": ["节食", "运动", "减肥药", "均未尝试"]},
            {"id": 6, "text": "是否有甲状腺疾病？", "type": "choice", "options": ["是", "否"]},
            {"id": 7, "text": "是否有胰腺炎病史？", "type": "choice", "options": ["是", "否"]},
            {"id": 8, "text": "是否怀孕或备孕中？", "type": "choice", "options": ["是", "否", "不适用"]},
            {"id": 9, "text": "是否有进食障碍史？", "type": "choice", "options": ["是", "否"]},
            {"id": 10, "text": "希望多久达到目标？", "type": "choice", "options": ["3个月", "6个月", "1年", "不急"]},
        ],
        "hair": [
            {"id": 1, "text": "脱发类型？", "type": "choice", "options": ["M型发际线", "头顶稀疏", "整体稀疏", "斑秃"]},
            {"id": 2, "text": "脱发持续多长时间？", "type": "choice", "options": ["不到半年", "半年~2年", "2年以上"]},
            {"id": 3, "text": "家族是否有脱发史？", "type": "choice", "options": ["父亲", "母亲", "双方", "无"]},
            {"id": 4, "text": "是否使用过防脱产品？", "type": "choice", "options": ["米诺地尔", "非那雄胺", "其他", "未使用"]},
            {"id": 5, "text": "是否有药物过敏？", "type": "choice", "options": ["是", "否"]},
            {"id": 6, "text": "是否有肝脏疾病？", "type": "choice", "options": ["是", "否"]},
        ],
        "skin": [
            {"id": 1, "text": "主要皮肤问题？", "type": "choice", "options": ["痘痘/痤疮", "色斑/暗沉", "皱纹/松弛", "敏感/红血丝"]},
            {"id": 2, "text": "皮肤类型？", "type": "choice", "options": ["油性", "干性", "混合", "敏感"]},
            {"id": 3, "text": "问题持续时间？", "type": "choice", "options": ["不到1个月", "1-6个月", "6个月以上"]},
            {"id": 4, "text": "是否使用过处方药？", "type": "choice", "options": ["维A酸", "抗生素", "激素类", "未使用"]},
            {"id": 5, "text": "是否有药物过敏？", "type": "choice", "options": ["是", "否"]},
        ],
        "mens": [
            {"id": 1, "text": "主要困扰？", "type": "choice", "options": ["精力不足", "性功能", "前列腺", "其他"]},
            {"id": 2, "text": "年龄？", "type": "input", "field": "age"},
            {"id": 3, "text": "是否有心血管疾病？", "type": "choice", "options": ["是", "否"]},
            {"id": 4, "text": "是否检测过睾酮水平？", "type": "choice", "options": ["是（偏低）", "是（正常）", "未检测"]},
            {"id": 5, "text": "是否有药物过敏？", "type": "choice", "options": ["是", "否"]},
        ],
        "sleep": [
            {"id": 1, "text": "失眠类型？", "type": "choice", "options": ["入睡困难", "易醒", "早醒", "多梦"]},
            {"id": 2, "text": "失眠持续时间？", "type": "choice", "options": ["不到1周", "1-4周", "1-3个月", "3个月以上"]},
            {"id": 3, "text": "是否伴有焦虑/抑郁？", "type": "choice", "options": ["是", "否", "不确定"]},
            {"id": 4, "text": "是否使用过助眠药物？", "type": "choice", "options": ["褪黑素", "安定类", "中成药", "未使用"]},
            {"id": 5, "text": "每天睡眠时长？", "type": "choice", "options": ["不到4小时", "4-6小时", "6-8小时"]},
        ],
    }

    PARTNER_HOSPITALS = [
        {"id": "p001", "name": "京东健康互联网医院", "specialties": ["全科", "皮肤科", "男科"], "type": "互联网医院"},
        {"id": "p002", "name": "微医互联网医院", "specialties": ["全科", "内分泌", "皮肤科"], "type": "互联网医院"},
        {"id": "p003", "name": "好大夫在线", "specialties": ["全科", "脱发", "减重"], "type": "互联网医院"},
    ]

    PARTNER_PHARMACIES = [
        {"id": "f001", "name": "大参林大药房", "type": "连锁药房", "delivery": "顺丰/京东"},
        {"id": "f002", "name": "益丰大药房", "type": "连锁药房", "delivery": "顺丰"},
    ]

# ========== 数据存储 ==========
DATA_DIR = Path("./data")
DATA_DIR.mkdir(exist_ok=True)

def load_data(name):
    """从JSON文件加载数据，解析失败时返回空字典。"""
    f = DATA_DIR / f"{name}.json"
    if f.exists():
        try:
            return json.loads(f.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"load_data({name}): JSON解析失败: {e}")
            return {}
    return {}

def save_data(name, data):
    """保存数据，带决策检查点校验"""
    result = validate_data_save(name, data)
    if not result.passed:
        logger.error(f"save_data({name}): 数据校验失败 - {result.message}")
        raise ValueError(f"数据校验失败: {result.message}")
    try:
        (DATA_DIR / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))
    except (TypeError, OSError) as e:
        logger.error(f"save_data({name}): 写入失败: {e}")
        raise

# ========== AI引擎 ==========
class SlimAIEngine:
    @staticmethod
    def analyze(product_id, answers):
        """分析评估结果，带完整异常处理"""
        if not product_id or not isinstance(product_id, str):
            logger.warning("analyze: product_id 为空或类型错误")
            return {"error": "产品ID不能为空", "eligible": False}

        product = Config.PRODUCTS.get(product_id)
        if not product:
            logger.warning(f"analyze: 未知产品 {product_id}")
            return {"error": f"未知产品: {product_id}", "eligible": False}

        questions = Config.ASSESSMENT_QUESTIONS.get(product_id, [])
        if not answers or not isinstance(answers, dict):
            logger.warning(f"analyze({product_id}): answers为空或类型错误")
            return {"error": "评估答案不能为空", "eligible": False}

        try:
            if product_id == "glp1":
                return SlimAIEngine._analyze_glp1(product, answers, questions)
            elif product_id == "hair":
                return SlimAIEngine._analyze_hair(product, answers, questions)
            else:
                return SlimAIEngine._analyze_generic(product, product_id, answers, questions)
        except (ValueError, TypeError) as e:
            logger.error(f"analyze({product_id}) 数据错误: {e}")
            return {"error": f"数据处理错误: {e}", "eligible": False}
        except Exception as e:
            logger.error(f"analyze({product_id}) 未知错误: {e}\n{traceback.format_exc()}")
            return {"error": "系统内部错误，请稍后重试", "eligible": False}

    @staticmethod
    def _analyze_glp1(product, answers, questions):
        """GLP-1减重专项评估：BMI计算、禁忌症筛查、疗程估算。"""
        try:
            height = float(answers.get("1", "170")) / 100
            weight = float(answers.get("2", "80"))
            target = float(answers.get("3", "70"))
        except (ValueError, TypeError) as e:
            logger.warning(f"GLP-1数据解析失败: {e}，使用默认值")
            height, weight, target = 1.70, 80.0, 70.0

        bmi = round(weight / (height ** 2), 1)
        need = round(weight - target, 1)

        # 禁忌症筛查
        contraindications = []
        if answers.get("4") == "是":
            contraindications.append("糖尿病（需医师评估用药方案）")
        if answers.get("6") == "是":
            contraindications.append("甲状腺疾病（需排除MTC风险）")
        if answers.get("7") == "是":
            contraindications.append("胰腺炎病史（GLP-1相对禁忌）")
        if answers.get("8") == "是":
            contraindications.append("怀孕/备孕（禁用GLP-1）")
        if answers.get("9") == "是":
            contraindications.append("进食障碍史（需心理评估）")

        if contraindications:
            return {
                "product": product["name"],
                "eligible": False,
                "reason": "存在用药禁忌，建议线下就诊",
                "contraindications": contraindications,
                "recommendation": "请前往三甲医院内分泌科进行详细评估",
            }

        # BMI评估
        if bmi >= 28:
            urgency = "high"
            plan = "强烈推荐GLP-1治疗 + 饮食运动指导"
        elif bmi >= 24:
            urgency = "medium"
            plan = "推荐GLP-1辅助减重 + 生活方式干预"
        elif bmi >= 18.5:
            urgency = "low"
            plan = "BMI正常，如确有减重需求建议先尝试生活方式干预"
        else:
            return {
                "product": product["name"],
                "eligible": False,
                "reason": f"BMI {bmi} 已偏瘦，不建议药物减重",
                "recommendation": "如有身体形象困扰，建议心理咨询",
            }

        # 估算方案
        months = max(3, min(12, round(need / 3)))  # 每月约减3kg
        est_cost = product["first_price"] + product["renew_price"] * (months - 1)

        return {
            "product": product["name"],
            "eligible": True,
            "bmi": bmi,
            "weight_to_lose": need,
            "urgency": urgency,
            "plan": plan,
            "estimated_months": months,
            "estimated_total_cost": est_cost,
            "first_month_price": product["first_price"],
            "includes": product["includes"],
            "next_step": "order",
        }

    @staticmethod
    def _analyze_hair(product, answers, questions):
        """防脱生发评估：脱发程度分级与用药方案推荐。"""
        severity_map = {
            "不到半年": "early",
            "半年~2年": "moderate",
            "2年以上": "advanced",
        }
        severity = severity_map.get(answers.get("2", ""), "unknown")

        family_history = answers.get("3", "无") != "无"
        prior_treatment = answers.get("4") not in ["未使用", None]
        has_liver = answers.get("6") == "是"

        if has_liver:
            return {
                "product": product["name"],
                "eligible": False,
                "reason": "肝脏疾病患者不建议使用口服非那雄胺",
                "recommendation": "可考虑外用米诺地尔（无需口服）",
            }

        if severity == "early":
            plan = "外用米诺地尔 + 口服非那雄胺（6个月疗程）"
            months = 6
        elif severity == "moderate":
            plan = "外用米诺地尔 + 口服非那雄胺 + 微针辅助（12个月疗程）"
            months = 12
        else:
            plan = "综合治疗方案（含口服+外用+辅助），12个月起"
            months = 12

        return {
            "product": product["name"],
            "eligible": True,
            "severity": severity,
            "family_history": family_history,
            "prior_treatment": prior_treatment,
            "plan": plan,
            "estimated_months": months,
            "estimated_total_cost": product["first_price"] + product["renew_price"] * (months - 1),
            "first_month_price": product["first_price"],
            "includes": product["includes"],
            "next_step": "order",
        }

    @staticmethod
    def _analyze_generic(product, product_id, answers, questions):
        """通用评估：根据症状应答分数生成治疗方案推荐。"""
        # 显式正向关键词 + 非空选项均视为症状信号
        positive_kw = {"是", "严重", "经常", "偏高", "偏低"}
        positive = 0
        for v in answers.values():
            if v in positive_kw:
                positive += 1
            elif isinstance(v, str) and v.strip() and v not in {"否", "无", "未使用", "未检测", "正常", "不适用", "不确定"}:
                positive += 0.5  # 非默认选项也计入半分
        total = len(questions)
        score = round(min(positive / max(total, 1), 1.0) * 100, 1)

        if score >= 60:
            urgency, plan = "high", f"建议立即开始{product.get('name', '治疗')}方案"
            months = 6
        elif score >= 30:
            urgency, plan = "medium", f"推荐{product.get('name', '调理')}方案"
            months = 3
        else:
            urgency, plan = "low", "症状较轻，可先尝试生活方式调整"
            months = 1

        return {
            "product": product.get("name", ""),
            "eligible": True,
            "urgency": urgency,
            "score": score,
            "plan": plan,
            "estimated_months": months,
            "estimated_total_cost": product.get("first_price", 0) + product.get("renew_price", 0) * (months - 1),
            "first_month_price": product.get("first_price", 0),
            "includes": product.get("includes", []),
            "next_step": "order",
        }

# ========== 订单管理 ==========
class OrderManager:
    @staticmethod
    def create_order(user_id, product_id, assessment_result, name, phone, address):
        """创建订单 — 带完整决策检查点流程：预览→校验→确认→执行"""

        # ====== 第一步：预览 ======
        preview_data = {
            "product_id": product_id,
            "product_name": Config.PRODUCTS.get(product_id, {}).get("name", ""),
            "price": Config.PRODUCTS.get(product_id, {}).get("first_price", 0),
            "name": name,
            "phone": phone,
            "address": address,
        }
        preview_result = validate_order_preview(preview_data)
        if not preview_result.passed:
            logger.warning(f"订单创建拦截(预览): {preview_result.message}")
            raise ValueError(preview_result.message)

        # ====== 第二步：校验 ======
        # 2a. 产品校验
        prod_check = validate_product_exists(product_id, Config.PRODUCTS)
        if not prod_check.passed:
            raise ValueError(prod_check.message)

        # 2b. 手机号校验
        phone_check = validate_phone(phone)
        if not phone_check.passed:
            raise ValueError(phone_check.message)

        product = Config.PRODUCTS.get(product_id, {})

        # 2c. 地址校验（处方药品必须有地址）
        addr_check = validate_address(address, product.get("requires_prescription", False))
        if not addr_check.passed:
            raise ValueError(addr_check.message)

        # 2d. 处方药品评估结果校验
        rx_check = validate_prescription_check(product, assessment_result)
        if not rx_check.passed:
            raise ValueError(rx_check.message)

        # ====== 第三步：确认（自动通过，生产环境应由用户前端确认） ======
        logger.info(f"订单创建确认通过：{product.get('name', product_id)} | {phone[:3]}****{phone[-4:]}")

        # ====== 第四步：执行 ======
        products_db = load_data("products")

        order = {
            "id": str(uuid.uuid4())[:12],
            "user_id": user_id,
            "product_id": product_id,
            "product_name": product.get("name", ""),
            "status": "pending_payment",
            "price": product.get("first_price", 0),
            "name": name,
            "phone": phone,
            "address": address,
            "assessment": assessment_result,
            "created_at": datetime.now().isoformat(),
            "timeline": [
                {"time": datetime.now().isoformat(), "status": "created", "desc": "订单创建（检查点全部通过）"},
            ],
            "checkpoints_passed": [
                "order_validate_phone",
                "order_validate_address",
                "order_create_confirm",
                "prescription_required",
            ],
        }

        products_db[order["id"]] = order
        # 模拟自动支付成功→进入医师审核
        order["status"] = "paid"
        order["timeline"].append({"time": datetime.now().isoformat(), "status": "paid", "desc": "支付成功"})
        order["status"] = "doctor_review"
        order["timeline"].append({"time": datetime.now().isoformat(), "status": "doctor_review", "desc": "已提交医师审核"})
        save_data("products", products_db)
        return order

# ========== HTTP处理器 ==========
class MediSlimHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        """处理GET请求：静态页面、API查询、审计日志。"""
        path = self.path.split("?")[0]

        if path in ("/", "/index.html"):
            self._serve("templates/index.html", "text/html; charset=utf-8")
        elif path == "/assess":
            self._serve("templates/assess.html", "text/html; charset=utf-8")
        elif path == "/flow":
            self._serve("templates/flow.html", "text/html; charset=utf-8")
        elif path == "/admin":
            self._serve("templates/admin2.html", "text/html; charset=utf-8")
        elif path.startswith("/static/"):
            ct = "text/css" if path.endswith(".css") else "application/javascript"
            self._serve(path[1:], ct)
        elif path == "/api/products":
            self._json(Config.PRODUCTS)
        elif path == "/api/hospitals":
            self._json(Config.PARTNER_HOSPITALS)
        elif path == "/api/stats":
            users = load_data("users")
            orders = load_data("products")
            self._json({
                "total_users": len(users),
                "total_orders": len(orders),
                "products": len(Config.PRODUCTS),
                "hospitals": len(Config.PARTNER_HOSPITALS),
            })
        elif path == "/api/checkpoints":
            self._json(get_checkpoint_registry())
        elif path == "/api/checkpoints/audit":
            limit = int(urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("limit", ["50"])[0])
            self._json(get_audit_log(limit))
        else:
            self._json({"error": "Not found"}, 404)

    def do_POST(self):
        """处理POST请求：评估分析、订单创建、数据更新。"""
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length > 1_000_000:  # 1MB限制
                logger.warning(f"请求体过大: {length} bytes")
                self._json({"error": "请求体过大"}, 413)
                return
            body = self.rfile.read(length).decode("utf-8") if length else "{}"
        except (ValueError, OSError) as e:
            logger.error(f"读取请求体失败: {e}")
            self._json({"error": "请求格式错误"}, 400)
            return

        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败: {e}")
            self._json({"error": "JSON格式错误"}, 400)
            return

        path = self.path

        if path == "/api/user/register":
            phone = data.get("phone", "")
            if not phone or not isinstance(phone, str) or len(phone) < 11:
                self._json({"error": "手机号格式不正确"}, 400)
                return
            users = load_data("users")
            uid = str(uuid.uuid4())[:12]
            users[uid] = {
                "id": uid,
                "phone": phone,
                "name": data.get("name", "用户"),
                "created_at": datetime.now().isoformat(),
                "orders": [],
            }
            save_data("users", users)
            logger.info(f"新用户注册: {uid} ({data.get('name', '')})")
            self._json(users[uid])

        elif path == "/api/assessment/start":
            pid = data.get("product_id", "")
            if not pid:
                self._json({"error": "缺少product_id参数"}, 400)
                return
            questions = Config.ASSESSMENT_QUESTIONS.get(pid, [])
            product = Config.PRODUCTS.get(pid, {})
            if not questions or not product:
                self._json({"error": f"产品不存在: {pid}"}, 400)
                return
            self._json({
                "product_id": pid,
                "product_name": product.get("name", ""),
                "questions": questions,
                "total": len(questions),
            })

        elif path == "/api/assessment/analyze":
            pid = data.get("product_id", "")
            answers = data.get("answers", {})
            result = SlimAIEngine.analyze(pid, answers)
            self._json(result)

        elif path == "/api/order/create":
            uid = data.get("user_id", "")
            pid = data.get("product_id", "")
            if not uid:
                self._json({"error": "缺少user_id参数"}, 400)
                return
            if not pid or pid not in Config.PRODUCTS:
                self._json({"error": f"无效的product_id: {pid}"}, 400)
                return
            name = data.get("name", "")
            phone = data.get("phone", "")
            if not phone:
                self._json({"error": "缺少手机号"}, 400)
                return
            result = data.get("assessment", {})
            try:
                order = OrderManager.create_order(
                    uid, pid, result, name, phone,
                    data.get("address", ""),
                )
                logger.info(f"订单创建: {order['id']} 用户:{uid} 产品:{pid}")
                self._json(order)
            except Exception as e:
                logger.error(f"订单创建失败: {e}\n{traceback.format_exc()}")
                self._json({"error": "订单创建失败，请稍后重试"}, 500)

        elif path == "/api/order/status":
            oid = data.get("order_id", "")
            orders = load_data("products")
            order = orders.get(oid)
            if not order:
                self._json({"error": "订单不存在"}, 404)
                return
            self._json(order)

        else:
            self._json({"error": "Not found"}, 404)

    def _json(self, data, status=200):
        """发送JSON响应，支持CORS跨域。"""
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))

    def _serve(self, filepath, content_type):
        """提供静态文件服务，文件不存在时返回404。"""
        full = Path(__file__).parent / filepath
        if full.exists():
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.end_headers()
            self.wfile.write(full.read_bytes())
        else:
            self._json({"error": "Not found"}, 404)

    def log_message(self, format, *args):
        """覆盖默认日志格式，统一使用项目logger。"""
        logger.info(f"{self.client_address[0]} - {format % args}")

# ========== 启动 ==========
def main():
    """启动MediSlim HTTP服务器，默认监听8090端口。"""
    port = int(os.environ.get("PORT", 8090))
    server = HTTPServer(("0.0.0.0", port), MediSlimHandler)
    print(f"💰 MediSlim 轻健康平台启动成功")
    print(f"📱 访问: http://localhost:{port}")
    print(f"📊 统计: http://localhost:{port}/api/stats")
    server.serve_forever()

if __name__ == "__main__":
    main()
