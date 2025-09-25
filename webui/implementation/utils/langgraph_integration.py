"""
LangGraph工作流集成模块
直接调用现有的LangGraph数据分析工作流
"""

import asyncio
import json
import uuid
import sys
from datetime import datetime
from typing import Dict, Any, Optional, Generator, List, AsyncGenerator
from pathlib import Path
import pandas as pd

import streamlit as st

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

# 导入现有的LangGraph工作流
try:
    from main_workflow import create_main_workflow, MainWorkflowState
    from langgraph.checkpoint.memory import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError as e:
    print(f"Warning: LangGraph modules not available: {e}")
    LANGGRAPH_AVAILABLE = False

# 全局共享的checkpointer实例，确保在整个Streamlit会话中持久化
_GLOBAL_CHECKPOINTER = None

def get_global_checkpointer():
    """获取全局共享的checkpointer实例"""
    global _GLOBAL_CHECKPOINTER
    if _GLOBAL_CHECKPOINTER is None:
        _GLOBAL_CHECKPOINTER = MemorySaver()
        print("创建新的全局 MemorySaver 实例")
    return _GLOBAL_CHECKPOINTER

class LangGraphIntegration:
    """LangGraph工作流集成类"""

    def __init__(self):
        self.graph = None
        self.compiled_graph = None
        self.pending_workflows = {}  # 存储等待人工审查的工作流状态
        self.initialize_workflow()

    def initialize_workflow(self) -> bool:
        """初始化LangGraph工作流"""
        try:
            if not LANGGRAPH_AVAILABLE:
                st.error("LangGraph工作流模块未找到，请检查项目结构")
                return False

            # 设置全局共享的checkpointer
            global_checkpointer = get_global_checkpointer()

            # 导入main_workflow模块并设置外部checkpointer
            import main_workflow
            main_workflow.set_external_checkpointer(global_checkpointer)

            # 强制设置webui环境变量，确保使用checkpointer
            import os
            # 在webui环境下，我们需要checkpointer来支持interrupts
            original_env = os.getenv("LANGGRAPH_API_ENV")
            os.environ["LANGGRAPH_API_ENV"] = "false"  # 强制使用本地checkpointer

            try:
                # 创建并获取已编译的工作流图
                self.compiled_graph = create_main_workflow()
                self.graph = self.compiled_graph  # 保持向后兼容
                print(f"成功初始化工作流，使用共享checkpointer: {type(global_checkpointer)}")
            finally:
                # 恢复原来的环境变量
                if original_env is not None:
                    os.environ["LANGGRAPH_API_ENV"] = original_env
                else:
                    os.environ.pop("LANGGRAPH_API_ENV", None)

            st.session_state.langgraph_connected = True
            return True

        except Exception as e:
            st.error(f"LangGraph初始化失败: {str(e)}")
            st.session_state.langgraph_connected = False
            self.compiled_graph = None
            return False

    async def process_query_async(
        self,
        user_question: str,
        session_id: str = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        异步处理用户查询
        使用Generator实现流式响应
        """

        if not self.compiled_graph:
            yield {
                "type": "error",
                "content": "LangGraph工作流未初始化",
                "step": "initialization"
            }
            return

        try:
            # 构建输入状态
            workflow_input = MainWorkflowState(
                user_question=user_question,
                session_id=session_id or f"session_{uuid.uuid4()}"
            )

            yield {
                "type": "workflow_start",
                "content": "开始分析问题",
                "step": "start",
                "title": "🚀 工作流启动"
            }

            # 执行工作流并流式返回结果
            async for event in self.compiled_graph.astream(workflow_input):
                node_name = list(event.keys())[0]
                node_output = event[node_name]

                # 转换工作流事件为前端可用格式
                yield self.transform_workflow_event(node_name, node_output)

        except Exception as e:
            yield {
                "type": "error",
                "content": f"工作流执行错误: {str(e)}",
                "step": "execution",
                "error_details": str(e)
            }

    def process_query_sync(
        self,
        user_question: str,
        session_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        同步处理用户查询（用于Streamlit）
        支持Human Review的中断和恢复
        """
        if not self.compiled_graph:
            return [{
                "type": "error",
                "content": "LangGraph工作流未初始化",
                "step": "initialization"
            }]

        try:
            # 构建输入状态
            workflow_input = MainWorkflowState(
                user_question=user_question,
                session_id=session_id or f"session_{uuid.uuid4()}"
            )

            # 使用可恢复的工作流执行
            return self.execute_with_checkpoints(workflow_input, session_id)

        except Exception as e:
            return [{
                "type": "error",
                "content": f"工作流执行错误: {str(e)}",
                "step": "execution",
                "error_details": str(e)
            }]

    def process_final_state(self, state: MainWorkflowState) -> Dict[str, Any]:
        """处理工作流最终状态"""

        # 类型检查和安全处理
        if not isinstance(state, dict):
            print(f"错误：收到非字典类型的状态: {type(state)}")
            return {
                "type": "error",
                "content": f"状态类型错误: 期望字典，收到 {type(state)}",
                "step": "process_final_state"
            }

        # 添加调试信息
        print(f"处理最终状态，当前步骤: {state.get('current_step', 'unknown')}")
        print(f"工作流状态: {state.get('workflow_status', 'unknown')}")

        # 检查是否有explanation，如果有则可能需要human review
        has_explanation = bool(state.get('explanation_markdown', ''))
        has_human_review = bool(state.get('review_decision', ''))

        print(f"是否有解释: {has_explanation}, 是否有human review: {has_human_review}")

        # 从执行结果中提取查询数据
        execution_result = state.get('execution_result', {})
        query_results = execution_result.get('results', [])
        sql_query = state.get('generated_sql', '')
        visualization_config = state.get('visualization_config', {})
        analysis_insights = state.get('analysis_insights', [])

        # 转换查询结果为DataFrame
        data = None
        if query_results:
            try:
                data = pd.DataFrame(query_results)
                print(f"✅ 成功转换 {len(query_results)} 行数据为DataFrame")
            except Exception as e:
                st.warning(f"数据转换失败: {str(e)}")
                data = pd.DataFrame()
        else:
            print("⚠️ 未找到查询结果数据")
            data = pd.DataFrame()

        # 生成分析洞察（基于实际数据内容）
        if not analysis_insights and data is not None and not data.empty:
            row_count = len(data)

            # 获取数据列信息
            columns = list(data.columns)

            # 根据实际数据生成洞察
            insights = [f"查询返回 {row_count:,} 条记录"]

            # 如果有数值列，添加统计信息
            numeric_columns = data.select_dtypes(include=['number']).columns.tolist()
            if numeric_columns:
                insights.append(f"包含 {len(numeric_columns)} 个数值字段: {', '.join(numeric_columns[:3])}")

            # 如果有特定的业务字段，添加相关信息
            if 'listing_status' in columns:
                try:
                    discontinued_data = data[data['listing_status'] == 'Discontinued']
                    if not discontinued_data.empty and 'product_count' in columns:
                        discontinued_count = discontinued_data['product_count'].sum()
                        insights.append(f"包含 {discontinued_count:,} 个Discontinued状态产品")
                except Exception as e:
                    print(f"处理listing_status时出错: {e}")

            if 'brand' in columns or 'brand_name' in columns:
                brand_col = 'brand' if 'brand' in columns else 'brand_name'
                try:
                    unique_brands = data[brand_col].nunique()
                    insights.append(f"涉及 {unique_brands} 个不同品牌")
                except Exception as e:
                    print(f"处理品牌信息时出错: {e}")

            analysis_insights = insights

        # process_final_state 现在只处理最终结果，不再包含human review逻辑
        # human review逻辑已移到 execute_with_checkpoints 中处理
        print(f"调试：process_final_state 被调用，has_explanation={has_explanation}, has_human_review={has_human_review}")

        return {
            "type": "final_result",
            "content": "分析完成",
            "step": "completed",
            "title": "✅ 分析完成",
            "success": True,
            "data": {
                "sql_query": sql_query,
                "query_results": data,
                "visualization_config": visualization_config,
                "insights": analysis_insights,
                "execution_time": state.get('execution_time', 0),
                "record_count": len(query_results) if query_results else 0,
                "report_path": state.get('report_path', ''),
                "data_summary": {
                    "columns": list(data.columns) if data is not None and not data.empty else [],
                    "shape": data.shape if data is not None else (0, 0)
                }
            }
        }

    def transform_workflow_event(self, node_name: str, node_output: Dict) -> Dict[str, Any]:
        """转换工作流事件为前端格式"""

        event_mappings = {
            "initialize_session": {
                "type": "initialization",
                "step": "session_init",
                "title": "🔧 会话初始化"
            },
            "analyze_question": {
                "type": "analysis",
                "step": "question_analysis",
                "title": "🔍 问题分析"
            },
            "generate_query": {
                "type": "generation",
                "step": "query_generation",
                "title": "📝 SQL生成"
            },
            "execute_script": {
                "type": "execution",
                "step": "query_execution",
                "title": "⚡ 查询执行"
            },
            "validate_results": {
                "type": "validation",
                "step": "validation",
                "title": "✅ 结果验证"
            },
            "generate_visualization": {
                "type": "visualization",
                "step": "visualization",
                "title": "📊 数据可视化"
            },
            "human_review": {
                "type": "review",
                "step": "human_review",
                "title": "👤 人工审查"
            },
            "finalize_workflow": {
                "type": "finalization",
                "step": "finalization",
                "title": "🎯 完成分析"
            },
            "handle_error": {
                "type": "error_handling",
                "step": "error_handling",
                "title": "🚨 错误处理"
            }
        }

        mapping = event_mappings.get(node_name, {
            "type": "unknown",
            "step": node_name,
            "title": f"📋 {node_name}"
        })

        return {
            **mapping,
            "content": self.extract_content_from_output(node_output),
            "data": node_output,
            "timestamp": datetime.now().isoformat(),
            "success": not node_output.get("error", False)
        }

    def extract_content_from_output(self, node_output: Dict) -> str:
        """从节点输出中提取内容信息"""

        if isinstance(node_output, dict):
            # 尝试提取不同类型的内容
            content_fields = ['message', 'output', 'result', 'summary', 'description']

            for field in content_fields:
                if field in node_output and node_output[field]:
                    return str(node_output[field])

            # 如果有SQL查询，显示SQL
            if 'generated_sql' in node_output:
                return f"生成SQL: {node_output['generated_sql'][:100]}..."

            # 如果有查询结果，显示记录数
            if 'query_results' in node_output:
                results = node_output['query_results']
                if isinstance(results, list):
                    return f"查询返回 {len(results)} 条记录"

            # 默认显示节点名称
            return f"节点 {node_output.get('node_name', 'unknown')} 执行完成"

        return str(node_output) if node_output else "节点执行完成"

    def validate_connection(self) -> bool:
        """验证LangGraph连接状态"""
        return self.compiled_graph is not None and LANGGRAPH_AVAILABLE

    def execute_with_checkpoints(self, workflow_input: MainWorkflowState, session_id: str) -> List[Dict[str, Any]]:
        """
        使用checkpoint执行工作流，支持中断和恢复
        使用流式执行来正确处理interrupts
        """
        thread_id = session_id or workflow_input.get("session_id", f"session_{uuid.uuid4()}")
        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 50
        }

        try:
            # 使用流式执行来正确处理中断
            events = []
            final_state = None

            # 先检查是否有已经存在的状态（例如从中断恢复）
            try:
                current_state = self.compiled_graph.get_state(config)
                if current_state and current_state.next:
                    print(f"发现已存在的工作流状态，当前步骤: {current_state.next}")
            except Exception as e:
                print(f"检查现有状态时出错: {e}")

            # 使用流式执行
            for event in self.compiled_graph.stream(workflow_input, config=config):
                events.append(event)
                # 获取最新状态
                if isinstance(event, dict) and len(event) > 0:
                    node_name = list(event.keys())[0]
                    final_state = event[node_name]
                    print(f"执行节点: {node_name}")

            # 检查工作流是否正常完成
            if final_state:
                print(f"调试：工作流完成，final_state keys: {list(final_state.keys()) if isinstance(final_state, dict) else 'not dict'}")

                # 检查是否到达了需要human review的状态
                current_graph_state = self.compiled_graph.get_state(config)
                print(f"调试：获取当前图状态: {current_graph_state is not None}")

                if current_graph_state and current_graph_state.next:
                    next_steps = current_graph_state.next
                    print(f"工作流中断，等待步骤: {next_steps}")

                    # 检查是否在human_review节点等待
                    if 'human_review' in next_steps:
                        print(f"调试：检测到human_review中断，调用handle_human_review_interrupt")
                        return self.handle_human_review_interrupt(thread_id, config, "Workflow interrupted at human_review")
                    else:
                        print(f"调试：中断状态但不是human_review: {next_steps}")
                elif current_graph_state:
                    print(f"调试：工作流状态存在但没有next步骤")
                else:
                    print(f"调试：无法获取当前图状态")

                # 特殊处理：如果工作流到达了 explain_results 但没有进入 human_review，强制触发
                has_explanation = bool(final_state.get('explanation_markdown', ''))
                current_step = final_state.get('current_step', '')

                print(f"调试：检查explain_results特殊情况 - has_explanation: {has_explanation}, current_step: {current_step}")

                if has_explanation and current_step == 'human_review':
                    print(f"调试：检测到explain_results完成但未触发human_review，强制触发")
                    return self.handle_human_review_interrupt(thread_id, config, "Force human review after explain_results")

                # 新的逻辑：默认所有成功执行的查询都需要human review
                print(f"调试：检查是否需要human review...")

                # 检查工作流的最终状态，判断是否需要human review
                should_review = self.should_trigger_human_review(final_state)
                print(f"调试：should_trigger_human_review 返回: {should_review}")

                if should_review:
                    print(f"调试：触发human review")
                    return self.handle_human_review_interrupt(thread_id, config, "Human review required based on workflow state")

                # 工作流正常完成（但这种情况现在应该很少见，因为我们默认都需要review）
                print(f"调试：工作流正常完成，无需human review")
                result = self.process_final_state(final_state)
                return [result]
            else:
                return [{
                    "type": "error",
                    "content": "工作流执行未返回最终状态",
                    "step": "execution"
                }]

        except Exception as e:
            error_str = str(e)
            print(f"工作流执行异常: {error_str}")

            # 检查是否是LangGraph的中断异常
            if any(keyword in error_str.lower() for keyword in ["interrupt", "waiting", "human"]):
                return self.handle_human_review_interrupt(thread_id, config, error_str)
            else:
                # 其他错误
                return [{
                    "type": "error",
                    "content": f"工作流执行错误: {error_str}",
                    "step": "execution",
                    "error_details": error_str
                }]

    def handle_human_review_interrupt(self, thread_id: str, config: Dict, error_str: str) -> List[Dict[str, Any]]:
        """
        处理人工审查中断
        """
        print(f"调试：handle_human_review_interrupt 被调用 - thread_id: {thread_id}")
        try:
            # 获取当前状态
            current_state = self.get_current_state(thread_id, config)
            print(f"调试：获取到的当前状态类型: {type(current_state)}")

            if current_state:
                print(f"调试：当前状态keys: {list(current_state.keys()) if isinstance(current_state, dict) else 'not dict'}")

                # 存储工作流状态以供后续恢复
                self.pending_workflows[thread_id] = {
                    "state": current_state,
                    "config": config,
                    "timestamp": datetime.now().isoformat()
                }

                # 提取review数据
                review_data = self.extract_review_data(current_state)
                print(f"调试：提取的review_data: {review_data is not None and len(review_data) > 0}")

                # 返回人工审查状态
                result = [{
                    "type": "human_review_required",
                    "content": "需要人工审查",
                    "step": "human_review",
                    "thread_id": thread_id,
                    "review_data": review_data
                }]
                print(f"调试：返回human_review_required结果")
                return result
            else:
                print(f"调试：无法获取工作流状态")
                return [{
                    "type": "error",
                    "content": "无法获取工作流状态",
                    "step": "human_review"
                }]
        except Exception as e:
            print(f"调试：handle_human_review_interrupt异常: {e}")
            return [{
                "type": "error",
                "content": f"处理人工审查中断失败: {str(e)}",
                "step": "human_review"
            }]

    def get_current_state(self, thread_id: str, config: Dict) -> Dict:
        """
        获取当前工作流状态
        """
        try:
            # 获取checkpoint状态
            state_snapshot = self.compiled_graph.get_state(config)
            return state_snapshot.values if state_snapshot else None
        except Exception as e:
            print(f"获取状态失败: {e}")
            return None

    def should_trigger_human_review(self, state: Dict) -> bool:
        """
        根据工作流状态判断是否需要触发human review
        默认所有成功的查询都需要human review
        """
        if not state:
            print("调试：状态为空，不触发human review")
            return False

        print(f"调试：检查状态的所有key: {list(state.keys())}")

        # 检查多种可能的完成状态指标
        execution_result = state.get("execution_result", {})
        has_execution_success = bool(state.get("execution_success", False))
        has_execution_result = bool(execution_result.get("success", False))
        has_generated_sql = bool(state.get("generated_sql", ""))
        has_human_review = bool(state.get("review_decision", ""))
        has_explanation = bool(state.get("explanation_markdown", ""))

        print(f"调试：human review触发检查 (默认必需模式):")
        print(f"  - has_execution_success: {has_execution_success}")
        print(f"  - has_execution_result: {has_execution_result}")
        print(f"  - has_generated_sql: {has_generated_sql}")
        print(f"  - has_explanation: {has_explanation}")
        print(f"  - has_human_review: {has_human_review}")
        print(f"  - execution_result keys: {list(execution_result.keys())}")

        # 更宽松的策略：任何有执行成功标志或有SQL生成的，且还没有human review，就触发
        # 这确保几乎所有成功的查询都会触发human review
        should_trigger = (
            (has_execution_success or has_execution_result or has_generated_sql)
            and not has_human_review
        )

        print(f"  - 最终决定：should_trigger_human_review = {should_trigger}")
        return should_trigger

    def extract_review_data(self, state: Dict) -> Dict:
        """
        从状态中提取人工审查所需的数据
        """
        if not state:
            return {}

        execution_result = state.get("execution_result", {})
        data_sample = execution_result.get("results", [])[:10]  # 前10条记录

        # 推荐图表类型
        recommended_charts = ["table", "bar_chart"]
        if len(data_sample) > 0:
            first_row = data_sample[0]
            numeric_cols = [k for k, v in first_row.items() if isinstance(v, (int, float))]
            if numeric_cols:
                recommended_charts.append("line_chart")

        return {
            "user_question": state.get("user_question", ""),
            "explanation": state.get("explanation_markdown", "No explanation available."),
            "validation_reasoning": state.get("validation_reasoning", ""),
            "data_summary": {
                "total_rows": len(execution_result.get("results", [])),
                "has_data": len(data_sample) > 0,
                "execution_success": execution_result.get("success", False)
            },
            "data_sample": data_sample,
            "recommended_charts": recommended_charts,
            "available_charts": ["table", "bar_chart", "line_chart", "pie_chart", "scatter_plot"]
        }

    def resume_workflow_with_human_input(self, thread_id: str, human_response: Dict) -> List[Dict[str, Any]]:
        """
        使用人类输入恢复工作流
        优先使用直接恢复方式，因为状态保存在共享checkpointer中
        """
        print(f"开始恢复工作流 {thread_id}")

        # 直接尝试恢复，因为状态保存在共享checkpointer中
        try:
            return self.try_direct_resume(thread_id, human_response)
        except Exception as e:
            print(f"直接恢复失败，尝试备用方案: {e}")

            # 备用方案：从pending_workflows恢复
            if thread_id not in self.pending_workflows:
                return [{
                    "type": "error",
                    "content": f"无法找到工作流状态: {thread_id}",
                    "step": "resume"
                }]

            try:
                # 获取存储的工作流信息
                workflow_info = self.pending_workflows[thread_id]
                config = workflow_info["config"]

                # 使用人类输入更新状态
                state_update = self.prepare_human_response_update(human_response)

                # 恢复工作流执行
                print(f"恢复工作流，使用状态更新: {state_update}")
                final_state = self.compiled_graph.invoke(state_update, config=config)

                # 清理存储的工作流状态
                del self.pending_workflows[thread_id]

                # 处理最终状态
                result = self.process_final_state(final_state)
                return [result]

            except Exception as e2:
                return [{
                    "type": "error",
                    "content": f"恢复工作流失败: {str(e2)}",
                    "step": "resume",
                    "error_details": str(e2)
                }]

    def try_direct_resume(self, thread_id: str, human_response: Dict) -> List[Dict[str, Any]]:
        """
        尝试直接恢复工作流（使用共享checkpointer中的状态）
        """
        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 50
        }

        try:
            # 检查当前状态
            current_state = self.compiled_graph.get_state(config)
            if not current_state:
                return [{
                    "type": "error",
                    "content": "无法获取工作流状态",
                    "step": "resume"
                }]

            print(f"当前工作流状态: next={current_state.next}")

            # 如果工作流不在等待状态，返回错误
            if not current_state.next:
                return [{
                    "type": "error",
                    "content": "工作流未处于等待状态",
                    "step": "resume"
                }]

            # 准备人类响应更新
            state_update = self.prepare_human_response_update(human_response)
            print(f"准备的状态更新: {state_update}")

            # 使用update_state方法更新状态
            self.compiled_graph.update_state(config, state_update)

            # 继续执行工作流
            final_state = None
            for event in self.compiled_graph.stream(None, config=config):
                if isinstance(event, dict) and len(event) > 0:
                    node_name = list(event.keys())[0]
                    final_state = event[node_name]
                    print(f"恢复执行节点: {node_name}")

            if final_state:
                # 处理最终状态
                result = self.process_final_state(final_state)
                return [result]
            else:
                return [{
                    "type": "error",
                    "content": "恢复后工作流未产生最终状态",
                    "step": "resume"
                }]

        except Exception as e:
            return [{
                "type": "error",
                "content": f"直接恢复失败: {str(e)}",
                "step": "resume",
                "error_details": str(e)
            }]

    def prepare_human_response_update(self, human_response: Dict) -> Dict:
        """
        准备人类响应的状态更新
        """
        decision = human_response.get("decision", "approve")
        chart_selection = human_response.get("chart_selection", "table")
        preferences = human_response.get("preferences", {})
        modifications = human_response.get("modifications", [])

        # 验证和设置默认偏好
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
            "user_chart_selection": chart_selection,
            "user_preferences": preferences,
            "review_decision": decision,
            "modification_requests": modifications
        }

    def is_workflow_pending_review(self, thread_id: str) -> bool:
        """
        检查工作流是否正在等待人工审查
        """
        return thread_id in self.pending_workflows

    def get_pending_review_data(self, thread_id: str) -> Dict:
        """
        获取等待审查的数据
        """
        if thread_id in self.pending_workflows:
            workflow_info = self.pending_workflows[thread_id]
            state = workflow_info["state"]
            return self.extract_review_data(state)
        return {}

class StreamlitWorkflowRunner:
    """Streamlit环境下的工作流运行器"""

    def __init__(self):
        self.integration = LangGraphIntegration()

    def run_query_workflow(self, question: str, session_id: str = None) -> Dict[str, Any]:
        """在Streamlit中运行查询工作流"""

        # 更新工作流状态
        st.session_state.workflow_status = "running"
        st.session_state.current_step = 0

        try:
            # 运行同步工作流
            results = self.integration.process_query_sync(question, session_id)

            # 更新完成状态
            st.session_state.workflow_status = "completed"

            # 检查是否有human_review_required的结果
            if results:
                # 优先查找human_review_required类型的结果
                for result in results:
                    if result.get('type') == 'human_review_required':
                        print(f"调试：找到human_review_required结果")
                        return result

                # 如果没有human_review_required，返回最后一个结果
                final_result = results[-1]
                print(f"调试：没有找到human_review_required，返回最终结果类型: {final_result.get('type')}")

                # 更新session state
                if final_result.get('data'):
                    data = final_result['data']
                    st.session_state.generated_sql = data.get('sql_query', '')
                    st.session_state.query_results = data.get('query_results')
                    st.session_state.visualization_config = data.get('visualization_config', {})

                return final_result

            return {"type": "error", "content": "未收到工作流结果"}

        except Exception as e:
            st.session_state.workflow_status = "error"
            st.error(f"工作流执行失败: {str(e)}")
            return {
                "type": "error",
                "content": f"工作流执行失败: {str(e)}",
                "error_details": str(e)
            }

def get_workflow_runner() -> StreamlitWorkflowRunner:
    """获取工作流运行器实例"""
    if "workflow_runner" not in st.session_state:
        st.session_state.workflow_runner = StreamlitWorkflowRunner()

    return st.session_state.workflow_runner

def test_langgraph_connection() -> bool:
    """测试LangGraph连接"""
    runner = get_workflow_runner()
    return runner.integration.validate_connection()

def process_user_query(query: str, session_id: str = None) -> Dict[str, Any]:
    """处理用户查询"""
    runner = get_workflow_runner()

    if not runner.integration.validate_connection():
        raise Exception("LangGraph工作流未正确初始化")

    # 运行工作流
    result = runner.run_query_workflow(query, session_id)

    # 更新session state
    st.session_state.current_query = query

    return result

def resume_workflow_with_review(thread_id: str, human_response: Dict) -> Dict[str, Any]:
    """使用人工审查结果恢复工作流"""
    runner = get_workflow_runner()

    if not runner.integration.validate_connection():
        raise Exception("LangGraph工作流未正确初始化")

    # 恢复工作流
    results = runner.integration.resume_workflow_with_human_input(thread_id, human_response)

    if results:
        return results[0]
    else:
        return {
            "type": "error",
            "content": "恢复工作流失败"
        }

def check_pending_review(thread_id: str) -> Dict[str, Any]:
    """检查是否有等待审查的工作流"""
    runner = get_workflow_runner()

    if runner.integration.is_workflow_pending_review(thread_id):
        review_data = runner.integration.get_pending_review_data(thread_id)
        return {
            "pending": True,
            "review_data": review_data
        }
    else:
        return {
            "pending": False
        }

def get_recent_queries() -> List[Dict]:
    """获取最近的查询历史"""
    chat_history = st.session_state.get("chat_history", [])
    return chat_history[-5:]  # 最近5次对话

def get_user_feedback() -> Dict:
    """获取用户反馈信息"""
    return st.session_state.get("user_feedback", {})