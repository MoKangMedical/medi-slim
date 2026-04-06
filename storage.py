"""
Shared storage helpers for MediSlim services.
"""
from __future__ import annotations

import json
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

ORDER_FILE = DATA_DIR / "orders.json"
LEGACY_ORDER_FILE = DATA_DIR / "products.json"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def short_id() -> str:
    return uuid.uuid4().hex[:12]


def data_path(name: str) -> Path:
    return DATA_DIR / f"{name}.json"


def load_json(name: str, default: Any | None = None) -> Any:
    path = data_path(name)
    if not path.exists():
        return {} if default is None else default

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {} if default is None else default


def save_json(name: str, data: Any) -> None:
    _atomic_write_json(data_path(name), data)


def load_orders() -> dict[str, Any]:
    orders = load_json("orders", {})
    if orders:
        return orders

    legacy_orders = load_json("products", {})
    if _looks_like_order_store(legacy_orders):
        return legacy_orders

    return {}


def migrate_legacy_orders() -> None:
    if ORDER_FILE.exists():
        return

    legacy_orders = load_json("products", {})
    if _looks_like_order_store(legacy_orders):
        _atomic_write_json(ORDER_FILE, legacy_orders)


def save_orders(data: dict[str, Any]) -> None:
    _atomic_write_json(ORDER_FILE, data)


def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
        prefix=f"{path.stem}-",
        suffix=".tmp",
    ) as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.flush()
        temp_path = Path(handle.name)

    temp_path.replace(path)


def _looks_like_order_store(data: Any) -> bool:
    if not isinstance(data, dict) or not data:
        return False

    for value in data.values():
        if not isinstance(value, dict):
            return False
        if "status" not in value and "timeline" not in value and "user_id" not in value:
            return False

    return True
