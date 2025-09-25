# 错误检测和分类系统
import re
import traceback
from typing import Tuple, Optional, Dict, Any
from .error_types import ErrorCategory

class ErrorDetector:
    """错误检测器"""

    def __init__(self):
        self.error_patterns = {
            # BigQuery Error Patterns
            ErrorCategory.BIGQUERY_QUOTA: [
                r"quota.*exceeded",
                r"rate limit.*exceeded",
                r"too many requests"
            ],
            ErrorCategory.BIGQUERY_SYNTAX: [
                r"syntax error",
                r"invalid.*query",
                r"unrecognized name",
                r"table.*not found"
            ],
            ErrorCategory.BIGQUERY_PERMISSION: [
                r"permission denied",
                r"access denied",
                r"forbidden",
                r"unauthorized"
            ],

            # LLM Error Patterns
            ErrorCategory.LLM_TIMEOUT: [
                r"timeout",
                r"request.*timed out",
                r"connection.*timeout"
            ],
            ErrorCategory.LLM_QUOTA: [
                r"rate limit",
                r"quota.*exceeded",
                r"too many tokens"
            ],
            ErrorCategory.LLM_CONTEXT_LENGTH: [
                r"context.*too long",
                r"maximum.*length.*exceeded",
                r"token limit.*exceeded"
            ],

            # Data Error Patterns
            ErrorCategory.DATA_TOO_LARGE: [
                r"dataset.*too large",
                r"exceeds.*limit",
                r"memory.*error"
            ],
            ErrorCategory.DATA_EMPTY: [
                r"no.*data.*returned",
                r"empty.*result",
                r"zero.*rows"
            ]
        }

    def detect_error_category(self, error_message: str) -> Tuple[ErrorCategory, float]:
        """检测错误类别"""

        error_message_lower = error_message.lower()
        best_match = None
        highest_confidence = 0.0

        for category, patterns in self.error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, error_message_lower):
                    # Calculate confidence based on pattern specificity
                    confidence = self._calculate_pattern_confidence(pattern, error_message_lower)
                    if confidence > highest_confidence:
                        highest_confidence = confidence
                        best_match = category

        if best_match:
            return best_match, highest_confidence
        else:
            return ErrorCategory.VALIDATION_FAILED, 0.5  # Default category

    def _calculate_pattern_confidence(self, pattern: str, error_message: str) -> float:
        """计算模式匹配置信度"""
        # Simple confidence calculation - could be enhanced
        if len(pattern) > 20:
            return 0.9  # More specific patterns get higher confidence
        elif len(pattern) > 10:
            return 0.7
        else:
            return 0.5

    def extract_error_details(self, error: Exception) -> Dict[str, Any]:
        """提取错误详细信息"""

        error_details = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "stack_trace": traceback.format_exc(),
        }

        # Extract additional context based on error type
        if hasattr(error, 'response'):
            error_details["response_status"] = getattr(error.response, 'status_code', None)

        if hasattr(error, 'code'):
            error_details["error_code"] = error.code

        return error_details