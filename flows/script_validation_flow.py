"""
Script Validation Flow Implementation
脚本验证流程实现

Implements LLM_B script execution result validator that evaluates query execution results,
checks data quality, and determines if the script meets user requirements.
"""

from langgraph.graph import StateGraph, START, END
from typing import TypedDict, List, Optional, Dict, Any
from dataclasses import dataclass
import structlog
import os
from datetime import datetime

logger = structlog.get_logger()


class ValidationState(TypedDict):
    """脚本验证状态管理"""
    user_question: str
    generated_script_path: str
    execution_result: Dict[str, Any]
    sql_query: str
    validation_decision: str  # "approved", "rejected", "needs_revision"
    quality_scores: Dict[str, float]
    data_quality_assessment: Dict[str, Any]
    improvement_suggestions: List[str]
    validation_reasoning: str
    retry_count: int
    next_action: str
    llm_confidence: float
    validation_metadata: Dict[str, Any]


@dataclass
class ValidationCriteria:
    """验证标准定义"""
    execution_success: bool
    data_relevance_score: float  # 0-1
    data_completeness_score: float  # 0-1
    token_compliance: bool
    cost_reasonableness: bool
    result_interpretability: float  # 0-1
    overall_quality_threshold: float = 0.7


def check_execution_status_node(state: ValidationState) -> ValidationState:
    """检查脚本执行状态节点"""
    try:
        logger.info("Checking script execution status")

        execution_result = state.get("execution_result", {})

        # Basic execution status check
        if not execution_result:
            state["validation_decision"] = "rejected"
            state["improvement_suggestions"] = ["No execution result provided"]
            state["next_action"] = "regenerate_script"
            return state

        execution_success = execution_result.get("success", False)
        error_message = execution_result.get("error_message", "")

        # Update validation metadata
        state["validation_metadata"] = {
            "execution_check_timestamp": datetime.now().isoformat(),
            "execution_success": execution_success,
            "has_data": bool(execution_result.get("row_count", 0) > 0),
            "execution_time": execution_result.get("execution_time_seconds", 0),
            "cost_estimate": execution_result.get("cost_estimate_usd", 0)
        }

        if execution_success:
            state["next_action"] = "analyze_data_quality"
            logger.info("Execution successful, proceeding to data quality analysis")
        else:
            state["validation_decision"] = "rejected"
            state["improvement_suggestions"] = [f"Execution failed: {error_message}"]
            state["next_action"] = "generate_suggestions"
            logger.warning(f"Execution failed: {error_message}")

        return state

    except Exception as e:
        logger.error(f"Error checking execution status: {e}")
        state["validation_decision"] = "rejected"
        state["improvement_suggestions"] = [f"Status check failed: {str(e)}"]
        state["next_action"] = "generate_suggestions"
        return state


def analyze_data_quality_node(state: ValidationState) -> ValidationState:
    """分析数据质量节点"""
    try:
        logger.info("Analyzing data quality")

        from tools.script_validation_tools import DataQualityAnalyzer

        execution_result = state.get("execution_result", {})
        user_question = state.get("user_question", "")

        # Extract data for analysis
        data = execution_result.get("sample_data", [])
        if not data and execution_result.get("processed_data"):
            data = execution_result["processed_data"][:100]  # First 100 rows for analysis

        # Perform quality analysis
        analyzer = DataQualityAnalyzer()
        quality_assessment = analyzer.analyze_data_quality(data, user_question)

        state["data_quality_assessment"] = quality_assessment
        state["next_action"] = "validate_with_llm_b"

        logger.info(f"Data quality analysis complete. Score: {quality_assessment.get('overall_quality_score', 0)}")

        return state

    except Exception as e:
        logger.error(f"Error analyzing data quality: {e}")
        state["data_quality_assessment"] = {
            "overall_quality_score": 0.5,
            "issues": [f"Quality analysis failed: {str(e)}"],
            "recommendations": ["Review data quality analysis implementation"]
        }
        state["next_action"] = "validate_with_llm_b"
        return state


def validate_with_llm_b_node(state: ValidationState) -> ValidationState:
    """使用LLM_B进行验证的节点"""
    try:
        logger.info("Validating results with LLM_B")

        from tools.script_validation_tools import ScriptResultValidator

        validator = ScriptResultValidator()

        validation_result = validator.validate_execution_results(
            user_question=state.get("user_question", ""),
            execution_result=state.get("execution_result", {}),
            sql_query=state.get("sql_query", "")
        )

        # Update state with validation results
        state["validation_decision"] = validation_result["validation_decision"]
        state["quality_scores"] = validation_result["quality_scores"]
        state["improvement_suggestions"] = validation_result.get("improvement_suggestions", [])
        state["validation_reasoning"] = validation_result["validation_reasoning"]
        state["llm_confidence"] = validation_result.get("llm_confidence", 0.8)

        # Determine next action based on validation decision
        if validation_result["validation_decision"] == "approved":
            state["next_action"] = "finalize_validation"
        else:
            state["next_action"] = "generate_suggestions"

        logger.info(f"LLM_B validation complete. Decision: {validation_result['validation_decision']}")

        return state

    except Exception as e:
        logger.error(f"Error in LLM_B validation: {e}")
        state["validation_decision"] = "needs_revision"
        state["improvement_suggestions"] = [f"LLM validation failed: {str(e)}"]
        state["validation_reasoning"] = f"Validation process encountered error: {str(e)}"
        state["next_action"] = "generate_suggestions"
        return state


def generate_suggestions_node(state: ValidationState) -> ValidationState:
    """生成改进建议节点"""
    try:
        logger.info("Generating improvement suggestions")

        from tools.script_validation_tools import ImprovementSuggestionGenerator

        generator = ImprovementSuggestionGenerator()

        # Compile validation results
        validation_result = {
            "validation_decision": state.get("validation_decision", "needs_revision"),
            "quality_scores": state.get("quality_scores", {}),
            "data_quality_assessment": state.get("data_quality_assessment", {})
        }

        suggestions = generator.generate_suggestions(
            validation_result=validation_result,
            execution_result=state.get("execution_result", {}),
            user_question=state.get("user_question", "")
        )

        # Merge with existing suggestions
        existing_suggestions = state.get("improvement_suggestions", [])
        all_suggestions = list(set(existing_suggestions + suggestions))

        state["improvement_suggestions"] = all_suggestions
        state["next_action"] = "finalize_validation"

        logger.info(f"Generated {len(suggestions)} improvement suggestions")

        return state

    except Exception as e:
        logger.error(f"Error generating suggestions: {e}")
        state["improvement_suggestions"].append(f"Suggestion generation failed: {str(e)}")
        state["next_action"] = "finalize_validation"
        return state


def finalize_validation_node(state: ValidationState) -> ValidationState:
    """最终化验证结果节点"""
    try:
        logger.info("Finalizing validation results")

        # Ensure all required fields are populated
        if not state.get("validation_decision"):
            state["validation_decision"] = "needs_revision"

        if not state.get("quality_scores"):
            state["quality_scores"] = {"overall_weighted_score": 0.5}

        if not state.get("improvement_suggestions"):
            state["improvement_suggestions"] = ["Review implementation and retry"]

        # Update final validation metadata
        final_metadata = state.get("validation_metadata", {})
        final_metadata.update({
            "validation_completed_timestamp": datetime.now().isoformat(),
            "final_decision": state["validation_decision"],
            "total_suggestions": len(state.get("improvement_suggestions", [])),
            "retry_count": state.get("retry_count", 0)
        })
        state["validation_metadata"] = final_metadata

        # Set next action based on final decision
        if state["validation_decision"] == "approved":
            state["next_action"] = "proceed_to_human_review"
        else:
            retry_count = state.get("retry_count", 0)
            if retry_count < 3:
                state["next_action"] = "regenerate_script"
                state["retry_count"] = retry_count + 1
            else:
                state["next_action"] = "escalate_to_human"

        logger.info(f"Validation finalized. Decision: {state['validation_decision']}, Next: {state['next_action']}")

        return state

    except Exception as e:
        logger.error(f"Error finalizing validation: {e}")
        state["validation_decision"] = "rejected"
        state["next_action"] = "escalate_to_human"
        return state


def decide_execution_path(state: ValidationState) -> str:
    """根据执行状态决定路径"""
    execution_result = state.get("execution_result", {})

    if execution_result.get("success", False):
        return "success"

    retry_count = state.get("retry_count", 0)
    if retry_count < 3:
        return "retry"

    return "failure"


def decide_validation_path(state: ValidationState) -> str:
    """根据验证结果决定路径"""
    decision = state.get("validation_decision", "rejected")
    return decision


def create_script_validation_flow() -> StateGraph:
    """创建脚本验证LangGraph流程"""

    workflow = StateGraph(ValidationState)

    # Add nodes
    workflow.add_node("check_execution_status", check_execution_status_node)
    workflow.add_node("analyze_data_quality", analyze_data_quality_node)
    workflow.add_node("validate_with_llm_b", validate_with_llm_b_node)
    workflow.add_node("generate_improvement_suggestions", generate_suggestions_node)
    workflow.add_node("finalize_validation", finalize_validation_node)

    # Define edges
    workflow.add_edge(START, "check_execution_status")

    # Conditional routing based on execution status
    workflow.add_conditional_edges(
        "check_execution_status",
        decide_execution_path,
        {
            "success": "analyze_data_quality",
            "failure": "generate_improvement_suggestions",
            "retry": "generate_improvement_suggestions"
        }
    )

    workflow.add_edge("analyze_data_quality", "validate_with_llm_b")

    # Conditional routing based on validation decision
    workflow.add_conditional_edges(
        "validate_with_llm_b",
        decide_validation_path,
        {
            "approved": "finalize_validation",
            "needs_revision": "generate_improvement_suggestions",
            "rejected": "generate_improvement_suggestions"
        }
    )

    workflow.add_edge("generate_improvement_suggestions", "finalize_validation")
    workflow.add_edge("finalize_validation", END)

    return workflow.compile()


# Create the compiled workflow for use in other modules
script_validation_workflow = create_script_validation_flow()


class ScriptValidationFlow:
    """脚本验证流程管理器"""

    def __init__(self):
        """初始化验证流程"""
        self.workflow = create_script_validation_flow()
        self.logger = structlog.get_logger()

    def validate_script_execution(self,
                                user_question: str,
                                execution_result: Dict[str, Any],
                                sql_query: str,
                                script_path: str = "") -> Dict[str, Any]:
        """验证脚本执行结果"""

        # Initialize validation state
        initial_state = ValidationState(
            user_question=user_question,
            generated_script_path=script_path,
            execution_result=execution_result,
            sql_query=sql_query,
            validation_decision="",
            quality_scores={},
            data_quality_assessment={},
            improvement_suggestions=[],
            validation_reasoning="",
            retry_count=0,
            next_action="",
            llm_confidence=0.0,
            validation_metadata={}
        )

        try:
            # Execute validation workflow
            self.logger.info("Starting script validation workflow")
            result = self.workflow.invoke(initial_state)

            self.logger.info(f"Validation workflow completed. Decision: {result.get('validation_decision')}")

            return {
                "success": True,
                "validation_result": result,
                "validation_decision": result.get("validation_decision", "rejected"),
                "quality_scores": result.get("quality_scores", {}),
                "improvement_suggestions": result.get("improvement_suggestions", []),
                "next_action": result.get("next_action", "escalate_to_human")
            }

        except Exception as e:
            self.logger.error(f"Validation workflow failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "validation_decision": "rejected",
                "improvement_suggestions": [f"Validation workflow failed: {str(e)}"],
                "next_action": "escalate_to_human"
            }


def get_validation_flow() -> ScriptValidationFlow:
    """获取验证流程实例"""
    return ScriptValidationFlow()