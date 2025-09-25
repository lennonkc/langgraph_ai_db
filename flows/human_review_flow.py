"""
Human Review Flow Implementation
人工审查流程实现

Implements the human-in-the-loop system using LangGraph's native interrupt functionality.
Users review query results and choose visualization formats for report generation.
"""

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from typing import TypedDict, List, Optional, Dict, Any
from dataclasses import dataclass
import structlog
from datetime import datetime

logger = structlog.get_logger()


class HumanReviewState(TypedDict):
    """人工审查状态管理"""
    user_question: str
    execution_result: Dict[str, Any]
    validation_reasoning: str
    data_sample: List[Dict]
    data_summary: Dict[str, Any]
    available_charts: List[str]
    recommended_charts: List[str]
    user_chart_selection: str
    user_preferences: Dict[str, Any]
    review_decision: str  # "approve", "modify", "regenerate"
    modification_requests: List[str]
    review_metadata: Dict[str, Any]


@dataclass
class ChartRecommendation:
    """图表推荐数据类"""
    chart_type: str
    suitability_score: float
    reasoning: str
    data_requirements: List[str]


def prepare_review_data_node(state: HumanReviewState) -> HumanReviewState:
    """准备审查数据节点"""
    try:
        logger.info("Preparing data for human review")

        execution_result = state.get("execution_result", {})

        # Extract sample data for presentation
        data_sample = execution_result.get("sample_data", [])
        if not data_sample and execution_result.get("processed_data"):
            data_sample = execution_result["processed_data"][:20]  # First 20 rows
        elif not data_sample and execution_result.get("results"):
            data_sample = execution_result["results"][:20]  # First 20 rows from results

        # Create basic data summary
        data_summary = {
            "total_rows": len(data_sample),
            "has_data": len(data_sample) > 0,
            "execution_success": execution_result.get("success", False)
        }

        # Basic chart recommendations based on data structure
        recommended_charts = _generate_simple_chart_recommendations(data_sample)
        available_charts = ["table", "bar_chart", "line_chart", "pie_chart", "scatter_plot"]

        updated_state = {
            **state,
            "data_sample": data_sample,
            "data_summary": data_summary,
            "recommended_charts": recommended_charts,
            "available_charts": available_charts,
            "review_metadata": {
                "preparation_timestamp": datetime.now().isoformat(),
                "sample_size": len(data_sample),
                "has_recommendations": len(recommended_charts) > 0
            }
        }

        logger.info(f"Review data prepared: {len(data_sample)} rows, {len(recommended_charts)} recommendations")
        return updated_state

    except Exception as e:
        logger.error(f"Error preparing review data: {e}")
        return {
            **state,
            "data_sample": [],
            "data_summary": {"error": str(e)},
            "recommended_charts": ["table"],
            "available_charts": ["table"],
            "review_metadata": {"error": str(e)}
        }


def _generate_simple_chart_recommendations(data_sample: List[Dict]) -> List[str]:
    """生成简单的图表推荐"""
    if not data_sample:
        return ["table"]

    recommendations = ["table"]  # Always include table as an option

    # Simple heuristics based on data
    if len(data_sample) > 0:
        first_row = data_sample[0]

        # If we have numeric columns, suggest bar chart
        numeric_cols = [k for k, v in first_row.items() if isinstance(v, (int, float))]
        if numeric_cols:
            recommendations.append("bar_chart")

        # If we have date/time columns, suggest line chart
        date_cols = [k for k, v in first_row.items() if 'date' in k.lower() or 'time' in k.lower()]
        if date_cols and numeric_cols:
            recommendations.append("line_chart")

    return recommendations


def human_review_interrupt_node(state: HumanReviewState) -> HumanReviewState:
    """人工审查中断节点 - 使用LangGraph的interrupt功能"""
    logger.info("Starting human review with interrupt")

    # Prepare the data for human review
    review_payload = {
        "task": "Please review the query results and choose how to proceed",
        "user_question": state.get("user_question", ""),
        "validation_reasoning": state.get("validation_reasoning", ""),
        "data_summary": state.get("data_summary", {}),
        "data_sample": state.get("data_sample", [])[:10],  # Show first 10 rows
        "recommended_charts": state.get("recommended_charts", []),
        "available_charts": state.get("available_charts", []),
        "options": {
            "approve": "Approve and proceed with visualization",
            "modify": "Request modifications to the query",
            "regenerate": "Regenerate the query from scratch"
        }
    }

    logger.info("Interrupting for human review...")

    # Use LangGraph's interrupt to pause and wait for human input
    # This will throw an interrupt and pause the workflow
    human_response = interrupt(review_payload)

    # This code will only execute after the workflow is resumed
    logger.info(f"Received human response: {human_response}")

    # Extract decision and preferences from human response
    decision = human_response.get("decision", "approve")
    chart_selection = human_response.get("chart_selection", "table")
    preferences = human_response.get("preferences", {})
    modifications = human_response.get("modifications", [])

    # Validate and process preferences
    processed_preferences = _validate_and_process_preferences(chart_selection, preferences)

    return {
        **state,
        "review_decision": decision,
        "user_chart_selection": chart_selection,
        "user_preferences": processed_preferences,
        "modification_requests": modifications,
        "review_metadata": {
            **state.get("review_metadata", {}),
            "review_timestamp": datetime.now().isoformat(),
            "review_method": "langgraph_interrupt",
            "human_decision": decision
        }
    }


def _validate_and_process_preferences(chart_type: str, preferences: Dict) -> Dict:
    """验证和处理用户偏好设置"""
    processed = preferences.copy()

    # Set defaults based on chart type
    if chart_type == "bar_chart":
        processed.setdefault("orientation", "vertical")
        processed.setdefault("color_scheme", "default")
    elif chart_type == "line_chart":
        processed.setdefault("show_markers", True)
        processed.setdefault("smooth_lines", False)
    elif chart_type == "pie_chart":
        processed.setdefault("show_percentages", True)
        processed.setdefault("explode_largest", False)

    # General defaults
    processed.setdefault("include_data_table", True)
    processed.setdefault("title", "Data Analysis Results")

    return processed


def _process_modification_requests(modifications: List[str]) -> List[str]:
    """处理修改请求"""
    processed = []

    for mod in modifications:
        if isinstance(mod, str) and mod.strip():
            processed.append(mod.strip())

    # Add default modification if none provided
    if not processed:
        processed.append("Review and optimize query for better performance")

    return processed


def decide_next_action(state: HumanReviewState) -> str:
    """根据用户决策决定下一步行动"""
    decision = state.get("review_decision", "approve")

    # Map decisions to workflow paths
    decision_mapping = {
        "approve": "approve",
        "modify": "modify",
        "regenerate": "regenerate"
    }

    return decision_mapping.get(decision, "approve")


def create_human_review_flow() -> StateGraph:
    """创建人工审查LangGraph流程"""
    import os
    from langgraph.checkpoint.memory import MemorySaver

    workflow = StateGraph(HumanReviewState)

    # Add nodes
    workflow.add_node("prepare_review_data", prepare_review_data_node)
    workflow.add_node("human_review_interrupt", human_review_interrupt_node)

    # Define edges
    workflow.add_edge(START, "prepare_review_data")
    workflow.add_edge("prepare_review_data", "human_review_interrupt")

    # Conditional routing based on user decision
    workflow.add_conditional_edges(
        "human_review_interrupt",
        decide_next_action,
        {
            "approve": END,     # Proceed to visualization
            "modify": END,      # Return to query modification
            "regenerate": END   # Return to query regeneration
        }
    )

    # Use checkpointer only when not running in LangGraph API environment
    use_custom_checkpointer = os.getenv("LANGGRAPH_API_ENV") != "true"

    if use_custom_checkpointer:
        # Add checkpointer to enable interrupts in local environment
        checkpointer = MemorySaver()
        return workflow.compile(checkpointer=checkpointer)
    else:
        # Let LangGraph API handle persistence
        return workflow.compile()


# Create the compiled workflow for use in other modules
human_review_workflow = create_human_review_flow()


class HumanReviewFlow:
    """人工审查流程管理器 - 简化版使用interrupt"""

    def __init__(self):
        """初始化审查流程"""
        self.workflow = create_human_review_flow()
        self.logger = structlog.get_logger()

    def conduct_human_review(self,
                            user_question: str,
                            execution_result: Dict[str, Any],
                            validation_reasoning: str = "") -> Dict[str, Any]:
        """进行人工审查"""

        # Initialize review state
        initial_state = HumanReviewState(
            user_question=user_question,
            execution_result=execution_result,
            validation_reasoning=validation_reasoning,
            data_sample=[],
            data_summary={},
            available_charts=[],
            recommended_charts=[],
            user_chart_selection="",
            user_preferences={},
            review_decision="",
            modification_requests=[],
            review_metadata={}
        )

        try:
            # Execute review workflow
            self.logger.info("Starting human review workflow with interrupt")
            result = self.workflow.invoke(initial_state)

            self.logger.info(f"Human review completed. Decision: {result.get('review_decision')}")

            return {
                "user_chart_selection": result.get("user_chart_selection", "table"),
                "user_preferences": result.get("user_preferences", {}),
                "review_decision": result.get("review_decision", "approve"),
                "modification_requests": result.get("modification_requests", [])
            }

        except Exception as e:
            self.logger.error(f"Human review workflow failed: {e}")
            return {
                "user_chart_selection": "table",
                "user_preferences": {"title": "Analysis Results"},
                "review_decision": "approve",
                "modification_requests": []
            }


def get_human_review_flow() -> HumanReviewFlow:
    """获取人工审查流程实例"""
    return HumanReviewFlow()