"""
Main Workflow Integration for AI Database Analyst

整合所有子流程为一个完整的LangGraph工作流程
"""

import os
import uuid
import importlib.util
from datetime import datetime
from typing import TypedDict, List, Optional, Dict, Any
import structlog

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入重构后的流程模块
from flows.semantic_matching_flow import perform_semantic_matching
from flows.chief_architect_flow import generate_chief_architect_query
from flows.dry_run_safety import execute_with_dry_run_safety
from flows.script_validation_flow import create_script_validation_flow
from flows.human_review_flow import create_human_review_flow
from flows.visualization_flow import create_visualization_flow

# 导入LangSmith跟踪组件
from monitoring.traceable_decorators import trace_workflow_step
from monitoring.workflow_tracking import execute_tracked_workflow, WorkflowMetricsCollector
from monitoring.performance_monitoring import performance_monitor, cost_tracker
from monitoring.debug_support import debug_support
from config.langsmith_config import langsmith_config

# 导入错误处理组件
from error_handling import (
    ErrorSeverity, ErrorCategory, ErrorContext, DatabaseAnalystError,
    ErrorDetector, ExponentialBackoffStrategy, with_retry, CircuitBreaker,
    RecoveryManager, log_error_with_context, message_translator
)

logger = structlog.get_logger()


class MainWorkflowState(TypedDict):
    """主工作流程状态定义"""
    # Input
    user_question: str
    session_id: str

    # Question Analysis Results (重构后的语义匹配结果)
    confidence_score: float
    matched_queries: List[Dict[str, Any]]  # 从questions_and_queries.json匹配的查询对象
    semantic_analysis: Dict[str, Any]  # 语义分析结果
    matched_question_ids: List[int]  # 匹配的问题ID列表

    # Query Generation Results (升级后的动态生成)
    generated_script_path: str
    generated_sql: str
    generation_metadata: Dict[str, Any]
    query_plan: List[Dict[str, Any]]  # 多步查询计划
    dry_run_result: Dict[str, Any]  # Dry run结果

    # Execution Results
    execution_result: Dict[str, Any]
    execution_success: bool

    # Validation Results
    validation_decision: str
    validation_reasoning: str
    improvement_suggestions: List[str]

    # Results Explanation (for human review)
    explanation_markdown: str

    # Human Review Results
    user_chart_selection: str
    user_preferences: Dict[str, Any]
    review_decision: str

    # Final Output
    report_path: str
    report_metadata: Dict[str, Any]

    # Control Flow
    current_step: str
    retry_count: int
    max_retries: int
    workflow_status: str
    error_messages: List[str]

    # Error Handling
    error_count: int
    last_error: str
    recovery_applied: bool
    user_error_message: Optional[Dict[str, Any]]
    technical_error_details: Optional[Dict[str, Any]]


def safe_log(level: str, message: str, **kwargs):
    """安全的日志记录函数，处理BrokenPipe错误"""
    try:
        getattr(logger, level)(message, **kwargs)
    except BrokenPipeError:
        # 使用print作为备用
        print(f"{level.upper()}: {message} {kwargs}")
    except Exception as e:
        print(f"LOG_ERROR: {message} {kwargs} (logger_error: {e})")


# 核心功能已移至模块化组件:
# - 语义匹配功能: flows/semantic_matching_flow.py
# - 首席查询架构师: flows/chief_architect_flow.py
# - Dry Run安全阀: flows/dry_run_safety.py


def create_main_workflow() -> StateGraph:
    """创建主工作流程图"""

    # Initialize main workflow state graph
    workflow = StateGraph(MainWorkflowState)

    # Add all sub-workflow nodes
    workflow.add_node("initialize_session", initialize_session_node)
    workflow.add_node("analyze_question", analyze_question_node)
    workflow.add_node("generate_query", generate_query_node)
    workflow.add_node("execute_script", execute_script_node)
    workflow.add_node("validate_results", validate_results_node)
    workflow.add_node("explain_results", explain_results_node)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("generate_visualization", generate_visualization_node)
    workflow.add_node("finalize_workflow", finalize_workflow_node)
    workflow.add_node("handle_error", handle_error_node)

    # Define workflow edges
    workflow.add_edge(START, "initialize_session")
    workflow.add_edge("initialize_session", "analyze_question")

    # Conditional routing after question analysis
    workflow.add_conditional_edges(
        "analyze_question",
        route_after_question_analysis,
        {
            "generate_query": "generate_query",
            "request_clarification": "handle_error",
            "error": "handle_error"
        }
    )

    workflow.add_edge("generate_query", "execute_script")

    # Conditional routing after script execution
    workflow.add_conditional_edges(
        "execute_script",
        route_after_execution,
        {
            "validate": "validate_results",
            "retry_generation": "generate_query",
            "error": "handle_error"
        }
    )

    # Conditional routing after validation
    workflow.add_conditional_edges(
        "validate_results",
        route_after_validation,
        {
            "explain": "explain_results",
            "regenerate": "generate_query",
            "error": "handle_error"
        }
    )

    # Direct edge from explain_results to human_review
    workflow.add_edge("explain_results", "human_review")

    # Conditional routing after human review
    workflow.add_conditional_edges(
        "human_review",
        route_after_human_review,
        {
            "generate_report": "generate_visualization",
            "modify_query": "generate_query",
            "regenerate": "generate_query"
        }
    )

    workflow.add_edge("generate_visualization", "finalize_workflow")
    workflow.add_edge("finalize_workflow", END)
    workflow.add_edge("handle_error", END)

    # Use checkpointer only when not running in LangGraph API environment
    # LangGraph API/Studio handles persistence automatically
    import os
    use_custom_checkpointer = os.getenv("LANGGRAPH_API_ENV") != "true"

    if use_custom_checkpointer:
        # 检查是否在WebUI环境中运行，如果是则使用外部提供的checkpointer
        checkpointer = get_external_checkpointer()
        if checkpointer is None:
            # Use MemorySaver for local development/testing
            checkpointer = MemorySaver()

        return workflow.compile(
            checkpointer=checkpointer,
            debug=True
        )
    else:
        # Let LangGraph API handle persistence
        return workflow.compile(debug=True)

# 全局变量用于存储外部checkpointer（来自WebUI）
_EXTERNAL_CHECKPOINTER = None

def set_external_checkpointer(checkpointer):
    """设置外部checkpointer（用于WebUI集成）"""
    global _EXTERNAL_CHECKPOINTER
    _EXTERNAL_CHECKPOINTER = checkpointer
    print(f"设置外部checkpointer: {type(checkpointer)}")

def get_external_checkpointer():
    """获取外部checkpointer"""
    return _EXTERNAL_CHECKPOINTER


@trace_workflow_step("session_initialization", "chain")
def initialize_session_node(state: MainWorkflowState) -> MainWorkflowState:
    """初始化会话节点"""

    session_id = str(uuid.uuid4())

    try:
        # Setup LangSmith session tracking
        langsmith_config.setup_session_tracking(session_id)
    except Exception as e:
        print(f"Warning: LangSmith setup failed: {e}")

    try:
        # Initialize debug session if needed
        debug_support.start_debug_session(session_id, "INFO")
    except Exception as e:
        print(f"Warning: Debug session setup failed: {e}")

    safe_log("info", "Initializing new workflow session", session_id=session_id)

    return {
        **state,
        "session_id": session_id,
        "current_step": "question_analysis",
        "retry_count": 0,
        "max_retries": 3,
        "workflow_status": "in_progress",
        "error_messages": [],
        "error_count": 0,
        "last_error": "",
        "recovery_applied": False,
        "user_error_message": None,
        "technical_error_details": None
    }


def route_after_question_analysis(state: MainWorkflowState) -> str:
    """语义匹配后的路由逻辑 - 重构为基于置信度的简单决策"""

    error_count = state.get("error_count", 0)
    max_errors = state.get("max_retries", 3)
    workflow_status = state.get("workflow_status", "in_progress")

    # Check if we've exceeded error limits
    if error_count >= max_errors or workflow_status == "failed":
        return "error"

    # Check if recovery was applied
    if state.get("recovery_applied", False):
        return "generate_query"

    confidence = state.get("confidence_score", 0.0)
    matched_queries = state.get("matched_queries", [])
    semantic_analysis = state.get("semantic_analysis", {})

    safe_log("info", "Routing after semantic matching",
             confidence=confidence,
             matched_queries_count=len(matched_queries),
             match_found=semantic_analysis.get("match_found", False),
             error_count=error_count)

    # 简化路由逻辑：只检查置信度是否达到阈值
    if confidence >= 0.75:
        safe_log("info", "High confidence semantic match found, proceeding with query generation",
                 confidence=confidence, match_count=len(matched_queries))
        return "generate_query"
    elif confidence >= 0.5:
        # 中等置信度，仍然尝试生成查询，但会在generate_query中特别处理
        safe_log("info", "Medium confidence match, proceeding with enhanced query generation",
                 confidence=confidence)
        return "generate_query"
    else:
        # 低置信度，要求澄清
        safe_log("info", "Low confidence match, requesting clarification",
                 confidence=confidence)
        return "request_clarification"


def route_after_execution(state: MainWorkflowState) -> str:
    """脚本执行后的路由逻辑"""

    execution_success = state.get("execution_success", False)
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    error_count = state.get("error_count", 0)

    # Check for specific failure conditions that indicate unrecoverable errors
    execution_result = state.get("execution_result", {})
    error_message = execution_result.get("error", "")

    safe_log("info", "Routing after execution",
             success=execution_success,
             retry_count=retry_count,
             error_count=error_count,
             error_message=error_message)

    if execution_success:
        return "validate"

    # Check for unrecoverable errors
    if ("No generated script path or SQL query available" in error_message or
        "No valid SQL query or script path provided" in error_message or
        error_count >= max_retries):
        safe_log("warning", "Unrecoverable execution error detected", error=error_message)
        return "error"

    # Allow retry if we haven't exceeded limits
    if retry_count < max_retries:
        return "retry_generation"
    else:
        return "error"


def route_after_validation(state: MainWorkflowState) -> str:
    """结果验证后的路由逻辑"""

    validation_decision = state.get("validation_decision", "rejected")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)

    safe_log("info", "Routing after validation",
             decision=validation_decision,
             retry_count=retry_count)

    if validation_decision == "approved":
        return "explain"
    elif validation_decision in ["needs_revision", "rejected"] and retry_count < max_retries:
        return "regenerate"
    else:
        return "error"


def route_after_human_review(state: MainWorkflowState) -> str:
    """人工审查后的路由逻辑"""

    review_decision = state.get("review_decision", "")

    safe_log("info", "Routing after human review", decision=review_decision)

    if review_decision == "approve":
        return "generate_report"
    elif review_decision == "modify":
        return "modify_query"
    elif review_decision == "regenerate":
        return "regenerate"
    else:
        # Default to report generation if unclear
        return "generate_report"


@trace_workflow_step("semantic_question_matching", "chain")
@with_retry(ExponentialBackoffStrategy(max_attempts=3))
def analyze_question_node(state: MainWorkflowState) -> MainWorkflowState:
    """语义匹配问题分析节点 - 使用模块化语义匹配功能"""

    session_id = state.get("session_id", "unknown")

    try:
        safe_log("info", "Starting semantic question matching",
                 question=state["user_question"],
                 session_id=session_id)

        # 调用语义匹配模块
        match_result = perform_semantic_matching(state["user_question"])

        safe_log("info", "Semantic matching completed",
                 confidence=match_result["confidence_score"],
                 matched_count=len(match_result["matched_queries"]))

        # 更新状态为新的语义匹配结果
        return {
            **state,
            "confidence_score": match_result["confidence_score"],
            "matched_queries": match_result["matched_queries"],
            "matched_question_ids": match_result["matched_question_ids"],
            "semantic_analysis": match_result["semantic_analysis"],
            "current_step": "query_generation",
            "error_count": state.get("error_count", 0)  # Reset on success
        }

    except Exception as e:
        # Create error context
        error_detector = ErrorDetector()
        error_category, confidence = error_detector.detect_error_category(str(e))

        error_context = ErrorContext(
            session_id=session_id,
            step_name="semantic_question_matching",
            user_question=state["user_question"],
            error_category=error_category,
            severity=ErrorSeverity.HIGH,
            error_message=str(e),
            retry_count=state.get("retry_count", 0),
            additional_context={"state": state}
        )

        # Log error
        log_error_with_context(error_context)

        # Attempt recovery
        recovery_manager = RecoveryManager()
        recovery_result = recovery_manager.attempt_recovery(error_context)

        if recovery_result["recovery_successful"]:
            # Apply recovery modifications
            modified_state = recovery_result.get("modified_state", {})
            return {
                **state,
                **modified_state,
                "error_count": state.get("error_count", 0) + 1,
                "last_error": recovery_result.get("user_guidance", ""),
                "recovery_applied": True
            }
        else:
            # Convert to user-friendly error
            user_error = message_translator.translate_error(error_context)

            return {
                **state,
                "workflow_status": "failed",
                "error_count": state.get("error_count", 0) + 1,
                "user_error_message": user_error["user_message"],
                "technical_error_details": user_error["technical_details"],
                "current_step": "error_handling"
            }


@trace_workflow_step("chief_query_architect", "chain")
def generate_query_node(state: MainWorkflowState) -> MainWorkflowState:
    """首席查询架构师 - 使用模块化查询生成功能"""

    try:
        safe_log("info", "Starting Chief Query Architect", session_id=state["session_id"])

        # Check if we've hit maximum retries
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)
        error_count = state.get("error_count", 0)

        if retry_count >= max_retries or error_count >= max_retries:
            safe_log("error", "Maximum retries exceeded", retry_count=retry_count, error_count=error_count)
            return {
                **state,
                "generated_script_path": "",
                "generated_sql": "-- Generation failed: Maximum retries exceeded",
                "generation_metadata": {"error": "Maximum retries exceeded"},
                "workflow_status": "error",
                "error_messages": state.get("error_messages", []) + ["Maximum generation retries exceeded"],
                "current_step": "error_handling"
            }

        # 调用首席查询架构师模块
        generation_result = generate_chief_architect_query(state)

        safe_log("info", "Chief Query Architect completed successfully",
                 script_path=generation_result["generated_script_path"],
                 plan_steps=len(generation_result.get("query_plan", [])),
                 final_sql_length=len(generation_result.get("generated_sql", "")))

        return {
            **state,
            "generated_script_path": generation_result["generated_script_path"],
            "generated_sql": generation_result["generated_sql"],
            "query_plan": generation_result.get("query_plan", []),
            "generation_metadata": generation_result["generation_metadata"],
            "retry_count": retry_count + 1,
            "current_step": "script_execution"
        }

    except Exception as e:
        safe_log("error", "Chief Query Architect failed", error=str(e))
        new_error_count = state.get("error_count", 0) + 1
        return {
            **state,
            "generated_script_path": "",
            "generated_sql": "-- Chief Architect generation failed",
            "generation_metadata": {"error": str(e)},
            "retry_count": state.get("retry_count", 0) + 1,
            "error_count": new_error_count,
            "error_messages": state.get("error_messages", []) + [f"Chief Architect failed: {str(e)}"],
            "current_step": "script_execution"
        }


@trace_workflow_step("script_execution_with_dry_run", "chain")
def execute_script_node(state: MainWorkflowState) -> MainWorkflowState:
    """脚本执行节点 - 使用模块化Dry Run安全功能"""

    try:
        safe_log("info", "Starting script execution with Dry Run safety valve", session_id=state["session_id"])

        script_path = state.get("generated_script_path", "")
        sql_query = state.get("generated_sql", "")

        # 调用Dry Run安全模块
        execution_result = execute_with_dry_run_safety(script_path, sql_query)

        safe_log("info", "Script execution completed",
                 success=execution_result["execution_success"],
                 row_count=execution_result["execution_result"].get("row_count", 0))

        # 合并状态
        result_state = {
            **state,
            "execution_result": execution_result["execution_result"],
            "execution_success": execution_result["execution_success"],
            "dry_run_result": execution_result["dry_run_result"],
            "current_step": "result_validation"
        }

        # 如果有改进建议，添加到状态中
        if "improvement_suggestions" in execution_result:
            result_state["improvement_suggestions"] = execution_result["improvement_suggestions"]
        if "validation_reasoning" in execution_result:
            result_state["validation_reasoning"] = execution_result["validation_reasoning"]

        return result_state

    except Exception as e:
        safe_log("error", "Script execution failed", error=str(e))
        return {
            **state,
            "execution_success": False,
            "execution_result": {"success": False, "error": str(e)},
            "error_messages": state.get("error_messages", []) + [f"Script execution failed: {str(e)}"],
            "current_step": "result_validation"
        }


def validate_results_node(state: MainWorkflowState) -> MainWorkflowState:
    """结果验证节点 - 调用子流程"""

    try:
        logger.info("Starting result validation", session_id=state["session_id"])

        # Create script validation sub-flow
        validation_flow = create_script_validation_flow()

        # Prepare input for sub-flow
        sub_state = {
            "user_question": state["user_question"],
            "execution_result": state["execution_result"],
            "generated_script_path": state["generated_script_path"],
            "sql_query": state["generated_sql"],
            "retry_count": state.get("retry_count", 0)
        }

        # Execute sub-flow
        result = validation_flow.invoke(sub_state)

        logger.info("Result validation completed",
                   decision=result.get("validation_decision", "rejected"))

        return {
            **state,
            "validation_decision": result.get("validation_decision", "rejected"),
            "validation_reasoning": result.get("validation_reasoning", ""),
            "improvement_suggestions": result.get("improvement_suggestions", []),
            "current_step": "human_review"
        }

    except Exception as e:
        logger.error("Result validation failed", error=str(e))
        return {
            **state,
            "validation_decision": "error",
            "error_messages": state.get("error_messages", []) + [f"Validation failed: {str(e)}"],
            "current_step": "error_handling"
        }


def explain_results_node(state: MainWorkflowState) -> MainWorkflowState:
    """结果解释节点 - 生成用户友好的解释和示例数据"""

    try:
        safe_log("info", "Starting results explanation", session_id=state["session_id"])

        # 导入必要的组件
        from langchain_google_vertexai import ChatVertexAI
        from langchain_core.messages import HumanMessage, SystemMessage
        from config.prompt_templates import EXPLAIN_RESULTS_PROMPT

        # 初始化LLM (使用与其他flow相同的配置)
        def get_llm():
            project_id = os.getenv("LLM__PROJECT_ID", "thrasio-dev-ai-agent")
            model_name = os.getenv("LLM__MODEL_NAME", "gemini-2.5-pro")
            temperature = float(os.getenv("LLM__TEMPERATURE", "0.2"))

            return ChatVertexAI(
                model_name=model_name,
                project=project_id,
                temperature=temperature,
                location="us-central1"
            )

        llm = get_llm()

        # 提取关键信息
        user_question = state.get("user_question", "")
        generated_sql = state.get("generated_sql", "")
        execution_result = state.get("execution_result", {})
        validation_reasoning = state.get("validation_reasoning", "")

        # 获取示例数据 (前5条记录)
        results_data = execution_result.get("results", [])
        sample_data = results_data[:5] if results_data else []
        total_rows = len(results_data)

        # 创建解释提示
        execution_success = execution_result.get('success', False)
        explanation_prompt = EXPLAIN_RESULTS_PROMPT.format(
            user_question=user_question,
            generated_sql=generated_sql,
            total_rows=total_rows,
            execution_success_text='是' if execution_success else '否',
            validation_reasoning=validation_reasoning
        )

        # 调用LLM生成解释
        messages = [
            SystemMessage(content="You are a professional and friendly data analyst who excels at explaining complex data analysis in simple language."),
            HumanMessage(content=explanation_prompt)
        ]

        llm_response = llm.invoke(messages)
        explanation_text = llm_response.content

        # 生成示例数据表格
        sample_table_markdown = ""
        if sample_data:
            # 获取列名
            columns = list(sample_data[0].keys()) if sample_data else []

            if columns:
                # 创建markdown表格头
                header = "| " + " | ".join(columns) + " |"
                separator = "| " + " | ".join(["---"] * len(columns)) + " |"

                # 创建数据行
                rows = []
                for row in sample_data:
                    row_values = []
                    for col in columns:
                        value = row.get(col, "")
                        # 处理None值和格式化数字
                        if value is None:
                            value = "—"
                        elif isinstance(value, float):
                            value = f"{value:.2f}"
                        elif isinstance(value, (int, float)) and abs(value) > 1000:
                            value = f"{value:,}"
                        row_values.append(str(value))
                    rows.append("| " + " | ".join(row_values) + " |")

                sample_table_markdown = f"""

## Example Data

The following are the top  {len(sample_data)} result from the query.（In total {total_rows} results）：

{header}
{separator}
{chr(10).join(rows)}
"""

        # 组合最终的markdown解释
        final_explanation = f"""{explanation_text}

{sample_table_markdown}

---
*This explanation is automatically generated based on the query verification results and is provided for manual review and reference.*
"""

        safe_log("info", "Results explanation generated successfully",
                explanation_length=len(final_explanation),
                sample_rows=len(sample_data))

        return {
            **state,
            "explanation_markdown": final_explanation,
            "current_step": "human_review"
        }

    except Exception as e:
        safe_log("error", "Results explanation failed", error=str(e))
        # 创建一个简单的fallback解释
        fallback_explanation = f"""
## 查询结果解释

**user question:** {state.get('user_question', '')}

**查询概览:**
- 执行状态: {'成功' if state.get('execution_result', {}).get('success', False) else '失败'}
- 数据行数: {len(state.get('execution_result', {}).get('results', []))}

**说明:** 由于技术原因无法生成详细解释，请直接查看下方的查询结果。

---
*解释生成遇到问题，使用简化版本。*
"""
        return {
            **state,
            "explanation_markdown": fallback_explanation,
            "current_step": "human_review",
            "error_messages": state.get("error_messages", []) + [f"Explanation generation failed: {str(e)}"]
        }


def human_review_node(state: MainWorkflowState) -> MainWorkflowState:
    """人工审查节点 - 使用直接interrupt"""
    from langgraph.types import interrupt

    safe_log("info", "Starting human review with interrupt", session_id=state["session_id"])

    # Extract data for human review
    execution_result = state.get("execution_result", {})
    results_data = execution_result.get("results", [])
    data_sample = results_data[:10] if results_data else []  # Show first 10 rows

    # Prepare simple chart recommendations
    recommended_charts = ["table", "bar_chart"]
    if len(data_sample) > 0:
        first_row = data_sample[0]
        numeric_cols = [k for k, v in first_row.items() if isinstance(v, (int, float))]
        if numeric_cols:
            recommended_charts.append("line_chart")

    # Prepare the interrupt payload
    review_payload = {
        "task": "Please review the query results and choose how to proceed",
        "user_question": state.get("user_question", ""),
        "explanation": state.get("explanation_markdown", "No explanation available."),
        "validation_reasoning": state.get("validation_reasoning", ""),
        "data_summary": {
            "total_rows": len(data_sample),
            "has_data": len(data_sample) > 0,
            "execution_success": execution_result.get("success", False)
        },
        "data_sample": data_sample,
        "recommended_charts": recommended_charts,
        "available_charts": ["table", "bar_chart", "line_chart", "pie_chart", "scatter_plot"],
        "options": {
            "approve": "Approve and proceed with visualization",
            "modify": "Request modifications to the query",
            "regenerate": "Regenerate the query from scratch"
        }
    }

    safe_log("info", "Interrupting for human review...")

    # Use LangGraph's interrupt to pause and wait for human input
    human_response = interrupt(review_payload)

    # Process the human response
    safe_log("info", "Received human response", decision=human_response.get("decision", "approve"))

    decision = human_response.get("decision", "approve")
    chart_selection = human_response.get("chart_selection", "table")
    preferences = human_response.get("preferences", {})
    modifications = human_response.get("modifications", [])

    # Validate and set default preferences
    if chart_selection == "bar_chart":
        preferences.setdefault("orientation", "vertical")
        preferences.setdefault("color_scheme", "default")
    elif chart_selection == "line_chart":
        preferences.setdefault("show_markers", True)
    elif chart_selection == "pie_chart":
        preferences.setdefault("show_percentages", True)

    preferences.setdefault("include_data_table", True)
    preferences.setdefault("title", "Analysis Results")

    return {
        **state,
        "user_chart_selection": chart_selection,
        "user_preferences": preferences,
        "review_decision": decision,
        "modification_requests": modifications,
        "current_step": "visualization"
    }


def generate_visualization_node(state: MainWorkflowState) -> MainWorkflowState:
    """可视化生成节点 - 调用子流程"""

    try:
        logger.info("Starting visualization generation", session_id=state["session_id"])

        # Create visualization sub-flow
        viz_flow = create_visualization_flow()

        # Prepare processed data from execution result
        execution_result = state["execution_result"]
        processed_data = execution_result.get("results", [])

        # Read generated script content if path exists
        generated_script_content = ""
        script_path = state.get("generated_script_path", "")
        if script_path and os.path.exists(script_path):
            try:
                with open(script_path, 'r', encoding='utf-8') as f:
                    generated_script_content = f.read()
                logger.info(f"Read script content from {script_path}")
            except Exception as e:
                logger.warning(f"Failed to read script file {script_path}: {e}")

        # Prepare input for sub-flow
        sub_state = {
            "user_question": state["user_question"],
            "processed_data": processed_data,
            "chart_type": state.get("user_chart_selection", "table"),
            "user_preferences": state.get("user_preferences", {}),
            "explanation_markdown": state.get("explanation_markdown", ""),
            "generated_script_content": generated_script_content,
        }

        # Execute sub-flow
        result = viz_flow.invoke(sub_state)

        logger.info("Visualization generation completed",
                   report_path=result.get("report_path", ""))

        return {
            **state,
            "report_path": result.get("report_path", ""),
            "report_metadata": result.get("report_metadata", {}),
            "current_step": "finalization"
        }

    except Exception as e:
        logger.error("Visualization generation failed", error=str(e))
        return {
            **state,
            "workflow_status": "error",
            "error_messages": state.get("error_messages", []) + [f"Visualization generation failed: {str(e)}"],
            "current_step": "error_handling"
        }


def finalize_workflow_node(state: MainWorkflowState) -> MainWorkflowState:
    """工作流程最终化节点"""

    logger.info("Finalizing workflow",
               session_id=state["session_id"],
               report_path=state.get("report_path", ""))

    return {
        **state,
        "workflow_status": "completed",
        "current_step": "completed",
        "completion_time": datetime.now().isoformat()
    }


def handle_error_node(state: MainWorkflowState) -> MainWorkflowState:
    """综合错误处理节点"""

    # Generate final error summary
    error_summary = {
        "session_id": state.get("session_id"),
        "failed_step": state.get("current_step"),
        "total_errors": state.get("error_count", 0),
        "user_message": state.get("user_error_message"),
        "technical_details": state.get("technical_error_details"),
        "recovery_attempts": state.get("recovery_applied", False),
        "timestamp": datetime.now().isoformat()
    }

    # Log final error state
    final_error_context = ErrorContext(
        session_id=state.get("session_id", "unknown"),
        step_name="workflow_completion",
        user_question=state.get("user_question", ""),
        error_category=ErrorCategory.VALIDATION_FAILED,
        severity=ErrorSeverity.HIGH,
        error_message="Workflow failed after multiple retry attempts",
        retry_count=state.get("error_count", 0),
        additional_context=error_summary
    )

    log_error_with_context(final_error_context)

    logger.error("Workflow failed", **error_summary)

    return {
        **state,
        "workflow_status": "failed",
        "error_summary": error_summary,
        "completion_time": datetime.now().isoformat()
    }


class WorkflowErrorHandler:
    """工作流程错误处理器"""

    def __init__(self):
        self.error_patterns = {
            "bigquery_quota": "BigQuery quota exceeded",
            "bigquery_syntax": "SQL syntax error",
            "llm_timeout": "LLM request timeout",
            "data_too_large": "Dataset exceeds size limits",
            "no_matching_queries": "No matching sample queries found"
        }

    def categorize_error(self, error_message: str) -> str:
        """对错误进行分类"""
        for category, pattern in self.error_patterns.items():
            if pattern.lower() in error_message.lower():
                return category
        return "unknown_error"

    def suggest_recovery_action(self, error_category: str, state: Dict) -> str:
        """建议恢复行动"""
        recovery_actions = {
            "bigquery_quota": "Wait and retry, or optimize query to reduce data processing",
            "bigquery_syntax": "Regenerate query with improved SQL validation",
            "llm_timeout": "Retry with shorter input or simplified prompt",
            "data_too_large": "Add more restrictive filters to reduce dataset size",
            "no_matching_queries": "Use custom query generation instead of template matching"
        }

        return recovery_actions.get(error_category, "Contact support team")


class AIDataAnalyst:
    """主要的AI数据分析师接口"""

    def __init__(self):
        self.workflow = create_main_workflow()
        self.session_storage = {}
        self.error_handler = WorkflowErrorHandler()

    def analyze_question(self, user_question: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """分析用户问题并生成报告"""

        # Initialize state
        thread_id = session_id or str(uuid.uuid4())
        initial_state = {
            "user_question": user_question,
            "session_id": thread_id
        }

        try:
            logger.info("Starting workflow execution",
                       question=user_question,
                       session_id=thread_id)

            # Execute workflow with recursion limit and thread configuration for checkpointer
            result = self.workflow.invoke(
                initial_state,
                config={
                    "recursion_limit": 50,
                    "configurable": {"thread_id": thread_id}
                }
            )

            # Store session for potential follow-up
            self.session_storage[result["session_id"]] = result

            logger.info("Workflow completed",
                       session_id=result["session_id"],
                       status=result["workflow_status"])

            return {
                "success": True,
                "session_id": result["session_id"],
                "workflow_status": result["workflow_status"],
                "report_path": result.get("report_path"),
                "report_metadata": result.get("report_metadata", {}),
                "execution_summary": self._generate_execution_summary(result)
            }

        except Exception as e:
            logger.error("Workflow execution failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "session_id": initial_state["session_id"]
            }

    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """获取会话状态"""

        if session_id in self.session_storage:
            session = self.session_storage[session_id]
            return {
                "session_id": session_id,
                "current_step": session.get("current_step", "unknown"),
                "workflow_status": session.get("workflow_status", "unknown"),
                "progress_percentage": self._calculate_progress(session)
            }
        else:
            return {"error": "Session not found"}

    def _generate_execution_summary(self, result: Dict) -> Dict[str, Any]:
        """生成执行摘要"""

        execution_result = result.get("execution_result", {})
        semantic_analysis = result.get("semantic_analysis", {})
        dry_run_result = result.get("dry_run_result", {})

        return {
            "semantic_match_found": semantic_analysis.get("match_found", False),
            "confidence_score": result.get("confidence_score", 0),
            "matched_question_ids": result.get("matched_question_ids", []),
            "execution_time": execution_result.get("execution_time_seconds", 0),
            "data_rows": execution_result.get("row_count", 0),
            "cost_estimate": execution_result.get("cost_estimate_usd", 0),
            "dry_run_estimate_gb": dry_run_result.get("gb_processed", 0),
            "validation_decision": result.get("validation_decision", ""),
            "chart_type": result.get("user_chart_selection", ""),
            "retry_count": result.get("retry_count", 0),
            "generation_approach": result.get("generation_metadata", {}).get("approach", "unknown")
        }

    def _calculate_progress(self, session: Dict) -> int:
        """计算进度百分比"""

        step_progress = {
            "question_analysis": 15,
            "query_generation": 30,
            "script_execution": 50,
            "result_validation": 65,
            "human_review": 80,
            "visualization": 95,
            "completed": 100,
            "failed": 0
        }

        current_step = session.get("current_step", "question_analysis")
        return step_progress.get(current_step, 0)


# LangGraph Studio graph export
graph = create_main_workflow()

# Main execution interface
if __name__ == "__main__":
    analyst = AIDataAnalyst()

    # Example usage
    result = analyst.analyze_question(
        "What are the top performing brands by revenue in Q1 2024?"
    )

    if result["success"]:
        print(f"Analysis completed successfully!")
        print(f"Report saved to: {result['report_path']}")
        print(f"Session ID: {result['session_id']}")
    else:
        print(f"Analysis failed: {result['error']}")