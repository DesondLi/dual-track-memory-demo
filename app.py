"""
电信客服双轨记忆系统 Demo

mem0：关键特征记忆库
memU：客户档案中心
"""
import sys
import os
import re
from pathlib import Path

base_dir = Path(__file__).parent
sys.path.insert(0, str(base_dir))

import streamlit as st
import pandas as pd

from orchestrator import DualTrackOrchestrator
from agent_module import TelecomAgent


# Page config
st.set_page_config(
    page_title="电信客服双轨记忆系统",
    page_icon="📞",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    /* 记忆卡片 */
    .memory-card {
        background-color: #f8fafc !important;
        border-radius: 10px;
        padding: 16px;
        margin: 10px 0;
        border-left: 5px solid #3b82f6;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        color: #1e293b !important;
    }
    .memory-card div, .memory-card span {
        color: #1e293b !important;
    }
    .mem0-card {
        border-left-color: #10b981;
        background-color: #f0fdf4 !important;
    }
    .memu-card {
        border-left-color: #8b5cf6;
        background-color: #faf5ff !important;
    }

    /* 统计卡片 */
    .stat-box {
        background-color: #f8fafc !important;
        border-radius: 12px;
        padding: 20px 16px;
        text-align: center;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    .stat-box div {
        color: #1e293b !important;
    }

    /* 档案章节卡片 */
    .profile-section {
        background-color: #ffffff;
        border-radius: 8px;
        padding: 16px;
        margin: 8px 0;
        border: 1px solid #e2e8f0;
    }

    /* 标签样式 */
    .tag-risk {
        background-color: #fef2f2;
        color: #dc2626;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.85em;
    }
    .tag-info {
        background-color: #eff6ff;
        color: #2563eb;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.85em;
    }

    /* 代码块 */
    pre, code {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)


# -------------------
# 演示数据 - 电信客服场景
# -------------------
DEMO_CONVERSATIONS = [
    {"role": "user", "content": "你好，我是13800138000，我家宽带最近总是掉线，一天能掉个五六次"},
    {"role": "assistant", "content": "您好，非常抱歉给您带来不便！请问您是朝阳区的59元融合套餐对吗？"},
    {"role": "user", "content": "对的，就是那个套餐，主要是晚上七八点高峰期特别严重，我在家办公都受影响"},
    {"role": "assistant", "content": "理解您的困扰！我先帮您做个远程检测，另外可以安排工程师明天上门，您看下午3点方便吗？"},
    {"role": "user", "content": "上午不行，得上班，下午3点以后吧。对了，这个问题我上个月3月15号已经投诉过一次了，当时说给我优化，结果一点改善都没有"},
    {"role": "assistant", "content": "非常抱歉让您再次失望！我看到了您的投诉记录，这次我帮您升级到专家级处理，保证彻底解决。"},
    {"role": "user", "content": "希望你们说到做到。另外说一下，上个月话费又多扣了15块钱，是什么爱音乐增值业务，但我从来没开通啊！"},
    {"role": "assistant", "content": "非常抱歉！我现在就帮您取消这个业务，并且双倍返还30元话费。另外我帮您屏蔽所有增值业务的开通渠道，可以吗？"},
    {"role": "user", "content": "一定要屏蔽！这半年来已经是第三次了，上次是彩铃，上上次是手机报。再这样我真要去工信部投诉了"},
    {"role": "assistant", "content": "非常理解您的心情！我完全明白。增值业务已屏蔽，费用已安排返还。后续有任何问题您直接找我，工号8866。"},
    {"role": "user", "content": "行吧。对了，我想办个副卡给我爸妈用，他们年纪大了，就打打电话，有什么优惠吗？"},
    {"role": "assistant", "content": "有的！您的套餐可以办两张副卡，每张每月5元，前三个月免费，我现在就帮您办可以吗？"},
    {"role": "user", "content": "先办一张试试吧。还有你们那个千兆套餐怎么样？我现在200M感觉不太够用了"},
    {"role": "assistant", "content": "千兆套餐现在79元，还送腾讯视频会员年卡，老用户前两个月半价，特别划算。需要我帮您介绍一下吗？"},
    {"role": "user", "content": "听起来还行。对了，记住啊，以后有什么事给我发短信就行，别打电话，我上班不方便接。上次你们的推销电话打了好几个，烦死了"},
    {"role": "assistant", "content": "好的，我记下了！只通过短信联系您，已帮您设置营销电话屏蔽。对了，您之前提过携号转网的事，还在考虑吗？"},
    {"role": "user", "content": "暂时先不转了，主要是你们公司信号在我公司那边不太好，电梯里经常没信号，这个让我很头疼"},
    {"role": "assistant", "content": "您说的是中关村科技园西区吧？我们正在那边做5G信号优化，预计下个月就能完工，完工后电梯和地下车库信号都会有明显改善。"},
    {"role": "user", "content": "那行，我就再等等看。希望这次你们说话算数，别再让我失望了"},
]


# -------------------
# Initialize Session State
# -------------------
def init_session_state():
    if "orchestrator" not in st.session_state:
        data_path = base_dir / "data" / "output"
        st.session_state.orchestrator = DualTrackOrchestrator(
            base_dir=str(data_path),
            auto_trigger_profile=True,
            trigger_threshold=10,
            user_id="13800138000",  # 演示用户
        )

    if "agent" not in st.session_state:
        st.session_state.agent = TelecomAgent(
            orchestrator=st.session_state.orchestrator,
        )

    if "demo_loaded" not in st.session_state:
        st.session_state.demo_loaded = False


# -------------------
# Sidebar
# -------------------
def render_sidebar():
    with st.sidebar:
        st.title("🎛️ 控制面板")

        st.divider()

        # 演示数据加载
        st.subheader("📚 演示数据")
        if st.button("🚀 加载电信客服演示对话", type="primary", use_container_width=True):
            with st.spinner("正在加载演示对话并提取特征..."):
                # 清空现有数据
                st.session_state.orchestrator.clear_all()

                # 逐句加载，提取特征
                for conv in DEMO_CONVERSATIONS:
                    st.session_state.orchestrator.add_message(
                        role=conv["role"],
                        content=conv["content"],
                    )

                # 强制构建档案
                st.session_state.orchestrator.force_build_profile()
                st.session_state.demo_loaded = True

            st.success("✅ 演示数据加载完成！")

        if st.session_state.demo_loaded:
            st.success(f"已加载 {len(DEMO_CONVERSATIONS)} 轮对话")

        st.divider()

        # 手动建档
        if st.button("📋 立即构建客户档案", use_container_width=True):
            with st.spinner("正在构建客户档案..."):
                result = st.session_state.orchestrator.force_build_profile()
            st.success(f"✅ 档案构建完成！使用了 {result['features_used']} 个特征")

        st.divider()

        # 清空数据
        if st.button("🗑️ 清空所有记忆", use_container_width=True):
            counts = st.session_state.orchestrator.clear_all()
            st.success(f"已清空：mem0 {counts['mem0_cleared']} 个特征，memU {counts['memu_cleared']} 份档案")

        st.divider()

        # 系统状态
        stats = st.session_state.orchestrator.get_stats()

        st.metric("🔍 mem0 特征数量", stats["mem0"]["total_features"])
        st.metric("📋 memU 档案数量", stats["memu"]["total_profiles"])

        # 建档进度条
        progress = stats["buffer"]["pending_conversations"] / stats["buffer"]["trigger_threshold"]
        st.progress(min(progress, 1.0),
                   text=f"建档触发进度：{stats['buffer']['trigger_progress']}")

        if progress >= 1:
            st.info("✅ 阈值已达到，下条消息将触发自动建档")


# -------------------
# Tab 1: 系统总览
# -------------------
def render_overview_tab():
    st.header("🎯 双轨记忆系统 - 电信客服场景")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="memory-card mem0-card">
            <h3>🔍 mem0 - 关键特征记忆库</h3>
            <p><b>定位</b>：实时提取对话中的结构化特征点</p>
            <p><b>存储形式</b>：键值对（Key-Value）</p>
            <p><b>特点</b>：快速写入、向量搜索、置信度管理</p>
            <hr>
            <p><b>五大分类</b>：</p>
            <ul>
                <li>📋 基本信息 - 手机号、套餐、地址等</li>
                <li>⚠️ 投诉记录 - 投诉类型、次数、历史</li>
                <li>💼 业务意向 - 办理/升级/拆机意向</li>
                <li>❤️ 用户偏好 - 联系偏好、敏感点</li>
                <li>🚨 风险标签 - 流失风险、投诉风险</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="memory-card memu-card">
            <h3>📋 memU - 客户档案中心</h3>
            <p><b>定位</b>：360° 完整客户画像</p>
            <p><b>存储形式</b>：结构化 Markdown 档案</p>
            <p><b>特点</b>：深度分析、业务洞察、跟进建议</p>
            <hr>
            <p><b>五大档案章节</b>：</p>
            <ul>
                <li>📋 基本信息 - 客户基础资料</li>
                <li>⚠️ 投诉记录 - 历史处理全记录</li>
                <li>💼 业务意向 - 业务机会挖掘</li>
                <li>❤️ 用户偏好 - 服务方式指引</li>
                <li>🚨 风险标签 - 预警和提示</li>
            </ul>
            <p><b>+ 💡 业务洞察 + 📌 跟进建议</b></p>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # 系统流程图
    st.subheader("🔄 工作流程")
    mermaid_code = """
graph LR
    A[📞 客户对话] --> B[🧠 特征提取]
    B --> C[<b>mem0</b><br/>向量记忆库]
    C -->|累计N轮| D[📋 档案构建]
    D --> E[<b>memU</b><br/>客户档案中心]
    E --> F[💡 业务洞察与建议]

    G[🔍 查询请求] --> H[双轨融合搜索]
    C -->|向量相似度| H
    E -->|关键词匹配| H
    H --> I[📊 融合结果]

    style A fill:#dbeafe,stroke:#3b82f6,color:#1e293b
    style C fill:#d1fae5,stroke:#10b981,color:#1e293b
    style E fill:#ede9fe,stroke:#8b5cf6,color:#1e293b
    style F fill:#fef3c7,stroke:#f59e0b,color:#1e293b
    style H fill:#fce7f3,stroke:#ec4899,color:#1e293b
    style I fill:#e0f2fe,stroke:#0ea5e9,color:#1e293b
"""
    st.components.v1.html(
        f"""<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
        <div class="mermaid">{mermaid_code}</div>
        <script>mermaid.initialize({{startOnLoad:true,theme:'default'}});</script>""",
        height=320,
    )

    # 系统统计
    st.divider()
    st.subheader("📊 系统状态")

    stats = st.session_state.orchestrator.get_stats()

    col_a, col_b, col_c, col_d = st.columns(4)

    with col_a:
        st.markdown(f"""
        <div class="stat-box">
            <div style="font-size: 2em; font-weight: bold; color: #10b981;">
                {stats['mem0']['total_features']}
            </div>
            <div>mem0 特征数</div>
        </div>
        """, unsafe_allow_html=True)

    with col_b:
        st.markdown(f"""
        <div class="stat-box">
            <div style="font-size: 2em; font-weight: bold; color: #8b5cf6;">
                {stats['memu']['total_profiles']}
            </div>
            <div>memU 档案数</div>
        </div>
        """, unsafe_allow_html=True)

    with col_c:
        st.markdown(f"""
        <div class="stat-box">
            <div style="font-size: 2em; font-weight: bold; color: #f59e0b;">
                {stats['buffer']['pending_conversations']}
            </div>
            <div>待建档对话数</div>
        </div>
        """, unsafe_allow_html=True)

    with col_d:
        build_time = stats['memu']['last_build_time'] or "未建档"
        if build_time != "未建档":
            build_time = build_time[:19]
        st.markdown(f"""
        <div class="stat-box">
            <div style="font-size: 1.5em; font-weight: bold; color: #3b82f6;">
                {build_time}
            </div>
            <div>最后建档时间</div>
        </div>
        """, unsafe_allow_html=True)


# -------------------
# Tab 2: mem0 特征记忆
# -------------------
def render_mem0_tab():
    st.header("🔍 mem0 - 关键特征记忆库")

    stats = st.session_state.orchestrator.get_stats()
    total = stats["mem0"]["total_features"]

    if total == 0:
        st.info("mem0 中还没有特征，请先在左侧加载演示数据")
        return

    # 获取所有特征
    all_features = st.session_state.orchestrator.mem0.get_all_features()

    # 按分类展示
    categories = ["基本信息", "投诉记录", "业务意向", "用户偏好", "风险标签", "其他"]

    selected_category = st.selectbox("筛选分类", ["全部"] + categories)

    # 展示特征列表
    display_features = []
    for feat in all_features:
        cat = getattr(feat, "category", "其他")
        if selected_category == "全部" or cat == selected_category:
            display_features.append({
                "分类": cat,
                "特征键": getattr(feat, "key", ""),
                "特征值": getattr(feat, "value", ""),
                "置信度": getattr(feat, "confidence", 1.0),
            })

    if display_features:
        df = pd.DataFrame(display_features)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("该分类下暂无特征")

    st.divider()

    # 搜索功能
    st.subheader("🔎 特征搜索")
    query = st.text_input("输入搜索关键词", placeholder="比如：手机号、套餐、投诉、转网...")
    if query:
        results = st.session_state.orchestrator.mem0.search(query, top_k=5)
        if results:
            st.success(f"找到 {len(results)} 个匹配特征")
            for r in results:
                st.markdown(f"""
                <div class="memory-card mem0-card">
                    <b>[{r.get('category', '其他')}]</b> {r['key']}: {r.get('value', '')}
                    <div style="font-size: 0.85em; color: #64748b;">
                        相似度: {r['similarity']:.1%}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("没有找到匹配的特征")


# -------------------
# Tab 3: memU 客户档案
# -------------------
def render_memu_tab():
    st.header("📋 memU - 客户档案中心")

    profile = st.session_state.orchestrator.get_profile()

    if not profile:
        st.info("客户档案尚未构建，请在左侧点击「立即构建客户档案」")
        return

    # 展示档案
    st.markdown(f"> **用户标识**：`{profile.user_id}`")
    st.markdown(f"> **最后更新**：{profile.updated_at[:19]}")

    st.divider()

    # 五大章节并排展示
    col1, col2 = st.columns(2)

    with col1:
        # 基本信息
        if profile.basic_info.items:
            st.markdown(f"""
            <div class="profile-section">
                <h4>📋 基本信息</h4>
                {'<br>'.join(profile.basic_info.items)}
            </div>
            """, unsafe_allow_html=True)

        # 投诉记录
        if profile.complaint_history.items:
            st.markdown(f"""
            <div class="profile-section">
                <h4>⚠️ 投诉记录</h4>
                {'<br>'.join(profile.complaint_history.items)}
            </div>
            """, unsafe_allow_html=True)

        # 业务意向
        if profile.business_intent.items:
            st.markdown(f"""
            <div class="profile-section">
                <h4>💼 业务意向</h4>
                {'<br>'.join(profile.business_intent.items)}
            </div>
            """, unsafe_allow_html=True)

    with col2:
        # 用户偏好
        if profile.user_preferences.items:
            st.markdown(f"""
            <div class="profile-section">
                <h4>❤️ 用户偏好</h4>
                {'<br>'.join(profile.user_preferences.items)}
            </div>
            """, unsafe_allow_html=True)

        # 风险标签
        if profile.risk_tags.items:
            risk_html = "<br>".join([f'<span class="tag-risk">{item}</span>' for item in profile.risk_tags.items])
            st.markdown(f"""
            <div class="profile-section">
                <h4>🚨 风险标签</h4>
                {risk_html}
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # 业务洞察和建议
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("💡 业务洞察")
        for insight in profile.insights:
            st.markdown(f"- {insight}")

    with col4:
        st.subheader("📌 跟进建议")
        for rec in profile.recommendations:
            st.markdown(f"- {rec}")

    st.divider()

    # 完整档案 Markdown
    with st.expander("📄 查看完整档案 Markdown"):
        md_content = profile.to_markdown()
        st.code(md_content, language="markdown")


# -------------------
# Tab 4: 智能搜索
# -------------------
def render_search_tab():
    st.header("🔎 双轨融合搜索")

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("输入查询", placeholder="比如：用户有什么投诉？有什么风险？套餐是什么？")
    with col2:
        top_k = st.number_input("返回数量", 1, 10, 5)

    # 预设查询
    preset_queries = [
        "用户手机号是什么？",
        "有什么投诉记录？",
        "有什么风险？",
        "套餐情况？",
        "用户偏好什么联系方式？",
    ]

    st.markdown("**快速查询：**")
    query_cols = st.columns(len(preset_queries))
    for i, pq in enumerate(preset_queries):
        if query_cols[i].button(pq, use_container_width=True):
            query = pq

    if query:
        results = st.session_state.orchestrator.search(query, top_k=top_k)

        st.info(f"""
        🔍 搜索「{query}」结果：
        - mem0 找到 {results['mem0_count']} 个特征
        - memU 找到 {results['memu_count']} 个档案匹配
        """)

        st.divider()

        # 分开展示
        col_a, col_b = st.columns(2)

        with col_a:
            st.subheader("🔍 mem0 - 特征匹配")
            if results["mem0_results"]:
                for r in results["mem0_results"]:
                    st.markdown(f"""
                    <div class="memory-card mem0-card">
                        <b>[{r.get('category', '其他')}]</b> {r['key']}
                        <div>{r.get('value', '')}</div>
                        <div style="font-size: 0.85em; color: #64748b;">
                            相似度: {r['similarity']:.1%}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("mem0 无匹配结果")

        with col_b:
            st.subheader("📋 memU - 档案匹配")
            if results["memu_results"]:
                for r in results["memu_results"]:
                    st.markdown(f"""
                    <div class="memory-card memu-card">
                        <b>用户 {r['user_id']}</b>
                        <div style="font-size: 0.85em; color: #64748b;">
                            相似度: {r['similarity']:.1%}
                        </div>
                        <div style="margin-top: 8px; font-size: 0.9em;">
                            {r['content_preview']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("memU 无匹配结果")

        st.divider()

        # 给 LLM 的上下文
        st.subheader("🧠 生成客服坐席上下文")
        context = st.session_state.orchestrator.get_context_for_llm(query)
        if context.strip():
            st.code(context, language="markdown")
        else:
            st.info("暂无上下文")


# -------------------
# Tab 5: 对话模拟
# -------------------
def render_chat_tab():
    st.header("💬 对话模拟")

    st.info("在这里输入新的对话，系统会自动提取特征到 mem0，累计 N 轮后会触发 memU 建档")

    # 输入
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_area("输入客户对话", height=100,
                                 placeholder="比如：我要投诉宽带又断了，这个月已经第三次了...")
        role = st.selectbox("发言角色", ["user (客户)", "assistant (客服)"])
        submitted = st.form_submit_button("提交对话并提取特征", type="primary")

        if submitted and user_input:
            role_value = "user" if role.startswith("user") else "assistant"
            result = st.session_state.orchestrator.add_message(
                role=role_value,
                content=user_input,
            )

            if result["features_extracted"] > 0:
                st.success(f"✅ 提取了 {result['features_extracted']} 个新特征")
            else:
                st.info("未提取到新特征（无匹配关键词）")

            if result["profile_triggered"]:
                st.success("📋 已触发 memU 客户档案构建！")

            st.rerun()

    # 显示缓冲区对话
    st.divider()
    st.subheader("📝 待建档对话缓冲区")
    stats = st.session_state.orchestrator.get_stats()
    pending = stats["buffer"]["pending_conversations"]
    threshold = stats["buffer"]["trigger_threshold"]

    st.progress(pending / threshold, text=f"已积累 {pending}/{threshold} 轮对话")

    if pending == 0:
        st.info("缓冲区为空")


# -------------------
# Tab 6: 智能坐席 Agent
# -------------------
def render_agent_tab():
    st.header("🤖 智能坐席 Agent")

    st.markdown("""
    演示 **Agent 如何消费 mem0 + memU 双轨记忆**，生成上下文感知的客服回答。

    > 闭环流程：用户提问 → mem0/memU 检索 → 上下文组装 → LLM 推理 → 结构化回答
    """)

    # LLM 状态
    if st.session_state.agent.is_available:
        st.success("🟢 LLM 已就绪 — 将使用大模型生成智能客服回答")
        st.caption(f"模型：`{st.session_state.agent.model}`")
    else:
        st.warning("🟡 LLM 初始化失败 — 将使用规则降级回答")
        error_msg = st.session_state.agent.error_message
        if error_msg:
            with st.expander("🔍 查看详细错误信息", expanded=True):
                st.error(f"```\n{error_msg}\n```")
                st.caption("常见问题：Streamlit Cloud 可能有网络出口限制，或 API Key 无效")

    st.divider()

    # 预设问题
    preset_questions = [
        "用户有什么投诉？该怎么处理？",
        "这个用户有什么风险？需要特别注意什么？",
        "用户想办什么业务？有什么推荐方案？",
        "用户有什么偏好和禁忌？",
        "请总结这位客户的完整画像和跟进方案",
    ]

    st.markdown("**常见客服场景：**")
    q_cols = st.columns(len(preset_questions))
    selected_query = ""
    for i, pq in enumerate(preset_questions):
        if q_cols[i].button(pq, use_container_width=True):
            selected_query = pq

    # 自由输入
    user_query = st.text_input(
        "或输入自定义问题",
        value=selected_query,
        placeholder="比如：用户刚才说想携号转网，我该怎么挽留？",
    )

    if user_query:
        with st.spinner("🤔 Agent 正在检索记忆并生成回答..."):
            result = st.session_state.agent.answer(
                query=user_query,
                show_context=True,
            )

        # Agent 回答（首要展示）
        st.subheader("🤖 Agent 回答")
        if result.get("error"):
            st.caption(f"⚠️ {result['error']}")

        # 压缩连续空行，用 markdown 渲染（字体正常、空行紧凑）
        answer_clean = re.sub(r'\n{3,}', '\n\n', result['answer'])
        st.markdown(answer_clean)

        st.divider()

        # 中间过程折叠展示
        with st.expander("🔍 查看推理过程（mem0 检索 → memU 档案 → 上下文组装）"):
            # Step 1: mem0 检索结果
            st.subheader("Step 1: mem0 检索 → 关键特征匹配")
            if result["context_mem0"]:
                mem0_df = pd.DataFrame(result["context_mem0"])
                st.dataframe(mem0_df, use_container_width=True, hide_index=True)
            else:
                st.info("mem0 无匹配特征")

            # Step 2: memU 档案
            st.subheader("Step 2: memU 检索 → 客户档案摘要")
            if result["context_memu"]:
                profile = st.session_state.orchestrator.get_profile()
                if profile:
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown("**风险标签：**")
                        for item in profile.risk_tags.items:
                            st.markdown(f"- {item}")
                        st.markdown("**用户偏好：**")
                        for item in profile.user_preferences.items:
                            st.markdown(f"- {item}")
                    with col_b:
                        st.markdown("**业务洞察：**")
                        for insight in profile.insights[:3]:
                            st.markdown(f"- {insight}")
                        st.markdown("**跟进建议：**")
                        for rec in profile.recommendations[:3]:
                            st.markdown(f"- {rec}")
            else:
                st.info("memU 暂无客户档案")

            # Step 3: 组装的上下文
            st.subheader("Step 3: 上下文组装 → 传给 LLM 的 Prompt")
            st.code(result["full_prompt"], language="markdown")


# -------------------
# Main
# -------------------
def main():
    init_session_state()
    render_sidebar()

    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🎯 系统总览",
        "🔍 mem0 特征记忆",
        "📋 memU 客户档案",
        "🔎 智能搜索",
        "💬 对话模拟",
        "🤖 智能坐席",
    ])

    with tab1:
        render_overview_tab()
    with tab2:
        render_mem0_tab()
    with tab3:
        render_memu_tab()
    with tab4:
        render_search_tab()
    with tab5:
        render_chat_tab()
    with tab6:
        render_agent_tab()


if __name__ == "__main__":
    main()
