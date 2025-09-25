# Task 03: 功能集成

## 任务概述
集成LangGraph工作流、数据可视化组件和人工审查界面，实现完整的AI数据分析功能。

## 实施目标
- 直接集成现有LangGraph工作流
- 实现数据可视化组件库
- 开发人工审查和反馈机制
- 建立数据处理管道

## 技术实现

### 1. LangGraph集成模块 (utils/langgraph_integration.py)

```python
"""
LangGraph工作流集成模块
直接调用现有的LangGraph数据分析工作流
"""

import asyncio
import json
from typing import Dict, Any, Optional, Generator, List
from pathlib import Path
import sys

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

# 导入现有的LangGraph工作流
try:
    from workflow.main import create_graph, WorkflowConfig
    from workflow.nodes.question_analyzer import QuestionAnalyzer
    from workflow.nodes.query_generator import QueryGenerator
    from workflow.nodes.validator import Validator
    from workflow.nodes.visualizer import Visualizer
    LANGGRAPH_AVAILABLE = True
except ImportError as e:
    print(f"Warning: LangGraph modules not available: {e}")
    LANGGRAPH_AVAILABLE = False

import streamlit as st

class LangGraphIntegration:
    """LangGraph工作流集成类"""

    def __init__(self):
        self.graph = None
        self.config = None
        self.initialize_workflow()

    def initialize_workflow(self) -> bool:
        """初始化LangGraph工作流"""
        try:
            if not LANGGRAPH_AVAILABLE:
                st.error("LangGraph工作流模块未找到，请检查项目结构")
                return False

            # 创建工作流配置
            self.config = WorkflowConfig(
                bigquery_project_id="your-project-id",
                enable_human_feedback=True,
                max_retries=3
            )

            # 创建工作流图
            self.graph = create_graph(self.config)

            st.session_state.langgraph_connected = True
            return True

        except Exception as e:
            st.error(f"LangGraph初始化失败: {str(e)}")
            st.session_state.langgraph_connected = False
            return False

    async def process_query(
        self,
        user_question: str,
        session_id: str = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        处理用户查询
        使用Generator实现流式响应
        """

        if not self.graph:
            yield {
                "type": "error",
                "content": "LangGraph工作流未初始化",
                "step": "initialization"
            }
            return

        try:
            # 构建输入
            workflow_input = {
                "question": user_question,
                "session_id": session_id or "default",
                "user_preferences": st.session_state.get("user_preferences", {}),
                "context": {
                    "previous_queries": self.get_recent_queries(),
                    "user_feedback": self.get_user_feedback()
                }
            }

            yield {
                "type": "workflow_start",
                "content": "开始分析问题",
                "step": "start"
            }

            # 执行工作流
            async for event in self.graph.astream(workflow_input):
                node_name = list(event.keys())[0]
                node_output = event[node_name]

                # 转换工作流事件为前端可用格式
                yield self.transform_workflow_event(node_name, node_output)

        except Exception as e:
            yield {
                "type": "error",
                "content": f"工作流执行错误: {str(e)}",
                "step": "execution",
                "error_details": str(e)
            }

    def transform_workflow_event(self, node_name: str, node_output: Dict) -> Dict[str, Any]:
        """转换工作流事件为前端格式"""

        event_mappings = {
            "question_analyzer": {
                "type": "analysis",
                "step": "question_analysis",
                "title": "🔍 问题分析"
            },
            "query_generator": {
                "type": "generation",
                "step": "query_generation",
                "title": "📝 SQL生成"
            },
            "query_executor": {
                "type": "execution",
                "step": "query_execution",
                "title": "⚡ 查询执行"
            },
            "validator": {
                "type": "validation",
                "step": "validation",
                "title": "✅ 结果验证"
            },
            "visualizer": {
                "type": "visualization",
                "step": "visualization",
                "title": "📊 数据可视化"
            }
        }

        mapping = event_mappings.get(node_name, {
            "type": "unknown",
            "step": node_name,
            "title": f"📋 {node_name}"
        })

        return {
            **mapping,
            "content": node_output.get("output", ""),
            "data": node_output,
            "timestamp": node_output.get("timestamp"),
            "success": node_output.get("success", True)
        }

    def get_recent_queries(self) -> List[Dict]:
        """获取最近的查询历史"""
        chat_history = st.session_state.get("chat_history", [])
        return chat_history[-5:]  # 最近5次对话

    def get_user_feedback(self) -> Dict:
        """获取用户反馈信息"""
        return st.session_state.get("user_feedback", {})

    def validate_connection(self) -> bool:
        """验证LangGraph连接状态"""
        return self.graph is not None and LANGGRAPH_AVAILABLE

class StreamlitWorkflowRunner:
    """Streamlit环境下的工作流运行器"""

    def __init__(self):
        self.integration = LangGraphIntegration()

    def run_query_workflow(self, question: str, session_id: str = None):
        """在Streamlit中运行查询工作流"""

        # 更新工作流状态
        st.session_state.workflow_status = "running"
        st.session_state.current_step = 0

        # 创建状态容器
        status_container = st.empty()
        progress_container = st.empty()
        result_container = st.empty()

        try:
            # 运行异步工作流
            workflow_generator = asyncio.run(
                self.integration.process_query(question, session_id)
            )

            results = []
            step_count = 0

            for event in workflow_generator:
                step_count += 1

                # 更新状态显示
                with status_container.container():
                    st.write(f"**{event.get('title', 'Processing')}**")
                    st.write(event.get('content', ''))

                # 更新进度
                with progress_container.container():
                    # 估算总步骤数为5
                    progress = min(step_count / 5, 1.0)
                    st.progress(progress)

                # 收集结果
                results.append(event)

                # 如果是错误，提前结束
                if event.get('type') == 'error':
                    st.session_state.workflow_status = "error"
                    break

                # 短暂延迟以显示进度
                import time
                time.sleep(0.5)

            # 显示最终结果
            if results:
                self.display_workflow_results(results, result_container)

            # 更新完成状态
            st.session_state.workflow_status = "completed"

        except Exception as e:
            st.session_state.workflow_status = "error"
            st.error(f"工作流执行失败: {str(e)}")

    def display_workflow_results(self, results: List[Dict], container):
        """显示工作流结果"""

        with container.container():
            st.markdown("### 🎯 分析结果")

            # 显示各个步骤的结果
            for result in results:
                if result.get('type') in ['analysis', 'generation', 'execution', 'visualization']:
                    with st.expander(result.get('title', '结果')):
                        st.write(result.get('content', ''))

                        # 如果有数据，显示详情
                        if result.get('data'):
                            st.json(result['data'])
```

### 2. 数据可视化组件 (components/chart_renderer.py)

```python
"""
数据可视化组件
支持多种图表类型和交互功能
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import altair as alt
from typing import Dict, Any, Optional, List
import json

class ChartRenderer:
    """图表渲染组件"""

    def __init__(self):
        self.supported_charts = [
            "line", "bar", "scatter", "pie", "histogram",
            "box", "violin", "heatmap", "treemap", "sunburst"
        ]

    def render_chart(
        self,
        data: pd.DataFrame,
        chart_type: str,
        config: Dict[str, Any],
        container_key: str = "main_chart"
    ):
        """渲染图表"""

        if data.empty:
            st.warning("📊 暂无数据可显示")
            return

        try:
            # 根据图表类型选择渲染方法
            if chart_type == "line":
                chart = self.create_line_chart(data, config)
            elif chart_type == "bar":
                chart = self.create_bar_chart(data, config)
            elif chart_type == "scatter":
                chart = self.create_scatter_chart(data, config)
            elif chart_type == "pie":
                chart = self.create_pie_chart(data, config)
            elif chart_type == "histogram":
                chart = self.create_histogram(data, config)
            elif chart_type == "heatmap":
                chart = self.create_heatmap(data, config)
            else:
                st.error(f"不支持的图表类型: {chart_type}")
                return

            # 显示图表
            st.plotly_chart(chart, use_container_width=True, key=container_key)

            # 显示图表配置选项
            self.render_chart_controls(data, chart_type, config)

        except Exception as e:
            st.error(f"图表渲染错误: {str(e)}")

    def create_line_chart(self, data: pd.DataFrame, config: Dict) -> go.Figure:
        """创建折线图"""

        x_col = config.get('x_column')
        y_col = config.get('y_column')
        color_col = config.get('color_column')

        if not x_col or not y_col:
            # 自动选择列
            numeric_cols = data.select_dtypes(include=['number']).columns.tolist()
            x_col = x_col or data.columns[0]
            y_col = y_col or (numeric_cols[0] if numeric_cols else data.columns[1])

        fig = px.line(
            data,
            x=x_col,
            y=y_col,
            color=color_col,
            title=config.get('title', f'{y_col} 趋势图'),
            labels=config.get('labels', {}),
            template='plotly_white'
        )

        fig.update_layout(
            height=500,
            showlegend=True,
            hovermode='x unified'
        )

        return fig

    def create_bar_chart(self, data: pd.DataFrame, config: Dict) -> go.Figure:
        """创建柱状图"""

        x_col = config.get('x_column')
        y_col = config.get('y_column')
        color_col = config.get('color_column')

        fig = px.bar(
            data,
            x=x_col,
            y=y_col,
            color=color_col,
            title=config.get('title', f'{y_col} 分布图'),
            labels=config.get('labels', {}),
            template='plotly_white'
        )

        fig.update_layout(height=500)
        return fig

    def create_scatter_chart(self, data: pd.DataFrame, config: Dict) -> go.Figure:
        """创建散点图"""

        x_col = config.get('x_column')
        y_col = config.get('y_column')
        size_col = config.get('size_column')
        color_col = config.get('color_column')

        fig = px.scatter(
            data,
            x=x_col,
            y=y_col,
            size=size_col,
            color=color_col,
            title=config.get('title', f'{x_col} vs {y_col}'),
            labels=config.get('labels', {}),
            template='plotly_white'
        )

        fig.update_layout(height=500)
        return fig

    def create_pie_chart(self, data: pd.DataFrame, config: Dict) -> go.Figure:
        """创建饼图"""

        names_col = config.get('names_column')
        values_col = config.get('values_column')

        fig = px.pie(
            data,
            names=names_col,
            values=values_col,
            title=config.get('title', '分布饼图'),
            template='plotly_white'
        )

        fig.update_layout(height=500)
        return fig

    def create_histogram(self, data: pd.DataFrame, config: Dict) -> go.Figure:
        """创建直方图"""

        x_col = config.get('x_column')
        color_col = config.get('color_column')

        fig = px.histogram(
            data,
            x=x_col,
            color=color_col,
            title=config.get('title', f'{x_col} 分布直方图'),
            labels=config.get('labels', {}),
            template='plotly_white'
        )

        fig.update_layout(height=500)
        return fig

    def create_heatmap(self, data: pd.DataFrame, config: Dict) -> go.Figure:
        """创建热力图"""

        # 计算相关性矩阵
        numeric_data = data.select_dtypes(include=['number'])
        correlation_matrix = numeric_data.corr()

        fig = px.imshow(
            correlation_matrix,
            title=config.get('title', '相关性热力图'),
            template='plotly_white',
            aspect='auto'
        )

        fig.update_layout(height=500)
        return fig

    def render_chart_controls(self, data: pd.DataFrame, chart_type: str, config: Dict):
        """渲染图表控制选项"""

        with st.expander("🛠️ 图表设置"):
            col1, col2 = st.columns(2)

            with col1:
                # 图表类型选择
                new_chart_type = st.selectbox(
                    "图表类型",
                    self.supported_charts,
                    index=self.supported_charts.index(chart_type) if chart_type in self.supported_charts else 0,
                    key=f"chart_type_{id(data)}"
                )

                # 如果图表类型改变，重新渲染
                if new_chart_type != chart_type:
                    st.session_state[f"chart_config_{id(data)}"] = {**config, "chart_type": new_chart_type}
                    st.rerun()

            with col2:
                # 列选择
                columns = data.columns.tolist()
                numeric_columns = data.select_dtypes(include=['number']).columns.tolist()

                if chart_type in ["line", "bar", "scatter"]:
                    x_column = st.selectbox("X轴", columns, key=f"x_col_{id(data)}")
                    y_column = st.selectbox("Y轴", numeric_columns, key=f"y_col_{id(data)}")

            # 导出选项
            st.markdown("### 📥 导出选项")
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("📊 下载图表(HTML)", key=f"export_html_{id(data)}"):
                    self.export_chart_html(data, chart_type, config)

            with col2:
                if st.button("📄 下载数据(CSV)", key=f"export_csv_{id(data)}"):
                    self.export_data_csv(data)

            with col3:
                if st.button("🖼️ 下载图片(PNG)", key=f"export_png_{id(data)}"):
                    st.info("图片导出功能开发中...")

    def export_chart_html(self, data: pd.DataFrame, chart_type: str, config: Dict):
        """导出图表为HTML"""
        try:
            # 重新创建图表
            if chart_type == "line":
                chart = self.create_line_chart(data, config)
            elif chart_type == "bar":
                chart = self.create_bar_chart(data, config)
            else:
                chart = self.create_line_chart(data, config)  # 默认折线图

            # 转换为HTML
            html_str = chart.to_html(include_plotlyjs='cdn')

            # 提供下载
            st.download_button(
                label="💾 确认下载HTML",
                data=html_str,
                file_name=f"chart_{chart_type}.html",
                mime="text/html"
            )

        except Exception as e:
            st.error(f"导出失败: {str(e)}")

    def export_data_csv(self, data: pd.DataFrame):
        """导出数据为CSV"""
        try:
            csv_data = data.to_csv(index=False)
            st.download_button(
                label="💾 确认下载CSV",
                data=csv_data,
                file_name="data_export.csv",
                mime="text/csv"
            )
        except Exception as e:
            st.error(f"导出失败: {str(e)}")

    def auto_suggest_chart_type(self, data: pd.DataFrame) -> str:
        """根据数据自动建议图表类型"""

        numeric_cols = data.select_dtypes(include=['number']).columns
        categorical_cols = data.select_dtypes(include=['object', 'category']).columns
        datetime_cols = data.select_dtypes(include=['datetime']).columns

        # 基于列类型建议图表类型
        if len(datetime_cols) > 0 and len(numeric_cols) > 0:
            return "line"  # 时间序列数据 -> 折线图
        elif len(categorical_cols) > 0 and len(numeric_cols) > 0:
            if data.shape[0] <= 20:
                return "bar"  # 少量分类数据 -> 柱状图
            else:
                return "scatter"  # 大量数据 -> 散点图
        elif len(numeric_cols) >= 2:
            return "scatter"  # 多个数值列 -> 散点图
        else:
            return "bar"  # 默认柱状图
```

### 3. 分析结果页面 (pages/2_📊_Analysis.py)

```python
"""
分析结果页面
显示查询结果、数据可视化和分析报告
"""

import streamlit as st
import pandas as pd
from components.chart_renderer import ChartRenderer
from utils.session_manager import initialize_session_state
from typing import Dict, Any, List

# 页面配置
st.set_page_config(
    page_title="分析结果",
    page_icon="📊",
    layout="wide"
)

def main():
    """分析结果页面主逻辑"""

    initialize_session_state()

    st.title("📊 数据分析结果")

    # 检查是否有分析结果
    if not st.session_state.get('analysis_results'):
        render_empty_state()
        return

    # 渲染分析结果
    render_analysis_results()

def render_empty_state():
    """渲染空状态"""

    st.info("""
    ### 🚀 开始您的数据分析之旅

    目前还没有分析结果。请：

    1. 📝 前往 **Chat** 页面与AI助手对话
    2. 🤔 提出您的数据问题
    3. 📊 等待生成分析结果
    4. 🎯 回到这里查看详细分析
    """)

    # 示例问题
    st.markdown("### 💡 示例问题")

    example_questions = [
        "显示过去30天的销售趋势",
        "哪个产品类别的销售额最高？",
        "分析客户年龄分布情况",
        "比较不同地区的销售表现"
    ]

    for question in example_questions:
        st.write(f"• {question}")

def render_analysis_results():
    """渲染分析结果"""

    results = st.session_state.analysis_results

    # 结果概览
    render_results_overview(results)

    # 详细结果
    for i, result in enumerate(results):
        render_single_result(result, i)

def render_results_overview(results: List[Dict]):
    """渲染结果概览"""

    st.markdown("### 📋 分析概览")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("分析次数", len(results))

    with col2:
        successful_count = sum(1 for r in results if r.get('success', False))
        st.metric("成功次数", successful_count)

    with col3:
        total_records = sum(r.get('record_count', 0) for r in results)
        st.metric("总记录数", f"{total_records:,}")

    with col4:
        avg_time = sum(r.get('execution_time', 0) for r in results) / len(results)
        st.metric("平均耗时", f"{avg_time:.1f}s")

def render_single_result(result: Dict[str, Any], index: int):
    """渲染单个分析结果"""

    with st.expander(f"📈 分析结果 {index + 1}: {result.get('title', '未知查询')}", expanded=index == 0):

        # 基本信息
        col1, col2 = st.columns([3, 1])

        with col1:
            st.write(f"**查询:** {result.get('query', 'N/A')}")
            st.write(f"**执行时间:** {result.get('execution_time', 0):.2f}秒")

        with col2:
            if result.get('success', False):
                st.success("✅ 执行成功")
            else:
                st.error("❌ 执行失败")

        # SQL查询
        if result.get('sql_query'):
            st.markdown("#### 🔍 生成的SQL")
            st.code(result['sql_query'], language='sql')

        # 数据结果
        if result.get('data') is not None:
            render_data_results(result['data'], index)

        # 可视化
        if result.get('visualization_config'):
            render_visualization(result['data'], result['visualization_config'], index)

        # 分析洞察
        if result.get('insights'):
            render_insights(result['insights'])

def render_data_results(data: pd.DataFrame, index: int):
    """渲染数据结果"""

    st.markdown("#### 📊 查询结果")

    if data.empty:
        st.warning("查询未返回任何数据")
        return

    # 数据概览
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("行数", len(data))

    with col2:
        st.metric("列数", len(data.columns))

    with col3:
        numeric_cols = len(data.select_dtypes(include=['number']).columns)
        st.metric("数值列", numeric_cols)

    # 数据预览
    st.markdown("##### 📋 数据预览")

    # 显示选项
    show_options = st.columns([1, 1, 1, 3])

    with show_options[0]:
        show_all = st.checkbox("显示全部", key=f"show_all_{index}")

    with show_options[1]:
        max_rows = st.number_input(
            "最大行数",
            min_value=5,
            max_value=1000,
            value=100,
            key=f"max_rows_{index}"
        )

    # 显示数据
    display_data = data if show_all else data.head(max_rows)

    st.dataframe(
        display_data,
        use_container_width=True,
        height=400
    )

    # 数据统计
    if numeric_cols > 0:
        st.markdown("##### 📈 数据统计")
        st.dataframe(data.describe(), use_container_width=True)

def render_visualization(data: pd.DataFrame, viz_config: Dict, index: int):
    """渲染可视化"""

    st.markdown("#### 📊 数据可视化")

    if data.empty:
        st.warning("无数据可视化")
        return

    # 创建图表渲染器
    chart_renderer = ChartRenderer()

    # 自动建议图表类型
    suggested_chart = chart_renderer.auto_suggest_chart_type(data)
    chart_type = viz_config.get('chart_type', suggested_chart)

    # 渲染图表
    chart_renderer.render_chart(
        data=data,
        chart_type=chart_type,
        config=viz_config,
        container_key=f"chart_{index}"
    )

def render_insights(insights: List[str]):
    """渲染分析洞察"""

    st.markdown("#### 💡 关键洞察")

    for i, insight in enumerate(insights):
        st.write(f"{i + 1}. {insight}")

def render_comparison_view():
    """渲染对比视图"""

    st.markdown("### 🔄 结果对比")

    results = st.session_state.analysis_results

    if len(results) < 2:
        st.info("需要至少2个分析结果才能进行对比")
        return

    # 选择对比的结果
    col1, col2 = st.columns(2)

    with col1:
        result1_idx = st.selectbox(
            "选择结果1",
            range(len(results)),
            format_func=lambda x: f"结果 {x+1}: {results[x].get('title', '未知')}"
        )

    with col2:
        result2_idx = st.selectbox(
            "选择结果2",
            range(len(results)),
            format_func=lambda x: f"结果 {x+1}: {results[x].get('title', '未知')}"
        )

    if result1_idx != result2_idx:
        # 显示对比结果
        result1 = results[result1_idx]
        result2 = results[result2_idx]

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"#### 结果 {result1_idx + 1}")
            render_single_result(result1, result1_idx)

        with col2:
            st.markdown(f"#### 结果 {result2_idx + 1}")
            render_single_result(result2, result2_idx)

if __name__ == "__main__":
    # 添加页面选项卡
    tab1, tab2 = st.tabs(["📊 分析结果", "🔄 结果对比"])

    with tab1:
        main()

    with tab2:
        render_comparison_view()
```

### 4. 人工审查组件 (components/human_review.py)

```python
"""
人工审查组件
提供SQL查询和结果的人工审查功能
"""

import streamlit as st
from typing import Dict, Any, List, Optional
import pandas as pd

class HumanReviewInterface:
    """人工审查界面组件"""

    def __init__(self):
        self.initialize_review_state()

    def initialize_review_state(self):
        """初始化审查状态"""
        if "pending_reviews" not in st.session_state:
            st.session_state.pending_reviews = []

        if "review_history" not in st.session_state:
            st.session_state.review_history = []

    def render_review_interface(self, review_item: Dict[str, Any]):
        """渲染审查界面"""

        st.markdown("### 🔍 人工审查")

        # 审查内容
        self.render_review_content(review_item)

        # 审查选项
        self.render_review_actions(review_item)

    def render_review_content(self, review_item: Dict[str, Any]):
        """渲染审查内容"""

        review_type = review_item.get('type', 'unknown')

        if review_type == 'sql_query':
            self.render_sql_review(review_item)
        elif review_type == 'query_results':
            self.render_results_review(review_item)
        elif review_type == 'visualization':
            self.render_visualization_review(review_item)

    def render_sql_review(self, review_item: Dict[str, Any]):
        """渲染SQL查询审查"""

        st.markdown("#### 📝 SQL查询审查")

        # 原始问题
        st.markdown("**用户问题:**")
        st.write(review_item.get('user_question', 'N/A'))

        # 生成的SQL
        st.markdown("**生成的SQL查询:**")
        sql_query = review_item.get('sql_query', '')

        # 可编辑的SQL
        edited_sql = st.text_area(
            "SQL查询 (可编辑)",
            value=sql_query,
            height=200,
            help="您可以直接编辑SQL查询"
        )

        # SQL分析
        if sql_query:
            self.analyze_sql_query(sql_query)

        # 保存编辑后的SQL
        review_item['edited_sql'] = edited_sql

    def analyze_sql_query(self, sql_query: str):
        """分析SQL查询"""

        st.markdown("**SQL分析:**")

        analysis_results = []

        # 基本语法检查
        if sql_query.strip().upper().startswith('SELECT'):
            analysis_results.append("✅ SQL语法：SELECT查询")
        else:
            analysis_results.append("⚠️ SQL语法：非SELECT查询，请注意安全性")

        # 关键词检查
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER']
        for keyword in dangerous_keywords:
            if keyword in sql_query.upper():
                analysis_results.append(f"🚨 检测到危险关键词：{keyword}")

        # 显示分析结果
        for result in analysis_results:
            st.write(result)

    def render_results_review(self, review_item: Dict[str, Any]):
        """渲染查询结果审查"""

        st.markdown("#### 📊 查询结果审查")

        # 显示结果数据
        data = review_item.get('data')
        if data is not None and not data.empty:
            st.markdown("**查询结果:**")
            st.dataframe(data, use_container_width=True)

            # 结果统计
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("记录数", len(data))

            with col2:
                st.metric("字段数", len(data.columns))

            with col3:
                data_size = data.memory_usage(deep=True).sum() / 1024  # KB
                st.metric("数据大小", f"{data_size:.1f} KB")

            # 数据质量检查
            self.check_data_quality(data)

        else:
            st.warning("无查询结果数据")

    def check_data_quality(self, data: pd.DataFrame):
        """检查数据质量"""

        st.markdown("**数据质量检查:**")

        quality_issues = []

        # 检查空值
        null_counts = data.isnull().sum()
        null_columns = null_counts[null_counts > 0]

        if not null_columns.empty:
            quality_issues.append(f"⚠️ 发现空值：{', '.join(null_columns.index.tolist())}")

        # 检查重复行
        duplicate_count = data.duplicated().sum()
        if duplicate_count > 0:
            quality_issues.append(f"⚠️ 发现 {duplicate_count} 行重复数据")

        # 检查数据范围
        numeric_columns = data.select_dtypes(include=['number']).columns
        for col in numeric_columns:
            if data[col].min() < 0 and col.lower() in ['price', 'amount', 'quantity']:
                quality_issues.append(f"⚠️ {col} 列包含负值")

        # 显示质量检查结果
        if quality_issues:
            for issue in quality_issues:
                st.write(issue)
        else:
            st.write("✅ 数据质量检查通过")

    def render_visualization_review(self, review_item: Dict[str, Any]):
        """渲染可视化审查"""

        st.markdown("#### 📈 可视化审查")

        viz_config = review_item.get('visualization_config', {})

        # 可视化配置
        st.markdown("**可视化配置:**")
        st.json(viz_config)

        # 可视化建议
        st.markdown("**可视化建议:**")
        suggestions = self.get_visualization_suggestions(review_item.get('data'), viz_config)

        for suggestion in suggestions:
            st.write(f"💡 {suggestion}")

    def get_visualization_suggestions(self, data: pd.DataFrame, viz_config: Dict) -> List[str]:
        """获取可视化建议"""

        suggestions = []

        if data is None or data.empty:
            return ["无数据可提供建议"]

        # 基于数据类型的建议
        numeric_cols = data.select_dtypes(include=['number']).columns
        categorical_cols = data.select_dtypes(include=['object', 'category']).columns

        if len(numeric_cols) >= 2:
            suggestions.append("考虑使用散点图展示数值变量间的关系")

        if len(categorical_cols) > 0 and len(numeric_cols) > 0:
            suggestions.append("可以按分类变量进行分组对比")

        return suggestions

    def render_review_actions(self, review_item: Dict[str, Any]):
        """渲染审查操作"""

        st.markdown("### ✅ 审查决定")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("✅ 批准", type="primary"):
                self.approve_review(review_item)

        with col2:
            if st.button("🔄 修改"):
                self.request_revision(review_item)

        with col3:
            if st.button("❌ 拒绝"):
                self.reject_review(review_item)

        # 评论框
        review_comment = st.text_area(
            "审查意见",
            placeholder="请输入您的审查意见和建议...",
            key=f"review_comment_{review_item.get('id', 'default')}"
        )

        review_item['review_comment'] = review_comment

    def approve_review(self, review_item: Dict[str, Any]):
        """批准审查"""

        review_item['status'] = 'approved'
        review_item['reviewer'] = 'human_reviewer'

        # 移到历史记录
        st.session_state.review_history.append(review_item)

        # 从待审查列表移除
        if review_item in st.session_state.pending_reviews:
            st.session_state.pending_reviews.remove(review_item)

        st.success("✅ 审查已批准")
        st.rerun()

    def request_revision(self, review_item: Dict[str, Any]):
        """请求修改"""

        review_item['status'] = 'revision_requested'
        review_item['reviewer'] = 'human_reviewer'

        st.warning("🔄 已请求修改，将重新生成")
        st.rerun()

    def reject_review(self, review_item: Dict[str, Any]):
        """拒绝审查"""

        review_item['status'] = 'rejected'
        review_item['reviewer'] = 'human_reviewer'

        # 移到历史记录
        st.session_state.review_history.append(review_item)

        # 从待审查列表移除
        if review_item in st.session_state.pending_reviews:
            st.session_state.pending_reviews.remove(review_item)

        st.error("❌ 审查已拒绝")
        st.rerun()
```

## 验收标准

### 功能验收
- [ ] LangGraph工作流成功集成
- [ ] 数据可视化组件正常工作
- [ ] 人工审查流程完整
- [ ] 数据处理管道稳定
- [ ] 错误处理机制完善

### 技术验收
- [ ] 异步工作流执行正确
- [ ] 多种图表类型支持
- [ ] 数据质量检查完整
- [ ] SQL安全性验证
- [ ] 组件化架构清晰

### 用户体验验收
- [ ] 工作流状态反馈及时
- [ ] 图表交互体验良好
- [ ] 审查界面直观易用
- [ ] 数据导出功能完整
- [ ] 错误提示友好准确

## 后续任务
完成此任务后，进入**Task 04: 完善优化**阶段，重点进行性能优化和用户体验提升。