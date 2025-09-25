"""
Session State管理模块
用于管理Streamlit应用的全局状态
"""

import streamlit as st
from typing import Dict, Any, List

def initialize_session_state():
    """初始化session state变量"""

    # 聊天相关状态
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if "current_conversation" not in st.session_state:
        st.session_state.current_conversation = []

    # 工作流状态
    if "workflow_stage" not in st.session_state:
        st.session_state.workflow_stage = "idle"

    if "workflow_progress" not in st.session_state:
        st.session_state.workflow_progress = 0

    if "workflow_steps" not in st.session_state:
        st.session_state.workflow_steps = []

    # 分析结果状态
    if "analysis_results" not in st.session_state:
        st.session_state.analysis_results = []

    if "current_query" not in st.session_state:
        st.session_state.current_query = ""

    if "generated_sql" not in st.session_state:
        st.session_state.generated_sql = ""

    # 系统连接状态
    if "langgraph_connected" not in st.session_state:
        st.session_state.langgraph_connected = False

    if "bigquery_connected" not in st.session_state:
        st.session_state.bigquery_connected = False

    # 用户设置
    if "user_preferences" not in st.session_state:
        st.session_state.user_preferences = {
            "theme": "light",
            "language": "zh",
            "chart_type": "auto",
            "max_results": 1000
        }

    # 错误处理
    if "error_messages" not in st.session_state:
        st.session_state.error_messages = []

def clear_chat_history():
    """清空聊天历史"""
    st.session_state.chat_history = []
    st.session_state.current_conversation = []

def add_chat_message(role: str, content: str, metadata: Dict[str, Any] = None):
    """添加聊天消息"""
    message = {
        "role": role,
        "content": content,
        "timestamp": st.session_state.get("current_time"),
        "metadata": metadata or {}
    }

    st.session_state.current_conversation.append(message)

def save_conversation():
    """保存当前对话到历史"""
    if st.session_state.current_conversation:
        conversation = {
            "messages": st.session_state.current_conversation.copy(),
            "timestamp": st.session_state.get("current_time"),
            "summary": generate_conversation_summary()
        }
        st.session_state.chat_history.append(conversation)
        st.session_state.current_conversation = []

def generate_conversation_summary() -> str:
    """生成对话摘要"""
    if not st.session_state.current_conversation:
        return "空对话"

    user_messages = [
        msg["content"] for msg in st.session_state.current_conversation
        if msg["role"] == "user"
    ]

    if user_messages:
        return user_messages[0][:50] + "..." if len(user_messages[0]) > 50 else user_messages[0]

    return "系统对话"

def update_workflow_progress(stage: str, progress: int, steps: List[str] = None):
    """更新工作流进度"""
    st.session_state.workflow_stage = stage
    st.session_state.workflow_progress = progress

    if steps:
        st.session_state.workflow_steps = steps

def add_error_message(error: str, error_type: str = "general"):
    """添加错误消息"""
    error_entry = {
        "message": error,
        "type": error_type,
        "timestamp": st.session_state.get("current_time")
    }
    st.session_state.error_messages.append(error_entry)

    # 保持错误消息列表在合理大小
    if len(st.session_state.error_messages) > 10:
        st.session_state.error_messages = st.session_state.error_messages[-10:]

def get_user_preference(key: str, default=None):
    """获取用户偏好设置"""
    return st.session_state.user_preferences.get(key, default)

def set_user_preference(key: str, value: Any):
    """设置用户偏好"""
    st.session_state.user_preferences[key] = value