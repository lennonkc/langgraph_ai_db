# 错误类型定义和分类系统
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import traceback
from datetime import datetime

class ErrorSeverity(Enum):
    CRITICAL = "critical"      # 系统故障，需要立即关注
    HIGH = "high"             # 重大功能影响
    MEDIUM = "medium"         # 可通过重试或回退恢复
    LOW = "low"              # 轻微问题，警告
    INFO = "info"            # 信息性，无需操作

class ErrorCategory(Enum):
    # Infrastructure Errors
    BIGQUERY_CONNECTION = "bigquery_connection"
    BIGQUERY_QUOTA = "bigquery_quota"
    BIGQUERY_SYNTAX = "bigquery_syntax"
    BIGQUERY_PERMISSION = "bigquery_permission"

    # LLM Errors
    LLM_TIMEOUT = "llm_timeout"
    LLM_QUOTA = "llm_quota"
    LLM_INVALID_RESPONSE = "llm_invalid_response"
    LLM_CONTEXT_LENGTH = "llm_context_length"

    # Data Errors
    DATA_TOO_LARGE = "data_too_large"
    DATA_EMPTY = "data_empty"
    DATA_INVALID_FORMAT = "data_invalid_format"
    DATA_QUALITY_POOR = "data_quality_poor"

    # Workflow Errors
    VALIDATION_FAILED = "validation_failed"
    GENERATION_FAILED = "generation_failed"
    STATE_CORRUPTION = "state_corruption"
    TIMEOUT = "timeout"

    # User Errors
    INVALID_QUESTION = "invalid_question"
    UNSUPPORTED_REQUEST = "unsupported_request"
    INSUFFICIENT_PERMISSIONS = "insufficient_permissions"

@dataclass
class ErrorContext:
    """错误上下文信息"""
    session_id: str
    step_name: str
    user_question: str
    error_category: ErrorCategory
    severity: ErrorSeverity
    error_message: str
    stack_trace: Optional[str] = None
    retry_count: int = 0
    additional_context: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    recovery_suggestions: Optional[List[str]] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

class DatabaseAnalystError(Exception):
    """AI数据分析师基础异常类"""

    def __init__(self,
                 message: str,
                 category: ErrorCategory,
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 context: Optional[Dict[str, Any]] = None,
                 recovery_suggestions: Optional[List[str]] = None):
        super().__init__(message)
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.recovery_suggestions = recovery_suggestions or []
        self.timestamp = datetime.now().isoformat()

# Specific Error Classes
class BigQueryError(DatabaseAnalystError):
    """BigQuery相关错误"""
    pass

class LLMError(DatabaseAnalystError):
    """LLM相关错误"""
    pass

class DataProcessingError(DatabaseAnalystError):
    """数据处理错误"""
    pass

class WorkflowError(DatabaseAnalystError):
    """工作流程错误"""
    pass

class ValidationError(DatabaseAnalystError):
    """验证错误"""
    pass