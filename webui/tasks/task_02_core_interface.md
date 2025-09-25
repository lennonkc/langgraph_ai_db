# Task 02: 核心界面

## 任务概述
开发AI聊天界面和工作流可视化组件，实现用户与AI助手的核心交互功能。

## 实施目标
- 实现基于st.chat_message的对话界面
- 开发工作流进度可视化
- 集成实时状态更新
- 提供流式响应体验

## 技术实现

### 1. AI聊天界面 (pages/1_💬_Chat.py)

```python
"""
AI聊天界面页面
使用Streamlit最新的chat功能实现对话体验
"""

import streamlit as st
import time
from components.chat_interface import ChatInterface
from components.workflow_display import WorkflowDisplay
from utils.session_manager import (
    initialize_session_state,
    add_chat_message,
    get_user_preference
)

# 页面配置
st.set_page_config(
    page_title="AI聊天",
    page_icon="💬",
    layout="wide"
)

def main():
    """聊天页面主逻辑"""

    # 初始化状态
    initialize_session_state()

    # 页面标题
    st.title("💬 AI数据库分析助手")

    # 创建布局
    chat_col, workflow_col = st.columns([2, 1])

    with chat_col:
        st.markdown("### 🤖 对话区域")
        render_chat_interface()

    with workflow_col:
        st.markdown("### 📊 工作流状态")
        WorkflowDisplay().render()

def render_chat_interface():
    """渲染聊天界面"""

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

请告诉我您想了解什么数据？"""
        }
        st.session_state.messages.append(welcome_message)

    # 显示聊天历史
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

                # 如果是助手消息且包含特殊内容，显示额外组件
                if message["role"] == "assistant" and message.get("metadata"):
                    render_message_extras(message["metadata"])

    # 聊天输入
    if prompt := st.chat_input("请输入您的问题..."):
        handle_user_input(prompt)

def handle_user_input(prompt: str):
    """处理用户输入"""

    # 添加用户消息到聊天历史
    user_message = {"role": "user", "content": prompt}
    st.session_state.messages.append(user_message)

    # 显示用户消息
    with st.chat_message("user"):
        st.markdown(prompt)

    # 显示助手响应
    with st.chat_message("assistant"):
        # 显示思考状态
        with st.status("正在分析您的问题...", expanded=True) as status:
            st.write("🔍 理解问题意图")
            time.sleep(1)
            st.write("🧠 生成分析计划")
            time.sleep(1)
            st.write("📊 准备响应")
            time.sleep(1)
            status.update(label="分析完成！", state="complete", expanded=False)

        # 模拟流式响应
        response = generate_assistant_response(prompt)
        response_placeholder = st.empty()

        # 流式输出响应
        displayed_response = ""
        for chunk in response:
            displayed_response += chunk
            response_placeholder.markdown(displayed_response + "▌")
            time.sleep(0.02)

        # 完成响应
        response_placeholder.markdown(displayed_response)

        # 添加助手消息到历史
        assistant_message = {
            "role": "assistant",
            "content": displayed_response,
            "metadata": {
                "query_type": classify_query(prompt),
                "processing_time": 3.0
            }
        }
        st.session_state.messages.append(assistant_message)

    # 重新运行以更新界面
    st.rerun()

def generate_assistant_response(prompt: str) -> str:
    """生成助手响应 (模拟)"""
    # 这里将替换为实际的LangGraph集成
    response_parts = [
        "我理解您想要",
        f'查询关于"{prompt}"的信息。',
        "\n\n让我为您分析一下：\n\n",
        "📊 **数据概览**\n",
        "- 相关数据表：customers, orders, products\n",
        "- 时间范围：最近30天\n",
        "- 数据量：约10,000条记录\n\n",
        "🔍 **分析建议**\n",
        "基于您的问题，我建议从以下角度分析：\n",
        "1. 按时间趋势查看数据变化\n",
        "2. 按分类维度进行对比分析\n",
        "3. 识别异常值和关键模式\n\n",
        "您希望我继续进行具体的数据查询吗？"
    ]

    for part in response_parts:
        yield part

def classify_query(prompt: str) -> str:
    """分类用户查询类型"""
    prompt_lower = prompt.lower()

    if any(word in prompt_lower for word in ["趋势", "变化", "时间"]):
        return "trend_analysis"
    elif any(word in prompt_lower for word in ["对比", "比较", "差异"]):
        return "comparison"
    elif any(word in prompt_lower for word in ["总和", "求和", "统计"]):
        return "aggregation"
    else:
        return "general"

def render_message_extras(metadata: dict):
    """渲染消息的额外组件"""

    query_type = metadata.get("query_type")
    processing_time = metadata.get("processing_time")

    col1, col2 = st.columns(2)

    with col1:
        if query_type:
            st.caption(f"🏷️ 查询类型: {query_type}")

    with col2:
        if processing_time:
            st.caption(f"⏱️ 处理时间: {processing_time:.1f}s")

if __name__ == "__main__":
    main()
```

### 2. 聊天接口组件 (components/chat_interface.py)

```python
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
```

### 3. 工作流显示组件 (components/workflow_display.py)

```python
"""
工作流可视化组件
显示LangGraph工作流的执行状态
"""

import streamlit as st
from typing import List, Dict, Any
import time

class WorkflowDisplay:
    """工作流显示组件"""

    def __init__(self):
        self.initialize_workflow_state()

    def initialize_workflow_state(self):
        """初始化工作流状态"""
        if "workflow_status" not in st.session_state:
            st.session_state.workflow_status = "idle"

        if "workflow_steps" not in st.session_state:
            st.session_state.workflow_steps = []

        if "current_step" not in st.session_state:
            st.session_state.current_step = 0

    def render(self):
        """渲染工作流显示"""

        # 工作流状态概览
        self.render_status_overview()

        # 步骤详情
        self.render_step_details()

        # 实时更新按钮
        if st.button("🔄 刷新状态", help="手动刷新工作流状态"):
            self.refresh_workflow_status()

    def render_status_overview(self):
        """渲染状态概览"""

        status = st.session_state.workflow_status
        current_step = st.session_state.current_step
        total_steps = len(st.session_state.workflow_steps)

        # 状态指示器
        if status == "idle":
            st.info("🟡 等待任务")
        elif status == "running":
            st.success("🟢 正在执行")
        elif status == "completed":
            st.success("✅ 执行完成")
        elif status == "error":
            st.error("❌ 执行错误")

        # 进度条
        if total_steps > 0:
            progress = current_step / total_steps
            st.progress(progress, text=f"进度: {current_step}/{total_steps}")

    def render_step_details(self):
        """渲染步骤详情"""

        if not st.session_state.workflow_steps:
            st.write("📋 暂无工作流步骤")
            return

        st.write("### 📋 执行步骤")

        for i, step in enumerate(st.session_state.workflow_steps):
            self.render_single_step(i, step)

    def render_single_step(self, index: int, step: Dict[str, Any]):
        """渲染单个步骤"""

        current_step = st.session_state.current_step
        step_name = step.get("name", f"步骤 {index + 1}")
        step_status = step.get("status", "pending")
        step_description = step.get("description", "")
        step_duration = step.get("duration", 0)

        # 步骤容器
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                # 步骤状态图标
                if index < current_step:
                    icon = "✅"
                    status_text = "已完成"
                elif index == current_step:
                    icon = "🔄"
                    status_text = "进行中"
                else:
                    icon = "⏳"
                    status_text = "待执行"

                st.write(f"{icon} **{step_name}**")
                if step_description:
                    st.caption(step_description)

            with col2:
                st.write(status_text)

            with col3:
                if step_duration > 0:
                    st.write(f"{step_duration:.1f}s")

            # 如果是当前步骤且正在执行，显示动画
            if index == current_step and st.session_state.workflow_status == "running":
                with st.spinner("执行中..."):
                    time.sleep(0.1)

            st.divider()

    def start_workflow(self, steps: List[Dict[str, Any]]):
        """启动工作流"""
        st.session_state.workflow_steps = steps
        st.session_state.current_step = 0
        st.session_state.workflow_status = "running"
        st.rerun()

    def update_step_status(self, step_index: int, status: str, duration: float = None):
        """更新步骤状态"""
        if step_index < len(st.session_state.workflow_steps):
            step = st.session_state.workflow_steps[step_index]
            step["status"] = status

            if duration is not None:
                step["duration"] = duration

            if status == "completed":
                st.session_state.current_step = step_index + 1

    def complete_workflow(self):
        """完成工作流"""
        st.session_state.workflow_status = "completed"
        st.session_state.current_step = len(st.session_state.workflow_steps)

    def error_workflow(self, error_message: str):
        """工作流错误"""
        st.session_state.workflow_status = "error"
        st.error(f"工作流执行错误: {error_message}")

    def refresh_workflow_status(self):
        """刷新工作流状态"""
        # 这里将集成实际的LangGraph状态查询
        st.toast("状态已刷新")
        st.rerun()

    def reset_workflow(self):
        """重置工作流"""
        st.session_state.workflow_steps = []
        st.session_state.current_step = 0
        st.session_state.workflow_status = "idle"
        st.rerun()

# 示例工作流步骤
SAMPLE_WORKFLOW_STEPS = [
    {
        "name": "问题分析",
        "description": "分析用户问题的意图和要求",
        "status": "pending"
    },
    {
        "name": "数据库查询",
        "description": "生成并执行SQL查询",
        "status": "pending"
    },
    {
        "name": "结果处理",
        "description": "处理查询结果并准备可视化",
        "status": "pending"
    },
    {
        "name": "图表生成",
        "description": "生成数据可视化图表",
        "status": "pending"
    },
    {
        "name": "响应生成",
        "description": "生成最终的分析报告",
        "status": "pending"
    }
]
```

## 验收标准

### 功能验收
- [ ] 聊天界面正常显示和交互
- [ ] 消息历史正确保存和显示
- [ ] 流式响应效果流畅
- [ ] 工作流状态实时更新
- [ ] 用户反馈功能正常

### 技术验收
- [ ] 使用最新的st.chat_message API
- [ ] Session State管理正确
- [ ] 组件化设计合理
- [ ] 错误处理完善
- [ ] 性能表现良好

### 用户体验验收
- [ ] 对话交互自然流畅
- [ ] 状态反馈及时准确
- [ ] 界面布局美观易用
- [ ] 响应时间合理
- [ ] 操作逻辑直观

## 后续任务
完成此任务后，进入**Task 03: 功能集成**阶段，将实际的LangGraph工作流集成到界面中。