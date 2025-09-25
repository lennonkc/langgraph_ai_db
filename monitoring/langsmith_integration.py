"""
LangSmith Integration for AI Database Analyst

提供LangSmith跟踪和监控功能
"""

import os
from typing import Dict, Any
from datetime import datetime
import structlog

logger = structlog.get_logger()

# 尝试导入LangSmith
try:
    from langsmith import traceable
    LANGSMITH_AVAILABLE = True
except ImportError:
    logger.warning("LangSmith not available, falling back to local logging")
    LANGSMITH_AVAILABLE = False

    # 创建装饰器的空实现
    def traceable(run_type=None, name=None):
        def decorator(func):
            return func
        return decorator


@traceable(run_type="chain", name="ai_database_analyst_main_workflow")
def execute_main_workflow_with_tracking(initial_state: Dict) -> Dict:
    """执行带LangSmith跟踪的主工作流程"""

    # Set up LangSmith tracking if available
    if LANGSMITH_AVAILABLE:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = "ai-database-analyst"

        # Set endpoint and API key from environment
        if os.getenv("LANGCHAIN_ENDPOINT"):
            os.environ["LANGCHAIN_ENDPOINT"] = os.getenv("LANGCHAIN_ENDPOINT")
        if os.getenv("LANGCHAIN_API_KEY"):
            os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")

    # Import here to avoid circular imports
    from main_workflow import create_main_workflow

    # Create and execute workflow
    workflow = create_main_workflow()
    result = workflow.invoke(initial_state)

    # Log key metrics
    langsmith_metadata = {
        "session_id": result.get("session_id"),
        "question_classification": result.get("question_classification"),
        "confidence_score": result.get("confidence_score"),
        "execution_time": result.get("execution_result", {}).get("execution_time_seconds"),
        "validation_decision": result.get("validation_decision"),
        "workflow_status": result.get("workflow_status"),
        "retry_count": result.get("retry_count"),
        "timestamp": datetime.now().isoformat()
    }

    logger.info("Workflow execution completed with tracking", **langsmith_metadata)

    return result


class WorkflowMonitor:
    """工作流程监控器"""

    def __init__(self):
        self.metrics = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_execution_time": 0,
            "step_failure_counts": {}
        }

    def record_execution_start(self, session_id: str, question: str):
        """记录执行开始"""
        logger.info("Workflow execution started",
                   session_id=session_id,
                   question=question,
                   timestamp=datetime.now().isoformat())

        self.metrics["total_executions"] += 1

    def record_execution_end(self, session_id: str, result: Dict):
        """记录执行结束"""
        status = result.get("workflow_status", "unknown")
        execution_time = result.get("execution_result", {}).get("execution_time_seconds", 0)

        if status == "completed":
            self.metrics["successful_executions"] += 1
        elif status == "failed":
            self.metrics["failed_executions"] += 1
            failed_step = result.get("current_step", "unknown")
            self.metrics["step_failure_counts"][failed_step] = \
                self.metrics["step_failure_counts"].get(failed_step, 0) + 1

        # Update average execution time
        if execution_time > 0:
            current_avg = self.metrics["average_execution_time"]
            total_completed = self.metrics["successful_executions"]
            self.metrics["average_execution_time"] = \
                ((current_avg * (total_completed - 1)) + execution_time) / total_completed

        logger.info("Workflow execution ended",
                   session_id=session_id,
                   status=status,
                   execution_time=execution_time,
                   timestamp=datetime.now().isoformat())

    def record_step_completion(self, session_id: str, step_name: str, duration: float):
        """记录步骤完成"""
        logger.info("Workflow step completed",
                   session_id=session_id,
                   step=step_name,
                   duration=duration,
                   timestamp=datetime.now().isoformat())

    def record_error(self, session_id: str, step_name: str, error_message: str):
        """记录错误"""
        logger.error("Workflow step failed",
                    session_id=session_id,
                    step=step_name,
                    error=error_message,
                    timestamp=datetime.now().isoformat())

    def get_metrics_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        success_rate = 0
        if self.metrics["total_executions"] > 0:
            success_rate = (self.metrics["successful_executions"] /
                          self.metrics["total_executions"]) * 100

        return {
            "total_executions": self.metrics["total_executions"],
            "successful_executions": self.metrics["successful_executions"],
            "failed_executions": self.metrics["failed_executions"],
            "success_rate_percentage": round(success_rate, 2),
            "average_execution_time_seconds": round(self.metrics["average_execution_time"], 2),
            "step_failure_counts": self.metrics["step_failure_counts"],
            "generated_at": datetime.now().isoformat()
        }


# Global monitor instance
workflow_monitor = WorkflowMonitor()


@traceable(run_type="tool", name="bigquery_execution")
def track_bigquery_execution(query: str, result: Dict) -> Dict:
    """跟踪BigQuery执行"""
    return {
        "query_length": len(query),
        "success": result.get("success", False),
        "row_count": result.get("row_count", 0),
        "cost_estimate": result.get("cost_estimate_usd", 0),
        "execution_time": result.get("execution_time_seconds", 0)
    }


@traceable(run_type="llm", name="question_classification")
def track_question_classification(question: str, classification: str, confidence: float) -> Dict:
    """跟踪问题分类"""
    return {
        "question_length": len(question),
        "classification": classification,
        "confidence_score": confidence,
        "timestamp": datetime.now().isoformat()
    }


@traceable(run_type="llm", name="query_generation")
def track_query_generation(question: str, generated_sql: str, metadata: Dict) -> Dict:
    """跟踪查询生成"""
    return {
        "question_length": len(question),
        "sql_length": len(generated_sql),
        "generation_method": metadata.get("generation_method", "unknown"),
        "template_used": metadata.get("template_id", "none"),
        "timestamp": datetime.now().isoformat()
    }


def setup_langsmith_environment():
    """设置LangSmith环境"""
    required_vars = ["LANGCHAIN_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.warning("LangSmith configuration incomplete",
                      missing_variables=missing_vars)
        return False

    # Set default values if not provided
    if not os.getenv("LANGCHAIN_PROJECT"):
        os.environ["LANGCHAIN_PROJECT"] = "ai-database-analyst"

    if not os.getenv("LANGCHAIN_ENDPOINT"):
        os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"

    logger.info("LangSmith environment configured successfully")
    return True


# Initialize LangSmith on module import
if LANGSMITH_AVAILABLE:
    setup_langsmith_environment()

# Import and expose langsmith_config from config module
try:
    from config.langsmith_config import langsmith_config
except ImportError:
    # Create a minimal config if the main one is not available
    class MockLangSmithConfig:
        def setup_session_tracking(self, session_id):
            return session_id

        def create_project_if_not_exists(self, project_name):
            pass

    langsmith_config = MockLangSmithConfig()