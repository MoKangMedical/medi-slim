"""
MediSlim Streamlit 原型
AI驱动的医美推荐平台 Demo
"""

import streamlit as st
import json
import os
import sys

# 添加父目录到 path
sys.path.insert(0, os.path.dirname(__file__))
from recommendation import RecommendationEngine, UserProfile


# 页面配置
st.set_page_config(
    page_title="MediSlim — AI医美推荐",
    page_icon="💊",
    layout="wide",
)

# 初始化推荐引擎
@st.cache_resource
def load_engine():
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    return RecommendationEngine(data_dir=data_dir)

engine = load_engine()


# ==================== 侧边栏 ====================
with st.sidebar:
    st.image("https://img.shields.io/badge/MediSlim-v5.0-brightgreen", width=200)
    st.title("💊 MediSlim")
    st.caption("AI驱动的消费医疗平台")
    st.divider()

    page = st.radio(
        "导航",
        ["🏠 首页", "🤖 AI推荐", "🏥 机构查询", "📊 项目对比"],
        index=0,
    )


# ==================== 首页 ====================
def page_home():
    st.title("💊 MediSlim — AI医美推荐平台")
    st.markdown("> 连接医美机构和消费者的智能平台")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("收录项目", "10+")
    col2.metric("合作机构", "6+")
    col3.metric("覆盖城市", "5+")
    col4.metric("用户满意度", "85%")

    st.divider()
    st.markdown("### 🚀 核心功能")

    cols = st.columns(4)
    features = [
        ("🤖 智能推荐", "基于AI的个性化推荐"),
        ("🏥 机构认证", "资质审核保障安全"),
        ("💰 价格透明", "横向对比消除信息差"),
        ("⭐ 用户评价", "真实反馈辅助决策"),
    ]
    for col, (title, desc) in zip(cols, features):
        with col:
            st.info(f"**{title}**\n\n{desc}")

    st.divider()
    st.markdown("### 📊 热门项目")

    products = engine.products
    for p in sorted(products, key=lambda x: x["popularity_score"], reverse=True)[:6]:
        with st.expander(f"{p['name']} — ¥{p['price_range']['min']:,}起"):
            st.write(p["description"])
            st.write(f"**适合**: {', '.join(p['suitable_for'])}")
            st.write(f"**恢复期**: {p['recovery_days']}天 | **满意度**: {p['satisfaction_rate']*100:.0f}%")


# ==================== AI 推荐 ====================
def page_recommend():
    st.title("🤖 AI 智能推荐")
    st.markdown("告诉我们你的需求，AI 为你匹配最合适的医美项目")

    with st.form("profile_form"):
        col1, col2 = st.columns(2)

        with col1:
            age = st.slider("年龄", 18, 65, 30)
            gender = st.selectbox("性别", ["female", "male"], format_func=lambda x: "女" if x == "female" else "男")
            budget_min, budget_max = st.slider(
                "预算范围 (¥)",
                min_value=0, max_value=100000,
                value=(2000, 20000),
                step=1000,
            )

        with col2:
            concerns = st.multiselect(
                "关注问题",
                ["抗衰", "祛斑", "瘦脸", "除皱", "紧致", "补水", "美白", "丰唇", "双眼皮", "隆鼻"],
                default=["抗衰"],
            )
            pain_tolerance = st.select_slider(
                "疼痛耐受度",
                options=["low", "medium", "high"],
                value="medium",
                format_func=lambda x: {"low": "低（怕疼）", "medium": "中等", "high": "高（不怕）"}[x],
            )
            recovery_days = st.slider("可接受恢复天数", 0, 30, 5)
            city = st.selectbox("所在城市", ["不限", "上海", "北京", "深圳", "广州", "杭州", "成都"])

        submitted = st.form_submit_button("🔍 开始推荐", use_container_width=True)

    if submitted:
        profile = UserProfile(
            age=age,
            gender=gender,
            budget_min=budget_min,
            budget_max=budget_max,
            concerns=concerns,
            pain_tolerance=pain_tolerance,
            recovery_days=recovery_days,
        )

        city_filter = None if city == "不限" else city

        with st.spinner("AI 正在分析..."):
            results = engine.recommend(profile, top_k=5, city=city_filter)

        if not results:
            st.warning("未找到匹配的项目，请调整筛选条件")
            return

        st.success(f"找到 {len(results)} 个推荐项目")
        st.divider()

        for i, item in enumerate(results, 1):
            p = item["product"]
            score = item["match_score"]

            with st.container():
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.markdown(f"### {i}. {p['name']}")
                    st.write(p["description"])

                    c1, c2, c3 = st.columns(3)
                    c1.write(f"💰 **价格**: ¥{p['price_range']['min']:,} - ¥{p['price_range']['max']:,}")
                    c2.write(f"⏱️ **恢复期**: {p['recovery_days']}天")
                    c3.write(f"⭐ **满意度**: {p['satisfaction_rate']*100:.0f}%")

                    st.write(f"**适合**: {', '.join(p['suitable_for'])}")

                    if item["recommended_clinics"]:
                        st.write("**推荐机构**:")
                        for clinic in item["recommended_clinics"]:
                            st.write(f"  - 🏥 {clinic['name']} ({clinic['city']}) ⭐{clinic['rating']}")

                with col2:
                    st.metric("匹配度", f"{score}%")

                st.divider()


# ==================== 机构查询 ====================
def page_clinics():
    st.title("🏥 机构查询")
    st.markdown("查看认证医美机构信息")

    city_filter = st.selectbox("筛选城市", ["全部"] + list(set(c["city"] for c in engine.clinics)))

    clinics = engine.clinics
    if city_filter != "全部":
        clinics = [c for c in clinics if c["city"] == city_filter]

    for clinic in clinics:
        with st.expander(f"🏥 {clinic['name']} — {clinic['city']} {clinic['district']}"):
            col1, col2 = st.columns(2)

            with col1:
                st.write(f"**类型**: {clinic['type']}")
                st.write(f"**等级**: {clinic['level']}")
                st.write(f"**地址**: {clinic['address']}")
                st.write(f"**电话**: {clinic['phone']}")
                st.write(f"**营业时间**: {clinic['opening_hours']}")

            with col2:
                st.write(f"**评分**: ⭐ {clinic['rating']} ({clinic['review_count']}条评价)")
                st.write(f"**医生数**: {clinic['doctor_count']}人")
                st.write(f"**床位数**: {clinic['bed_count']}张")
                st.write(f"**价格定位**: {clinic['price_level']}")
                cert = "✅ 已认证" if clinic["certified"] else "❌ 未认证"
                st.write(f"**资质**: {cert}")

            st.write(f"**擅长**: {', '.join(clinic['specialties'])}")
            st.write(f"**简介**: {clinic['description']}")


# ==================== 项目对比 ====================
def page_compare():
    st.title("📊 项目对比")
    st.markdown("横向对比不同医美项目")

    product_names = [p["name"] for p in engine.products]
    selected = st.multiselect("选择要对比的项目", product_names, default=product_names[:3])

    if not selected:
        st.info("请至少选择一个项目")
        return

    products = [p for p in engine.products if p["name"] in selected]

    # 对比表格
    import pandas as pd

    data = []
    for p in products:
        data.append({
            "项目": p["name"],
            "类别": p["category"],
            "最低价(¥)": p["price_range"]["min"],
            "最高价(¥)": p["price_range"]["max"],
            "恢复天数": p["recovery_days"],
            "效果持续(月)": p["effect_months"] if p["effect_months"] > 0 else "永久",
            "风险等级": {"low": "低", "medium": "中", "high": "高"}.get(p["risk_level"], p["risk_level"]),
            "满意度": f"{p['satisfaction_rate']*100:.0f}%",
            "热度": p["popularity_score"],
        })

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # 价格对比图
    st.divider()
    st.subheader("💰 价格对比")
    chart_data = pd.DataFrame({
        "项目": [p["name"] for p in products],
        "最低价": [p["price_range"]["min"] for p in products],
        "最高价": [p["price_range"]["max"] for p in products],
    })
    st.bar_chart(chart_data.set_index("项目"))


# ==================== 路由 ====================
if page == "🏠 首页":
    page_home()
elif page == "🤖 AI推荐":
    page_recommend()
elif page == "🏥 机构查询":
    page_clinics()
elif page == "📊 项目对比":
    page_compare()
