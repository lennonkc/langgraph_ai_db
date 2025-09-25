"""
LangGraph AI数据库分析师 - Streamlit前端
主应用入口文件
"""

import streamlit as st
from utils.session_manager import initialize_session_state

# 页面配置
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

    # 侧边栏导航
    with st.sidebar:
        st.title("🤖 AI数据库分析师")
        st.markdown("---")

        # 导航说明
        st.markdown("""
        ### 📖 使用指南

        **💬 Chat**: 与AI助手对话
        - 自然语言提问
        - 获取数据洞察

        **📊 Analysis**: 查看分析结果
        - 数据可视化
        - 查询历史

        **🔧 Settings**: 系统设置
        - 数据源配置
        - 偏好设置
        """)

        st.markdown("---")

        # 系统状态
        if st.session_state.get('langgraph_connected', False):
            st.success("🟢 LangGraph已连接")
        else:
            st.error("🔴 LangGraph未连接")

        if st.session_state.get('bigquery_connected', False):
            st.success("🟢 BigQuery已连接")
        else:
            st.warning("🟡 BigQuery未连接")

    # 主内容区域
    st.title("🏠 欢迎使用AI数据库分析师")

    st.markdown("""
    ### 🚀 快速开始

    1. **💬 进入聊天页面** - 开始与AI助手对话
    2. **📝 输入您的问题** - 使用自然语言描述数据需求
    3. **📊 查看分析结果** - 获取智能生成的图表和洞察
    """)

    # 功能概览卡片
    col1, col2, col3 = st.columns(3)

    with col1:
        st.info("""
        **💬 智能对话**

        - 自然语言查询
        - 上下文理解
        - 实时响应
        """)

    with col2:
        st.info("""
        **📊 数据可视化**

        - 多种图表类型
        - 交互式展示
        - 一键导出
        """)

    with col3:
        st.info("""
        **🔧 工作流程**

        - 可视化流程
        - 步骤跟踪
        - 错误处理
        """)

    # 最近使用
    if st.session_state.get('chat_history'):
        st.markdown("### 📝 最近对话")
        recent_chats = st.session_state.chat_history[-3:]

        for i, chat in enumerate(recent_chats):
            with st.expander(f"对话 {len(st.session_state.chat_history) - len(recent_chats) + i + 1}"):
                st.markdown(f"**用户:** {chat.get('user_message', 'N/A')}")
                st.markdown(f"**助手:** {chat.get('assistant_message', 'N/A')[:100]}...")

if __name__ == "__main__":
    main()