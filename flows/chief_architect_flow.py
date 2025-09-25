#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
首席查询架构师流程模块

升级的动态查询生成系统，支持多轮查询和智能优化
从简单的模板匹配升级为强大的查询架构师
"""

import os
import json
import re
from datetime import datetime
from typing import Dict, Any, List
import structlog

from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import HumanMessage, SystemMessage
from config.prompt_templates import CHIEF_ARCHITECT_PROMPT, DATABASE_SCHEMA_INFO, SAMPLE_DATA_INFO

logger = structlog.get_logger()


def safe_log(level: str, message: str, **kwargs):
    """安全的日志记录函数，处理BrokenPipe错误"""
    try:
        getattr(logger, level)(message, **kwargs)
    except BrokenPipeError:
        print(f"{level.upper()}: {message} {kwargs}")
    except Exception as e:
        print(f"LOG_ERROR: {message} {kwargs} (logger_error: {e})")


def collect_generation_context(state: Dict[str, Any]) -> dict:
    """收集查询生成所需的所有上下文信息"""

    context = {
        "user_question": state.get("user_question", ""),
        "confidence_score": state.get("confidence_score", 0.0),
        "matched_queries": state.get("matched_queries", []),
        "matched_question_ids": state.get("matched_question_ids", []),
        "semantic_analysis": state.get("semantic_analysis", {}),
        "improvement_suggestions": state.get("improvement_suggestions", []),
        "validation_reasoning": state.get("validation_reasoning", ""),
        "retry_count": state.get("retry_count", 0),
        "is_retry": state.get("retry_count", 0) > 0
    }

    # 获取最佳匹配查询作为参考
    if context["matched_queries"]:
        context["reference_query"] = context["matched_queries"][0]
    else:
        context["reference_query"] = None

    # 数据库Schema信息
    context["database_schema"] = DATABASE_SCHEMA_INFO

    # 示例数据
    context["sample_data"] = SAMPLE_DATA_INFO

    return context




def build_chief_architect_prompt(context: dict) -> str:
    """构建首席查询架构师的复杂Prompt"""

    user_question = context["user_question"]
    confidence_score = context["confidence_score"]
    reference_query = context.get("reference_query")
    improvement_suggestions = context.get("improvement_suggestions", [])
    validation_reasoning = context.get("validation_reasoning", "")
    is_retry = context.get("is_retry", False)

    # 构建参考查询部分
    reference_section = ""
    if reference_query:
        reference_section = f"""
## 参考查询
基于语义匹配找到的相关查询 (置信度: {confidence_score:.2f}):

**问题**: {reference_query.get('question', 'N/A')}

**查询示例**:
```sql
{reference_query.get('queries', [{}])[0].get('query', 'N/A') if reference_query.get('queries') else 'N/A'}
```
"""

    # 构建修正指令部分
    correction_section = ""
    if is_retry and (improvement_suggestions or validation_reasoning):
        correction_section = f"""
## 重要修正指令
这是一个重试请求，上次尝试失败了：

**失败原因**: {validation_reasoning}

**修正建议**:
{chr(10).join(['- ' + suggestion for suggestion in improvement_suggestions])}

请根据这些修正建议优化你的新查询。
"""

    return CHIEF_ARCHITECT_PROMPT.format(
        user_question=user_question,
        reference_section=reference_section,
        database_schema=context["database_schema"],
        sample_data=context["sample_data"],
        correction_section=correction_section
    )


def invoke_chief_architect_llm(prompt: str, context: dict) -> dict:
    """调用首席查询架构师LLM"""
    project_id = os.getenv("LLM__PROJECT_ID", "thrasio-dev-ai-agent")
    model_name = os.getenv("LLM__MODEL_NAME", "gemini-2.5-pro")
    temperature = float(os.getenv("LLM__TEMPERATURE", "0.2"))

    llm = ChatVertexAI(
        model_name=model_name,
        project=project_id,
        temperature=temperature,
        location="us-central1"
    )

    messages = [
        SystemMessage(content="你是一位世界顶级的BigQuery数据分析专家和查询架构师，擅长编写最优化的SQL查询和Python脚本。"),
        HumanMessage(content=prompt)
    ]

    response = llm.invoke(messages)

    return {"content": response.content}


def parse_generation_result(generation_result: dict) -> dict:
    """解析查询生成结果"""
    content = generation_result.get("content", "")

    try:
        # 清理响应内容
        content_clean = content.strip()
        if content_clean.startswith('```json'):
            content_clean = content_clean[7:]
        if content_clean.endswith('```'):
            content_clean = content_clean[:-3]
        content_clean = content_clean.strip()

        result = json.loads(content_clean)

        # 验证必需字段
        if "final_sql_python" not in result:
            result["final_sql_python"] = "# 解析失败，无法生成Python脚本"
        if "explanation" not in result:
            result["explanation"] = "查询生成解析失败"
        if "query_plan" not in result:
            result["query_plan"] = []

        return result

    except json.JSONDecodeError as e:
        safe_log("warning", f"查询生成结果JSON解析失败: {str(e)}")

        # 尝试提取JSON部分
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
                return result
            except json.JSONDecodeError:
                pass

        # 提供默认结构
        return {
            "explanation": f"解析失败: {str(e)}",
            "query_plan": [],
            "final_sql_python": "# 查询生成失败，请重试"
        }
    except Exception as e:
        safe_log("error", f"查询生成结果解析失败: {str(e)}")
        return {
            "explanation": f"解析错误: {str(e)}",
            "query_plan": [],
            "final_sql_python": "# 查询生成错误，请重试"
        }


def generate_python_script_with_plan(parsed_result: dict, context: dict, timestamp: str) -> str:
    """生成包含查询计划的Python脚本"""

    explanation = parsed_result.get("explanation", "")
    query_plan = parsed_result.get("query_plan", [])
    final_script = parsed_result.get("final_sql_python", "")
    user_question = context.get("user_question", "")

    header = f"""#!/usr/bin/env python3
# -*- coding: utf-8 -*-
\"\"\"
首席查询架构师生成的查询脚本
生成时间: {datetime.now().isoformat()}
用户问题: {user_question}

查询说明: {explanation}

查询计划:
{chr(10).join([f"步骤{step.get('step', i+1)}: {step.get('description', '')}" for i, step in enumerate(query_plan)])}
\"\"\"

"""

    return header + final_script


def save_generated_script(script_path: str, script_content: str):
    """保存生成的脚本文件"""
    # 确保目录存在
    os.makedirs(os.path.dirname(script_path), exist_ok=True)

    try:
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        safe_log("info", f"Script saved successfully: {script_path}")
    except Exception as e:
        safe_log("error", f"Failed to save script {script_path}: {str(e)}")
        raise


def generate_chief_architect_query(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    首席查询架构师主函数 - 动态生成最优查询

    Args:
        state: 工作流状态字典

    Returns:
        dict: 生成结果
        {
            "generated_script_path": str,
            "generated_sql": str,
            "query_plan": List[Dict],
            "generation_metadata": Dict
        }
    """
    try:
        safe_log("info", "Starting Chief Query Architect")

        # 收集所有必需的上下文信息
        context = collect_generation_context(state)

        # 构建高质量的复杂Prompt
        generation_prompt = build_chief_architect_prompt(context)

        # 调用强大的LLM生成查询
        generation_result = invoke_chief_architect_llm(generation_prompt, context)

        # 解析生成结果
        parsed_result = parse_generation_result(generation_result)

        # 创建时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 生成Python脚本文件
        script_content = generate_python_script_with_plan(parsed_result, context, timestamp)
        script_path = f"generated_queries/chief_architect_query_{timestamp}.py"

        # 保存脚本文件
        save_generated_script(script_path, script_content)

        safe_log("info", "Chief Query Architect completed successfully",
                 script_path=script_path,
                 plan_steps=len(parsed_result.get("query_plan", [])),
                 final_sql_length=len(parsed_result.get("final_sql_python", "")))

        return {
            "generated_script_path": script_path,
            "generated_sql": parsed_result.get("final_sql_python", ""),
            "query_plan": parsed_result.get("query_plan", []),
            "generation_metadata": {
                "approach": "chief_architect",
                "timestamp": timestamp,
                "plan_steps": len(parsed_result.get("query_plan", [])),
                "explanation": parsed_result.get("explanation", ""),
                "confidence_level": context.get("confidence_score", 0.0)
            }
        }

    except Exception as e:
        safe_log("error", f"Chief Query Architect failed: {str(e)}")
        return {
            "generated_script_path": "",
            "generated_sql": "# Chief Architect generation failed",
            "query_plan": [],
            "generation_metadata": {"error": str(e)}
        }