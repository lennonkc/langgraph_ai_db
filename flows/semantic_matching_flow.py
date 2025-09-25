#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语义匹配流程模块

从机械化的问题分类+实体提取升级为智能的语义匹配系统
直接将用户问题与预定义的问题-查询对进行语义匹配
"""

import json
import re
import os
from typing import List, Dict, Any
import structlog

from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import HumanMessage, SystemMessage
from config.prompt_templates import SEMANTIC_MATCHING_PROMPT

logger = structlog.get_logger()


def safe_log(level: str, message: str, **kwargs):
    """安全的日志记录函数，处理BrokenPipe错误"""
    try:
        getattr(logger, level)(message, **kwargs)
    except BrokenPipeError:
        print(f"{level.upper()}: {message} {kwargs}")
    except Exception as e:
        print(f"LOG_ERROR: {message} {kwargs} (logger_error: {e})")


def load_questions_and_queries():
    """加载预定义的问题-查询对"""
    try:
        questions_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'questions_and_queries.json'
        )
        with open(questions_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        safe_log("error", f"Failed to load questions_and_queries.json: {str(e)}")
        return []


def build_semantic_matching_prompt(user_question: str, predefined_questions: list) -> str:
    """构建语义匹配Prompt"""

    questions_list = "\n".join([
        f"{q['id']}. {q['question']}"
        for q in predefined_questions
    ])

    return SEMANTIC_MATCHING_PROMPT.format(
        user_question=user_question,
        questions_list=questions_list
    )


def get_llm_for_semantic_matching():
    """获取用于语义匹配的LLM实例"""
    project_id = os.getenv("LLM__PROJECT_ID", "thrasio-dev-ai-agent")
    model_name = os.getenv("LLM__MODEL_NAME", "gemini-2.5-pro")
    temperature = float(os.getenv("LLM__TEMPERATURE", "0.2"))

    return ChatVertexAI(
        model_name=model_name,
        project=project_id,
        temperature=temperature,
        location="us-central1"
    )


def parse_semantic_match_response(response_content: str) -> dict:
    """解析语义匹配LLM响应"""
    try:
        # 清理响应内容，移除可能的markdown代码块标记
        content = response_content.strip()
        if content.startswith('```json'):
            content = content[7:]
        if content.endswith('```'):
            content = content[:-3]
        content = content.strip()

        result = json.loads(content)

        # 验证必需字段
        if "match_found" not in result:
            result["match_found"] = False
        if "confidence" not in result:
            result["confidence"] = 0.0
        if "matched_ids" not in result:
            result["matched_ids"] = []
        if "reasoning" not in result:
            result["reasoning"] = "无法解析匹配推理"

        return result

    except json.JSONDecodeError as e:
        safe_log("warning", f"JSON解析失败，尝试修复: {str(e)}")

        # 尝试提取JSON部分
        json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
                return result
            except json.JSONDecodeError:
                pass

        # 提供默认结构
        return {
            "match_found": False,
            "matched_ids": [],
            "confidence": 0.0,
            "reasoning": f"JSON解析失败: {str(e)}",
            "alternatives": []
        }
    except Exception as e:
        safe_log("error", f"语义匹配响应解析失败: {str(e)}")
        return {
            "match_found": False,
            "matched_ids": [],
            "confidence": 0.0,
            "reasoning": f"解析错误: {str(e)}",
            "alternatives": []
        }


def find_query_by_id(questions_and_queries: list, question_id: int) -> dict:
    """根据ID查找查询对象"""
    for item in questions_and_queries:
        if item.get("id") == question_id:
            return item
    return None


def perform_semantic_matching(user_question: str) -> Dict[str, Any]:
    """
    执行语义匹配的主函数

    Args:
        user_question: 用户输入的问题

    Returns:
        dict: 包含匹配结果的字典
        {
            "confidence_score": float,
            "matched_queries": List[Dict],
            "matched_question_ids": List[int],
            "semantic_analysis": Dict
        }
    """
    try:
        safe_log("info", "Starting semantic question matching", question=user_question)

        # 加载预定义的问题-查询对
        questions_and_queries = load_questions_and_queries()

        # 提取所有问题用于匹配
        predefined_questions = [
            {"id": item["id"], "question": item["question"]}
            for item in questions_and_queries
        ]

        # 构建语义匹配Prompt
        semantic_matching_prompt = build_semantic_matching_prompt(
            user_question,
            predefined_questions
        )

        # 调用LLM进行语义匹配
        llm = get_llm_for_semantic_matching()

        messages = [
            SystemMessage(content="You are a semantic matching expert, skilled at understanding the intent behind users’ questions and finding the most similar predefined question."),
            HumanMessage(content=semantic_matching_prompt)
        ]

        response = llm.invoke(messages)

        # 解析LLM响应
        match_result = parse_semantic_match_response(response.content)

        # 根据匹配结果获取对应的查询
        matched_queries = []
        matched_question_ids = []

        if match_result.get("match_found", False):
            matched_ids = match_result.get("matched_ids", [])
            for question_id in matched_ids:
                query_item = find_query_by_id(questions_and_queries, question_id)
                if query_item:
                    matched_queries.append(query_item)
                    matched_question_ids.append(question_id)

        confidence_score = match_result.get("confidence", 0.0)

        safe_log("info", "Semantic matching completed",
                 confidence=confidence_score,
                 matched_count=len(matched_queries))

        return {
            "confidence_score": confidence_score,
            "matched_queries": matched_queries,
            "matched_question_ids": matched_question_ids,
            "semantic_analysis": {
                "match_found": match_result.get("match_found", False),
                "reasoning": match_result.get("reasoning", ""),
                "alternatives": match_result.get("alternatives", [])
            }
        }

    except Exception as e:
        safe_log("error", f"Semantic matching failed: {str(e)}")
        return {
            "confidence_score": 0.0,
            "matched_queries": [],
            "matched_question_ids": [],
            "semantic_analysis": {
                "match_found": False,
                "reasoning": f"语义匹配失败: {str(e)}",
                "alternatives": []
            }
        }