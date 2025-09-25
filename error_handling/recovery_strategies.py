# 错误恢复策略实现
from typing import Dict, Any, Optional
from .error_types import ErrorCategory, ErrorContext

class RecoveryManager:
    """恢复管理器"""

    def __init__(self):
        self.recovery_strategies = {
            ErrorCategory.BIGQUERY_QUOTA: self._recover_from_bigquery_quota,
            ErrorCategory.BIGQUERY_SYNTAX: self._recover_from_syntax_error,
            ErrorCategory.LLM_TIMEOUT: self._recover_from_llm_timeout,
            ErrorCategory.LLM_CONTEXT_LENGTH: self._recover_from_context_length,
            ErrorCategory.DATA_TOO_LARGE: self._recover_from_large_data,
            ErrorCategory.DATA_EMPTY: self._recover_from_empty_data,
            ErrorCategory.VALIDATION_FAILED: self._recover_from_validation_failure
        }

    def attempt_recovery(self, error_context: ErrorContext) -> Dict[str, Any]:
        """尝试错误恢复"""

        recovery_strategy = self.recovery_strategies.get(error_context.error_category)

        if recovery_strategy:
            try:
                recovery_result = recovery_strategy(error_context)
                return {
                    "recovery_attempted": True,
                    "recovery_successful": recovery_result.get("success", False),
                    "recovery_actions": recovery_result.get("actions", []),
                    "modified_state": recovery_result.get("modified_state", {}),
                    "user_guidance": recovery_result.get("user_guidance", "")
                }

            except Exception as recovery_error:
                return {
                    "recovery_attempted": True,
                    "recovery_successful": False,
                    "recovery_error": str(recovery_error),
                    "user_guidance": "Unable to recover automatically. Manual intervention required."
                }

        return {
            "recovery_attempted": False,
            "user_guidance": f"No automatic recovery available for {error_context.error_category.value}"
        }

    def _recover_from_bigquery_quota(self, context: ErrorContext) -> Dict[str, Any]:
        """从BigQuery配额错误恢复"""

        # Strategy 1: Reduce query complexity
        if context.additional_context and "generated_sql" in context.additional_context:
            sql = context.additional_context["generated_sql"]

            # Add more restrictive filters
            optimized_sql = self._optimize_query_for_quota(sql)

            return {
                "success": True,
                "actions": ["reduced_query_complexity", "added_date_filters"],
                "modified_state": {"generated_sql": optimized_sql},
                "user_guidance": "Query has been optimized to reduce data processing requirements."
            }

        # Strategy 2: Suggest waiting and retry
        return {
            "success": False,
            "actions": ["suggest_wait_and_retry"],
            "user_guidance": "BigQuery quota exceeded. Please wait a few minutes and try again, or consider using a more specific date range."
        }

    def _recover_from_syntax_error(self, context: ErrorContext) -> Dict[str, Any]:
        """从SQL语法错误恢复"""

        return {
            "success": False,
            "actions": ["trigger_query_regeneration"],
            "modified_state": {"retry_generation": True, "use_simpler_template": True},
            "user_guidance": "SQL syntax error detected. Regenerating query with improved validation."
        }

    def _recover_from_llm_timeout(self, context: ErrorContext) -> Dict[str, Any]:
        """从LLM超时恢复"""

        # Strategy: Reduce input complexity
        simplified_context = self._simplify_llm_input(context.additional_context)

        return {
            "success": True,
            "actions": ["reduced_input_complexity", "use_shorter_prompt"],
            "modified_state": simplified_context,
            "user_guidance": "Request simplified to improve response time."
        }

    def _recover_from_context_length(self, context: ErrorContext) -> Dict[str, Any]:
        """从LLM上下文长度限制恢复"""

        # Strategy: Truncate input data
        if context.additional_context and "sample_data" in context.additional_context:
            sample_data = context.additional_context["sample_data"]
            truncated_data = sample_data[:50]  # Keep only first 50 rows

            return {
                "success": True,
                "actions": ["truncated_sample_data"],
                "modified_state": {"sample_data": truncated_data},
                "user_guidance": "Sample data has been reduced to fit processing limits."
            }

        return {
            "success": False,
            "actions": ["suggest_simpler_question"],
            "user_guidance": "Question complexity exceeds processing limits. Please try a more specific question."
        }

    def _recover_from_large_data(self, context: ErrorContext) -> Dict[str, Any]:
        """从数据量过大错误恢复"""

        recovery_actions = []

        # Strategy 1: Add LIMIT clause
        if context.additional_context and "generated_sql" in context.additional_context:
            sql = context.additional_context["generated_sql"]

            if "LIMIT" not in sql.upper():
                limited_sql = sql.rstrip(';') + " LIMIT 1000;"
                recovery_actions.append("added_limit_clause")

                return {
                    "success": True,
                    "actions": recovery_actions,
                    "modified_state": {"generated_sql": limited_sql},
                    "user_guidance": "Query has been limited to 1000 rows to manage data size."
                }

        # Strategy 2: Suggest aggregation
        return {
            "success": False,
            "actions": ["suggest_aggregation"],
            "user_guidance": "Dataset is too large. Consider requesting summary statistics instead of detailed data."
        }

    def _recover_from_empty_data(self, context: ErrorContext) -> Dict[str, Any]:
        """从空数据错误恢复"""

        suggestions = [
            "Expand the date range for your analysis",
            "Remove restrictive filters (brand, category, etc.)",
            "Check if the requested data exists in the database",
            "Try a broader version of your question"
        ]

        return {
            "success": False,
            "actions": ["provide_suggestions"],
            "user_guidance": f"No data found. Try these suggestions: {'; '.join(suggestions)}"
        }

    def _recover_from_validation_failure(self, context: ErrorContext) -> Dict[str, Any]:
        """从验证失败恢复"""

        if context.retry_count < 2:
            return {
                "success": True,
                "actions": ["trigger_regeneration_with_feedback"],
                "modified_state": {
                    "regenerate_with_validation_feedback": True,
                    "validation_errors": context.error_message
                },
                "user_guidance": "Regenerating query based on validation feedback."
            }

        return {
            "success": False,
            "actions": ["escalate_to_manual_review"],
            "user_guidance": "Unable to automatically generate a valid query. Please try rephrasing your question."
        }

    def _optimize_query_for_quota(self, sql: str) -> str:
        """为配额限制优化查询"""

        # Add more restrictive date filter
        if "WHERE" in sql.upper():
            # Find WHERE clause and add date restriction
            sql_parts = sql.split("WHERE")
            if len(sql_parts) >= 2:
                additional_filter = " AND f.order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)"
                sql = sql_parts[0] + "WHERE" + sql_parts[1] + additional_filter

        # Add LIMIT if not present
        if "LIMIT" not in sql.upper():
            sql = sql.rstrip(';') + " LIMIT 100;"

        return sql

    def _simplify_llm_input(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """简化LLM输入"""

        if not context:
            return {}

        simplified = {}

        for key, value in context.items():
            if isinstance(value, str) and len(value) > 1000:
                simplified[key] = value[:1000] + "..."
            elif isinstance(value, list) and len(value) > 10:
                simplified[key] = value[:10]
            else:
                simplified[key] = value

        return simplified