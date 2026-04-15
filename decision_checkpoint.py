"""
MediSlim 决策检查点机制
=============================
核心设计原则：
1. 任何关键操作必须经过「预览→校验→确认→执行」四步流程
2. 检查点提供统一的决策记录和审计追踪
3. 数据保存前自动校验完整性
4. 批量操作必须二次确认

检查点类型：
- ORDER_CONFIRM: 下单前确认
- DATA_VALIDATE: 数据保存前校验
- STATE_TRANSITION: 状态流转确认
- BATCH_CONFIRM: 批量操作确认
- CONTENT_APPROVE: 内容发布审批
- OPERATION_AUDIT: 操作审计记录
"""

import json
import uuid
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple

logger = logging.getLogger("DecisionCheckpoint")

DATA_DIR = Path("./data")
DATA_DIR.mkdir(exist_ok=True)

# ========== 检查点注册表 ==========

CHECKPOINT_REGISTRY: Dict[str, Dict] = {}


def register_checkpoint(checkpoint_id: str, name: str, description: str, 
                        severity: str = "normal"):
    """注册一个检查点"""
    CHECKPOINT_REGISTRY[checkpoint_id] = {
        "id": checkpoint_id,
        "name": name,
        "description": description,
        "severity": severity,  # normal / high / critical
        "registered_at": datetime.now().isoformat(),
    }


# ========== 预注册关键检查点 ==========

register_checkpoint(
    "order_create_confirm", "下单确认", 
    "用户提交订单前，确认产品、价格、个人信息无误", "critical"
)
register_checkpoint(
    "order_validate_phone", "手机号校验",
    "订单创建前校验手机号格式", "high"
)
register_checkpoint(
    "order_validate_address", "地址校验",
    "处方类药品订单必须提供收货地址", "high"
)
register_checkpoint(
    "state_advance_confirm", "状态流转确认",
    "订单关键状态流转前需确认当前状态有效且满足流转条件", "critical"
)
register_checkpoint(
    "prescription_required", "处方药品检查",
    "处方类药品下单前检查评估结果是否包含禁忌症筛查", "critical"
)
register_checkpoint(
    "data_save_validate", "数据保存校验",
    "关键数据保存前校验完整性和格式", "high"
)
register_checkpoint(
    "batch_operation_confirm", "批量操作确认",
    "批量处理订单前需二次确认", "normal"
)
register_checkpoint(
    "content_publish_approve", "内容发布审批",
    "内容对外发布前需审批确认", "normal"
)
register_checkpoint(
    "crm_operation_audit", "CRM操作审计",
    "CRM关键操作记录审计日志", "normal"
)


# ========== 检查点执行引擎 ==========

class CheckpointResult:
    """检查点执行结果"""
    def __init__(self, checkpoint_id: str, passed: bool, message: str, 
                 details: Optional[Dict] = None):
        self.checkpoint_id = checkpoint_id
        self.passed = passed
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return {
            "checkpoint_id": self.checkpoint_id,
            "passed": self.passed,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
        }
    
    def __bool__(self):
        return self.passed


def _load_audit_log() -> List[Dict]:
    f = DATA_DIR / "checkpoint_audit.json"
    if f.exists():
        try:
            return json.loads(f.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            return []
    return []


def _save_audit_log(log: List[Dict]):
    (DATA_DIR / "checkpoint_audit.json").write_text(
        json.dumps(log[-1000:], ensure_ascii=False, indent=2)  # 保留最近1000条
    )


def log_checkpoint(result: CheckpointResult, context: Optional[Dict] = None):
    """记录检查点审计日志"""
    try:
        log = _load_audit_log()
        log.append({
            "checkpoint": result.checkpoint_id,
            "passed": result.passed,
            "message": result.message,
            "details": result.details,
            "context": context or {},
            "timestamp": result.timestamp,
        })
        _save_audit_log(log)
    except Exception as e:
        logger.error(f"审计日志写入失败: {e}")


# ========== 具体检查点实现 ==========

def validate_phone(phone: str) -> CheckpointResult:
    """校验手机号格式"""
    cp_id = "order_validate_phone"
    if not phone or not isinstance(phone, str):
        result = CheckpointResult(cp_id, False, "手机号为空")
        log_checkpoint(result)
        return result
    if len(phone) < 11 or not phone.isdigit():
        result = CheckpointResult(cp_id, False, f"手机号格式不正确: {phone}")
        log_checkpoint(result)
        return result
    result = CheckpointResult(cp_id, True, f"手机号校验通过: {phone[:3]}****{phone[-4:]}")
    log_checkpoint(result)
    return result


def validate_address(address: str, is_prescription: bool) -> CheckpointResult:
    """校验收货地址"""
    cp_id = "order_validate_address"
    if is_prescription and (not address or not address.strip()):
        result = CheckpointResult(cp_id, False, "处方类药品必须提供收货地址")
        log_checkpoint(result)
        return result
    if address and len(address.strip()) < 5:
        result = CheckpointResult(cp_id, False, "地址信息不完整（至少5个字符）")
        log_checkpoint(result)
        return result
    result = CheckpointResult(cp_id, True, "地址校验通过")
    log_checkpoint(result)
    return result


def validate_product_exists(product_id: str, products: Dict) -> CheckpointResult:
    """校验产品是否存在"""
    cp_id = "order_create_confirm"
    if not product_id:
        result = CheckpointResult(cp_id, False, "产品ID为空")
        log_checkpoint(result)
        return result
    if product_id not in products:
        result = CheckpointResult(cp_id, False, f"产品不存在: {product_id}")
        log_checkpoint(result)
        return result
    result = CheckpointResult(cp_id, True, f"产品确认: {products[product_id].get('name', product_id)}")
    log_checkpoint(result)
    return result


def validate_order_preview(order_data: Dict) -> CheckpointResult:
    """下单预览：汇总确认信息"""
    cp_id = "order_create_confirm"
    
    # 生成订单预览摘要
    preview = {
        "产品": order_data.get("product_name", "未知"),
        "首月价格": f"¥{order_data.get('price', 0)}",
        "用户姓名": order_data.get("name", "未填写"),
        "手机号": (order_data.get("phone", "")[:3] + "****" + order_data.get("phone", "")[-4:]) if order_data.get("phone") else "未填写",
        "收货地址": order_data.get("address", "未填写")[:20] + "..." if len(order_data.get("address", "")) > 20 else order_data.get("address", "未填写"),
    }
    
    # 检查必填字段
    missing = []
    if not order_data.get("phone"):
        missing.append("手机号")
    if not order_data.get("name"):
        missing.append("姓名")
    
    if missing:
        result = CheckpointResult(
            cp_id, False, 
            f"订单预览：以下必填字段缺失 → {', '.join(missing)}",
            {"preview": preview, "missing_fields": missing}
        )
        log_checkpoint(result, {"action": "order_preview", "result": "rejected"})
        return result
    
    result = CheckpointResult(
        cp_id, True,
        f"订单预览确认：{preview['产品']} | {preview['首月价格']} | {preview['手机号']}",
        {"preview": preview}
    )
    log_checkpoint(result, {"action": "order_preview", "result": "approved"})
    return result


def validate_prescription_check(product: Dict, assessment: Dict) -> CheckpointResult:
    """处方药品前置检查"""
    cp_id = "prescription_required"
    requires_rx = product.get("requires_prescription", False)
    
    if requires_rx and (not assessment or not isinstance(assessment, dict)):
        result = CheckpointResult(
            cp_id, False,
            f"处方药品 [{product.get('name', '')}] 必须先完成健康评估"
        )
        log_checkpoint(result)
        return result
    
    if requires_rx and assessment:
        # 检查是否有禁忌症标记
        if assessment.get("eligible") is False:
            result = CheckpointResult(
                cp_id, False,
                f"处方药品 [{product.get('name', '')}] 评估结果不合格：{assessment.get('reason', '存在禁忌症')}",
                {"contraindications": assessment.get("contraindications", [])}
            )
            log_checkpoint(result)
            return result
    
    result = CheckpointResult(cp_id, True, "处方药品检查通过")
    log_checkpoint(result)
    return result


def validate_state_transition(order: Dict, from_state: str, to_state: str,
                               valid_states: Dict) -> CheckpointResult:
    """状态流转校验"""
    cp_id = "state_advance_confirm"
    
    if not order:
        result = CheckpointResult(cp_id, False, "订单不存在")
        log_checkpoint(result)
        return result
    
    current = order.get("state")
    if current != from_state:
        result = CheckpointResult(
            cp_id, False,
            f"状态不一致：期望 [{from_state}]，实际 [{current}]"
        )
        log_checkpoint(result)
        return result
    
    expected_next = valid_states.get(from_state, {}).get("next")
    if expected_next != to_state:
        result = CheckpointResult(
            cp_id, False,
            f"非法状态流转：{from_state} → {to_state}（应为 {from_state} → {expected_next}）"
        )
        log_checkpoint(result)
        return result
    
    # 检查终态保护
    if from_state == "cancelled":
        result = CheckpointResult(cp_id, False, "已取消的订单不可流转")
        log_checkpoint(result)
        return result
    
    result = CheckpointResult(
        cp_id, True,
        f"状态流转确认：{from_state} → {to_state}"
    )
    log_checkpoint(result, {"action": "state_transition", "from": from_state, "to": to_state})
    return result


def validate_data_save(name: str, data: Any) -> CheckpointResult:
    """数据保存前校验"""
    cp_id = "data_save_validate"
    
    if data is None:
        result = CheckpointResult(cp_id, False, f"数据集 [{name}] 内容为空")
        log_checkpoint(result)
        return result
    
    if isinstance(data, dict) and len(data) == 0:
        # 空字典允许（清空操作）
        pass
    elif isinstance(data, str) and len(data.strip()) == 0:
        result = CheckpointResult(cp_id, False, f"数据集 [{name}] 内容为空字符串")
        log_checkpoint(result)
        return result
    
    # 尝试序列化验证
    try:
        json.dumps(data, ensure_ascii=False, default=str)
    except (TypeError, ValueError) as e:
        result = CheckpointResult(
            cp_id, False,
            f"数据集 [{name}] 序列化失败：{str(e)}"
        )
        log_checkpoint(result)
        return result
    
    # 数据指纹（用于变更追踪）
    data_hash = hashlib.md5(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()[:8]
    
    result = CheckpointResult(
        cp_id, True,
        f"数据校验通过：{name} (hash:{data_hash})",
        {"data_name": name, "data_hash": data_hash}
    )
    log_checkpoint(result)
    return result


def validate_batch_operation(operation: str, count: int, 
                              confirm_token: Optional[str] = None) -> CheckpointResult:
    """批量操作确认"""
    cp_id = "batch_operation_confirm"
    
    if count <= 0:
        result = CheckpointResult(cp_id, False, f"批量操作 [{operation}] 无待处理项目")
        log_checkpoint(result)
        return result
    
    if count > 50:
        result = CheckpointResult(
            cp_id, False,
            f"批量操作 [{operation}] 数量过大({count})，请分批处理（上限50）"
        )
        log_checkpoint(result)
        return result
    
    expected_token = hashlib.md5(f"{operation}:{count}".encode()).hexdigest()[:8]
    if confirm_token != expected_token:
        result = CheckpointResult(
            cp_id, False,
            f"批量操作 [{operation}] 需确认（影响 {count} 条记录），确认码: {expected_token}",
            {"count": count, "confirm_token": expected_token, "needs_confirm": True}
        )
        log_checkpoint(result)
        return result
    
    result = CheckpointResult(
        cp_id, True,
        f"批量操作确认：{operation} ({count}条)"
    )
    log_checkpoint(result, {"action": "batch_confirm", "operation": operation, "count": count})
    return result


def validate_content_publish(content: Dict) -> CheckpointResult:
    """内容发布审批"""
    cp_id = "content_publish_approve"
    
    if not content:
        result = CheckpointResult(cp_id, False, "内容为空")
        log_checkpoint(result)
        return result
    
    # 检查必要字段
    required = ["title", "platform"]
    missing = [f for f in required if not content.get(f)]
    if missing:
        result = CheckpointResult(
            cp_id, False,
            f"内容发布：缺少必填字段 → {', '.join(missing)}"
        )
        log_checkpoint(result)
        return result
    
    # 医疗内容合规检查
    sensitive_words = ["根治", "包治", "100%有效", "无副作用", "祖传秘方"]
    title = content.get("title", "")
    body = content.get("body", content.get("content", ""))
    full_text = f"{title} {body}"
    
    found_sensitive = [w for w in sensitive_words if w in full_text]
    if found_sensitive:
        result = CheckpointResult(
            cp_id, False,
            f"内容合规检查失败：包含敏感词 [{', '.join(found_sensitive)}]",
            {"sensitive_words": found_sensitive}
        )
        log_checkpoint(result)
        return result
    
    result = CheckpointResult(
        cp_id, True,
        f"内容发布审批通过：{title[:30]}"
    )
    log_checkpoint(result, {"action": "content_approve", "title": title})
    return result


# ========== 统一检查点执行器 ==========

def run_checkpoint(checkpoint_id: str, **kwargs) -> CheckpointResult:
    """统一执行检查点入口"""
    cp = CHECKPOINT_REGISTRY.get(checkpoint_id)
    if not cp:
        return CheckpointResult(checkpoint_id, False, f"未注册的检查点: {checkpoint_id}")
    
    dispatch = {
        "order_validate_phone": lambda: validate_phone(kwargs.get("phone", "")),
        "order_validate_address": lambda: validate_address(
            kwargs.get("address", ""), kwargs.get("is_prescription", False)
        ),
        "order_create_confirm": lambda: validate_order_preview(kwargs.get("order_data", {})),
        "prescription_required": lambda: validate_prescription_check(
            kwargs.get("product", {}), kwargs.get("assessment", {})
        ),
        "state_advance_confirm": lambda: validate_state_transition(
            kwargs.get("order"), kwargs.get("from_state", ""),
            kwargs.get("to_state", ""), kwargs.get("valid_states", {})
        ),
        "data_save_validate": lambda: validate_data_save(
            kwargs.get("name", ""), kwargs.get("data")
        ),
        "batch_operation_confirm": lambda: validate_batch_operation(
            kwargs.get("operation", ""), kwargs.get("count", 0),
            kwargs.get("confirm_token")
        ),
        "content_publish_approve": lambda: validate_content_publish(
            kwargs.get("content", {})
        ),
    }
    
    handler = dispatch.get(checkpoint_id)
    if handler:
        return handler()
    
    return CheckpointResult(checkpoint_id, True, f"检查点 {checkpoint_id} 无实现，放行")


def get_audit_log(limit: int = 50) -> List[Dict]:
    """获取审计日志"""
    log = _load_audit_log()
    return log[-limit:]


def get_checkpoint_registry() -> Dict:
    """获取所有已注册的检查点"""
    return CHECKPOINT_REGISTRY
