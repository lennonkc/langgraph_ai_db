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

def render_review_dashboard():
    """渲染审查仪表板"""

    st.markdown("### 📋 审查仪表板")

    # 统计信息
    col1, col2, col3 = st.columns(3)

    with col1:
        pending_count = len(st.session_state.get('pending_reviews', []))
        st.metric("待审查", pending_count)

    with col2:
        approved_count = len([r for r in st.session_state.get('review_history', [])
                            if r.get('status') == 'approved'])
        st.metric("已批准", approved_count)

    with col3:
        rejected_count = len([r for r in st.session_state.get('review_history', [])
                            if r.get('status') == 'rejected'])
        st.metric("已拒绝", rejected_count)

    # 待审查列表
    if st.session_state.get('pending_reviews'):
        st.markdown("#### 🔍 待审查项目")

        for i, review_item in enumerate(st.session_state.pending_reviews):
            with st.expander(f"审查 {i+1}: {review_item.get('type', 'unknown')}"):
                review_interface = HumanReviewInterface()
                review_interface.render_review_interface(review_item)

    else:
        st.info("📝 当前没有待审查的项目")

def add_review_item(item_type: str, item_data: Dict[str, Any]):
    """添加审查项目"""

    if "pending_reviews" not in st.session_state:
        st.session_state.pending_reviews = []

    review_item = {
        'id': len(st.session_state.pending_reviews),
        'type': item_type,
        'status': 'pending',
        'created_at': pd.Timestamp.now().isoformat(),
        **item_data
    }

    st.session_state.pending_reviews.append(review_item)

def get_pending_review_count() -> int:
    """获取待审查项目数量"""
    return len(st.session_state.get('pending_reviews', []))

def has_pending_reviews() -> bool:
    """检查是否有待审查项目"""
    return get_pending_review_count() > 0