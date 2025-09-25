# 错误日志记录和监控集成
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from .error_types import ErrorContext, ErrorSeverity

class ErrorLogger:
    """错误日志记录器"""

    def __init__(self):
        self.setup_logging()
        self.error_aggregator = ErrorAggregator()

    def setup_logging(self):
        """设置日志记录"""

        # Ensure logs directory exists
        os.makedirs("logs", exist_ok=True)

        # Create error-specific logger
        self.logger = logging.getLogger("ai_database_analyst_errors")
        self.logger.setLevel(logging.INFO)

        # Clear existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # Create file handler for error logs
        error_handler = logging.FileHandler("logs/error_log.jsonl")
        error_handler.setLevel(logging.ERROR)

        # Create console handler for immediate feedback
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)

        # Create formatters
        json_formatter = JsonFormatter()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        error_handler.setFormatter(json_formatter)
        console_handler.setFormatter(console_formatter)

        self.logger.addHandler(error_handler)
        self.logger.addHandler(console_handler)

    def log_error_with_context(self, error_context: ErrorContext):
        """记录带上下文的错误"""

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": error_context.session_id,
            "step_name": error_context.step_name,
            "error_category": error_context.error_category.value,
            "severity": error_context.severity.value,
            "error_message": error_context.error_message,
            "retry_count": error_context.retry_count,
            "user_question": error_context.user_question[:200],  # Truncate for privacy
            "additional_context": self._sanitize_context(error_context.additional_context),
            "recovery_suggestions": error_context.recovery_suggestions
        }

        # Log based on severity
        if error_context.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(json.dumps(log_entry))
        elif error_context.severity == ErrorSeverity.HIGH:
            self.logger.error(json.dumps(log_entry))
        elif error_context.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(json.dumps(log_entry))
        else:
            self.logger.info(json.dumps(log_entry))

        # Aggregate for monitoring
        self.error_aggregator.record_error(error_context)

        # Send to LangSmith for correlation
        self._send_to_langsmith(log_entry)

    def _sanitize_context(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """清理上下文信息"""
        if not context:
            return {}

        sanitized = {}
        for key, value in context.items():
            if any(sensitive in key.lower() for sensitive in ['key', 'token', 'password', 'secret']):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, str) and len(value) > 500:
                sanitized[key] = value[:500] + "..."
            else:
                sanitized[key] = value

        return sanitized

    def _send_to_langsmith(self, log_entry: Dict[str, Any]):
        """发送错误日志到LangSmith"""
        try:
            # Check if monitoring module exists
            import importlib.util
            spec = importlib.util.find_spec("monitoring.langsmith_integration")

            if spec is not None:
                from monitoring.langsmith_integration import langsmith_config

                langsmith_config.client.create_run(
                    name="error_log",
                    run_type="tool",
                    inputs={"log_type": "error"},
                    outputs=log_entry,
                    project_name="ai-database-analyst"
                )
        except Exception as e:
            # Don't let logging errors break the main flow
            print(f"Failed to send error log to LangSmith: {e}")

class JsonFormatter(logging.Formatter):
    """JSON格式化器"""

    def format(self, record):
        log_obj = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        if hasattr(record, 'session_id'):
            log_obj["session_id"] = record.session_id

        return json.dumps(log_obj)

class ErrorAggregator:
    """错误聚合器"""

    def __init__(self):
        self.error_counts = {}
        self.error_trends = {}

    def record_error(self, error_context: ErrorContext):
        """记录错误用于聚合分析"""

        # Count by category
        category = error_context.error_category.value
        self.error_counts[category] = self.error_counts.get(category, 0) + 1

        # Track trends by hour
        hour_key = datetime.now().strftime("%Y-%m-%d %H:00")
        if hour_key not in self.error_trends:
            self.error_trends[hour_key] = {}

        self.error_trends[hour_key][category] = self.error_trends[hour_key].get(category, 0) + 1

    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """获取错误摘要"""

        recent_trends = {}
        cutoff_time = datetime.now() - timedelta(hours=hours)

        for time_key, errors in self.error_trends.items():
            try:
                if datetime.fromisoformat(time_key + ":00") >= cutoff_time:
                    recent_trends[time_key] = errors
            except ValueError:
                # Skip invalid time keys
                continue

        return {
            "total_errors_by_category": self.error_counts,
            "recent_trends": recent_trends,
            "most_common_errors": sorted(self.error_counts.items(),
                                       key=lambda x: x[1], reverse=True)[:5]
        }

# Global error logger instance
error_logger = ErrorLogger()

def log_error_with_context(error_context: ErrorContext):
    """全局错误记录函数"""
    error_logger.log_error_with_context(error_context)