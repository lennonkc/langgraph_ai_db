"""
Result Processing Tools
结果处理工具

Comprehensive tools for processing BigQuery results, managing token limits,
and generating summaries for downstream analysis.
"""

import pandas as pd
import numpy as np
import os
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import logging

from tools.bigquery_executor import QueryExecutionResult

logger = logging.getLogger(__name__)


class ResultProcessor:
    """结果处理器 - 处理查询结果并生成摘要"""

    def __init__(self):
        """初始化结果处理器"""
        self.max_token_limit = int(os.getenv('MAX_TOKEN_LIMIT', 2000000))  # Very large limit
        self.max_rows_for_full_data = int(os.getenv('MAX_ROWS_FULL_DATA', 10000))

    def process_query_results(self, execution_result: QueryExecutionResult) -> Dict[str, Any]:
        """处理查询结果并生成摘要"""

        if not execution_result.success:
            return {
                "success": False,
                "error": execution_result.error_message,
                "processed_data": None,
                "summary": None
            }

        df = execution_result.data

        # Generate comprehensive summary
        summary = self._generate_comprehensive_summary(df, execution_result)

        # Sample data for preview
        sample_size = min(10, len(df))
        sample_data = df.head(sample_size).to_dict('records')

        # Process full data with token limit considerations
        processed_data, token_info = self._process_data_for_token_limits(df)

        return {
            "success": True,
            "processed_data": processed_data,
            "sample_data": sample_data,
            "summary": summary,
            "token_info": token_info,
            "data_insights": self._generate_data_insights(df),
            "visualization_suggestions": self._suggest_visualizations(df)
        }

    def _generate_comprehensive_summary(self, df: pd.DataFrame, execution_result: QueryExecutionResult) -> Dict[str, Any]:
        """生成综合摘要"""
        summary = {
            "basic_info": {
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "columns": list(df.columns),
                "column_types": {col: str(dtype) for col, dtype in df.dtypes.items()}
            },
            "execution_metadata": {
                "execution_time_seconds": execution_result.execution_time_seconds,
                "bytes_processed": execution_result.bytes_processed,
                "cost_estimate_usd": execution_result.cost_estimate_usd,
                "query_job_id": execution_result.query_job_id
            }
        }

        # Add column-specific statistics
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        text_columns = df.select_dtypes(include=['object', 'string']).columns
        datetime_columns = df.select_dtypes(include=['datetime64']).columns

        # Numeric column analysis
        if len(numeric_columns) > 0:
            summary["numeric_analysis"] = {}
            for col in numeric_columns:
                if not df[col].isna().all():
                    summary["numeric_analysis"][col] = {
                        "min": float(df[col].min()) if pd.notna(df[col].min()) else None,
                        "max": float(df[col].max()) if pd.notna(df[col].max()) else None,
                        "mean": float(df[col].mean()) if pd.notna(df[col].mean()) else None,
                        "median": float(df[col].median()) if pd.notna(df[col].median()) else None,
                        "std": float(df[col].std()) if pd.notna(df[col].std()) else None,
                        "sum": float(df[col].sum()) if pd.notna(df[col].sum()) else None,
                        "null_count": int(df[col].isna().sum()),
                        "unique_count": int(df[col].nunique())
                    }

        # Text column analysis
        if len(text_columns) > 0:
            summary["text_analysis"] = {}
            for col in text_columns:
                unique_values = df[col].value_counts().head(10)
                summary["text_analysis"][col] = {
                    "unique_count": int(df[col].nunique()),
                    "null_count": int(df[col].isna().sum()),
                    "top_values": unique_values.to_dict() if len(unique_values) > 0 else {},
                    "avg_length": float(df[col].astype(str).str.len().mean()) if not df[col].isna().all() else None
                }

        # DateTime column analysis
        if len(datetime_columns) > 0:
            summary["datetime_analysis"] = {}
            for col in datetime_columns:
                if not df[col].isna().all():
                    summary["datetime_analysis"][col] = {
                        "min_date": df[col].min().isoformat() if pd.notna(df[col].min()) else None,
                        "max_date": df[col].max().isoformat() if pd.notna(df[col].max()) else None,
                        "date_range_days": (df[col].max() - df[col].min()).days if pd.notna(df[col].min()) and pd.notna(df[col].max()) else None,
                        "null_count": int(df[col].isna().sum())
                    }

        # Data quality assessment
        summary["data_quality"] = self._assess_data_quality(df)

        return summary

    def _process_data_for_token_limits(self, df: pd.DataFrame) -> tuple[List[Dict], Dict[str, Any]]:
        """处理数据以符合token限制"""

        # Convert DataFrame to list of dictionaries
        full_data = df.to_dict('records')

        # Estimate token count
        estimated_tokens = self._estimate_token_count(full_data)

        token_info = {
            "estimated_tokens": estimated_tokens,
            "max_token_limit": self.max_token_limit,
            "within_limits": estimated_tokens <= self.max_token_limit,
            "truncation_applied": False
        }

        # If within limits and not too many rows, return full data
        if estimated_tokens <= self.max_token_limit and len(df) <= self.max_rows_for_full_data:
            return full_data, token_info

        # If exceeds token limits, truncate
        if estimated_tokens > self.max_token_limit:
            truncation_ratio = self.max_token_limit / estimated_tokens
            keep_rows = int(len(df) * truncation_ratio * 0.9)  # 90% of limit for safety
            truncated_data = df.head(keep_rows).to_dict('records')

            token_info.update({
                "truncation_applied": True,
                "original_rows": len(df),
                "truncated_to": keep_rows,
                "truncation_reason": "Token limit exceeded",
                "estimated_tokens": self._estimate_token_count(truncated_data)
            })

            return truncated_data, token_info

        # If too many rows but within token limits, sample the data
        if len(df) > self.max_rows_for_full_data:
            sample_size = min(self.max_rows_for_full_data, len(df))
            sampled_df = df.sample(n=sample_size, random_state=42)
            sampled_data = sampled_df.to_dict('records')

            token_info.update({
                "truncation_applied": True,
                "original_rows": len(df),
                "truncated_to": sample_size,
                "truncation_reason": "Row count limit exceeded",
                "estimated_tokens": self._estimate_token_count(sampled_data)
            })

            return sampled_data, token_info

        return full_data, token_info

    def _estimate_token_count(self, data: List[Dict]) -> int:
        """估算数据的token数量"""
        if not data:
            return 0

        # Convert to JSON string and estimate tokens
        json_str = json.dumps(data, default=str)
        total_chars = len(json_str)
        return total_chars // 4  # Rough approximation: 4 characters per token

    def _assess_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """评估数据质量"""
        total_cells = len(df) * len(df.columns)
        null_cells = df.isnull().sum().sum()
        null_percentage = (null_cells / total_cells) * 100 if total_cells > 0 else 0

        # Detect potential data quality issues
        issues = []

        if null_percentage > 20:
            issues.append(f"High null percentage: {null_percentage:.1f}%")

        # Check for duplicate rows
        duplicate_rows = df.duplicated().sum()
        if duplicate_rows > 0:
            issues.append(f"Duplicate rows detected: {duplicate_rows}")

        # Check for columns with all same values
        constant_columns = [col for col in df.columns if df[col].nunique() <= 1]
        if constant_columns:
            issues.append(f"Constant value columns: {constant_columns}")

        # Check for potential outliers in numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        outlier_columns = []
        for col in numeric_cols:
            if len(df[col].dropna()) > 10:  # Only check if we have enough data
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                outliers = df[(df[col] < (Q1 - 1.5 * IQR)) | (df[col] > (Q3 + 1.5 * IQR))]
                if len(outliers) > len(df) * 0.05:  # More than 5% outliers
                    outlier_columns.append(col)

        if outlier_columns:
            issues.append(f"Columns with potential outliers: {outlier_columns}")

        return {
            "total_cells": total_cells,
            "null_cells": null_cells,
            "null_percentage": round(null_percentage, 2),
            "duplicate_rows": duplicate_rows,
            "constant_columns": constant_columns,
            "outlier_columns": outlier_columns,
            "quality_issues": issues,
            "quality_score": max(0, 100 - len(issues) * 10 - null_percentage)  # Simple scoring
        }

    def _generate_data_insights(self, df: pd.DataFrame) -> Dict[str, Any]:
        """生成数据洞察"""
        insights = {
            "key_findings": [],
            "trends": [],
            "anomalies": [],
            "recommendations": []
        }

        # Key findings based on data
        if len(df) > 0:
            insights["key_findings"].append(f"Dataset contains {len(df)} records across {len(df.columns)} dimensions")

        # Analyze numeric columns for trends
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if not df[col].isna().all():
                mean_val = df[col].mean()
                median_val = df[col].median()

                if abs(mean_val - median_val) > (df[col].std() or 0):
                    insights["trends"].append(f"{col}: Skewed distribution (mean: {mean_val:.2f}, median: {median_val:.2f})")

        # Look for date-based trends
        date_cols = df.select_dtypes(include=['datetime64']).columns
        if len(date_cols) > 0 and len(numeric_cols) > 0:
            for date_col in date_cols:
                for num_col in numeric_cols:
                    if not df[date_col].isna().all() and not df[num_col].isna().all():
                        # Simple trend analysis
                        df_sorted = df.sort_values(date_col)
                        first_half_mean = df_sorted[num_col].iloc[:len(df_sorted)//2].mean()
                        second_half_mean = df_sorted[num_col].iloc[len(df_sorted)//2:].mean()

                        if not pd.isna(first_half_mean) and not pd.isna(second_half_mean):
                            change_pct = ((second_half_mean - first_half_mean) / first_half_mean) * 100
                            if abs(change_pct) > 10:
                                trend_direction = "increasing" if change_pct > 0 else "decreasing"
                                insights["trends"].append(f"{num_col} is {trend_direction} over time ({change_pct:+.1f}%)")

        # Recommendations based on data characteristics
        if len(df) < 100:
            insights["recommendations"].append("Small dataset - consider gathering more data for robust analysis")

        if len(df.columns) > 20:
            insights["recommendations"].append("High dimensional data - consider dimensionality reduction or feature selection")

        null_percentage = (df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100
        if null_percentage > 15:
            insights["recommendations"].append(f"High null percentage ({null_percentage:.1f}%) - consider data cleaning or imputation")

        return insights

    def _suggest_visualizations(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """建议可视化方案"""
        visualizations = []

        numeric_cols = df.select_dtypes(include=[np.number]).columns
        text_cols = df.select_dtypes(include=['object', 'string']).columns
        date_cols = df.select_dtypes(include=['datetime64']).columns

        # Suggest visualizations based on column types
        if len(numeric_cols) >= 2:
            visualizations.append({
                "type": "scatter_plot",
                "title": f"Scatter Plot: {numeric_cols[0]} vs {numeric_cols[1]}",
                "x_axis": numeric_cols[0],
                "y_axis": numeric_cols[1],
                "description": "Explore correlation between two numeric variables"
            })

        if len(numeric_cols) >= 1 and len(text_cols) >= 1:
            visualizations.append({
                "type": "bar_chart",
                "title": f"Bar Chart: {numeric_cols[0]} by {text_cols[0]}",
                "x_axis": text_cols[0],
                "y_axis": numeric_cols[0],
                "description": "Compare numeric values across categories"
            })

        if len(date_cols) >= 1 and len(numeric_cols) >= 1:
            visualizations.append({
                "type": "time_series",
                "title": f"Time Series: {numeric_cols[0]} over {date_cols[0]}",
                "x_axis": date_cols[0],
                "y_axis": numeric_cols[0],
                "description": "Analyze trends over time"
            })

        if len(numeric_cols) >= 1:
            visualizations.append({
                "type": "histogram",
                "title": f"Distribution of {numeric_cols[0]}",
                "column": numeric_cols[0],
                "description": "Understand the distribution of values"
            })

        # Suggest top categories chart for categorical data with many unique values
        for col in text_cols:
            unique_count = df[col].nunique()
            if 5 <= unique_count <= 20:
                visualizations.append({
                    "type": "pie_chart",
                    "title": f"Distribution of {col}",
                    "column": col,
                    "description": f"Show proportion of different {col} values"
                })

        return visualizations

    def export_results_to_formats(self, processed_results: Dict[str, Any],
                                 formats: List[str] = ['json', 'csv']) -> Dict[str, str]:
        """导出结果到不同格式"""
        export_paths = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Ensure export directory exists
        export_dir = "exports"
        os.makedirs(export_dir, exist_ok=True)

        try:
            if 'json' in formats:
                json_path = f"{export_dir}/results_{timestamp}.json"
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(processed_results, f, indent=2, default=str, ensure_ascii=False)
                export_paths['json'] = json_path

            if 'csv' in formats and processed_results.get('processed_data'):
                csv_path = f"{export_dir}/data_{timestamp}.csv"
                df = pd.DataFrame(processed_results['processed_data'])
                df.to_csv(csv_path, index=False, encoding='utf-8')
                export_paths['csv'] = csv_path

            if 'summary' in formats:
                summary_path = f"{export_dir}/summary_{timestamp}.txt"
                with open(summary_path, 'w', encoding='utf-8') as f:
                    f.write("Data Analysis Summary\n")
                    f.write("=" * 50 + "\n\n")

                    summary = processed_results.get('summary', {})
                    basic_info = summary.get('basic_info', {})

                    f.write(f"Total Rows: {basic_info.get('total_rows', 'N/A')}\n")
                    f.write(f"Total Columns: {basic_info.get('total_columns', 'N/A')}\n")
                    f.write(f"Columns: {', '.join(basic_info.get('columns', []))}\n\n")

                    # Data quality info
                    quality = summary.get('data_quality', {})
                    f.write(f"Data Quality Score: {quality.get('quality_score', 'N/A')}/100\n")
                    f.write(f"Null Percentage: {quality.get('null_percentage', 'N/A')}%\n")

                    if quality.get('quality_issues'):
                        f.write(f"Quality Issues: {', '.join(quality['quality_issues'])}\n")

                export_paths['summary'] = summary_path

        except Exception as e:
            logger.error(f"Error exporting results: {e}")
            export_paths['error'] = str(e)

        return export_paths