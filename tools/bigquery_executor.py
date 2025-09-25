"""
BigQuery Execution System
BigQuery执行系统

Comprehensive BigQuery tools for script execution, cost estimation, and result management
with enhanced error handling and optimization capabilities.
"""

from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError
import pandas as pd
import os
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
import json
import logging
from dataclasses import dataclass

from config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class QueryExecutionResult:
    """Data class for query execution results"""
    success: bool
    data: Optional[pd.DataFrame]
    row_count: int
    execution_time_seconds: float
    bytes_processed: int
    cost_estimate_usd: float
    error_message: Optional[str]
    query_job_id: Optional[str]


class BigQueryExecutor:
    """Enhanced BigQuery executor with comprehensive cost management and optimization"""

    def __init__(self):
        """初始化BigQuery执行器"""
        try:
            self.settings = get_settings()
            self.client = bigquery.Client()
            self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT', self.settings.google_cloud.project)
            self.dataset_id = os.getenv('BIGQUERY_DATASET', 'reporting_us')
            self.bigquery_project_id = os.getenv('GOOGLE_CLOUD__BIGQUERY_PROJECT_ID',
                                                self.settings.google_cloud.bigquery_project_id)
            self.max_bytes_limit = int(os.getenv('MAX_QUERY_SIZE_GB', 200)) * 1e9

            logger.info(f"BigQuery executor initialized with project: {self.bigquery_project_id}")

        except Exception as e:
            logger.error(f"Failed to initialize BigQuery executor: {e}")
            raise

    def estimate_query_cost_and_size(self, sql_query: str) -> Dict[str, Any]:
        """使用dry run估算查询成本和数据量"""

        try:
            # Configure dry run job
            job_config = bigquery.QueryJobConfig(
                dry_run=True,
                use_query_cache=False
            )

            # Execute dry run
            start_time = datetime.now()
            query_job = self.client.query(sql_query, job_config=job_config)
            end_time = datetime.now()

            # Calculate estimates
            bytes_processed = query_job.total_bytes_processed or 0
            cost_estimate = (bytes_processed / 1e12) * 5.0  # $5 per TB
            gb_processed = bytes_processed / 1e9

            # Check against limits
            within_limits = bytes_processed <= self.max_bytes_limit
            exceeds_limit = bytes_processed > self.max_bytes_limit

            estimation_result = {
                "success": True,
                "bytes_processed": bytes_processed,
                "gb_processed": round(gb_processed, 2),
                "cost_estimate_usd": round(cost_estimate, 4),
                "within_limits": within_limits,
                "exceeds_limit": exceeds_limit,
                "max_limit_gb": self.max_bytes_limit / 1e9,
                "estimation_time_ms": (end_time - start_time).total_seconds() * 1000,
                "recommendations": self._generate_size_recommendations(bytes_processed)
            }

            return estimation_result

        except GoogleCloudError as e:
            logger.error(f"BigQuery error during cost estimation: {e}")
            return {
                "success": False,
                "error": f"BigQuery error: {str(e)}",
                "error_type": "bigquery_error",
                "bytes_processed": None,
                "cost_estimate_usd": None,
                "within_limits": False
            }

        except Exception as e:
            logger.error(f"Unexpected error during cost estimation: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "error_type": "general_error",
                "bytes_processed": None,
                "cost_estimate_usd": None,
                "within_limits": False
            }

    def execute_bigquery_script(self, sql_query: str, timeout_seconds: int = 300) -> QueryExecutionResult:
        """执行BigQuery脚本并返回结果"""

        start_time = datetime.now()

        try:
            # First, check cost and size
            estimation = self.estimate_query_cost_and_size(sql_query)

            if not estimation["success"]:
                return QueryExecutionResult(
                    success=False,
                    data=None,
                    row_count=0,
                    execution_time_seconds=0,
                    bytes_processed=0,
                    cost_estimate_usd=0,
                    error_message=f"Cost estimation failed: {estimation['error']}",
                    query_job_id=None
                )

            if estimation["exceeds_limit"]:
                return QueryExecutionResult(
                    success=False,
                    data=None,
                    row_count=0,
                    execution_time_seconds=0,
                    bytes_processed=estimation["bytes_processed"],
                    cost_estimate_usd=estimation["cost_estimate_usd"],
                    error_message=f"Query exceeds {estimation['max_limit_gb']}GB limit. "
                                f"Processes {estimation['gb_processed']}GB",
                    query_job_id=None
                )

            # Configure actual execution job
            job_config = bigquery.QueryJobConfig(
                use_query_cache=True,
                maximum_bytes_billed=int(self.max_bytes_limit)
            )

            # Execute query
            query_job = self.client.query(sql_query, job_config=job_config)

            # Wait for completion with timeout
            try:
                results = query_job.result(timeout=timeout_seconds)
            except Exception as timeout_error:
                return QueryExecutionResult(
                    success=False,
                    data=None,
                    row_count=0,
                    execution_time_seconds=(datetime.now() - start_time).total_seconds(),
                    bytes_processed=estimation["bytes_processed"],
                    cost_estimate_usd=estimation["cost_estimate_usd"],
                    error_message=f"Query timeout after {timeout_seconds} seconds: {str(timeout_error)}",
                    query_job_id=query_job.job_id
                )

            # Convert to DataFrame
            df = results.to_dataframe()
            end_time = datetime.now()

            # Validate result size for token limits
            result_validation = self._validate_result_size(df)

            execution_result = QueryExecutionResult(
                success=True,
                data=df,
                row_count=len(df),
                execution_time_seconds=(end_time - start_time).total_seconds(),
                bytes_processed=query_job.total_bytes_processed or estimation["bytes_processed"],
                cost_estimate_usd=((query_job.total_bytes_processed or estimation["bytes_processed"]) / 1e12) * 5.0,
                error_message=None,
                query_job_id=query_job.job_id
            )

            # Add warnings for large results
            if not result_validation["within_token_limits"]:
                execution_result.error_message = result_validation["warning"]

            return execution_result

        except GoogleCloudError as e:
            logger.error(f"BigQuery execution error: {e}")
            return QueryExecutionResult(
                success=False,
                data=None,
                row_count=0,
                execution_time_seconds=(datetime.now() - start_time).total_seconds(),
                bytes_processed=0,
                cost_estimate_usd=0,
                error_message=f"BigQuery execution error: {str(e)}",
                query_job_id=None
            )

        except Exception as e:
            logger.error(f"Unexpected execution error: {e}")
            return QueryExecutionResult(
                success=False,
                data=None,
                row_count=0,
                execution_time_seconds=(datetime.now() - start_time).total_seconds(),
                bytes_processed=0,
                cost_estimate_usd=0,
                error_message=f"Unexpected execution error: {str(e)}",
                query_job_id=None
            )

    def _validate_result_size(self, df: pd.DataFrame) -> Dict[str, Any]:
        """验证结果大小是否在token限制内"""

        # Estimate token count (rough approximation)
        # Average ~4 characters per token for English text
        total_chars = sum(len(str(val)) for val in df.values.flatten())
        estimated_tokens = total_chars / 4

        max_tokens = int(os.getenv('MAX_TOKEN_LIMIT', 2000000))  # Very large limit
        within_limits = estimated_tokens <= max_tokens

        return {
            "within_token_limits": within_limits,
            "estimated_tokens": int(estimated_tokens),
            "max_tokens": max_tokens,
            "warning": None if within_limits else
                      f"Result size (~{int(estimated_tokens)} tokens) may exceed LLM limits ({max_tokens} tokens)"
        }

    def _generate_size_recommendations(self, bytes_processed: int) -> List[str]:
        """生成查询优化建议"""
        recommendations = []

        if bytes_processed > self.max_bytes_limit:
            gb_processed = bytes_processed / 1e9
            recommendations.extend([
                f"Query processes {gb_processed:.1f}GB, exceeds {self.max_bytes_limit/1e9}GB limit",
                "Add more restrictive WHERE clauses to limit date range",
                "Use LIMIT clause to cap result size",
                "Consider aggregating data instead of returning raw records",
                "Filter by specific brands, categories, or channels",
                "Use date partitioning for better performance"
            ])

        elif bytes_processed > (self.max_bytes_limit * 0.8):
            recommendations.append("Query is close to size limit, consider optimization")

        return recommendations

    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """获取表信息"""
        try:
            table_ref = f"{self.bigquery_project_id}.{self.dataset_id}.{table_name}"
            table = self.client.get_table(table_ref)

            return {
                "success": True,
                "table_id": table.table_id,
                "num_rows": table.num_rows,
                "num_bytes": table.num_bytes,
                "created": table.created.isoformat() if table.created else None,
                "modified": table.modified.isoformat() if table.modified else None,
                "schema": [{"name": field.name, "type": field.field_type, "mode": field.mode}
                          for field in table.schema]
            }

        except Exception as e:
            logger.error(f"Error getting table info for {table_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def list_tables(self) -> Dict[str, Any]:
        """列出数据集中的所有表"""
        try:
            dataset_ref = f"{self.bigquery_project_id}.{self.dataset_id}"
            dataset = self.client.get_dataset(dataset_ref)
            tables = list(self.client.list_tables(dataset))

            table_info = []
            for table in tables:
                table_details = self.client.get_table(table.reference)
                table_info.append({
                    "table_id": table.table_id,
                    "table_type": table.table_type,
                    "num_rows": table_details.num_rows,
                    "num_bytes": table_details.num_bytes,
                    "created": table_details.created.isoformat() if table_details.created else None
                })

            return {
                "success": True,
                "dataset_id": self.dataset_id,
                "table_count": len(table_info),
                "tables": table_info
            }

        except Exception as e:
            logger.error(f"Error listing tables: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class QueryOptimizer:
    """查询优化工具"""

    def __init__(self, executor: BigQueryExecutor):
        """初始化查询优化器"""
        self.executor = executor

    def optimize_query_for_size(self, original_query: str, target_gb: float = 50) -> Dict[str, Any]:
        """自动优化查询以减小数据处理量"""

        logger.info(f"Optimizing query for target size: {target_gb}GB")
        optimization_attempts = []

        # Get original estimation
        original_estimation = self.executor.estimate_query_cost_and_size(original_query)

        # Strategy 1: Add LIMIT if not present
        if "limit" not in original_query.lower():
            limited_query = self._add_limit_clause(original_query, 10000)
            estimation = self.executor.estimate_query_cost_and_size(limited_query)
            optimization_attempts.append({
                "strategy": "add_limit",
                "query": limited_query,
                "estimation": estimation,
                "gb_processed": estimation.get("gb_processed", 999)
            })

        # Strategy 2: Add date range restriction
        if "where" in original_query.lower() and "order_date" in original_query.lower():
            date_restricted_query = self._add_recent_date_filter(original_query)
            estimation = self.executor.estimate_query_cost_and_size(date_restricted_query)
            optimization_attempts.append({
                "strategy": "restrict_date_range",
                "query": date_restricted_query,
                "estimation": estimation,
                "gb_processed": estimation.get("gb_processed", 999)
            })

        # Strategy 3: Add aggregation if returning raw data
        if "group by" not in original_query.lower():
            aggregated_query = self._suggest_aggregation(original_query)
            if aggregated_query != original_query:
                estimation = self.executor.estimate_query_cost_and_size(aggregated_query)
                optimization_attempts.append({
                    "strategy": "add_aggregation",
                    "query": aggregated_query,
                    "estimation": estimation,
                    "gb_processed": estimation.get("gb_processed", 999)
                })

        # Select best optimization
        valid_attempts = [a for a in optimization_attempts
                         if a["estimation"]["success"] and a["gb_processed"] <= target_gb]

        if valid_attempts:
            best_attempt = min(valid_attempts, key=lambda x: x["gb_processed"])
            return {
                "success": True,
                "optimized_query": best_attempt["query"],
                "strategy_used": best_attempt["strategy"],
                "gb_reduction": original_estimation.get("gb_processed", 999) - best_attempt["gb_processed"],
                "original_gb": original_estimation.get("gb_processed", 999),
                "optimized_gb": best_attempt["gb_processed"],
                "all_attempts": optimization_attempts
            }
        else:
            return {
                "success": False,
                "optimized_query": original_query,
                "strategy_used": None,
                "error": "Could not optimize query to meet size requirements",
                "original_gb": original_estimation.get("gb_processed", 999),
                "target_gb": target_gb,
                "all_attempts": optimization_attempts
            }

    def _add_limit_clause(self, query: str, limit: int) -> str:
        """添加LIMIT子句"""
        if query.strip().endswith(';'):
            query = query.strip()[:-1]
        return f"{query}\nLIMIT {limit}"

    def _add_recent_date_filter(self, query: str, days_back: int = 90) -> str:
        """添加最近日期过滤器"""
        cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

        # Simple approach: add to WHERE clause
        where_pos = query.lower().find("where")
        if where_pos != -1:
            # Find end of WHERE clause
            group_pos = query.lower().find("group by", where_pos)
            order_pos = query.lower().find("order by", where_pos)
            limit_pos = query.lower().find("limit", where_pos)

            insert_pos = len(query)
            for pos in [group_pos, order_pos, limit_pos]:
                if pos != -1 and pos < insert_pos:
                    insert_pos = pos

            additional_filter = f" AND order_date >= '{cutoff_date}'"
            return query[:insert_pos] + additional_filter + query[insert_pos:]

        return query

    def _suggest_aggregation(self, query: str) -> str:
        """建议聚合查询替代原始数据"""
        # This is a simplified approach - in practice, would need more sophisticated parsing
        if "select" in query.lower() and "sum(" not in query.lower() and "group by" not in query.lower():
            # Try to add basic aggregation
            if "order_date" in query.lower() and "sub_brand" in query.lower():
                # Replace detailed selection with aggregated version
                return query.replace(
                    "SELECT *",
                    "SELECT sub_brand as brand_name, DATE_TRUNC(order_date, MONTH) as month, "
                    "SUM(net_revenue_usd) as total_revenue, COUNT(*) as order_count"
                ).replace(
                    "ORDER BY order_date",
                    "GROUP BY sub_brand, month ORDER BY month"
                )
        return query

    def analyze_query_complexity(self, query: str) -> Dict[str, Any]:
        """分析查询复杂度"""
        query_lower = query.lower()

        complexity_score = 0
        complexity_factors = []

        # Count various complexity factors
        join_count = query_lower.count("join")
        subquery_count = query_lower.count("(select")
        window_function_count = query_lower.count("over(")

        if "select *" in query_lower:
            complexity_score += 2
            complexity_factors.append("SELECT * used")

        complexity_score += join_count * 1
        if join_count > 0:
            complexity_factors.append(f"{join_count} JOIN operations")

        complexity_score += subquery_count * 3
        if subquery_count > 0:
            complexity_factors.append(f"{subquery_count} subqueries")

        complexity_score += window_function_count * 4
        if window_function_count > 0:
            complexity_factors.append(f"{window_function_count} window functions")

        if "group by" in query_lower:
            complexity_score += 2
            complexity_factors.append("GROUP BY aggregation")

        if "order by" in query_lower:
            complexity_score += 1
            complexity_factors.append("ORDER BY sorting")

        # Determine complexity level
        if complexity_score <= 3:
            complexity_level = "Low"
        elif complexity_score <= 8:
            complexity_level = "Medium"
        else:
            complexity_level = "High"

        return {
            "complexity_score": complexity_score,
            "complexity_level": complexity_level,
            "complexity_factors": complexity_factors,
            "recommendations": self._get_complexity_recommendations(complexity_score, complexity_factors)
        }

    def _get_complexity_recommendations(self, score: int, factors: List[str]) -> List[str]:
        """获取复杂度优化建议"""
        recommendations = []

        if score > 10:
            recommendations.append("Consider breaking this query into smaller, simpler queries")

        if "SELECT * used" in factors:
            recommendations.append("Replace SELECT * with specific column names for better performance")

        if any("subqueries" in factor for factor in factors):
            recommendations.append("Consider using JOINs instead of subqueries where possible")

        if any("window functions" in factor for factor in factors):
            recommendations.append("Window functions can be expensive - ensure they are necessary")

        return recommendations