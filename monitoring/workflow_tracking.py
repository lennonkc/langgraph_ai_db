# Workflow-Level Tracking Implementation
from langsmith import traceable
from typing import Dict, Any, Optional
import uuid
import time
import os
from datetime import datetime
from config.langsmith_config import langsmith_config

@traceable(run_type="chain", name="ai_database_analyst_complete_workflow")
def execute_tracked_workflow(user_question: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """执行带完整跟踪的工作流程"""

    # Setup session tracking
    if not session_id:
        session_id = str(uuid.uuid4())

    langsmith_config.setup_session_tracking(session_id)

    # Create workflow execution context
    workflow_context = {
        "session_id": session_id,
        "user_question": user_question,
        "start_time": datetime.now().isoformat(),
        "workflow_version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "production")
    }

    try:
        from main_workflow import AIDataAnalyst

        analyst = AIDataAnalyst()
        result = analyst.analyze_question(user_question, session_id)

        # Enhance result with tracking metadata
        result["workflow_context"] = workflow_context
        result["end_time"] = datetime.now().isoformat()

        # Log successful completion
        log_workflow_completion(session_id, result, "success")

        return result

    except Exception as e:
        # Log workflow failure
        error_context = {
            **workflow_context,
            "end_time": datetime.now().isoformat(),
            "error": str(e),
            "error_type": type(e).__name__
        }

        log_workflow_completion(session_id, error_context, "failed")
        raise

def log_workflow_completion(session_id: str, result: Dict[str, Any], status: str):
    """记录工作流程完成状态"""

    completion_metrics = {
        "session_id": session_id,
        "status": status,
        "total_execution_time": calculate_total_execution_time(result),
        "steps_completed": count_completed_steps(result),
        "cost_estimate": calculate_total_cost(result),
        "data_processed_gb": get_data_processing_volume(result)
    }

    # Log to LangSmith
    langsmith_config.client.create_run(
        name="workflow_completion_summary",
        run_type="chain",
        inputs={"session_id": session_id},
        outputs=completion_metrics,
        project_name="ai-database-analyst"
    )

def calculate_total_execution_time(result: Dict[str, Any]) -> float:
    """计算总执行时间"""
    workflow_context = result.get("workflow_context", {})
    start_time = workflow_context.get("start_time")
    end_time = result.get("end_time")

    if start_time and end_time:
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)
        return (end_dt - start_dt).total_seconds()
    return 0.0

def count_completed_steps(result: Dict[str, Any]) -> int:
    """计算完成的步骤数"""
    # Simple heuristic based on workflow status
    if result.get("workflow_status") == "completed":
        return 7  # All steps completed
    elif result.get("workflow_status") == "failed":
        return result.get("retry_count", 0) + 1
    return 0

def calculate_total_cost(result: Dict[str, Any]) -> float:
    """计算总成本"""
    execution_summary = result.get("execution_summary", {})
    return execution_summary.get("cost_estimate", 0.0)

def get_data_processing_volume(result: Dict[str, Any]) -> float:
    """获取数据处理量（GB）"""
    execution_summary = result.get("execution_summary", {})
    data_rows = execution_summary.get("data_rows", 0)
    # Rough estimation: 1000 rows ≈ 1MB
    return (data_rows * 1024) / (1024 * 1024 * 1024) if data_rows > 0 else 0.0

class WorkflowMetricsCollector:
    """工作流程指标收集器"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.step_metrics = {}
        self.llm_calls = []
        self.errors = []

    def record_step_start(self, step_name: str):
        """记录步骤开始"""
        self.step_metrics[step_name] = {
            "start_time": time.time(),
            "status": "running"
        }

    def record_step_completion(self, step_name: str, result: Dict[str, Any]):
        """记录步骤完成"""
        if step_name in self.step_metrics:
            self.step_metrics[step_name].update({
                "end_time": time.time(),
                "status": "completed",
                "execution_time": time.time() - self.step_metrics[step_name]["start_time"],
                "result_summary": self._summarize_step_result(result)
            })

    def record_llm_call(self, operation: str, model: str, tokens: int, cost: float):
        """记录LLM调用"""
        self.llm_calls.append({
            "operation": operation,
            "model": model,
            "tokens": tokens,
            "cost": cost,
            "timestamp": time.time()
        })

    def record_error(self, step_name: str, error: Exception):
        """记录错误"""
        self.errors.append({
            "step": step_name,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": time.time()
        })

    def get_session_summary(self) -> Dict[str, Any]:
        """获取会话摘要"""
        total_llm_cost = sum(call["cost"] for call in self.llm_calls)
        total_tokens = sum(call["tokens"] for call in self.llm_calls)

        return {
            "session_id": self.session_id,
            "steps_executed": len(self.step_metrics),
            "total_llm_calls": len(self.llm_calls),
            "total_tokens_used": total_tokens,
            "total_llm_cost": total_llm_cost,
            "errors_encountered": len(self.errors),
            "step_breakdown": self.step_metrics,
            "error_details": self.errors
        }

    def _summarize_step_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """总结步骤结果"""
        return {
            "has_result": bool(result),
            "result_keys": list(result.keys()) if isinstance(result, dict) else [],
            "result_size": len(str(result))
        }