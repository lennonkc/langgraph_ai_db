"""
LangGraph AI数据库分析师 - 单页面 Streamlit 前端
整合所有功能到一个统一的仪表板
"""

import streamlit as st
import time
import uuid
import pandas as pd
from typing import Dict, Any
from streamlit_mermaid import st_mermaid
from utils.session_manager import initialize_session_state
from utils.langgraph_integration import (
    test_langgraph_connection,
    process_user_query,
    get_workflow_runner,
    resume_workflow_with_review,
    check_pending_review
)

# 页面配置 - 必须是第一行代码
st.set_page_config(
    page_title="AI数据库分析师",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/your-repo/help',
        'Report a bug': 'https://github.com/your-repo/issues',
        'About': """
        # AI数据库分析师
        基于LangGraph的智能数据分析助手

        **功能特性:**
        - 自然语言查询
        - 智能SQL生成
        - 数据可视化
        - 工作流可视化
        """
    }
)

def main():
    """主应用逻辑"""

    # 初始化session state
    initialize_session_state()

    # 渲染侧边栏
    render_sidebar()

    # 渲染顶部区域
    render_header()

    # 渲染主体区域（左右分栏）
    render_main_content()

def render_sidebar():
    """渲染左侧可隐藏栏"""

    with st.sidebar:
        st.title("🤖 AI数据库分析师")
        st.markdown("---")

        # 使用指南
        render_usage_guide()

        st.markdown("---")

        # 问题案例（快速填充）
        render_quick_questions()

        st.markdown("---")

        # 系统状态
        render_system_status()

def render_usage_guide():
    """渲染使用指南"""

    st.markdown("""
    ### 📖 使用指南

    **🚀 快速开始:**
    1. 在右侧聊天区域输入问题
    2. 查看LangGraph工作流执行过程
    3. 获取智能分析结果

    **💡 功能特色:**
    - 自然语言查询数据
    - 实时工作流可视化
    - 智能SQL生成和执行
    - 多维度数据分析
    """)

def render_quick_questions():
    """渲染问题案例快速填充"""

    st.markdown("### 🔥 热门问题")

    # 分类的问题案例
    question_categories = {
        "📊 趋势分析": [
            "最近7天的订单总量趋势如何？",
            "本月相比上月的收入增长情况？",
            "用户活跃度的变化趋势是什么？"
        ],
        "🔍 数据对比": [
            "哪个产品类别的销售额最高？",
            "不同地区的销售表现对比？",
            "各品牌的市场份额分布如何？"
        ],
        "📈 业务分析": [
            "用户留存率如何？",
            "平均订单价值是多少？",
            "哪些产品需要补货？"
        ]
    }

    # 使用tabs来组织不同类别的问题
    tab_names = list(question_categories.keys())
    tabs = st.tabs(tab_names)

    for tab, (category, questions) in zip(tabs, question_categories.items()):
        with tab:
            for i, question in enumerate(questions):
                if st.button(
                    f"💬 {question}",
                    key=f"quick_q_{category}_{i}",
                    help=f"点击快速发送: {question}",
                    use_container_width=True
                ):
                    # 将问题填充到聊天输入框
                    st.session_state['quick_question'] = question
                    st.toast(f"✅ 已选择问题: {question[:40]}...")
                    st.rerun()

    # 添加自定义问题功能
    st.markdown("---")
    st.markdown("### ✏️ 自定义问题")

    with st.expander("💡 问题建议"):
        st.markdown("""
        **好的问题示例:**
        - 包含具体的时间范围
        - 明确的数据指标
        - 清晰的对比维度

        **示例格式:**
        - "最近30天的..."
        - "按产品类别统计..."
        - "对比2023年和2024年..."
        """)

    # 最近使用的问题
    if st.session_state.get('messages'):
        st.markdown("### 🕒 最近提问")
        recent_questions = []
        for msg in reversed(st.session_state.messages):
            if msg["role"] == "user" and len(recent_questions) < 3:
                recent_questions.append(msg["content"])

        for i, question in enumerate(recent_questions):
            question_preview = question[:30] + "..." if len(question) > 30 else question
            if st.button(
                f"🔄 {question_preview}",
                key=f"recent_q_{i}",
                help=question,
                use_container_width=True
            ):
                st.session_state['quick_question'] = question
                st.toast("🔄 重新发送之前的问题")
                st.rerun()

def render_system_status():
    """渲染系统状态"""

    st.markdown("### 🔧 系统状态")

    # LangGraph连接状态
    connected = test_langgraph_connection()
    if connected:
        st.success("🟢 LangGraph已连接")
    else:
        st.error("🔴 LangGraph未连接")

    # BigQuery连接状态（从session state读取）
    if st.session_state.get('bigquery_connected', False):
        st.success("🟢 BigQuery已连接")
    else:
        st.warning("🟡 BigQuery未连接")

    # 会话信息
    session_id = st.session_state.get('session_id', 'unknown')
    st.caption(f"会话ID: {session_id[:8]}...")

def render_header():
    """渲染顶部区域"""

    # 添加自定义CSS样式
    st.markdown("""
    <style>
    .header-container {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        color: white;
    }
    .header-title {
        font-size: 2.2rem;
        font-weight: bold;
        margin: 0;
        text-align: center;
    }
    .header-subtitle {
        font-size: 1.1rem;
        margin: 0;
        text-align: center;
        opacity: 0.9;
    }
    .status-card {
        text-align: center;
        padding: 0.5rem;
        background: rgba(255,255,255,0.1);
        border-radius: 8px;
        margin-bottom: 0.5rem;
        min-height: 60px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .status-label {
        font-size: 0.8rem;
        color: #666;
        margin-bottom: 0.2rem;
    }
    .status-value {
        font-size: 0.9rem;
        font-weight: bold;
    }
    .status-chip {
        text-align: center;
        padding: 0.4rem;
        background: rgba(255,255,255,0.1);
        border-radius: 6px;
        margin-bottom: 0.3rem;
        min-height: 40px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    </style>
    """, unsafe_allow_html=True)

    # 创建美观的header容器
    st.markdown("""
    <div class="header-container">
        <h1 class="header-title">🤖 Thrasio AI数据分析师</h1>
        <p class="header-subtitle">基于 LangGraph 的智能数据分析平台</p>
    </div>
    """, unsafe_allow_html=True)

    # 状态和控制栏
    render_header_status_bar()

def render_header_status_bar():
    """渲染头部状态栏"""

    status_col1, status_col2, status_col3, status_col4 = st.columns([2, 1, 1, 1])

    with status_col1:
        render_connection_status_chips()

    with status_col2:
        render_session_info()

    with status_col3:
        render_workflow_status_indicator()

    with status_col4:
        render_header_action_buttons()

def render_connection_status_chips():
    """渲染连接状态芯片"""

    # LangGraph连接状态
    langgraph_connected = test_langgraph_connection()
    langgraph_icon = "🟢" if langgraph_connected else "🔴"
    langgraph_color = "#28a745" if langgraph_connected else "#dc3545"

    # BigQuery连接状态
    bigquery_connected = st.session_state.get('bigquery_connected', False)
    bigquery_icon = "🟢" if bigquery_connected else "🟡"
    bigquery_color = "#28a745" if bigquery_connected else "#ffc107"

    # 使用统一的紧凑样式
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"""
        <div class='status-chip'>
            <div style='font-size: 0.75rem; font-weight: bold; color: {langgraph_color};'>
                {langgraph_icon} LangGraph
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class='status-chip'>
            <div style='font-size: 0.75rem; font-weight: bold; color: {bigquery_color};'>
                {bigquery_icon} BigQuery
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_session_info():
    """渲染会话信息"""

    # 确保session_id存在，如果不存在则创建并保存到session_state
    if 'session_id' not in st.session_state:
        st.session_state['session_id'] = str(uuid.uuid4())[:8]

    session_id = st.session_state['session_id']

    # 使用统一的紧凑样式
    st.markdown(f"""
    <div class='status-card'>
        <div class='status-label'>🆔 当前会话</div>
        <div class='status-value'>{session_id}</div>
    </div>
    """, unsafe_allow_html=True)


def render_workflow_status_indicator():
    """渲染工作流状态指示器"""

    workflow_status = st.session_state.get('workflow_status', 'idle')
    current_step = st.session_state.get('current_step', 0)
    total_steps = len(st.session_state.get('workflow_steps', []))

    # 状态映射
    status_config = {
        'idle': {'icon': '⏸️', 'label': '待机', 'color': '#6c757d'},
        'running': {'icon': '🔄', 'label': '运行中', 'color': '#007bff'},
        'completed': {'icon': '✅', 'label': '已完成', 'color': '#28a745'},
        'error': {'icon': '❌', 'label': '错误', 'color': '#dc3545'}
    }

    config = status_config.get(workflow_status, status_config['idle'])

    # 使用统一的紧凑样式
    if total_steps > 0:
        progress_text = f"{current_step}/{total_steps}"
        status_display = f"{progress_text} {config['label']}"
    else:
        status_display = config['label']

    st.markdown(f"""
    <div class='status-card'>
        <div class='status-label'>{config['icon']} 工作流</div>
        <div class='status-value' style='color: {config["color"]};'>{status_display}</div>
    </div>
    """, unsafe_allow_html=True)

def render_header_action_buttons():
    """渲染顶部操作按钮"""

    # 新对话按钮 - 使用小型按钮
    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("🆕 新对话", help="开始新的对话会话", use_container_width=True):
            start_new_conversation()

    with col2:
        # 高级选项按钮 - 使用紧凑的popover
        with st.popover("⚙️", help="高级选项", use_container_width=True):
            st.markdown("**🔧 高级设置**")

            # 使用紧凑的按钮布局
            if st.button("🗑️ 清理缓存", help="清理所有session缓存", use_container_width=True):
                clear_all_cache()

            if st.button("📥 导出会话", help="导出当前会话数据", use_container_width=True):
                export_session_data()

            if st.button("🔄 重新连接", help="重新连接所有服务", use_container_width=True):
                reconnect_services()

def clear_all_cache():
    """清理所有缓存"""
    cache_keys = [
        'messages', 'chat_history', 'workflow_steps', 'current_step',
        'workflow_status', 'analysis_results', 'generated_sql', 'query_results'
    ]

    cleared_count = 0
    for key in cache_keys:
        if key in st.session_state:
            del st.session_state[key]
            cleared_count += 1

    st.toast(f"✅ 已清理 {cleared_count} 个缓存项")
    st.rerun()

def export_session_data():
    """导出会话数据"""
    import json
    from datetime import datetime

    session_data = {
        'session_id': st.session_state.get('session_id', 'unknown'),
        'export_time': datetime.now().isoformat(),
        'messages': st.session_state.get('messages', []),
        'analysis_results': st.session_state.get('analysis_results', []),
        'workflow_status': st.session_state.get('workflow_status', 'idle')
    }

    # 转换为JSON字符串
    json_str = json.dumps(session_data, ensure_ascii=False, indent=2)

    # 提供下载
    st.download_button(
        label="💾 下载会话数据",
        data=json_str,
        file_name=f"session_{session_data['session_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json"
    )

def reconnect_services():
    """重新连接所有服务"""
    with st.spinner("正在重新连接服务..."):
        # 重新测试LangGraph连接
        langgraph_connected = test_langgraph_connection()

        # 重新初始化工作流运行器
        if 'workflow_runner' in st.session_state:
            del st.session_state['workflow_runner']

        # 获取新的运行器
        new_runner = get_workflow_runner()

        success_msg = []
        if langgraph_connected:
            success_msg.append("LangGraph")

        if success_msg:
            st.toast(f"✅ 成功重连: {', '.join(success_msg)}")
        else:
            st.toast("⚠️ 部分服务重连失败，请检查配置")

# render_header_controls函数已被新的header系统替代

def start_new_conversation():
    """开始新对话"""

    # 清理会话相关状态
    keys_to_clear = [
        'messages', 'chat_history', 'workflow_steps',
        'current_step', 'workflow_status', 'analysis_results'
    ]

    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

    # 生成新的会话ID
    st.session_state['session_id'] = str(uuid.uuid4())[:8]

    st.toast("🎉 新对话已开始！")
    st.rerun()

def render_main_content():
    """渲染主体内容区域"""

    # 左右分栏：聊天区域 (70%) + 工作流可视化 (30%)
    chat_col, workflow_col = st.columns([0.7, 0.3])

    with chat_col:
        render_chat_section()

    with workflow_col:
        render_workflow_section()

def render_chat_section():
    """渲染聊天区域"""

    st.markdown("### 💬 智能对话")

    # 初始化聊天历史
    if "messages" not in st.session_state:
        st.session_state.messages = []
        # 添加欢迎消息
        welcome_message = {
            "role": "assistant",
            "content": """👋 您好！我是AI数据库分析助手。

我可以帮助您：
- 📝 用自然语言查询数据
- 📊 生成数据可视化图表
- 🔍 分析数据趋势和模式
- 💡 提供业务洞察建议

请告诉我您想了解什么数据？您也可以从左侧选择热门问题快速开始。"""
        }
        st.session_state.messages.append(welcome_message)

    # 显示聊天历史
    chat_container = st.container(height=800)
    with chat_container:
        for i, message in enumerate(st.session_state.messages):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

                # 显示消息的额外信息
                if message["role"] == "assistant" and message.get("metadata"):
                    render_message_metadata(message["metadata"])

                # 如果这是最后一条助手消息且需要Human Review，显示交互组件
                is_last_message = i == len(st.session_state.messages) - 1
                requires_review = message.get("requires_human_review", False)

                # 调试信息
                if message["role"] == "assistant" and is_last_message:
                    print(f"调试：最后一条助手消息 - requires_human_review: {requires_review}")
                    if requires_review:
                        print(f"调试：显示human review界面，thread_id: {message.get('thread_id', 'N/A')}")

                if (message["role"] == "assistant" and is_last_message and requires_review):
                    render_inline_human_review(message.get("review_data", {}), message.get("thread_id", ""))

                # 如果是已处理的Review消息，显示决策信息
                elif (message["role"] == "assistant" and
                      message.get("review_processed", False)):
                    decision = message.get("review_decision", "未知")
                    st.markdown(f"""
                    <div style="background: #e8f5e8; border-left: 4px solid #4caf50;
                                padding: 10px; border-radius: 5px; margin: 10px 0;">
                        <small style="color: #2e7d32;">
                            ✅ <strong>已处理</strong> - 您选择了：{decision}
                        </small>
                    </div>
                    """, unsafe_allow_html=True)

                # 如果消息包含报告按钮，显示打开报告按钮
                if (message["role"] == "assistant" and
                    message.get("show_report_button", False) and
                    message.get("report_path")):
                    render_inline_report_button(message.get("report_path"))

    # 聊天输入
    render_chat_input()

    # 显示报告访问按钮
    render_report_access_button()

def render_chat_input():
    """渲染聊天输入区域"""

    # 检查是否有快速问题需要填充
    default_value = ""
    if 'quick_question' in st.session_state:
        default_value = st.session_state['quick_question']
        del st.session_state['quick_question']  # 使用后删除

    # 重新启用测试按钮来诊断问题
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🧪 测试Human Review界面", help="测试交互界面显示"):
            test_human_review_display()
            return
    with col2:
        if st.button("🔍 检查最后消息状态", help="检查最后一条消息是否有review标记"):
            check_last_message_status()
            return

    # 聊天输入框
    if prompt := st.chat_input("请输入您的问题...", key="main_chat_input"):
        handle_user_input(prompt)
    elif default_value:
        # 如果有快速问题，自动处理
        handle_user_input(default_value)

def test_human_review_display():
    """测试Human Review界面显示"""

    # 创建一个模拟的review消息
    test_message = {
        "role": "assistant",
        "content": "🧪 **测试消息** - 这是一个测试human review界面的消息",
        "requires_human_review": True,
        "thread_id": "test_thread_123",
        "review_data": {
            "user_question": "测试问题：最近7天的订单总量趋势如何？",
            "data_summary": {
                "total_rows": 7,
                "has_data": True,
                "execution_success": True
            },
            "data_sample": [
                {"order_date": "2024-09-15", "total_orders": 1250},
                {"order_date": "2024-09-16", "total_orders": 1180},
                {"order_date": "2024-09-17", "total_orders": 1320}
            ],
            "available_charts": ["table", "bar_chart", "line_chart", "pie_chart"],
            "recommended_charts": ["line_chart", "bar_chart"],
            "explanation": "这是一个测试解释，用于验证human review界面显示。",
            "validation_reasoning": "测试验证：数据查询成功，返回了7天的订单数据。"
        },
        "metadata": {
            "processing_time": 2.5,
            "query_type": "test"
        }
    }

    # 添加到消息历史
    st.session_state.messages.append(test_message)

    st.toast("✅ 已添加测试Human Review消息")
    st.rerun()

def check_last_message_status():
    """检查最后一条消息的状态"""

    if not st.session_state.get('messages'):
        # 创建一个诊断消息
        diagnostic_message = {
            "role": "assistant",
            "content": "🔍 **诊断结果：** 没有找到任何聊天消息。请先提问一个问题，然后再检查消息状态。",
            "metadata": {"query_type": "diagnostic"}
        }
        st.session_state.messages.append(diagnostic_message)
        st.rerun()
        return

    last_message = st.session_state.messages[-1]

    # 创建诊断报告消息
    diagnostic_content = f"""🔍 **最后一条消息状态诊断：**

**基本信息：**
- 消息角色: `{last_message.get('role', 'N/A')}`
- 消息长度: {len(last_message.get('content', ''))} 字符
- 有metadata: {bool(last_message.get('metadata'))}

**Human Review 相关：**
- requires_human_review: `{last_message.get('requires_human_review', False)}`
- thread_id: `{last_message.get('thread_id', 'N/A')}`
- 有review_data: `{bool(last_message.get('review_data'))}`

**问题诊断：**"""

    if last_message.get('role') == 'assistant':
        if not last_message.get('requires_human_review', False):
            diagnostic_content += """
❌ **发现问题：** 助手消息没有设置 `requires_human_review=True`

**可能原因：**
1. LangGraph工作流没有返回 `human_review_required` 类型
2. `should_trigger_human_review` 检查失败
3. 工作流在到达human review步骤之前就结束了

**建议：** 查看控制台日志中的调试信息，确认工作流执行状态。"""
        else:
            diagnostic_content += """
✅ **正常：** 助手消息已正确设置为需要human review

**如果交互界面仍未显示：**
1. 检查这是否是最后一条消息
2. 确认浏览器没有缓存问题
3. 查看浏览器开发者工具中的错误"""
    else:
        diagnostic_content += f"""
ℹ️ **信息：** 最后一条消息是 {last_message.get('role')} 消息，不是助手消息。"""

    # 添加诊断消息到聊天历史
    diagnostic_message = {
        "role": "assistant",
        "content": diagnostic_content,
        "metadata": {"query_type": "diagnostic"}
    }
    st.session_state.messages.append(diagnostic_message)
    st.rerun()

def handle_user_input(prompt: str):
    """处理用户输入"""

    # 添加用户消息
    user_message = {"role": "user", "content": prompt}
    st.session_state.messages.append(user_message)

    # 显示用户消息
    with st.chat_message("user"):
        st.markdown(prompt)

    # 生成并显示助手响应
    with st.chat_message("assistant"):
        response = generate_assistant_response(prompt)
        response_placeholder = st.empty()

        # 模拟流式输出
        displayed_response = ""
        thread_id = None
        review_data = None

        for chunk in response:
            if isinstance(chunk, tuple) and len(chunk) == 3 and chunk[0] == "HUMAN_REVIEW_REQUIRED":
                # 如果返回的是特殊标记元组，说明需要Human Review
                _, thread_id, review_data = chunk
                print(f"调试：检测到HUMAN_REVIEW_REQUIRED标记，thread_id: {thread_id}, review_data存在: {bool(review_data)}")
                break
            elif isinstance(chunk, str):
                displayed_response += chunk
                response_placeholder.markdown(displayed_response + "▌")
                time.sleep(0.02)
            else:
                print(f"调试：收到非字符串chunk: {type(chunk)}, {chunk}")

        # 完成响应
        response_placeholder.markdown(displayed_response)

        # 添加助手消息到历史
        assistant_message = {
            "role": "assistant",
            "content": displayed_response,
            "metadata": {
                "processing_time": 2.5,
                "query_type": "analysis"
            }
        }

        # 如果需要Human Review，添加相关信息到消息
        if thread_id and review_data:
            assistant_message["requires_human_review"] = True
            assistant_message["thread_id"] = thread_id
            assistant_message["review_data"] = review_data
            print(f"调试：设置了human review标记，thread_id: {thread_id}")
        else:
            print(f"调试：未设置human review标记，thread_id: {thread_id}, review_data: {bool(review_data)}")

        st.session_state.messages.append(assistant_message)

    st.rerun()

def generate_assistant_response(prompt: str):
    """使用LangGraph工作流生成助手响应"""

    try:
        # 检查LangGraph连接
        if not test_langgraph_connection():
            yield "❌ LangGraph工作流未连接，请检查配置或重新连接。"
            return

        # 初始化工作流状态
        yield "🚀 开始分析您的问题...\n\n"

        # 更新工作流状态
        st.session_state.workflow_status = "running"

        # 获取会话ID
        session_id = st.session_state.get('session_id', 'default')

        # 调用LangGraph工作流
        with st.spinner("正在执行LangGraph工作流..."):
            result = process_user_query(prompt, session_id)

        # 处理工作流结果
        if result.get('type') == 'error':
            yield f"❌ 处理过程中出现错误：{result.get('content', '未知错误')}\n\n"
            yield "请检查：\n"
            yield "1. LangGraph工作流配置是否正确\n"
            yield "2. 数据库连接是否正常\n"
            yield "3. 问题描述是否清晰\n\n"
            return
        elif result.get('type') == 'human_review_required':
            # 工作流需要人工审查
            thread_id = result.get('thread_id', session_id)
            review_data = result.get('review_data', {})

            yield f"✅ **数据分析已完成！**\n\n"

            # 显示分析的问题
            user_question = review_data.get('user_question', '')
            if user_question:
                yield f"📝 **原始问题：** {user_question}\n\n"

            # 显示数据概览
            data_summary = review_data.get('data_summary', {})
            total_rows = data_summary.get('total_rows', 0)
            execution_success = data_summary.get('execution_success', False)
            has_data = data_summary.get('has_data', False)

            yield f"📊 **数据分析结果：**\n"

            # 使用更友好的格式
            status_icon = "✅" if execution_success else "❌"
            data_icon = "✅" if has_data else "⚠️"

            yield f"- {status_icon} **执行状态：** {'成功' if execution_success else '失败'}\n"
            yield f"- 📊 **数据行数：** {total_rows:,} 条\n"
            yield f"- {data_icon} **数据可用：** {'是' if has_data else '否'}\n\n"

            # 显示数据样本预览
            data_sample = review_data.get('data_sample', [])
            if data_sample and len(data_sample) > 0:
                yield "**📋 数据预览：**\n"
                df_sample = pd.DataFrame(data_sample)

                # 显示前3行数据
                preview_df = df_sample.head(3)

                # 使用更简洁的表格显示
                yield "```\n"
                yield preview_df.to_string(index=False, max_cols=6, max_colwidth=20)
                yield "\n```\n\n"

                if len(df_sample) > 3:
                    yield f"*显示前3行，共{len(df_sample)}行数据*\n\n"
            else:
                yield "⚠️ **没有找到数据样本**\n\n"

            # 显示解释信息（如果有）
            explanation = review_data.get('explanation', '')
            if explanation and explanation != 'No explanation available.':
                yield f"📝 **分析解释：**\n{explanation}\n\n"

            # 显示验证理由（如果有）
            validation_reasoning = review_data.get('validation_reasoning', '')
            if validation_reasoning:
                yield f"✅ **验证结果：**\n{validation_reasoning}\n\n"

            # 显示可用的图表类型选项
            available_charts = review_data.get('available_charts', [])
            recommended_charts = review_data.get('recommended_charts', [])

            if available_charts:
                yield "📊 **可选图表类型：**\n"
                chart_names = {
                    'table': '📋 数据表格',
                    'bar_chart': '📊 柱状图',
                    'line_chart': '📈 折线图',
                    'pie_chart': '🥧 饼图',
                    'scatter_plot': '🔴 散点图'
                }

                for chart in available_charts:
                    chart_name = chart_names.get(chart, chart)
                    is_recommended = chart in recommended_charts
                    recommendation_mark = " ⭐ **推荐**" if is_recommended else ""
                    yield f"- {chart_name}{recommendation_mark}\n"
                yield "\n"

                if recommended_charts:
                    yield f"💡 **系统推荐：** 基于您的数据特征，推荐使用 {', '.join([chart_names.get(c, c) for c in recommended_charts])}\n\n"

            # 显示图表配置选项
            yield "🛠️ **图表配置选项：**\n"
            yield "- 📊 **柱状图**：垂直/水平方向，多种颜色方案\n"
            yield "- 📈 **折线图**：数据点标记，平滑曲线选项\n"
            yield "- 🥧 **饼图**：百分比标签，突出显示最大部分\n"
            yield "- 📋 **数据表格**：可与其他图表同时显示\n"
            yield "- 🎨 **自定义**：图表标题，颜色主题等\n\n"

            # 提示用户下一步操作
            yield "🎯 **请做出您的决策：**\n"
            yield "- 👍 **批准：** 继续生成可视化报告\n"
            yield "- ✏️ **修改：** 调整查询条件\n"
            yield "- 🔄 **重新生成：** 从头开始分析\n\n"

            yield "📝 **操作提示：** 决策和图表配置将在下方的交互界面中进行。"

            # 将review信息作为特殊标记yield出来，供调用方处理
            yield ("HUMAN_REVIEW_REQUIRED", thread_id, review_data)
            return

        # 提取工作流数据
        data_info = result.get('data', {})
        sql_query = data_info.get('sql_query', '')
        query_results = data_info.get('query_results')
        insights = data_info.get('insights', [])
        execution_time = data_info.get('execution_time', 0)

        # 生成成功响应
        yield f"✅ 已成功完成数据分析\n\n"

        if sql_query:
            yield f"**生成的SQL查询：**\n```sql\n{sql_query}\n```\n\n"

        if query_results is not None and not query_results.empty:
            record_count = len(query_results)
            yield f"📊 **查询结果概览：**\n"
            yield f"- 返回记录数：{record_count:,} 条\n"
            yield f"- 数据列数：{len(query_results.columns)} 列\n"
            yield f"- 执行时间：{execution_time:.2f} 秒\n\n"

            # 显示数据预览
            if record_count > 0:
                yield "**数据预览：**\n"
                preview_data = query_results.head(3).to_string(index=False)
                yield f"```\n{preview_data}\n```\n\n"

            # 保存结果到session state
            save_analysis_result(prompt, sql_query, query_results, insights, execution_time)

        # 显示分析洞察
        if insights:
            yield "🔍 **关键洞察：**\n"
            for i, insight in enumerate(insights, 1):
                yield f"{i}. {insight}\n"
            yield "\n"

            # 检查是否生成了报告文件
        report_path = data_info.get('report_path')
        if report_path:
            yield f"\n📊 **报告已生成：** `{report_path}`\n\n"

            # 在session state中存储报告路径
            st.session_state.latest_report_path = report_path

            yield "📝 您可以点击下方的按钮查看报告。\n\n"

        # 显示后续操作建议
        yield "📈 **后续操作：**\n"
        yield "- 您可以继续提问进行更深入的分析\n"
        yield "- 支持导出数据和图表\n"
        yield "- 可以查看右侧的详细工作流执行过程\n\n"

        yield "如果您需要进一步分析或有其他问题，请随时告诉我！"

        # 完成工作流
        st.session_state.workflow_status = "completed"

    except Exception as e:
        yield f"❌ 处理请求时发生错误：{str(e)}\n\n"
        yield "请检查：\n"
        yield "1. LangGraph工作流配置是否正确\n"
        yield "2. 数据库连接是否正常\n"
        yield "3. 问题描述是否清晰\n\n"
        yield "您可以尝试重新表述问题或联系管理员。"

        # 设置工作流为错误状态
        st.session_state.workflow_status = "error"




def save_analysis_result(prompt: str, sql_query: str, query_results: pd.DataFrame,
                        insights: list, execution_time: float):
    """保存分析结果到session state"""

    if "analysis_results" not in st.session_state:
        st.session_state.analysis_results = []

    record_count = len(query_results) if query_results is not None else 0

    analysis_result = {
        "title": prompt[:50] + "..." if len(prompt) > 50 else prompt,
        "query": prompt,
        "sql_query": sql_query,
        "data": query_results,
        "success": True,
        "execution_time": execution_time,
        "record_count": record_count,
        "insights": insights,
        "timestamp": time.time()
    }

    st.session_state.analysis_results.append(analysis_result)


def render_message_metadata(metadata: dict):
    """渲染消息元数据"""

    col1, col2 = st.columns(2)

    with col1:
        if metadata.get("query_type"):
            st.caption(f"🏷️ 类型: {metadata['query_type']}")

    with col2:
        if metadata.get("processing_time"):
            st.caption(f"⏱️ 用时: {metadata['processing_time']:.1f}s")

def render_inline_human_review(review_data: Dict, thread_id: str):
    """在聊天消息中渲染内联Human Review界面"""

    if not review_data:
        st.error("无法获取审查数据")
        return

    # 添加优雅的分隔线和样式
    st.markdown("""
    <div style="border-top: 2px solid #f0f0f0; margin: 20px 0;"></div>
    <div style="background: linear-gradient(90deg, #e3f2fd 0%, #f3e5f5 100%);
                padding: 15px; border-radius: 10px; margin: 10px 0;">
        <h4 style="margin: 0; color: #1976d2;">🎯 数据审查 - 请做出您的决策</h4>
        <p style="margin: 5px 0 0 0; color: #555; font-size: 0.9em;">分析已完成，请选择后续操作</p>
    </div>
    """, unsafe_allow_html=True)

    # 使用唯一的key来避免冲突
    form_key = f"human_review_form_{thread_id}_{hash(str(review_data))}".replace("-", "_")

    # 显示数据概览信息
    data_summary = review_data.get('data_summary', {})
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="📊 数据行数",
            value=f"{data_summary.get('total_rows', 0):,}",
            delta=None
        )

    with col2:
        execution_status = "✅ 成功" if data_summary.get('execution_success') else "❌ 失败"
        st.metric(
            label="⚡ 执行状态",
            value=execution_status
        )

    with col3:
        data_available = "✅ 有数据" if data_summary.get('has_data') else "❌ 无数据"
        st.metric(
            label="📋 数据状态",
            value=data_available
        )

    # 显示数据样本预览（如果有数据）
    data_sample = review_data.get('data_sample', [])
    if data_sample and len(data_sample) > 0:
        st.markdown("**📋 数据预览：**")
        df_sample = pd.DataFrame(data_sample)
        st.dataframe(df_sample.head(3), use_container_width=True, hide_index=True)

    # Human Review表单
    with st.form(form_key):
        # 决策选项 - 使用更直观的layout
        st.markdown("#### 🎯 选择您的操作")

        # 使用columns来优化layout
        decision_col, info_col = st.columns([2, 1])

        with decision_col:
            decision = st.radio(
                "您希望如何处理这个结果？",
                options=["approve", "modify", "regenerate"],
                format_func=lambda x: {
                    "approve": "👍 批准并生成可视化报告",
                    "modify": "✏️ 修改查询条件",
                    "regenerate": "🔄 重新生成查询"
                }[x],
                index=0,
                key=f"decision_{form_key}"
            )

        with info_col:
            # 显示决策帮助信息
            help_text = {
                "approve": "✅ 继续生成图表和报告",
                "modify": "✏️ 调整查询以获得更好结果",
                "regenerate": "🔄 从头开始重新分析"
            }
            st.info(help_text.get(decision, ""))

        # 图表选择（仅在approve时显示）
        chart_selection = "table"
        preferences = {}

        if decision == "approve":
            st.markdown("---")
            st.markdown("#### 📊 选择可视化方式")

            available_charts = review_data.get('available_charts', ['table', 'bar_chart', 'line_chart'])
            recommended_charts = review_data.get('recommended_charts', ['table'])

            # 显示推荐信息
            if recommended_charts:
                st.success(f"💡 系统推荐：{', '.join([{
                    'table': '📋 数据表格',
                    'bar_chart': '📊 柱状图',
                    'line_chart': '📈 折线图',
                    'pie_chart': '🥧 饼图',
                    'scatter_plot': '🔴 散点图'
                }.get(c, c) for c in recommended_charts])}")

            # 使用更友好的图表选择界面
            chart_col, preview_col = st.columns([1, 1])

            with chart_col:
                chart_selection = st.selectbox(
                    "图表类型",
                    options=available_charts,
                    format_func=lambda x: {
                        "table": "📋 数据表格",
                        "bar_chart": "📊 柱状图",
                        "line_chart": "📈 折线图",
                        "pie_chart": "🥧 饼图",
                        "scatter_plot": "🔴 散点图"
                    }.get(x, x),
                    index=0 if not recommended_charts else (available_charts.index(recommended_charts[0]) if recommended_charts[0] in available_charts else 0),
                    key=f"chart_{form_key}"
                )

            with preview_col:
                # 显示图表类型描述
                chart_descriptions = {
                    "table": "清晰展示所有数据细节",
                    "bar_chart": "适合比较不同类别的数值",
                    "line_chart": "显示数据随时间的变化趋势",
                    "pie_chart": "展示各部分占整体的比例",
                    "scatter_plot": "显示两个变量间的关系"
                }
                st.info(f"💡 {chart_descriptions.get(chart_selection, '通用图表类型')}")

            # 图表偏好设置
            with st.expander("🛠️ 高级图表设置", expanded=False):
                # 通用设置
                col1, col2 = st.columns(2)

                with col1:
                    title = st.text_input("图表标题", value="数据分析结果", key=f"title_{form_key}")

                with col2:
                    include_data_table = st.checkbox("同时显示数据表", value=True, key=f"table_{form_key}")

                preferences = {
                    "title": title,
                    "include_data_table": include_data_table
                }

                # 特定图表的设置
                if chart_selection == "bar_chart":
                    col1, col2 = st.columns(2)
                    with col1:
                        orientation = st.radio(
                            "图表方向",
                            ["vertical", "horizontal"],
                            format_func=lambda x: "🏗️ 竖直" if x == "vertical" else "↔️ 水平",
                            key=f"orient_{form_key}"
                        )
                    with col2:
                        color_scheme = st.selectbox(
                            "颜色方案",
                            ["default", "viridis", "plasma"],
                            format_func=lambda x: {
                                "default": "🎨 默认",
                                "viridis": "🌈 彩虹",
                                "plasma": "🔥 热力"
                            }.get(x, x),
                            key=f"color_{form_key}"
                        )
                    preferences.update({
                        "orientation": orientation,
                        "color_scheme": color_scheme
                    })

                elif chart_selection == "line_chart":
                    show_markers = st.checkbox("🔵 显示数据点标记", value=True, key=f"markers_{form_key}")
                    preferences.update({
                        "show_markers": show_markers
                    })

                elif chart_selection == "pie_chart":
                    show_percentages = st.checkbox("📊 显示百分比标签", value=True, key=f"percent_{form_key}")
                    preferences.update({
                        "show_percentages": show_percentages
                    })

        # 修改指令（仅在modify时显示）
        modifications = []
        if decision == "modify":
            st.markdown("---")
            st.markdown("#### ✏️ 描述您希望的修改")

            # 提供一些修改建议
            st.markdown("""
            💡 **修改建议示例：**
            - 调整时间范围："改为最近30天的数据"
            - 添加筛选条件："只显示状态为Active的记录"
            - 修改分组方式："按月份而不是按天分组"
            - 调整排序："按销售额从高到低排序"
            """)

            modification_text = st.text_area(
                "请详细描述您希望如何修改查询",
                placeholder="例如：请将时间范围改为最近7天，并且只显示销售额大于1000的订单...",
                height=120,
                key=f"modify_{form_key}"
            )
            if modification_text:
                modifications = [modification_text]

        # 提交按钮区域
        st.markdown("---")

        # 根据决策显示不同的提交按钮样式
        button_text = {
            "approve": "🚀 批准并生成报告",
            "modify": "✏️ 提交修改请求",
            "regenerate": "🔄 重新生成查询"
        }.get(decision, "🚀 提交决策")

        submitted = st.form_submit_button(
            button_text,
            use_container_width=True,
            type="primary"
        )

        if submitted:
            # 显示提交确认
            with st.spinner(f"正在处理您的{['批准', '修改', '重新生成'][['approve', 'modify', 'regenerate'].index(decision)]}请求..."):
                # 准备人类响应
                human_response = {
                    "decision": decision,
                    "chart_selection": chart_selection,
                    "preferences": preferences,
                    "modifications": modifications
                }

                # 发送给LangGraph并恢复工作流
                handle_inline_human_review_submission(thread_id, human_response)

def render_inline_report_button(report_path: str):
    """在聊天消息中渲染内联报告按钮"""

    st.markdown("---")

    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown(f"📄 **报告文件**: `{report_path}`")

    with col2:
        if st.button("🔍 打开报告", key=f"open_report_{hash(report_path)}", use_container_width=True):
            open_local_report(report_path)

def render_human_review_interface():
    """渲染Human Review交互界面"""

    st.markdown("---")
    st.markdown("### 👤 Human Review - 需要您的决策")

    review_data = st.session_state.get('human_review_data', {})
    thread_id = st.session_state.get('human_review_thread_id', '')

    if not review_data:
        st.error("无法获取审查数据")
        return

    # 显示问题和解释
    st.markdown(f"**原始问题：** {review_data.get('user_question', '')}")

    # 显示数据概览
    data_summary = review_data.get('data_summary', {})
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("数据行数", data_summary.get('total_rows', 0))
    with col2:
        st.metric("执行状态", "成功" if data_summary.get('execution_success') else "失败")
    with col3:
        st.metric("数据可用", "是" if data_summary.get('has_data') else "否")

    # 显示数据示例
    data_sample = review_data.get('data_sample', [])
    if data_sample:
        st.markdown("**数据示例：**")
        df_sample = pd.DataFrame(data_sample)
        st.dataframe(df_sample, use_container_width=True)

    # Human Review表单
    with st.form("human_review_form"):
        st.markdown("#### 请做出您的决策")

        # 决策选项
        decision = st.radio(
            "您希望如何处理这个结果？",
            options=["approve", "modify", "regenerate"],
            format_func=lambda x: {
                "approve": "👍 批准 - 继续生成可视化报告",
                "modify": "✏️ 修改 - 请求修改查询",
                "regenerate": "🔄 重新生成 - 重新开始查询"
            }[x],
            index=0
        )

        # 图表选择（仅在approve时显示）
        chart_selection = "table"
        preferences = {}

        if decision == "approve":
            st.markdown("#### 选择可视化方式")

            available_charts = review_data.get('available_charts', ['table', 'bar_chart', 'line_chart'])
            recommended_charts = review_data.get('recommended_charts', ['table'])

            chart_selection = st.selectbox(
                "图表类型",
                options=available_charts,
                format_func=lambda x: {
                    "table": "📋 表格",
                    "bar_chart": "📊 柱状图",
                    "line_chart": "📈 线图",
                    "pie_chart": "🥧 饼图",
                    "scatter_plot": "🔴 散点图"
                }.get(x, x),
                help=f"推荐： {', '.join(recommended_charts)}"
            )

            # 图表偏好设置
            with st.expander("🛠️ 高级设置", expanded=False):

                # 通用设置
                title = st.text_input("图表标题", value="Analysis Results")
                include_data_table = st.checkbox("包含数据表", value=True)

                preferences = {
                    "title": title,
                    "include_data_table": include_data_table
                }

                # 特定图表的设置
                if chart_selection == "bar_chart":
                    orientation = st.radio("方向", ["vertical", "horizontal"], format_func=lambda x: "竖直" if x == "vertical" else "水平")
                    color_scheme = st.selectbox("颜色方案", ["default", "viridis", "plasma"], index=0)
                    preferences.update({
                        "orientation": orientation,
                        "color_scheme": color_scheme
                    })

                elif chart_selection == "line_chart":
                    show_markers = st.checkbox("显示数据点", value=True)
                    preferences.update({
                        "show_markers": show_markers
                    })

                elif chart_selection == "pie_chart":
                    show_percentages = st.checkbox("显示百分比", value=True)
                    preferences.update({
                        "show_percentages": show_percentages
                    })

        # 修改指令（仅在modify时显示）
        modifications = []
        if decision == "modify":
            st.markdown("#### 请描述需要的修改")
            modification_text = st.text_area(
                "修改说明",
                placeholder="请详细描述您希望如何修改这个查询...",
                height=100
            )
            if modification_text:
                modifications = [modification_text]

        # 提交按钮
        submitted = st.form_submit_button(
            "🚀 提交决策",
            use_container_width=True,
            type="primary"
        )

        if submitted:
            # 准备人类响应
            human_response = {
                "decision": decision,
                "chart_selection": chart_selection,
                "preferences": preferences,
                "modifications": modifications
            }

            # 发送给LangGraph并恢复工作流
            handle_human_review_submission(thread_id, human_response)

def handle_inline_human_review_submission(thread_id: str, human_response: Dict):
    """处理内联Human Review提交"""

    decision = human_response.get('decision', 'approve')
    decision_names = {
        'approve': '批准',
        'modify': '修改',
        'regenerate': '重新生成'
    }

    try:
        # 显示处理进度
        progress_placeholder = st.empty()
        status_placeholder = st.empty()

        with progress_placeholder:
            st.info(f"🚀 正在处理您的{decision_names.get(decision, '决策')}请求...")

        # 使用人类响应恢复工作流
        result = resume_workflow_with_review(thread_id, human_response)

        # 清理进度显示
        progress_placeholder.empty()

        if result.get('type') == 'error':
            with status_placeholder:
                st.error(f"❌ 处理失败：{result.get('content', '未知错误')}")
            return

        # 移除当前消息的Human Review标记
        if st.session_state.messages:
            last_message = st.session_state.messages[-1]
            if last_message.get("requires_human_review"):
                last_message["requires_human_review"] = False
                # 添加已处理标记
                last_message["review_processed"] = True
                last_message["review_decision"] = decision_names.get(decision, decision)

        # 根据决策类型处理结果
        if decision == 'approve':
            chart_selection = human_response.get('chart_selection', 'table')
            chart_names = {
                'table': '数据表格',
                'bar_chart': '柱状图',
                'line_chart': '折线图',
                'pie_chart': '饼图',
                'scatter_plot': '散点图'
            }

            success_msg = f"✅ **批准成功！**\n\n"
            success_msg += f"📋 **选择的可视化类型：** {chart_names.get(chart_selection, chart_selection)}\n"
            success_msg += f"🚀 **状态：** 正在生成最终报告和图表...\n\n"

            # 检查报告路径
            report_path = result.get('data', {}).get('report_path')
            if report_path:
                st.session_state.latest_report_path = report_path
                success_msg += f"📊 **报告已生成：** `{report_path}`\n"
                success_msg += f"🔍 您可以使用下方按钮打开报告。"
            else:
                success_msg += f"⚠️ 报告正在生成中，请稍候..."

            # 添加成功消息到聊天历史
            success_message = {
                "role": "assistant",
                "content": success_msg,
                "show_report_button": bool(report_path),
                "report_path": report_path if report_path else None,
                "metadata": {
                    "processing_time": 2.5,
                    "query_type": "visualization_approval",
                    "chart_type": chart_selection
                }
            }
            st.session_state.messages.append(success_message)

        elif decision == 'modify':
            modifications = human_response.get('modifications', [])
            modify_msg = f"✏️ **修改请求已提交！**\n\n"
            modify_msg += f"🔄 **状态：** 正在根据您的要求重新生成查询...\n\n"

            if modifications:
                modify_msg += f"📝 **您的修改说明：**\n"
                for i, mod in enumerate(modifications, 1):
                    modify_msg += f"{i}. {mod}\n"
                modify_msg += "\n"

            modify_msg += f"⏳ 请稍候，系统正在处理您的请求..."

            modify_message = {
                "role": "assistant",
                "content": modify_msg,
                "metadata": {
                    "processing_time": 1.0,
                    "query_type": "modification_request",
                    "modifications_count": len(modifications)
                }
            }
            st.session_state.messages.append(modify_message)

        elif decision == 'regenerate':
            regen_msg = f"🔄 **重新生成请求已提交！**\n\n"
            regen_msg += f"🚀 **状态：** 正在从头开始重新分析您的问题...\n\n"
            regen_msg += f"⏳ 请稍候，系统正在重新生成查询和分析..."

            regen_message = {
                "role": "assistant",
                "content": regen_msg,
                "metadata": {
                    "processing_time": 1.0,
                    "query_type": "regeneration_request"
                }
            }
            st.session_state.messages.append(regen_message)

        # 显示成功反馈
        with status_placeholder:
            st.success(f"✅ {decision_names.get(decision, '决策')}请求已成功提交！")

        # 延迟一点时间再刷新，让用户看到反馈
        time.sleep(0.5)
        st.rerun()

    except Exception as e:
        # 详细的错误处理
        error_msg = f"❌ **处理{decision_names.get(decision, '决策')}请求时发生错误**\n\n"
        error_msg += f"🚫 **错误信息：** {str(e)}\n\n"
        error_msg += f"🔧 **建议解决方案：**\n"
        error_msg += f"1. 请稍候片刻后重试\n"
        error_msg += f"2. 检查LangGraph服务连接状态\n"
        error_msg += f"3. 如问题持续，请开始新的对话"

        error_message = {
            "role": "assistant",
            "content": error_msg,
            "metadata": {
                "processing_time": 0.1,
                "query_type": "error",
                "error_type": "human_review_processing"
            }
        }
        st.session_state.messages.append(error_message)

        st.error(f"🚫 处理失败：{str(e)}")
        st.rerun()

def handle_human_review_submission(thread_id: str, human_response: Dict):
    """处理Human Review提交"""

    try:
        with st.spinner("正在处理您的决策..."):
            # 使用人类响应恢复工作流
            result = resume_workflow_with_review(thread_id, human_response)

            if result.get('type') == 'error':
                st.error(f"恢复工作流失败：{result.get('content', '未知错误')}")
                return

            # 清理Human Review状态
            st.session_state.human_review_required = False
            st.session_state.human_review_thread_id = None
            st.session_state.human_review_data = None

            # 处理最终结果
            decision = human_response.get('decision', 'approve')

            if decision == 'approve':
                # 显示成功消息
                success_msg = "✅ 您的决策已提交，正在生成最终报告..."

                # 检查报告路径
                report_path = result.get('data', {}).get('report_path')
                if report_path:
                    st.session_state.latest_report_path = report_path
                    success_msg += f"\n\n📊 报告已生成：`{report_path}`"

                # 添加成功消息到聊天历史
                success_message = {
                    "role": "assistant",
                    "content": success_msg
                }
                st.session_state.messages.append(success_message)

            elif decision == 'modify':
                modify_msg = "✏️ 您的修改请求已提交，正在重新生成查询..."
                modify_message = {
                    "role": "assistant",
                    "content": modify_msg
                }
                st.session_state.messages.append(modify_message)

            elif decision == 'regenerate':
                regen_msg = "🔄 正在重新生成查询，请稍候..."
                regen_message = {
                    "role": "assistant",
                    "content": regen_msg
                }
                st.session_state.messages.append(regen_message)

            st.success("决策已提交！")
            st.rerun()

    except Exception as e:
        st.error(f"处理决策时出错：{str(e)}")

def render_report_access_button():
    """渲染报告访问按钮"""

    if 'latest_report_path' in st.session_state and st.session_state.latest_report_path:
        report_path = st.session_state.latest_report_path

        st.markdown("---")
        st.markdown("### 📊 查看报告")

        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown(f"📄 报告文件： `{report_path}`")

        with col2:
            if st.button("🔍 打开报告", use_container_width=True):
                open_local_report(report_path)

def open_local_report(report_path: str):
    """打开本地报告文件"""

    import os
    import subprocess
    import platform

    try:
        # 检查文件是否存在
        if not os.path.exists(report_path):
            st.error(f"报告文件不存在：{report_path}")
            return

        # 根据操作系统选择打开方式
        system = platform.system()

        if system == "Darwin":  # macOS
            subprocess.run(["open", report_path], check=True)
        elif system == "Windows":
            os.startfile(report_path)
        elif system == "Linux":
            subprocess.run(["xdg-open", report_path], check=True)
        else:
            st.warning(f"不支持的操作系统：{system}")
            return

        st.success("报告已在默认应用程序中打开！")

    except subprocess.CalledProcessError as e:
        st.error(f"打开报告失败：{str(e)}")
    except Exception as e:
        st.error(f"发生错误：{str(e)}")

def render_workflow_section():
    """渲染工作流可视化区域"""

    st.markdown("### 📊 执行流程图")

    # 工作流状态显示（简化版）


    # Mermaid流程图区域
    render_mermaid_graph()

def render_mermaid_graph():
    """渲染静态Mermaid流程图"""

    # 显示静态流程图
    mermaid_graph = get_default_mermaid_graph()
    st_mermaid(mermaid_graph, height=900)


def get_default_mermaid_graph():
    """获取基于真实LangGraph工作流的Mermaid流程图"""

    return """
graph TD
    START([Start]) --> INIT[initialize_session]
    INIT --> ANALYZE[analyze_question]
    ANALYZE --> GENERATE[generate_query]
    GENERATE --> EXECUTE[execute_script]

    EXECUTE --> VALIDATE[validate_results]
    EXECUTE --> ERROR[handle_error]
    EXECUTE --> GENERATE

    VALIDATE --> EXPLAIN[explain_results]
    VALIDATE --> GENERATE
    VALIDATE --> ERROR

    EXPLAIN --> REVIEW[human_review]

    REVIEW --> VIZ[generate_visualization]
    REVIEW --> GENERATE

    VIZ --> FINAL[finalize_workflow]
    FINAL --> END([END])
    ERROR --> END

    classDef startEnd fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef process fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef decision fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef error fill:#ffebee,stroke:#c62828,stroke-width:2px

    class START,END startEnd
    class INIT,ANALYZE,GENERATE,EXECUTE,VALIDATE,EXPLAIN,REVIEW,VIZ,FINAL process
    class ERROR error
"""



if __name__ == "__main__":
    main()