"""
聊天界面组件
提供可复用的聊天功能
"""

import streamlit as st
from typing import List, Dict, Any, Generator
import time

class ChatInterface:
    """聊天界面组件类"""

    def __init__(self):
        self.initialize_chat_state()

    def initialize_chat_state(self):
        """初始化聊天状态"""
        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = []

        if "chat_input_value" not in st.session_state:
            st.session_state.chat_input_value = ""

    def render(self, container_key: str = "main_chat"):
        """渲染聊天界面"""

        # 创建聊天容器
        chat_container = st.container()

        with chat_container:
            # 显示聊天历史
            self.render_chat_history()

            # 聊天输入
            self.render_chat_input()

    def render_chat_history(self):
        """渲染聊天历史"""
        for i, message in enumerate(st.session_state.chat_messages):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

                # 如果是助手消息，添加反馈按钮
                if message["role"] == "assistant":
                    self.render_feedback_buttons(i)

    def render_feedback_buttons(self, message_index: int):
        """渲染反馈按钮"""
        col1, col2, col3 = st.columns([1, 1, 6])

        with col1:
            if st.button("👍", key=f"like_{message_index}"):
                self.handle_feedback(message_index, "like")

        with col2:
            if st.button("👎", key=f"dislike_{message_index}"):
                self.handle_feedback(message_index, "dislike")

    def render_chat_input(self):
        """渲染聊天输入框"""

        # 使用最新的chat_input功能
        if prompt := st.chat_input(
            "请输入您的问题...",
            key="main_chat_input"
        ):
            self.handle_user_message(prompt)

    def handle_user_message(self, message: str):
        """处理用户消息"""

        # 添加用户消息
        self.add_message("user", message)

        # 显示用户消息
        with st.chat_message("user"):
            st.markdown(message)

        # 生成并显示助手响应
        self.generate_assistant_response(message)

    def add_message(self, role: str, content: str, metadata: Dict = None):
        """添加消息到聊天历史"""
        message = {
            "role": role,
            "content": content,
            "timestamp": time.time(),
            "metadata": metadata or {}
        }
        st.session_state.chat_messages.append(message)

    def generate_assistant_response(self, user_message: str):
        """生成助手响应"""

        with st.chat_message("assistant"):
            # 显示思考过程
            thinking_container = st.status("思考中...", expanded=True)

            with thinking_container:
                thinking_steps = [
                    "🔍 分析问题内容",
                    "📊 查找相关数据",
                    "🧠 生成回答策略",
                    "✨ 准备响应"
                ]

                for step in thinking_steps:
                    st.write(step)
                    time.sleep(0.5)

            thinking_container.update(label="思考完成", state="complete", expanded=False)

            # 流式响应
            response_text = self.get_mock_response(user_message)
            response_container = st.empty()

            displayed_text = ""
            for char in response_text:
                displayed_text += char
                response_container.markdown(displayed_text + "▌")
                time.sleep(0.01)

            # 完成响应
            response_container.markdown(displayed_text)

            # 添加助手消息到历史
            self.add_message("assistant", displayed_text)

        # 更新界面
        st.rerun()

    def get_mock_response(self, user_message: str) -> str:
        """获取模拟响应"""
        # 这里将替换为实际的LangGraph集成
        return f"""我收到了您的问题："{user_message}"

让我为您分析一下相关数据：

📊 **数据查询结果**
- 找到相关记录：1,234条
- 数据时间范围：2024年1月-12月
- 主要趋势：呈上升趋势

🔍 **关键洞察**
1. 数据显示明显的季节性模式
2. 第三季度表现最佳
3. 建议关注10月的异常峰值

需要我生成具体的图表来展示这些数据吗？"""

    def handle_feedback(self, message_index: int, feedback_type: str):
        """处理用户反馈"""
        if message_index < len(st.session_state.chat_messages):
            message = st.session_state.chat_messages[message_index]
            message["metadata"]["feedback"] = feedback_type
            st.toast(f"感谢您的反馈！({feedback_type})")

    def clear_chat(self):
        """清空聊天历史"""
        st.session_state.chat_messages = []
        st.rerun()

    def export_chat(self) -> str:
        """导出聊天记录"""
        chat_export = []
        for message in st.session_state.chat_messages:
            role = "用户" if message["role"] == "user" else "助手"
            chat_export.append(f"{role}: {message['content']}\n")

        return "\n".join(chat_export)

def render_chat_message(role: str, content: str, metadata: Dict[str, Any] = None):
    """渲染单条聊天消息"""
    with st.chat_message(role):
        st.markdown(content)

        # 如果有元数据，显示额外信息
        if metadata:
            if metadata.get("timestamp"):
                st.caption(f"时间: {metadata['timestamp']}")

def render_chat_history(messages: List[Dict[str, Any]]):
    """渲染聊天历史"""
    for message in messages:
        render_chat_message(
            role=message.get("role", "user"),
            content=message.get("content", ""),
            metadata=message.get("metadata", {})
        )

def create_chat_input(placeholder: str = "请输入您的问题...") -> str:
    """创建聊天输入框"""
    return st.chat_input(placeholder)

def render_typing_indicator():
    """显示正在输入指示器"""
    with st.chat_message("assistant"):
        st.markdown("正在思考中...")
        return st.empty()

def render_error_message(error: str):
    """渲染错误消息"""
    with st.chat_message("assistant"):
        st.error(f"出现错误: {error}")

def render_system_message(message: str):
    """渲染系统消息"""
    with st.chat_message("assistant"):
        st.info(message)