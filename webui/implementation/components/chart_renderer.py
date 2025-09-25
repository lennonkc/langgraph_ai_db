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

# 兼容性函数（保持原有API）
def render_line_chart(data: pd.DataFrame, x_col: str, y_col: str, title: str = "线形图"):
    """渲染线形图"""
    renderer = ChartRenderer()
    config = {
        'x_column': x_col,
        'y_column': y_col,
        'title': title
    }
    renderer.render_chart(data, 'line', config)

def render_bar_chart(data: pd.DataFrame, x_col: str, y_col: str, title: str = "柱状图"):
    """渲染柱状图"""
    renderer = ChartRenderer()
    config = {
        'x_column': x_col,
        'y_column': y_col,
        'title': title
    }
    renderer.render_chart(data, 'bar', config)

def render_scatter_plot(data: pd.DataFrame, x_col: str, y_col: str, title: str = "散点图"):
    """渲染散点图"""
    renderer = ChartRenderer()
    config = {
        'x_column': x_col,
        'y_column': y_col,
        'title': title
    }
    renderer.render_chart(data, 'scatter', config)

def render_histogram(data: pd.DataFrame, col: str, title: str = "直方图"):
    """渲染直方图"""
    renderer = ChartRenderer()
    config = {
        'x_column': col,
        'title': title
    }
    renderer.render_chart(data, 'histogram', config)

def render_pie_chart(data: pd.DataFrame, values_col: str, names_col: str, title: str = "饼图"):
    """渲染饼图"""
    renderer = ChartRenderer()
    config = {
        'values_column': values_col,
        'names_column': names_col,
        'title': title
    }
    renderer.render_chart(data, 'pie', config)

def create_chart_selector(chart_types: List[str] = None) -> str:
    """创建图表类型选择器"""
    renderer = ChartRenderer()
    if chart_types is None:
        chart_types = renderer.supported_charts

    chart_labels = {
        "line": "线形图",
        "bar": "柱状图",
        "scatter": "散点图",
        "histogram": "直方图",
        "pie": "饼图",
        "box": "箱线图",
        "violin": "小提琴图",
        "heatmap": "热力图",
        "treemap": "树状图",
        "sunburst": "旭日图"
    }

    selected = st.selectbox(
        "选择图表类型",
        chart_types,
        format_func=lambda x: chart_labels.get(x, x)
    )

    return selected

def render_chart_by_type(chart_type: str, data: pd.DataFrame, config: Dict[str, Any]):
    """根据类型渲染图表"""
    renderer = ChartRenderer()
    renderer.render_chart(data, chart_type, config)

def render_data_summary(data: pd.DataFrame):
    """渲染数据摘要"""
    st.markdown("### 📊 数据摘要")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("行数", len(data))

    with col2:
        st.metric("列数", len(data.columns))

    with col3:
        st.metric("内存使用", f"{data.memory_usage(deep=True).sum() / 1024:.1f} KB")

    # 显示数据类型
    st.markdown("#### 列信息")
    info_df = pd.DataFrame({
        "列名": data.columns,
        "数据类型": [str(dtype) for dtype in data.dtypes],
        "非空值": [data[col].count() for col in data.columns],
        "空值": [data[col].isnull().sum() for col in data.columns]
    })

    st.dataframe(info_df, use_container_width=True)