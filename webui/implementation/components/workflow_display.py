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

        # 控制按钮
        self.render_control_buttons()

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
            self.render_demo_workflow_button()
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
                elif index == current_step and st.session_state.workflow_status == "running":
                    icon = "🔄"
                    status_text = "进行中"
                elif index == current_step:
                    icon = "🟡"
                    status_text = "当前步骤"
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

    def render_control_buttons(self):
        """渲染控制按钮"""
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🔄 刷新状态", help="手动刷新工作流状态"):
                self.refresh_workflow_status()

        with col2:
            if st.button("🗑️ 重置工作流", help="重置工作流状态"):
                self.reset_workflow()

        with col3:
            if st.button("▶️ 启动演示", help="启动演示工作流"):
                self.start_demo_workflow()

    def render_demo_workflow_button(self):
        """渲染演示工作流按钮"""
        if st.button("🚀 启动演示工作流", help="启动一个演示工作流以查看效果"):
            self.start_demo_workflow()

    def start_workflow(self, steps: List[Dict[str, Any]]):
        """启动工作流"""
        st.session_state.workflow_steps = steps
        st.session_state.current_step = 0
        st.session_state.workflow_status = "running"
        st.rerun()

    def start_demo_workflow(self):
        """启动演示工作流"""
        demo_steps = SAMPLE_WORKFLOW_STEPS.copy()
        self.start_workflow(demo_steps)
        st.toast("演示工作流已启动！")

    def update_step_status(self, step_index: int, status: str, duration: float = None):
        """更新步骤状态"""
        if step_index < len(st.session_state.workflow_steps):
            step = st.session_state.workflow_steps[step_index]
            step["status"] = status

            if duration is not None:
                step["duration"] = duration

            if status == "completed":
                st.session_state.current_step = step_index + 1

                # 如果是最后一个步骤，完成工作流
                if step_index + 1 >= len(st.session_state.workflow_steps):
                    self.complete_workflow()

    def complete_workflow(self):
        """完成工作流"""
        st.session_state.workflow_status = "completed"
        st.session_state.current_step = len(st.session_state.workflow_steps)
        st.toast("🎉 工作流执行完成！")

    def error_workflow(self, error_message: str):
        """工作流错误"""
        st.session_state.workflow_status = "error"
        st.error(f"工作流执行错误: {error_message}")

    def refresh_workflow_status(self):
        """刷新工作流状态"""
        # 这里将集成实际的LangGraph状态查询
        if st.session_state.workflow_status == "running":
            # 模拟自动推进工作流
            current = st.session_state.current_step
            if current < len(st.session_state.workflow_steps):
                # 模拟步骤完成
                import random
                duration = random.uniform(1.0, 3.0)
                self.update_step_status(current, "completed", duration)
                st.rerun()

        st.toast("状态已刷新")

    def reset_workflow(self):
        """重置工作流"""
        st.session_state.workflow_steps = []
        st.session_state.current_step = 0
        st.session_state.workflow_status = "idle"
        st.toast("工作流已重置")
        st.rerun()

def render_workflow_progress(current_stage: str, progress: int, total_steps: int = 100):
    """渲染工作流进度条"""
    st.progress(progress / total_steps)
    st.caption(f"当前阶段: {current_stage} ({progress}/{total_steps})")

def render_workflow_steps(steps: List[str], current_step: int = 0):
    """渲染工作流步骤列表"""
    for i, step in enumerate(steps):
        if i < current_step:
            st.success(f"✅ {step}")
        elif i == current_step:
            st.info(f"🔄 {step}")
        else:
            st.write(f"⏳ {step}")

def render_workflow_status(stage: str, status: str = "running"):
    """渲染工作流状态"""
    status_colors = {
        "idle": "🔵",
        "running": "🟡",
        "completed": "🟢",
        "error": "🔴",
        "paused": "🟠"
    }

    color = status_colors.get(status, "🔵")
    st.markdown(f"{color} **状态**: {stage}")

def create_workflow_container():
    """创建工作流显示容器"""
    container = st.container()
    with container:
        st.markdown("### 🔄 工作流状态")
    return container

def render_step_details(step_name: str, step_data: Dict[str, Any]):
    """渲染步骤详细信息"""
    with st.expander(f"📋 {step_name}"):
        if step_data.get("input"):
            st.markdown("**输入:**")
            st.code(step_data["input"])

        if step_data.get("output"):
            st.markdown("**输出:**")
            st.code(step_data["output"])

        if step_data.get("duration"):
            st.markdown(f"**执行时间:** {step_data['duration']}s")

def render_workflow_graph():
    """渲染工作流图表（占位符）"""
    st.markdown("### 🗂️ 工作流图")
    st.info("工作流可视化图表将在后续版本中实现")

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