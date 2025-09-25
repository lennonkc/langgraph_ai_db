# Task 01: 基础搭建

## 任务概述
设置Streamlit项目基础架构，包括项目初始化、环境配置和多页面布局设计。

## 实施目标
- 创建Streamlit项目结构
- 配置开发环境和依赖
- 实现多页面应用架构
- 设置基础导航和布局

## 技术实现

### 1. 项目结构创建

```bash
# 创建项目目录结构
webui/implementation/
├── pages/
│   ├── 1_💬_Chat.py
│   ├── 2_📊_Analysis.py
│   └── 3_🔧_Settings.py
├── components/
│   ├── __init__.py
│   ├── chat_interface.py
│   ├── workflow_display.py
│   └── chart_renderer.py
├── utils/
│   ├── __init__.py
│   ├── langgraph_integration.py
│   └── session_manager.py
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml
├── requirements.txt
├── main.py
└── README.md
```

### 2. 依赖配置 (requirements.txt)

```txt
# 核心框架
streamlit>=1.30.0

# 数据处理
pandas>=2.0.0
numpy>=1.24.0

# 可视化
plotly>=5.17.0
altair>=5.2.0

# LangGraph集成
langgraph>=0.0.40
langchain>=0.1.0

# 数据库连接
google-cloud-bigquery>=3.13.0

# 其他工具
python-dotenv>=1.0.0
```

### 3. Streamlit配置 (.streamlit/config.toml)

```toml
[global]
# 开发模式配置
developmentMode = true

[server]
# 服务器配置
port = 8501
address = "localhost"
headless = false
runOnSave = true
allowRunOnSave = true

[browser]
# 浏览器配置
gatherUsageStats = false
showErrorDetails = true

[theme]
# 主题配置
primaryColor = "#FF6B6B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"

[client]
# 客户端配置
showSidebarNavigation = true
```

### 4. 主应用入口 (main.py)

```python
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
```

### 5. Session State管理器 (utils/session_manager.py)

```python
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
```

## 验收标准

### 功能验收
- [ ] Streamlit应用能够正常启动
- [ ] 多页面导航工作正常
- [ ] Session State初始化正确
- [ ] 配置文件加载成功
- [ ] 项目结构符合规范

### 技术验收
- [ ] 所有Python文件无语法错误
- [ ] requirements.txt包含所有必要依赖
- [ ] .streamlit/config.toml配置正确
- [ ] Session State管理功能完整
- [ ] 代码符合PEP8规范

### 用户体验验收
- [ ] 页面加载速度 < 3秒
- [ ] 导航操作流畅
- [ ] 界面布局合理
- [ ] 错误提示友好
- [ ] 响应式设计适配

## 后续任务
完成此任务后，进入**Task 02: 核心界面**开发阶段。