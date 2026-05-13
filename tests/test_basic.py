"""
基础测试 — 验证项目结构和导入
"""
import os
import json
import pytest


def test_project_structure():
    """测试项目基本结构"""
    assert os.path.exists("README.md"), "README.md 不存在"
    assert os.path.exists("requirements.txt"), "requirements.txt 不存在"


def test_data_files():
    """测试数据文件有效性"""
    data_dir = "data"
    if os.path.exists(data_dir):
        for filename in os.listdir(data_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(data_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    json.load(f)  # 验证 JSON 有效


def test_ai_assistant_local_fallback(monkeypatch):
    """AI助手在未配置外部API时也要有本地兜底。"""
    monkeypatch.setenv("AI_ENABLED", "0")
    from ai_assistant import smart_chat

    result = smart_chat("我想了解减重")
    assert result["reply"]
    assert result["source"] in {"local", "deepseek"}


def test_nutrition_seed_data():
    """营养数据作为可复用种子数据纳入归档。"""
    with open("data/nutrition-data.json", "r", encoding="utf-8") as f:
        payload = json.load(f)
    assert len(payload.get("foods", [])) >= 40


def test_product_catalog_dashboards():
    """三圈产品目录和收入看板应能在无数据时稳定返回。"""
    from product_catalog import product_catalog_summary, product_performance_dashboard, revenue_dashboard

    catalog = product_catalog_summary()
    assert catalog["total"] >= 15
    assert "处方药" in catalog["by_circle"]

    performance = product_performance_dashboard({})
    assert len(performance) == catalog["total"]
    assert all("gross_margin" in row for row in performance)

    revenue = revenue_dashboard({}, {})
    assert revenue["total_revenue"] == 0
    assert revenue["total_orders"] == 0


def test_python_syntax():
    """测试 Python 文件语法"""
    src_dir = "src"
    if os.path.exists(src_dir):
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                if file.endswith(".py"):
                    filepath = os.path.join(root, file)
                    with open(filepath, "r", encoding="utf-8") as f:
                        compile(f.read(), filepath, "exec")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
