"""
Script Validation Tools
脚本验证工具

Comprehensive tools for validating BigQuery script execution results,
including LLM_B integration, data quality analysis, and improvement suggestions.
"""

import json
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog
import pandas as pd
import numpy as np

from config import get_settings
from config.prompt_templates import SCRIPT_VALIDATION_PROMPT

logger = structlog.get_logger()


class ScriptResultValidator:
    """脚本结果验证器 - 使用LLM_B进行验证"""

    def __init__(self):
        """初始化验证器"""
        self.llm = self._initialize_llm_b()
        self.quality_thresholds = {
            "data_relevance": 0.7,
            "data_completeness": 0.6,
            "result_interpretability": 0.8,
            "overall_quality": 0.7
        }

    def _initialize_llm_b(self):
        """初始化LLM_B"""
        try:
            from langchain_google_vertexai import ChatVertexAI
            settings = get_settings()

            # Use Gemini-2.5-Pro for validation (LLM_B)
            return ChatVertexAI(
                model="gemini-2.5-pro",  # Using Gemini instead of GPT-4
                temperature=0.1,  # Lower temperature for more consistent validation
                project=settings.google_cloud.project_id
                # max_output_tokens removed - use model's full capacity
            )
        except Exception as e:
            logger.warning(f"Could not initialize LLM_B: {e}")
            return None

    def validate_execution_results(self,
                                 user_question: str,
                                 execution_result: Dict[str, Any],
                                 sql_query: str) -> Dict[str, Any]:
        """使用LLM_B验证脚本执行结果"""

        try:
            validation_prompt = self._build_validation_prompt(
                user_question, execution_result, sql_query
            )

            # Call LLM_B for validation
            if self.llm:
                llm_response = self._call_llm_b(validation_prompt)
                validation_assessment = self._parse_validation_response(llm_response)
            else:
                # Fallback validation without LLM
                validation_assessment = self._fallback_validation(
                    user_question, execution_result, sql_query
                )

            # Calculate overall validation decision
            decision = self._make_validation_decision(validation_assessment)

            return {
                "validation_decision": decision["decision"],
                "quality_scores": validation_assessment["quality_scores"],
                "data_quality_metrics": validation_assessment["data_quality"],
                "improvement_suggestions": validation_assessment["suggestions"],
                "validation_reasoning": validation_assessment["reasoning"],
                "llm_confidence": validation_assessment.get("confidence", 0.8)
            }

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {
                "validation_decision": "needs_revision",
                "quality_scores": {"overall_weighted_score": 0.3},
                "data_quality_metrics": {"has_meaningful_data": False},
                "improvement_suggestions": [f"Validation process failed: {str(e)}"],
                "validation_reasoning": f"Technical error in validation: {str(e)}",
                "llm_confidence": 0.1
            }

    def _build_validation_prompt(self,
                               user_question: str,
                               execution_result: Dict[str, Any],
                               sql_query: str) -> str:
        """构建LLM_B验证提示词"""

        return SCRIPT_VALIDATION_PROMPT.format(
            user_question=user_question,
            sql_query=sql_query,
            execution_success=execution_result.get("success", False),
            row_count=execution_result.get("row_count", 0),
            execution_time=execution_result.get("execution_time_seconds", 0),
            bytes_processed=execution_result.get("bytes_processed", 0),
            cost_estimate=execution_result.get("cost_estimate_usd", 0),
            error_message=execution_result.get("error_message", "None"),
            sample_data=self._format_sample_data(execution_result.get("sample_data", [])),
            data_summary=self._format_data_summary(execution_result.get("summary", {}))
        )

    def _call_llm_b(self, prompt: str) -> str:
        """调用LLM_B进行验证"""
        try:
            response = self.llm.invoke(prompt)
            return response.content
        except Exception as e:
            logger.error(f"LLM_B call failed: {e}")
            raise

    def _parse_validation_response(self, response: str) -> Dict[str, Any]:
        """解析LLM_B验证响应"""
        try:
            # Try to extract JSON from response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1

            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                parsed = json.loads(json_str)

                # Validate required fields
                required_fields = ['quality_scores', 'validation_decision', 'reasoning']
                for field in required_fields:
                    if field not in parsed:
                        raise ValueError(f"Missing required field: {field}")

                return {
                    "quality_scores": parsed.get("quality_scores", {}),
                    "data_quality": parsed.get("data_quality_metrics", {}),
                    "suggestions": parsed.get("improvement_suggestions", []),
                    "reasoning": parsed.get("reasoning", ""),
                    "confidence": parsed.get("confidence", 0.8),
                    "validation_decision": parsed.get("validation_decision", "needs_revision")
                }
            else:
                raise ValueError("No valid JSON found in response")

        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            # Return fallback response
            return self._create_fallback_assessment(response)

    def _create_fallback_assessment(self, response: str) -> Dict[str, Any]:
        """创建回退评估结果"""
        return {
            "quality_scores": {
                "data_relevance": 0.5,
                "data_completeness": 0.5,
                "data_quality": 0.5,
                "token_compliance": 0.8,
                "result_interpretability": 0.5,
                "overall_weighted_score": 0.5
            },
            "data_quality": {
                "has_meaningful_data": True,
                "appropriate_time_range": True,
                "relevant_metrics": True,
                "reasonable_data_volume": True
            },
            "suggestions": ["Review validation results and retry if needed"],
            "reasoning": "Automated fallback assessment due to parsing issues",
            "confidence": 0.3,
            "validation_decision": "needs_revision"
        }

    def _fallback_validation(self,
                           user_question: str,
                           execution_result: Dict[str, Any],
                           sql_query: str) -> Dict[str, Any]:
        """不使用LLM的回退验证"""

        # Basic rule-based validation
        success = execution_result.get("success", False)
        row_count = execution_result.get("row_count", 0)
        error_message = execution_result.get("error_message", "")

        if not success:
            return {
                "quality_scores": {
                    "overall_weighted_score": 0.0
                },
                "data_quality": {"has_meaningful_data": False},
                "suggestions": [f"Execution failed: {error_message}"],
                "reasoning": "Query execution failed",
                "confidence": 0.9,
                "validation_decision": "rejected"
            }

        if row_count == 0:
            return {
                "quality_scores": {
                    "overall_weighted_score": 0.3
                },
                "data_quality": {"has_meaningful_data": False},
                "suggestions": ["No data returned - check query filters"],
                "reasoning": "Query returned no results",
                "confidence": 0.8,
                "validation_decision": "needs_revision"
            }

        # Basic successful validation
        return {
            "quality_scores": {
                "data_relevance": 0.7,
                "data_completeness": 0.8,
                "data_quality": 0.7,
                "token_compliance": 1.0,
                "result_interpretability": 0.8,
                "overall_weighted_score": 0.75
            },
            "data_quality": {
                "has_meaningful_data": True,
                "appropriate_time_range": True,
                "relevant_metrics": True,
                "reasonable_data_volume": True
            },
            "suggestions": [],
            "reasoning": "Basic validation passed - query executed successfully with data",
            "confidence": 0.6,
            "validation_decision": "approved"
        }

    def _make_validation_decision(self, assessment: Dict[str, Any]) -> Dict[str, str]:
        """基于评估结果做出验证决策"""
        overall_score = assessment.get("quality_scores", {}).get("overall_weighted_score", 0.0)

        if overall_score >= self.quality_thresholds["overall_quality"]:
            decision = "approved"
        elif overall_score >= 0.5:
            decision = "needs_revision"
        else:
            decision = "rejected"

        return {"decision": decision}

    def _format_sample_data(self, sample_data: List[Dict]) -> str:
        """格式化示例数据用于LLM分析"""
        if not sample_data:
            return "No sample data available"

        try:
            # Convert to readable table format
            if len(sample_data) > 0:
                headers = list(sample_data[0].keys())
                rows = []
                for item in sample_data[:5]:  # First 5 rows only
                    row = [str(item.get(h, "")) for h in headers]
                    rows.append(" | ".join(row))

                table = "| " + " | ".join(headers) + " |\n"
                table += "|" + "|".join(["---"] * len(headers)) + "|\n"
                for row in rows:
                    table += "| " + row + " |\n"

                return table
        except Exception as e:
            logger.warning(f"Error formatting sample data: {e}")

        return "No data rows available"

    def _format_data_summary(self, summary: Dict) -> str:
        """格式化数据摘要"""
        if not summary:
            return "No summary available"

        try:
            basic_info = summary.get("basic_info", {})
            summary_text = f"Total Rows: {basic_info.get('total_rows', 'Unknown')}\n"
            summary_text += f"Columns: {', '.join(basic_info.get('columns', []))}\n"

            # Add statistics for numeric columns
            numeric_analysis = summary.get("numeric_analysis", {})
            for col_name, stats in numeric_analysis.items():
                summary_text += f"{col_name}: min={stats.get('min')}, max={stats.get('max')}, sum={stats.get('sum')}\n"

            return summary_text
        except Exception as e:
            logger.warning(f"Error formatting data summary: {e}")
            return "Summary formatting failed"


class DataQualityAnalyzer:
    """数据质量分析器"""

    def __init__(self):
        """初始化质量分析器"""
        self.quality_checks = [
            self._check_data_completeness,
            self._check_value_ranges,
            self._check_null_ratios,
            self._check_data_consistency,
            self._check_business_logic
        ]

    def analyze_data_quality(self, data: List[Dict], user_question: str) -> Dict[str, Any]:
        """综合数据质量分析"""

        if not data:
            return {
                "overall_quality_score": 0.0,
                "issues": ["No data returned"],
                "recommendations": ["Review query filters and data availability"],
                "detailed_checks": {}
            }

        quality_results = {}
        for check in self.quality_checks:
            try:
                result = check(data, user_question)
                quality_results[check.__name__] = result
            except Exception as e:
                logger.warning(f"Quality check {check.__name__} failed: {e}")
                quality_results[check.__name__] = {
                    "score": 0.5,
                    "issues": [f"Quality check failed: {str(e)}"],
                    "recommendations": []
                }

        # Calculate overall quality score
        scores = [r.get("score", 0.5) for r in quality_results.values()]
        overall_score = sum(scores) / len(scores) if scores else 0.0

        # Aggregate all issues and recommendations
        all_issues = []
        all_recommendations = []
        for result in quality_results.values():
            all_issues.extend(result.get("issues", []))
            all_recommendations.extend(result.get("recommendations", []))

        return {
            "overall_quality_score": overall_score,
            "detailed_checks": quality_results,
            "issues": list(set(all_issues)),
            "recommendations": list(set(all_recommendations))
        }

    def _check_data_completeness(self, data: List[Dict], question: str) -> Dict:
        """检查数据完整性"""
        if len(data) == 0:
            return {
                "score": 0.0,
                "issues": ["No data returned"],
                "recommendations": ["Check query filters and data availability"]
            }

        # Check for reasonable data volume
        if len(data) < 5:
            return {
                "score": 0.3,
                "issues": ["Very limited data returned"],
                "recommendations": ["Expand date range or remove restrictive filters"]
            }

        if len(data) > 10000:
            return {
                "score": 0.7,
                "issues": ["Very large result set"],
                "recommendations": ["Consider aggregation to reduce data volume"]
            }

        return {
            "score": 1.0,
            "issues": [],
            "recommendations": []
        }

    def _check_value_ranges(self, data: List[Dict], question: str) -> Dict:
        """检查数值范围合理性"""
        issues = []
        recommendations = []

        try:
            for item in data[:100]:  # Check first 100 rows
                for key, value in item.items():
                    if isinstance(value, (int, float)):
                        # Check for extremely large values
                        if abs(value) > 1e12:
                            issues.append(f"Extremely large value in {key}: {value}")
                        # Check for negative values where they shouldn't be
                        if "count" in key.lower() and value < 0:
                            issues.append(f"Negative count value in {key}: {value}")

            score = 1.0 if not issues else max(0.3, 1.0 - len(issues) * 0.2)

            return {
                "score": score,
                "issues": issues[:5],  # Limit to first 5 issues
                "recommendations": recommendations
            }

        except Exception as e:
            return {
                "score": 0.7,
                "issues": [f"Value range check failed: {str(e)}"],
                "recommendations": []
            }

    def _check_null_ratios(self, data: List[Dict], question: str) -> Dict:
        """检查空值比例"""
        if not data:
            return {"score": 0.0, "issues": ["No data to analyze"], "recommendations": []}

        try:
            null_ratios = {}
            total_rows = len(data)

            for key in data[0].keys():
                null_count = sum(1 for item in data if item.get(key) is None or item.get(key) == "")
                null_ratios[key] = null_count / total_rows

            high_null_columns = [col for col, ratio in null_ratios.items() if ratio > 0.5]

            if high_null_columns:
                return {
                    "score": 0.4,
                    "issues": [f"High null ratios in columns: {', '.join(high_null_columns)}"],
                    "recommendations": ["Review data quality or adjust query to exclude sparse columns"]
                }

            return {
                "score": 1.0,
                "issues": [],
                "recommendations": []
            }

        except Exception as e:
            return {
                "score": 0.7,
                "issues": [f"Null ratio check failed: {str(e)}"],
                "recommendations": []
            }

    def _check_data_consistency(self, data: List[Dict], question: str) -> Dict:
        """检查数据一致性"""
        issues = []
        recommendations = []

        try:
            # Check for duplicate rows
            if len(data) > 1:
                data_str_list = [json.dumps(item, sort_keys=True, default=str) for item in data]
                unique_count = len(set(data_str_list))
                duplicate_count = len(data) - unique_count

                if duplicate_count > len(data) * 0.1:  # More than 10% duplicates
                    issues.append(f"High duplicate rate: {duplicate_count} duplicates out of {len(data)} rows")
                    recommendations.append("Consider adding DISTINCT clause or reviewing aggregation logic")

            score = 1.0 if not issues else 0.6

            return {
                "score": score,
                "issues": issues,
                "recommendations": recommendations
            }

        except Exception as e:
            return {
                "score": 0.7,
                "issues": [f"Consistency check failed: {str(e)}"],
                "recommendations": []
            }

    def _check_business_logic(self, data: List[Dict], question: str) -> Dict:
        """检查业务逻辑合理性"""
        issues = []
        recommendations = []

        try:
            # Check for negative revenues or units (shouldn't normally happen)
            for item in data[:100]:  # Check first 100 rows
                for key, value in item.items():
                    if isinstance(value, (int, float)):
                        if "revenue" in key.lower() and value < 0:
                            issues.append(f"Negative revenue found: {value}")
                        if "units" in key.lower() and value < 0:
                            issues.append(f"Negative units found: {value}")

            # Check for extremely high values that might indicate data issues
            for item in data[:100]:
                for key, value in item.items():
                    if isinstance(value, (int, float)) and value > 1e9:
                        issues.append(f"Extremely high value in {key}: {value}")

            score = 1.0 if not issues else 0.6 if len(issues) < 5 else 0.3

            return {
                "score": score,
                "issues": issues[:5],  # Limit to first 5 issues
                "recommendations": recommendations
            }

        except Exception as e:
            return {
                "score": 0.7,
                "issues": [f"Business logic check failed: {str(e)}"],
                "recommendations": []
            }


class ImprovementSuggestionGenerator:
    """改进建议生成器"""

    def __init__(self):
        """初始化建议生成器"""
        self.suggestion_templates = {
            "data_relevance": [
                "Adjust WHERE clauses to filter for more relevant data",
                "Include additional columns that directly address the user question",
                "Modify time range to capture more appropriate business period"
            ],
            "data_completeness": [
                "Expand date range to include more historical data",
                "Remove overly restrictive filters",
                "Include additional business entities (brands, categories, etc.)"
            ],
            "data_quality": [
                "Add data validation checks to exclude invalid records",
                "Include null handling for better data quality",
                "Filter out outliers that may skew analysis"
            ],
            "performance": [
                "Add LIMIT clause to reduce result size",
                "Use aggregation instead of returning raw data",
                "Optimize date range for better performance"
            ]
        }

    def generate_suggestions(self,
                           validation_result: Dict,
                           execution_result: Dict,
                           user_question: str) -> List[str]:
        """生成具体的改进建议"""

        suggestions = []
        quality_scores = validation_result.get("quality_scores", {})

        # Generate suggestions based on low quality scores
        for metric, score in quality_scores.items():
            if score < 0.7:
                suggestions.extend(self.suggestion_templates.get(metric, []))

        # Add specific suggestions based on execution issues
        if not execution_result.get("success", False):
            error_message = execution_result.get("error_message", "")
            if "timeout" in error_message.lower():
                suggestions.append("Optimize query performance by adding more restrictive filters")
            if "limit" in error_message.lower():
                suggestions.append("Reduce data processing by using aggregation or smaller time windows")

        # Customize suggestions based on user question intent
        question_lower = user_question.lower()
        if "trend" in question_lower:
            suggestions.append("Consider adding ORDER BY date for trend analysis")

        if "top" in question_lower:
            suggestions.append("Add ORDER BY clause to identify top performers")

        if "compare" in question_lower:
            suggestions.append("Include comparison metrics or time periods")

        # Add general performance suggestions if large result set
        row_count = execution_result.get("row_count", 0)
        if row_count > 1000:
            suggestions.append("Consider using LIMIT clause to reduce result size")

        return list(set(suggestions))  # Remove duplicates