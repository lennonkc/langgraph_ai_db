"""
Visualization Flow Implementation
可视化流程实现

LangGraph workflow for generating interactive HTML reports with charts
using Vega-Lite, Plotly, or other visualization libraries.
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, TypedDict
from dataclasses import dataclass
import structlog

from langgraph.graph import StateGraph, START, END

logger = structlog.get_logger()


class VisualizationState(TypedDict):
    """可视化状态管理"""
    user_question: str
    processed_data: List[Dict]
    chart_type: str
    user_preferences: Dict[str, Any]
    visualization_spec: Dict[str, Any]
    html_report: str
    report_path: str
    report_metadata: Dict[str, Any]
    next_action: str
    success: bool
    error: Optional[str]
    explanation_markdown: str
    generated_script_content: str
    ai_summary_markdown: str


@dataclass
class ReportConfig:
    """报告配置"""
    title: str
    chart_type: str
    data: List[Dict]
    preferences: Dict[str, Any]
    theme: str = "default"
    interactive: bool = True


class VisualizationFlow:
    """可视化流程管理器"""

    def __init__(self):
        """初始化可视化流程"""
        self.workflow = self._create_workflow()

    def generate_visualization_report(self,
                                    user_question: str,
                                    processed_data: List[Dict],
                                    chart_type: str,
                                    user_preferences: Dict[str, Any],
                                    explanation_markdown: str = "",
                                    generated_script_content: str = "") -> Dict[str, Any]:
        """生成可视化报告"""

        try:
            logger.info("Starting visualization report generation")

            initial_state = VisualizationState(
                user_question=user_question,
                processed_data=processed_data,
                chart_type=chart_type,
                user_preferences=user_preferences,
                visualization_spec={},
                html_report="",
                report_path="",
                report_metadata={},
                next_action="",
                success=False,
                error=None,
                explanation_markdown=explanation_markdown,
                generated_script_content=generated_script_content,
                ai_summary_markdown=""
            )

            # Execute workflow
            final_state = self.workflow.invoke(initial_state)

            logger.info(f"Visualization report generation completed: {final_state['success']}")

            return {
                "success": final_state["success"],
                "report_path": final_state.get("report_path", ""),
                "html_report": final_state.get("html_report", ""),
                "visualization_spec": final_state.get("visualization_spec", {}),
                "report_metadata": final_state.get("report_metadata", {}),
                "error": final_state.get("error")
            }

        except Exception as e:
            logger.error(f"Visualization flow error: {e}")
            return {
                "success": False,
                "error": str(e),
                "report_path": "",
                "html_report": "",
                "visualization_spec": {},
                "report_metadata": {}
            }

    def _create_workflow(self) -> StateGraph:
        """创建LangGraph工作流"""
        workflow = StateGraph(VisualizationState)

        # Add nodes
        workflow.add_node("prepare_visualization_data", prepare_visualization_data_node)
        workflow.add_node("generate_chart_spec", generate_chart_spec_node)
        workflow.add_node("generate_ai_summary", generate_ai_summary_node)
        workflow.add_node("create_html_report", create_html_report_node)
        workflow.add_node("save_report", save_report_node)
        workflow.add_node("finalize_output", finalize_output_node)

        # Define edges
        workflow.add_edge(START, "prepare_visualization_data")
        workflow.add_edge("prepare_visualization_data", "generate_chart_spec")
        workflow.add_edge("generate_chart_spec", "generate_ai_summary")
        workflow.add_edge("generate_ai_summary", "create_html_report")
        workflow.add_edge("create_html_report", "save_report")
        workflow.add_edge("save_report", "finalize_output")
        workflow.add_edge("finalize_output", END)

        return workflow.compile()


def prepare_visualization_data_node(state: VisualizationState) -> VisualizationState:
    """准备可视化数据节点"""

    try:
        logger.info("Preparing visualization data")

        # Validate input data
        if not state["processed_data"]:
            return {
                **state,
                "success": False,
                "error": "No data available for visualization",
                "next_action": "error"
            }

        # Create report metadata
        metadata = {
            "generated_at": datetime.now().isoformat(),
            "chart_type": state["chart_type"],
            "data_points": len(state["processed_data"]),
            "user_question": state["user_question"],
            "preferences": state["user_preferences"]
        }

        logger.info(f"Data preparation completed with {len(state['processed_data'])} records")

        return {
            **state,
            "report_metadata": metadata,
            "next_action": "generate_chart"
        }

    except Exception as e:
        logger.error(f"Data preparation error: {e}")
        return {
            **state,
            "success": False,
            "error": f"Data preparation failed: {str(e)}",
            "next_action": "error"
        }


def generate_chart_spec_node(state: VisualizationState) -> VisualizationState:
    """生成图表规格节点"""

    try:
        logger.info(f"Generating chart specification for {state['chart_type']}")

        from tools.visualization_tools import ChartGenerator

        chart_generator = ChartGenerator()

        chart_result = chart_generator.generate_chart(
            state["chart_type"],
            state["processed_data"],
            state["user_preferences"],
            state["user_question"]
        )

        logger.info(f"Chart specification generated using {chart_result.get('library', 'unknown')} library")

        return {
            **state,
            "visualization_spec": chart_result,
            "next_action": "create_report"
        }

    except Exception as e:
        logger.error(f"Chart generation error: {e}")
        return {
            **state,
            "success": False,
            "error": f"Chart generation failed: {str(e)}",
            "next_action": "error"
        }


def generate_ai_summary_node(state: VisualizationState) -> VisualizationState:
    """生成AI摘要节点"""

    try:
        logger.info("Generating AI summary for the data analysis")

        # Import LLM dependencies
        from langchain_google_vertexai import ChatVertexAI
        from langchain.schema import HumanMessage, SystemMessage
        import os
        from config.prompt_templates import VISUALIZATION_AI_SUMMARY_PROMPT

        # Initialize LLM client (same configuration as in LLMClient)
        project_id = os.getenv("LLM__PROJECT_ID", "thrasio-dev-ai-agent")
        model_name = os.getenv("LLM__MODEL_NAME", "gemini-2.5-pro")
        temperature = float(os.getenv("LLM__TEMPERATURE", "0.1"))

        llm = ChatVertexAI(
            model_name=model_name,
            project=project_id,
            temperature=temperature,
            top_p=0.8,
            top_k=40,
        )

        # Prepare data sample for LLM
        processed_data = state["processed_data"]
        user_question = state["user_question"]

        # Sample data to avoid overwhelming the LLM
        if len(processed_data) > 20:
            sample_data = processed_data[:10] + processed_data[-10:]
            data_info = f"Showing sample of {len(sample_data)} rows from total {len(processed_data)} rows"
        else:
            sample_data = processed_data
            data_info = f"Complete dataset with {len(sample_data)} rows"

        # Get column information
        columns = list(sample_data[0].keys()) if sample_data else []

        # Build the prompt
        system_prompt = VISUALIZATION_AI_SUMMARY_PROMPT

        # Prepare data summary for the prompt
        data_summary = json.dumps(sample_data, ensure_ascii=False, indent=2)

        human_prompt = f"""
用户问题：{user_question}

数据信息：{data_info}
数据列：{', '.join(columns)}

数据内容：
```json
{data_summary}
```

请基于以上信息生成分析摘要："""

        # Call LLM
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]

        response = llm.invoke(messages)
        ai_summary = response.content.strip()

        logger.info("AI summary generated successfully")

        return {
            **state,
            "ai_summary_markdown": ai_summary,
            "next_action": "create_report"
        }

    except Exception as e:
        logger.error(f"AI summary generation error: {e}")
        # Fallback: continue without AI summary
        return {
            **state,
            "ai_summary_markdown": "",
            "next_action": "create_report"
        }


def create_html_report_node(state: VisualizationState) -> VisualizationState:
    """创建HTML报告节点"""

    try:
        logger.info("Creating HTML report")

        from tools.visualization_tools import HTMLReportGenerator

        report_generator = HTMLReportGenerator()

        html_report = report_generator.generate_full_report(
            state["user_question"],
            state["visualization_spec"],
            state["processed_data"],
            state["user_preferences"],
            state["report_metadata"],
            state.get("explanation_markdown", ""),
            state.get("generated_script_content", ""),
            state.get("ai_summary_markdown", "")
        )

        logger.info("HTML report created successfully")

        return {
            **state,
            "html_report": html_report,
            "next_action": "save_report"
        }

    except Exception as e:
        logger.error(f"HTML report creation error: {e}")
        return {
            **state,
            "success": False,
            "error": f"HTML report creation failed: {str(e)}",
            "next_action": "error"
        }


def save_report_node(state: VisualizationState) -> VisualizationState:
    """保存报告节点"""

    try:
        logger.info("Saving report to file")

        # Create reports directory if it doesn't exist
        reports_dir = "reports"
        os.makedirs(reports_dir, exist_ok=True)

        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analysis_report_{timestamp}.html"
        report_path = os.path.join(reports_dir, filename)

        # Save HTML report
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(state["html_report"])

        # Save metadata
        metadata_path = report_path.replace('.html', '_metadata.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(state["report_metadata"], f, indent=2, ensure_ascii=False)

        logger.info(f"Report saved to {report_path}")

        return {
            **state,
            "report_path": report_path,
            "next_action": "finalize"
        }

    except Exception as e:
        logger.error(f"Report saving error: {e}")
        return {
            **state,
            "success": False,
            "error": f"Report saving failed: {str(e)}",
            "next_action": "error"
        }


def finalize_output_node(state: VisualizationState) -> VisualizationState:
    """完成输出节点"""

    try:
        logger.info("Finalizing visualization output")

        # Update metadata with final information
        final_metadata = {
            **state["report_metadata"],
            "report_path": state["report_path"],
            "report_size_bytes": len(state["html_report"].encode('utf-8')),
            "completion_timestamp": datetime.now().isoformat(),
            "workflow_status": "completed"
        }

        logger.info("Visualization workflow completed successfully")

        return {
            **state,
            "report_metadata": final_metadata,
            "success": True,
            "next_action": "completed"
        }

    except Exception as e:
        logger.error(f"Finalization error: {e}")
        return {
            **state,
            "success": False,
            "error": f"Finalization failed: {str(e)}",
            "next_action": "error"
        }


def create_visualization_flow() -> StateGraph:
    """创建可视化生成LangGraph流程"""

    workflow = StateGraph(VisualizationState)

    # Add nodes
    workflow.add_node("prepare_visualization_data", prepare_visualization_data_node)
    workflow.add_node("generate_chart_spec", generate_chart_spec_node)
    workflow.add_node("generate_ai_summary", generate_ai_summary_node)
    workflow.add_node("create_html_report", create_html_report_node)
    workflow.add_node("save_report", save_report_node)
    workflow.add_node("finalize_output", finalize_output_node)

    # Define edges
    workflow.add_edge(START, "prepare_visualization_data")
    workflow.add_edge("prepare_visualization_data", "generate_chart_spec")
    workflow.add_edge("generate_chart_spec", "generate_ai_summary")
    workflow.add_edge("generate_ai_summary", "create_html_report")
    workflow.add_edge("create_html_report", "save_report")
    workflow.add_edge("save_report", "finalize_output")
    workflow.add_edge("finalize_output", END)

    return workflow.compile()