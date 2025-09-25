# 用户友好错误消息转换器
from typing import Dict, Any
from .error_types import ErrorCategory, ErrorContext, ErrorSeverity

class UserMessageTranslator:
    """用户友好错误消息转换器"""

    def __init__(self):
        self.message_templates = {
            ErrorCategory.BIGQUERY_QUOTA: {
                "title": "Data Processing Limit Reached",
                "message": "The system has reached its data processing limit. This usually resolves quickly.",
                "actions": [
                    "Wait 2-3 minutes and try again",
                    "Use a more specific date range",
                    "Focus on a particular brand or product category"
                ],
                "technical_note": "BigQuery quota exceeded"
            },

            ErrorCategory.BIGQUERY_SYNTAX: {
                "title": "Query Generation Issue",
                "message": "There was an issue generating the database query for your question.",
                "actions": [
                    "The system will automatically try a different approach",
                    "If the issue persists, try rephrasing your question",
                    "Use more specific business terms"
                ],
                "technical_note": "SQL syntax error"
            },

            ErrorCategory.LLM_TIMEOUT: {
                "title": "Processing Timeout",
                "message": "Your request is taking longer than expected to process.",
                "actions": [
                    "The system will automatically retry with a simplified approach",
                    "Try asking a more specific question",
                    "Break complex questions into smaller parts"
                ],
                "technical_note": "LLM request timeout"
            },

            ErrorCategory.DATA_TOO_LARGE: {
                "title": "Dataset Too Large",
                "message": "The requested analysis covers a very large dataset that may be difficult to process.",
                "actions": [
                    "Narrow your date range (e.g., last quarter instead of last year)",
                    "Focus on specific brands, categories, or channels",
                    "Request summary statistics instead of detailed data"
                ],
                "technical_note": "Data volume exceeds processing limits"
            },

            ErrorCategory.DATA_EMPTY: {
                "title": "No Data Found",
                "message": "Your query didn't return any data. This might be due to filters that are too restrictive.",
                "actions": [
                    "Expand your date range",
                    "Remove specific brand or category filters",
                    "Check if the requested data exists in our system",
                    "Try a broader version of your question"
                ],
                "technical_note": "Query returned zero results"
            },

            ErrorCategory.INVALID_QUESTION: {
                "title": "Question Not Understood",
                "message": "I'm having trouble understanding your business question.",
                "actions": [
                    "Try rephrasing using business terms like 'revenue', 'profit', 'sales'",
                    "Specify a time period (e.g., 'last quarter', 'this year')",
                    "Mention specific metrics you're interested in",
                    "Look at the example questions for guidance"
                ],
                "technical_note": "Question classification failed"
            },

            ErrorCategory.VALIDATION_FAILED: {
                "title": "Analysis Quality Check Failed",
                "message": "The generated analysis didn't meet our quality standards.",
                "actions": [
                    "The system is automatically regenerating the analysis",
                    "If issues persist, try a more specific question",
                    "Contact support if you continue experiencing problems"
                ],
                "technical_note": "Query validation failed"
            }
        }

    def translate_error(self, error_context: ErrorContext) -> Dict[str, Any]:
        """将技术错误转换为用户友好消息"""

        template = self.message_templates.get(
            error_context.error_category,
            self._get_default_template(error_context.severity)
        )

        # Customize message based on context
        customized_message = self._customize_message(template, error_context)

        return {
            "user_message": {
                "title": customized_message["title"],
                "message": customized_message["message"],
                "suggested_actions": customized_message["actions"],
                "severity": error_context.severity.value
            },
            "technical_details": {
                "category": error_context.error_category.value,
                "technical_note": template["technical_note"],
                "session_id": error_context.session_id,
                "retry_count": error_context.retry_count
            },
            "recovery_info": {
                "auto_recovery_attempted": error_context.recovery_suggestions is not None,
                "recovery_suggestions": error_context.recovery_suggestions or []
            }
        }

    def _customize_message(self, template: Dict, context: ErrorContext) -> Dict[str, Any]:
        """根据上下文定制消息"""

        customized = template.copy()

        # Add context-specific information
        if context.retry_count > 0:
            customized["message"] += f" (Attempt {context.retry_count + 1})"

        # Add question-specific suggestions
        if context.user_question:
            question_lower = context.user_question.lower()

            if "brand" in question_lower and context.error_category == ErrorCategory.DATA_EMPTY:
                customized["actions"].insert(0, "Check the spelling of the brand name")

            if "year" in question_lower and context.error_category == ErrorCategory.DATA_TOO_LARGE:
                customized["actions"].insert(0, "Try analyzing by quarter instead of the full year")

        return customized

    def _get_default_template(self, severity: ErrorSeverity) -> Dict[str, Any]:
        """获取默认模板"""

        if severity == ErrorSeverity.CRITICAL:
            return {
                "title": "System Error",
                "message": "A system error occurred while processing your request.",
                "actions": [
                    "Please try again in a few minutes",
                    "Contact support if the issue persists"
                ],
                "technical_note": "Unhandled system error"
            }
        else:
            return {
                "title": "Processing Issue",
                "message": "There was an issue processing your request.",
                "actions": [
                    "Try rephrasing your question",
                    "Check that your question is about business data analysis"
                ],
                "technical_note": "General processing error"
            }

# Global message translator instance
message_translator = UserMessageTranslator()