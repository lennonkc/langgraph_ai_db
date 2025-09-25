#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dry Run安全阀模块

为BigQuery查询提供成本和性能安全检查
防止执行超大数据量的查询导致成本失控
"""

import os
import re
from typing import Dict, Any
import structlog

logger = structlog.get_logger()


def safe_log(level: str, message: str, **kwargs):
    """安全的日志记录函数，处理BrokenPipe错误"""
    try:
        getattr(logger, level)(message, **kwargs)
    except BrokenPipeError:
        print(f"{level.upper()}: {message} {kwargs}")
    except Exception as e:
        print(f"LOG_ERROR: {message} {kwargs} (logger_error: {e})")


def perform_dry_run_check(script_path: str, sql_query: str) -> dict:
    """
    执行Dry Run安全检查

    Args:
        script_path: 生成的脚本文件路径
        sql_query: SQL查询字符串

    Returns:
        dict: Dry Run检查结果
        {
            "safe_to_execute": bool,
            "reason": str,
            "bytes_processed": int,
            "gb_processed": float,
            "improvement_suggestions": List[str]
        }
    """
    try:
        from google.cloud import bigquery

        # 初始化BigQuery客户端
        client = bigquery.Client(project="thrasio-dev-data-wh-7ee095")

        # 从脚本或SQL中提取查询
        final_sql = extract_sql_for_dry_run(script_path, sql_query)

        if not final_sql:
            return {
                "safe_to_execute": False,
                "reason": "无法提取有效的SQL查询进行Dry Run检查",
                "bytes_processed": 0,
                "improvement_suggestions": ["请检查生成的查询脚本是否包含有效的SQL语句"]
            }

        safe_log("info", f"Performing dry run check for SQL: {final_sql[:200]}...")

        # 配置查询作业进行Dry Run
        job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)

        # 执行Dry Run
        query_job = client.query(final_sql, job_config=job_config)

        # 获取处理的字节数
        bytes_processed = query_job.total_bytes_processed
        gb_processed = bytes_processed / (1024 ** 3)  # 转换为GB

        safe_log("info", f"Dry run completed: {gb_processed:.2f} GB estimated")

        # 检查是否超过200GB限制
        if gb_processed > 200:
            return {
                "safe_to_execute": False,
                "reason": f"查询预估处理数据量 {gb_processed:.2f} GB 超过200GB限制",
                "bytes_processed": bytes_processed,
                "gb_processed": gb_processed,
                "improvement_suggestions": [
                    "请增加更严格的日期范围过滤条件",
                    "在WHERE子句中添加更多限制条件",
                    "使用聚合查询替代返回大量原始数据",
                    "添加或减小LIMIT子句的限制数量",
                    "考虑分批查询较小的时间范围"
                ]
            }

        return {
            "safe_to_execute": True,
            "reason": f"查询预估处理 {gb_processed:.2f} GB，在安全范围内",
            "bytes_processed": bytes_processed,
            "gb_processed": gb_processed,
            "estimated_cost": gb_processed * 5.0 / 1000  # 粗略估算成本 (USD)
        }

    except Exception as e:
        safe_log("error", f"Dry run check failed: {str(e)}")
        return {
            "safe_to_execute": False,
            "reason": f"Dry Run检查失败: {str(e)}",
            "bytes_processed": 0,
            "improvement_suggestions": ["无法执行Dry Run检查，请检查查询语法是否正确"]
        }


def extract_sql_for_dry_run(script_path: str, sql_query: str) -> str:
    """
    从脚本或SQL中提取用于Dry Run的查询

    Args:
        script_path: 脚本文件路径
        sql_query: 直接的SQL查询字符串

    Returns:
        str: 提取的SQL查询
    """
    # 如果有直接的SQL查询，优先使用
    if sql_query and sql_query.strip() and not sql_query.startswith("--"):
        # 检查是否是Python代码（包含import等关键词）
        if not any(keyword in sql_query for keyword in ['import ', 'def ', 'class ', 'from ']):
            return sql_query.strip()

    # 如果有脚本文件，尝试从中提取SQL
    if script_path and os.path.exists(script_path):
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                script_content = f.read()

            # 策略1：直接查找并执行脚本，提取query_plan
            try:
                # 创建一个临时的局部环境来执行部分脚本
                local_vars = {}

                # 提取query_plan定义部分
                query_plan_pattern = r"query_plan\s*=\s*(\[.*?\])"
                query_plan_match = re.search(query_plan_pattern, script_content, re.DOTALL)

                if query_plan_match:
                    query_plan_code = f"query_plan = {query_plan_match.group(1)}"
                    exec(query_plan_code, {"__builtins__": {}}, local_vars)

                    if 'query_plan' in local_vars and local_vars['query_plan']:
                        # 获取最后一个步骤的SQL
                        last_step = local_vars['query_plan'][-1]
                        if 'sql' in last_step:
                            return last_step['sql'].strip()

            except Exception as exec_error:
                safe_log("debug", f"Failed to execute query_plan extraction: {str(exec_error)}")

            # 策略2：正则表达式提取，适应实际格式
            # 寻找 "sql": "..." 模式，考虑多行
            sql_pattern = r'"sql":\s*"([^"]+(?:\\.[^"]*)*)"'
            matches = re.findall(sql_pattern, script_content, re.DOTALL)

            if matches:
                # 取最后一个匹配（通常是主查询）
                sql_candidate = matches[-1]
                # 处理转义字符
                sql_candidate = sql_candidate.replace('\\n', '\n').replace('\\"', '"').strip()
                if sql_candidate and 'SELECT' in sql_candidate.upper():
                    return sql_candidate

            # 策略3：寻找final_query变量赋值
            final_query_patterns = [
                r'final_query\s*=\s*query_plan\[-1\]\[.sql.\]',
                r'final_query\s*=\s*["\']([^"\']+)["\']',
                r'final_query\s*=\s*"""(.*?)"""'
            ]

            for pattern in final_query_patterns:
                matches = re.findall(pattern, script_content, re.DOTALL | re.IGNORECASE)
                if matches:
                    candidate = matches[-1].strip()
                    if candidate and 'SELECT' in candidate.upper():
                        return candidate

            # 策略4：传统的三引号字符串提取
            sql_patterns = [
                r'"""(SELECT.*?)"""',
                r"'''(SELECT.*?)'''",
                r'"(SELECT.*?)"',
                r"'(SELECT.*?)'"
            ]

            for pattern in sql_patterns:
                matches = re.findall(pattern, script_content, re.DOTALL | re.IGNORECASE)
                if matches:
                    # 过滤掉包含Python关键词的匹配
                    valid_matches = [
                        match for match in matches
                        if not any(keyword in match for keyword in ['import ', 'def ', 'class ', 'from ', 'print('])
                    ]
                    if valid_matches:
                        # 返回最长的有效匹配
                        return max(valid_matches, key=len).strip()

        except Exception as e:
            safe_log("warning", f"Failed to extract SQL from script {script_path}: {str(e)}")

    return ""


def execute_actual_query(script_path: str, sql_query: str, dry_run_result: dict) -> dict:
    """
    执行实际查询（在Dry Run通过后）

    Args:
        script_path: 脚本文件路径
        sql_query: SQL查询字符串
        dry_run_result: Dry Run检查结果

    Returns:
        dict: 查询执行结果
    """
    try:
        import importlib.util

        # 优先使用脚本文件执行（如果存在且有效）
        if script_path and script_path != "" and os.path.exists(script_path):
            try:
                # Import and run the generated script
                spec = importlib.util.spec_from_file_location("query_module", script_path)
                query_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(query_module)

                # Check if module has execute_analysis method
                if hasattr(query_module, 'execute_analysis'):
                    execution_result = query_module.execute_analysis()
                elif hasattr(query_module, 'QueryExecutor'):
                    query_executor = query_module.QueryExecutor()
                    execution_result = query_executor.execute_analysis()
                else:
                    execution_result = {"success": False, "error": "Generated script missing execute_analysis method or QueryExecutor class"}

                # 添加Dry Run信息到结果中
                if execution_result.get("success") and "query_metadata" in execution_result:
                    execution_result["query_metadata"]["dry_run_estimate_gb"] = dry_run_result.get("gb_processed", 0)
                    execution_result["query_metadata"]["dry_run_estimate_cost"] = dry_run_result.get("estimated_cost", 0)

                return execution_result

            except Exception as e:
                safe_log("error", f"Script execution failed: {str(e)}")
                return {"success": False, "error": f"Script execution failed: {str(e)}"}

        # 备用：直接执行SQL查询
        elif sql_query and sql_query.strip() and not sql_query.startswith("--"):
            try:
                from bigquery_client import BigQueryClient

                client = BigQueryClient(project_id="thrasio-dev-data-wh-7ee095")
                results = client.execute_query(sql_query, max_results=1000)

                return {
                    "success": True,
                    "results": results,
                    "row_count": len(results) if results else 0,
                    "query_metadata": {
                        "execution_time": None,
                        "bytes_processed": None,
                        "cost_estimate_usd": None,
                        "dry_run_estimate_gb": dry_run_result.get("gb_processed", 0),
                        "dry_run_estimate_cost": dry_run_result.get("estimated_cost", 0)
                    }
                }
            except Exception as e:
                return {"success": False, "error": f"SQL execution failed: {str(e)}"}

        else:
            return {"success": False, "error": "No valid SQL query or script path provided"}

    except Exception as e:
        safe_log("error", f"Query execution failed: {str(e)}")
        return {"success": False, "error": f"Query execution failed: {str(e)}"}


def execute_with_dry_run_safety(script_path: str, sql_query: str) -> Dict[str, Any]:
    """
    带Dry Run安全检查的查询执行主函数

    Args:
        script_path: 生成的脚本文件路径
        sql_query: SQL查询字符串

    Returns:
        dict: 执行结果
        {
            "execution_result": Dict,
            "execution_success": bool,
            "dry_run_result": Dict,
            "improvement_suggestions": List[str] (如果被阻止的话)
        }
    """
    try:
        safe_log("info", "Starting script execution with Dry Run safety valve")

        # Check if we have valid script path or SQL query
        if not script_path and not sql_query:
            execution_result = {"success": False, "error": "No generated script path or SQL query available"}
            return {
                "execution_result": execution_result,
                "execution_success": False,
                "dry_run_result": {"safe_to_execute": False, "reason": "No query to execute"}
            }

        # 执行Dry Run安全检查
        dry_run_result = perform_dry_run_check(script_path, sql_query)

        # 检查Dry Run结果
        if not dry_run_result["safe_to_execute"]:
            safe_log("warning", "Dry run failed safety check",
                     bytes_estimated=dry_run_result.get("bytes_processed", 0),
                     reason=dry_run_result.get("reason", "Unknown"))

            # 不执行查询，返回错误和改进建议
            execution_result = {
                "success": False,
                "error": dry_run_result.get("reason", "Query cost exceeds limit"),
                "dry_run_blocked": True,
                "bytes_processed_estimate": dry_run_result.get("bytes_processed", 0)
            }

            # 设置改进建议供下次重试使用
            improvement_suggestions = dry_run_result.get("improvement_suggestions", [
                "请增加更严格的过滤条件（如缩小日期范围或在 WHERE 子句中增加限制）",
                "考虑使用聚合查询而非返回大量原始数据",
                "添加LIMIT子句限制返回行数"
            ])

            return {
                "execution_result": execution_result,
                "execution_success": False,
                "dry_run_result": dry_run_result,
                "improvement_suggestions": improvement_suggestions,
                "validation_reasoning": f"Dry run检查失败: {dry_run_result.get('reason', 'Unknown')}"
            }

        # Dry Run通过，执行实际查询
        safe_log("info", "Dry run passed, executing actual query",
                 bytes_estimated=dry_run_result.get("bytes_processed", 0))

        execution_result = execute_actual_query(script_path, sql_query, dry_run_result)

        safe_log("info", "Script execution completed",
                 success=execution_result.get("success", False),
                 row_count=execution_result.get("row_count", 0))

        return {
            "execution_result": execution_result,
            "execution_success": execution_result.get("success", False),
            "dry_run_result": dry_run_result
        }

    except Exception as e:
        safe_log("error", f"Script execution failed: {str(e)}")
        return {
            "execution_result": {"success": False, "error": str(e)},
            "execution_success": False,
            "dry_run_result": {"safe_to_execute": False, "reason": f"Execution error: {str(e)}"}
        }