"""
BigQuery Tools for AI Database Analyst

Implements specialized tools for BigQuery integration:
- execute_bigquery_script: Execute Python scripts with BigQuery queries
- estimate_query_cost_and_size: Dry run estimation for data volume and cost
- validate_query_syntax: Syntax validation for BigQuery SQL
"""

import os
import subprocess
import sys
from typing import Any, Dict, Optional, Type
from pathlib import Path

import structlog
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

# Add project root to path
current_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config import get_settings
from bigquery_client import BigQueryClient

logger = structlog.get_logger()


class ExecuteBigQueryScriptInput(BaseModel):
    """Input for execute_bigquery_script tool"""

    script_content: str = Field(description="Python script content to execute")
    script_name: str = Field(description="Name for the script file")
    timeout_seconds: int = Field(
        default=300, description="Execution timeout in seconds"
    )


class ExecuteBigQueryScriptTool(BaseTool):
    """Tool to execute Python scripts containing BigQuery queries"""

    name: str = "execute_bigquery_script"
    description: str = (
        "Execute a Python script that contains BigQuery queries and return the results"
    )
    args_schema: type[BaseModel] = ExecuteBigQueryScriptInput

    def _run(
        self, script_content: str, script_name: str, timeout_seconds: int = 300
    ) -> Dict[str, Any]:
        """Execute the BigQuery script"""
        try:
            # Create temporary script file
            temp_dir = Path("./temp_scripts")
            temp_dir.mkdir(exist_ok=True)

            script_path = temp_dir / f"{script_name}.py"

            # Write script to file
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script_content)

            # Execute the script
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                cwd=str(script_path.parent),
            )

            # Clean up temporary file
            try:
                script_path.unlink()
            except:
                pass

            return {
                "success": result.returncode == 0,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "execution_time_seconds": (
                    timeout_seconds if result.returncode != 0 else "completed"
                ),
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Script execution timed out after {timeout_seconds} seconds",
                "timeout": True,
            }
        except Exception as e:
            logger.error("Script execution failed", error=str(e))
            return {"success": False, "error": str(e)}


class EstimateQueryCostInput(BaseModel):
    """Input for estimate_query_cost_and_size tool"""

    sql_query: str = Field(description="BigQuery SQL query to estimate")
    project_id: Optional[str] = Field(default=None, description="BigQuery project ID")


class EstimateQueryCostTool(BaseTool):
    """Tool to estimate BigQuery query cost and data size using dry run"""

    name: str = "estimate_query_cost_and_size"
    description: str = (
        "Estimate the cost and data size of a BigQuery query using dry run"
    )
    args_schema: type[BaseModel] = EstimateQueryCostInput

    def _run(self, sql_query: str, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Estimate query cost and size"""
        try:
            settings = get_settings()
            if not project_id:
                project_id = settings.google_cloud.bigquery_project_id

            client = BigQueryClient(project_id=project_id)

            # Perform dry run
            from google.cloud.bigquery import QueryJobConfig

            job_config = QueryJobConfig(dry_run=True)
            query_job = client.client.query(sql_query, job_config=job_config)

            # Calculate estimates
            bytes_processed = query_job.total_bytes_processed or 0
            gb_processed = bytes_processed / (1024**3)
            estimated_cost = gb_processed * 5.0  # $5 per TB

            # Estimate execution time based on data size
            if gb_processed < 0.1:
                estimated_time = "< 30 seconds"
            elif gb_processed < 1:
                estimated_time = "1-3 minutes"
            elif gb_processed < 10:
                estimated_time = "3-10 minutes"
            else:
                estimated_time = "> 10 minutes"

            return {
                "success": True,
                "bytes_processed": bytes_processed,
                "gb_processed": round(gb_processed, 4),
                "estimated_cost_usd": round(estimated_cost, 6),
                "estimated_execution_time": estimated_time,
                "query_valid": True,
            }

        except Exception as e:
            logger.error("Query cost estimation failed", error=str(e))
            return {"success": False, "error": str(e), "query_valid": False}


class ValidateQuerySyntaxInput(BaseModel):
    """Input for validate_query_syntax tool"""

    sql_query: str = Field(description="BigQuery SQL query to validate")
    project_id: Optional[str] = Field(default=None, description="BigQuery project ID")


class ValidateQuerySyntaxTool(BaseTool):
    """Tool to validate BigQuery SQL syntax"""

    name: str = "validate_query_syntax"
    description: str = "Validate the syntax of a BigQuery SQL query"
    args_schema: Type[ValidateQuerySyntaxInput] = ValidateQuerySyntaxInput

    def _run(self, sql_query: str, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Validate query syntax"""
        try:
            settings = get_settings()
            if not project_id:
                project_id = settings.google_cloud.bigquery_project_id

            client = BigQueryClient(project_id=project_id)

            # Perform dry run for syntax validation
            from google.cloud.bigquery import QueryJobConfig

            job_config = QueryJobConfig(dry_run=True)
            query_job = client.client.query(sql_query, job_config=job_config)

            return {
                "success": True,
                "syntax_valid": True,
                "message": "Query syntax is valid",
            }

        except Exception as e:
            error_message = str(e)
            return {
                "success": False,
                "syntax_valid": False,
                "error": error_message,
                "message": f"Syntax error: {error_message}",
            }


# Create tool instances
execute_bigquery_script_tool = ExecuteBigQueryScriptTool()
estimate_query_cost_tool = EstimateQueryCostTool()
validate_query_syntax_tool = ValidateQuerySyntaxTool()

# Tool registry for easy access
BIGQUERY_TOOLS = [
    execute_bigquery_script_tool,
    estimate_query_cost_tool,
    validate_query_syntax_tool,
]


class ExecuteQueryTool(BaseTool):
    """Tool to execute BigQuery queries and return pandas DataFrame"""

    name: str = "execute_bigquery_query"
    description: str = (
        "Execute a BigQuery SQL query and return results as pandas DataFrame"
    )

    class InputSchema(BaseModel):
        sql_query: str = Field(description="SQL query to execute")
        project_id: Optional[str] = Field(
            default=None, description="BigQuery project ID"
        )
        max_results: int = Field(
            default=1000, description="Maximum number of results to return"
        )

    args_schema: type[BaseModel] = InputSchema

    def _run(
        self, sql_query: str, project_id: Optional[str] = None, max_results: int = 1000
    ) -> Dict[str, Any]:
        """Execute BigQuery query and return results"""
        try:
            client = BigQueryClient(project_id=project_id)

            # Execute query and get results as list of dictionaries
            results = client.execute_query(sql_query, max_results=max_results)

            if not results:
                return {
                    "success": True,
                    "rows": 0,
                    "columns": [],
                    "data": [],
                    "sample_data": [],
                }

            # Extract column names from first row
            columns = list(results[0].keys()) if results else []

            return {
                "success": True,
                "rows": len(results),
                "columns": columns,
                "data": results,
                "sample_data": results[:5],  # First 5 rows as sample
            }

        except Exception as e:
            logger.error("Query execution failed", error=str(e))
            return {"success": False, "error": str(e)}


# Add the new tool to the registry
execute_query_tool = ExecuteQueryTool()
BIGQUERY_TOOLS.append(execute_query_tool)


def get_bigquery_tools():
    """Get all BigQuery tools"""
    return BIGQUERY_TOOLS


def get_enhanced_bigquery_tools():
    """Get enhanced BigQuery tools with optimization and processing capabilities"""
    try:
        from tools.bigquery_langgraph_tools import get_bigquery_enhanced_tools

        return get_bigquery_enhanced_tools()
    except ImportError:
        # Fallback to basic tools if enhanced tools not available
        return BIGQUERY_TOOLS


def get_all_bigquery_tools():
    """Get both basic and enhanced BigQuery tools"""
    basic_tools = get_bigquery_tools()
    try:
        enhanced_tools = get_enhanced_bigquery_tools()
        # Combine without duplicates (by tool name)
        all_tools = basic_tools.copy()
        basic_tool_names = {tool.name for tool in basic_tools}

        for tool in enhanced_tools:
            if tool.name not in basic_tool_names:
                all_tools.append(tool)

        return all_tools
    except Exception:
        return basic_tools


# Enhanced tool access functions
def get_bigquery_executor():
    """Get BigQuery executor instance for advanced operations"""
    try:
        from tools.bigquery_executor import BigQueryExecutor

        return BigQueryExecutor()
    except ImportError:
        return None


def get_query_optimizer():
    """Get query optimizer instance"""
    try:
        from tools.bigquery_executor import QueryOptimizer

        executor = get_bigquery_executor()
        if executor:
            return QueryOptimizer(executor)
    except ImportError:
        pass
    return None


def get_result_processor():
    """Get result processor instance"""
    try:
        from tools.result_processor import ResultProcessor

        return ResultProcessor()
    except ImportError:
        return None


if __name__ == "__main__":
    # Get settings
    settings = get_settings()
    project_id = settings.google_cloud.bigquery_project_id

    # Test with real BigQuery data
    test_query = f"""
    SELECT
        dim.brand_name,
        COUNT(DISTINCT fact.item_id) as product_count,
        SUM(fact.gross_sales_usd) as total_sales_usd,
        SUM(fact.units) as total_units,
        ROUND(SUM(fact.gross_sales_usd) / SUM(fact.units), 2) as avg_price_per_unit
    FROM `{project_id}.reporting_us.rpt_fct_order` fact
    JOIN `{project_id}.reporting_us.rpt_dim_item` dim
    ON fact.item_id = dim.item_id
    WHERE fact.order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
        AND dim.brand_name IS NOT NULL
        AND dim.brand_name != ''
        AND fact.gross_sales_usd > 0
    GROUP BY dim.brand_name
    ORDER BY total_sales_usd DESC
    LIMIT 10
    """

    print("Testing BigQuery tools with real data...")

    # Test syntax validation
    print("1. Testing syntax validation...")
    result = validate_query_syntax_tool._run(test_query)
    print(f"Syntax validation: {'✅ PASSED' if result.get('success') else '❌ FAILED'}")
    if not result.get("success"):
        print(f"Error: {result.get('error')}")

    # Test cost estimation
    print("\n2. Testing cost estimation...")
    result = estimate_query_cost_tool._run(test_query)
    print(f"Cost estimation: {'✅ PASSED' if result.get('success') else '❌ FAILED'}")
    if result.get("success"):
        print(f"Estimated cost: ${result.get('estimated_cost_usd', 0):.6f}")
        print(f"Data to process: {result.get('gb_processed', 0):.4f} GB")
    else:
        print(f"Error: {result.get('error')}")

    # Test query execution
    print("\n3. Testing query execution...")
    result = execute_query_tool._run(test_query, max_results=5)
    print(f"Query execution: {'✅ PASSED' if result.get('success') else '❌ FAILED'}")
    if result.get("success"):
        print(
            f"Returned {result.get('rows')} rows with {len(result.get('columns', []))} columns"
        )
        print("Sample data:")
        for i, row in enumerate(result.get("sample_data", []), 1):
            print(f"  {i}. {row}")
    else:
        print(f"Error: {result.get('error')}")
