"""
LangGraph Tool Integration for BigQuery
BigQuery的LangGraph工具集成

Provides LangGraph-compatible tools for BigQuery operations including
script execution, cost estimation, and result processing.
"""

from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from typing import Dict, Any, List, Optional
import os
import importlib.util
import sys
import logging
import json
from pathlib import Path

from tools.bigquery_executor import BigQueryExecutor, QueryOptimizer
from tools.result_processor import ResultProcessor

logger = logging.getLogger(__name__)


@tool
def execute_bigquery_script(script_path: str) -> Dict[str, Any]:
    """Execute a generated BigQuery script and return results

    Args:
        script_path: Path to the Python script file containing BigQuery code

    Returns:
        Dictionary containing execution results, data, and metadata
    """
    try:
        logger.info(f"Executing BigQuery script: {script_path}")

        # Validate script path
        if not os.path.exists(script_path):
            return {
                "tool": "execute_bigquery_script",
                "success": False,
                "error": f"Script file not found: {script_path}",
                "script_path": script_path
            }

        # Import and execute the script
        spec = importlib.util.spec_from_file_location("query_module", script_path)
        if not spec or not spec.loader:
            return {
                "tool": "execute_bigquery_script",
                "success": False,
                "error": f"Could not load script module from {script_path}",
                "script_path": script_path
            }

        query_module = importlib.util.module_from_spec(spec)
        sys.modules["query_module"] = query_module
        spec.loader.exec_module(query_module)

        # Execute the main analysis
        if hasattr(query_module, 'QueryExecutor'):
            executor = query_module.QueryExecutor()
            result = executor.execute_analysis()

            return {
                "tool": "execute_bigquery_script",
                "success": True,
                "script_path": script_path,
                "execution_result": result
            }
        else:
            return {
                "tool": "execute_bigquery_script",
                "success": False,
                "error": "Script does not contain QueryExecutor class",
                "script_path": script_path
            }

    except Exception as e:
        logger.error(f"Error executing script {script_path}: {e}")
        return {
            "tool": "execute_bigquery_script",
            "success": False,
            "error": str(e),
            "script_path": script_path
        }
    finally:
        # Clean up module from sys.modules
        if "query_module" in sys.modules:
            del sys.modules["query_module"]


@tool
def estimate_query_cost_and_size(sql_query: str) -> Dict[str, Any]:
    """Estimate BigQuery processing cost and data size using dry run

    Args:
        sql_query: The SQL query to estimate

    Returns:
        Dictionary containing cost estimation and size information
    """
    try:
        logger.info("Estimating query cost and size")

        executor = BigQueryExecutor()
        estimation = executor.estimate_query_cost_and_size(sql_query)

        return {
            "tool": "estimate_query_cost_and_size",
            **estimation
        }

    except Exception as e:
        logger.error(f"Error estimating query cost: {e}")
        return {
            "tool": "estimate_query_cost_and_size",
            "success": False,
            "error": str(e)
        }


@tool
def optimize_query_for_performance(sql_query: str, target_gb: float = 50.0) -> Dict[str, Any]:
    """Optimize a BigQuery query to reduce processing size and cost

    Args:
        sql_query: The SQL query to optimize
        target_gb: Target processing size in GB (default: 50)

    Returns:
        Dictionary containing optimized query and optimization details
    """
    try:
        logger.info(f"Optimizing query for target size: {target_gb}GB")

        executor = BigQueryExecutor()
        optimizer = QueryOptimizer(executor)

        optimization_result = optimizer.optimize_query_for_size(sql_query, target_gb)

        return {
            "tool": "optimize_query_for_performance",
            **optimization_result
        }

    except Exception as e:
        logger.error(f"Error optimizing query: {e}")
        return {
            "tool": "optimize_query_for_performance",
            "success": False,
            "error": str(e),
            "original_query": sql_query
        }


@tool
def execute_and_process_query(sql_query: str, timeout_seconds: int = 300) -> Dict[str, Any]:
    """Execute a BigQuery query and process results with comprehensive analysis

    Args:
        sql_query: The SQL query to execute
        timeout_seconds: Execution timeout in seconds (default: 300)

    Returns:
        Dictionary containing processed results, summary, and insights
    """
    try:
        logger.info("Executing and processing BigQuery query")

        # Execute query
        executor = BigQueryExecutor()
        execution_result = executor.execute_bigquery_script(sql_query, timeout_seconds)

        if not execution_result.success:
            return {
                "tool": "execute_and_process_query",
                "success": False,
                "error": execution_result.error_message,
                "execution_metadata": {
                    "execution_time_seconds": execution_result.execution_time_seconds,
                    "bytes_processed": execution_result.bytes_processed,
                    "cost_estimate_usd": execution_result.cost_estimate_usd
                }
            }

        # Process results
        processor = ResultProcessor()
        processed_results = processor.process_query_results(execution_result)

        return {
            "tool": "execute_and_process_query",
            "success": True,
            "query_executed": sql_query,
            **processed_results
        }

    except Exception as e:
        logger.error(f"Error executing and processing query: {e}")
        return {
            "tool": "execute_and_process_query",
            "success": False,
            "error": str(e)
        }


@tool
def analyze_query_complexity(sql_query: str) -> Dict[str, Any]:
    """Analyze the complexity of a BigQuery query

    Args:
        sql_query: The SQL query to analyze

    Returns:
        Dictionary containing complexity analysis and recommendations
    """
    try:
        logger.info("Analyzing query complexity")

        executor = BigQueryExecutor()
        optimizer = QueryOptimizer(executor)

        complexity_analysis = optimizer.analyze_query_complexity(sql_query)

        return {
            "tool": "analyze_query_complexity",
            "success": True,
            "query_analyzed": sql_query,
            **complexity_analysis
        }

    except Exception as e:
        logger.error(f"Error analyzing query complexity: {e}")
        return {
            "tool": "analyze_query_complexity",
            "success": False,
            "error": str(e)
        }


@tool
def get_table_information(table_name: str) -> Dict[str, Any]:
    """Get information about a BigQuery table

    Args:
        table_name: Name of the table to analyze

    Returns:
        Dictionary containing table schema and metadata
    """
    try:
        logger.info(f"Getting information for table: {table_name}")

        executor = BigQueryExecutor()
        table_info = executor.get_table_info(table_name)

        return {
            "tool": "get_table_information",
            "table_name": table_name,
            **table_info
        }

    except Exception as e:
        logger.error(f"Error getting table information: {e}")
        return {
            "tool": "get_table_information",
            "success": False,
            "error": str(e),
            "table_name": table_name
        }


@tool
def list_available_tables() -> Dict[str, Any]:
    """List all available tables in the BigQuery dataset

    Returns:
        Dictionary containing list of tables and their metadata
    """
    try:
        logger.info("Listing available tables")

        executor = BigQueryExecutor()
        tables_info = executor.list_tables()

        return {
            "tool": "list_available_tables",
            **tables_info
        }

    except Exception as e:
        logger.error(f"Error listing tables: {e}")
        return {
            "tool": "list_available_tables",
            "success": False,
            "error": str(e)
        }


@tool
def export_results_to_file(results_data: Dict[str, Any],
                          export_format: str = "json",
                          filename_prefix: str = "bigquery_results") -> Dict[str, Any]:
    """Export BigQuery results to a file

    Args:
        results_data: The results data to export
        export_format: Format to export (json, csv, summary)
        filename_prefix: Prefix for the output filename

    Returns:
        Dictionary containing export status and file path
    """
    try:
        logger.info(f"Exporting results to {export_format} format")

        processor = ResultProcessor()
        export_paths = processor.export_results_to_formats(
            results_data,
            formats=[export_format]
        )

        if 'error' in export_paths:
            return {
                "tool": "export_results_to_file",
                "success": False,
                "error": export_paths['error']
            }

        return {
            "tool": "export_results_to_file",
            "success": True,
            "export_format": export_format,
            "export_paths": export_paths
        }

    except Exception as e:
        logger.error(f"Error exporting results: {e}")
        return {
            "tool": "export_results_to_file",
            "success": False,
            "error": str(e)
        }


# Create comprehensive tool list
bigquery_enhanced_tools = [
    execute_bigquery_script,
    estimate_query_cost_and_size,
    optimize_query_for_performance,
    execute_and_process_query,
    analyze_query_complexity,
    get_table_information,
    list_available_tables,
    export_results_to_file
]

# Create tool node for LangGraph
bigquery_enhanced_tool_node = ToolNode(bigquery_enhanced_tools)


def get_bigquery_enhanced_tools() -> List:
    """Get all enhanced BigQuery tools"""
    return bigquery_enhanced_tools


def get_bigquery_tool_node() -> ToolNode:
    """Get BigQuery tool node for LangGraph integration"""
    return bigquery_enhanced_tool_node


# Tool categories for easier selection
EXECUTION_TOOLS = [execute_bigquery_script, execute_and_process_query]
OPTIMIZATION_TOOLS = [estimate_query_cost_and_size, optimize_query_for_performance, analyze_query_complexity]
METADATA_TOOLS = [get_table_information, list_available_tables]
UTILITY_TOOLS = [export_results_to_file]


def get_tools_by_category(category: str) -> List:
    """Get tools by category

    Args:
        category: Tool category ('execution', 'optimization', 'metadata', 'utility')

    Returns:
        List of tools in the specified category
    """
    categories = {
        'execution': EXECUTION_TOOLS,
        'optimization': OPTIMIZATION_TOOLS,
        'metadata': METADATA_TOOLS,
        'utility': UTILITY_TOOLS,
        'all': bigquery_enhanced_tools
    }

    return categories.get(category.lower(), [])


class BigQueryToolManager:
    """管理BigQuery工具的中心类"""

    def __init__(self):
        """初始化BigQuery工具管理器"""
        self.executor = BigQueryExecutor()
        self.optimizer = QueryOptimizer(self.executor)
        self.processor = ResultProcessor()

    def execute_workflow(self, sql_query: str,
                        optimize_first: bool = True,
                        process_results: bool = True) -> Dict[str, Any]:
        """执行完整的BigQuery工作流"""

        workflow_result = {
            "workflow_steps": [],
            "final_result": None,
            "success": False
        }

        try:
            # Step 1: Analyze complexity
            complexity = self.optimizer.analyze_query_complexity(sql_query)
            workflow_result["workflow_steps"].append({
                "step": "complexity_analysis",
                "result": complexity
            })

            # Step 2: Optimize if requested
            if optimize_first and complexity.get("complexity_score", 0) > 5:
                optimization = self.optimizer.optimize_query_for_size(sql_query)
                workflow_result["workflow_steps"].append({
                    "step": "optimization",
                    "result": optimization
                })

                if optimization.get("success"):
                    sql_query = optimization["optimized_query"]

            # Step 3: Execute query
            execution_result = self.executor.execute_bigquery_script(sql_query)
            workflow_result["workflow_steps"].append({
                "step": "execution",
                "result": {
                    "success": execution_result.success,
                    "row_count": execution_result.row_count,
                    "execution_time": execution_result.execution_time_seconds,
                    "cost_usd": execution_result.cost_estimate_usd,
                    "error": execution_result.error_message
                }
            })

            if not execution_result.success:
                workflow_result["final_result"] = {"error": execution_result.error_message}
                return workflow_result

            # Step 4: Process results
            if process_results:
                processed = self.processor.process_query_results(execution_result)
                workflow_result["workflow_steps"].append({
                    "step": "result_processing",
                    "result": processed
                })
                workflow_result["final_result"] = processed
            else:
                workflow_result["final_result"] = {
                    "raw_data": execution_result.data.to_dict('records') if execution_result.data is not None else None,
                    "row_count": execution_result.row_count
                }

            workflow_result["success"] = True
            return workflow_result

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            workflow_result["final_result"] = {"error": str(e)}
            return workflow_result