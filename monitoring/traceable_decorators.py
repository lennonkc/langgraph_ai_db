# Traceable Decorators for Workflow Tracking
from functools import wraps
from langsmith import traceable
from typing import Dict, Any, Optional
import time
import json

def trace_workflow_step(step_name: str,
                       step_type: str = "chain",
                       include_inputs: bool = True,
                       include_outputs: bool = True):
    """工作流程步骤跟踪装饰器"""

    def decorator(func):
        @traceable(
            run_type=step_type,
            name=f"ai_analyst_{step_name}",
            project_name="ai-database-analyst"
        )
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                # Execute function
                result = func(*args, **kwargs)

                # Calculate execution time
                execution_time = time.time() - start_time

                # Add metadata to result if it's a dict
                if isinstance(result, dict):
                    result["_langsmith_metadata"] = {
                        "step_name": step_name,
                        "execution_time_seconds": execution_time,
                        "status": "success"
                    }

                return result

            except Exception as e:
                execution_time = time.time() - start_time

                # Log error details
                error_metadata = {
                    "step_name": step_name,
                    "execution_time_seconds": execution_time,
                    "status": "error",
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }

                # Re-raise with additional context
                raise Exception(f"Step {step_name} failed: {str(e)}") from e

        return wrapper
    return decorator

def trace_llm_call(operation_name: str, model_name: str = "unknown"):
    """LLM调用跟踪装饰器"""

    def decorator(func):
        @traceable(
            run_type="llm",
            name=f"llm_call_{operation_name}",
            project_name="ai-database-analyst"
        )
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Track token usage and costs
            start_time = time.time()

            try:
                result = func(*args, **kwargs)

                # Extract token information if available
                token_info = extract_token_info(result)

                execution_time = time.time() - start_time

                # Add LLM-specific metadata
                if isinstance(result, dict):
                    result["_langsmith_llm_metadata"] = {
                        "operation": operation_name,
                        "model": model_name,
                        "execution_time_seconds": execution_time,
                        "token_usage": token_info,
                        "estimated_cost": calculate_llm_cost(token_info, model_name)
                    }

                return result

            except Exception as e:
                execution_time = time.time() - start_time
                raise Exception(f"LLM call {operation_name} failed after {execution_time:.2f}s: {str(e)}") from e

        return wrapper
    return decorator

def extract_token_info(llm_result: Any) -> Dict[str, int]:
    """提取token使用信息"""
    # This would extract actual token usage from LLM response
    # Implementation depends on the LLM provider
    return {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0
    }

def calculate_llm_cost(token_info: Dict[str, int], model_name: str) -> float:
    """计算LLM调用成本"""
    # Cost calculation based on model and token usage
    cost_per_1k_tokens = {
        "gemini-2.5-pro": 0.002,  # Primary model for all tasks
        "gemini-2.5-flash": 0.0001,
        "gpt-3.5-turbo": 0.002,
        "claude-3": 0.015
    }

    rate = cost_per_1k_tokens.get(model_name, 0.01)
    total_tokens = token_info.get("total_tokens", 0)

    return (total_tokens / 1000) * rate