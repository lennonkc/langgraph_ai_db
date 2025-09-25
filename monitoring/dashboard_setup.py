# LangSmith Dashboard Configuration
from typing import Dict, List, Any

def setup_langsmith_dashboards():
    """设置LangSmith仪表板"""

    # Workflow Performance Dashboard
    workflow_dashboard = {
        "name": "AI Database Analyst - Workflow Performance",
        "description": "Complete workflow execution metrics and performance",
        "charts": [
            {
                "name": "Execution Time Distribution",
                "type": "histogram",
                "metric": "execution_time_seconds",
                "filters": {"run_type": "chain", "name": "ai_database_analyst_complete_workflow"}
            },
            {
                "name": "Success Rate Over Time",
                "type": "time_series",
                "metric": "success_rate",
                "aggregation": "daily"
            },
            {
                "name": "Cost per Analysis",
                "type": "line_chart",
                "metric": "total_cost",
                "time_range": "7d"
            },
            {
                "name": "Error Rate by Step",
                "type": "bar_chart",
                "metric": "error_count",
                "group_by": "step_name"
            }
        ]
    }

    # LLM Performance Dashboard
    llm_dashboard = {
        "name": "AI Database Analyst - LLM Performance",
        "description": "LLM call performance, token usage, and costs",
        "charts": [
            {
                "name": "Token Usage by Operation",
                "type": "stacked_bar",
                "metric": "total_tokens",
                "group_by": "operation"
            },
            {
                "name": "LLM Cost Trends",
                "type": "area_chart",
                "metric": "llm_cost",
                "time_range": "30d"
            },
            {
                "name": "Model Performance Comparison",
                "type": "table",
                "metrics": ["avg_execution_time", "avg_tokens", "success_rate"],
                "group_by": "model"
            }
        ]
    }

    # Data Quality Dashboard
    quality_dashboard = {
        "name": "AI Database Analyst - Data Quality",
        "description": "Query results quality and validation metrics",
        "charts": [
            {
                "name": "Validation Decision Distribution",
                "type": "pie_chart",
                "metric": "validation_decision",
                "group_by": "decision_type"
            },
            {
                "name": "Data Size Distribution",
                "type": "histogram",
                "metric": "data_rows_returned",
                "bins": 20
            },
            {
                "name": "Query Optimization Rate",
                "type": "gauge",
                "metric": "optimization_applied_rate",
                "target": 0.8
            }
        ]
    }

    return [workflow_dashboard, llm_dashboard, quality_dashboard]

def create_custom_metrics():
    """创建自定义指标"""

    custom_metrics = [
        {
            "name": "workflow_completion_rate",
            "description": "Percentage of workflows that complete successfully",
            "formula": "COUNT(completed_workflows) / COUNT(total_workflows) * 100"
        },
        {
            "name": "average_analysis_cost",
            "description": "Average cost per complete analysis",
            "formula": "SUM(total_costs) / COUNT(completed_analyses)"
        },
        {
            "name": "user_satisfaction_score",
            "description": "Average user satisfaction based on report generation success",
            "formula": "AVG(user_approval_rate)"
        },
        {
            "name": "query_efficiency_score",
            "description": "Ratio of data processing cost to result value",
            "formula": "SUM(data_rows) / SUM(processing_cost)"
        }
    ]

    return custom_metrics

def get_dashboard_configuration() -> Dict[str, Any]:
    """获取完整的仪表板配置"""

    dashboards = setup_langsmith_dashboards()
    custom_metrics = create_custom_metrics()

    return {
        "dashboards": dashboards,
        "custom_metrics": custom_metrics,
        "project_name": "ai-database-analyst",
        "update_frequency": "hourly",
        "retention_days": 30
    }