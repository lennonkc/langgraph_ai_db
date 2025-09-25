"""
Simple configuration module for LangGraph Order Analysis App
"""
import os
from typing import Optional


class LLMConfig:
    """LLM configuration"""
    def __init__(self):
        self.project_id = os.getenv("LLM__PROJECT_ID", "thrasio-dev-ai-agent")
        self.model_name = os.getenv("LLM__MODEL_NAME", "gemini-2.5-pro")
        self.temperature = float(os.getenv("LLM__TEMPERATURE", "0.1"))
        # No max_output_tokens limit - use model's full capacity
        self.max_token_limit = int(os.getenv("MAX_TOKEN_LIMIT", "2000000"))  # Very large limit


class GoogleCloudConfig:
    """Google Cloud configuration"""
    def __init__(self):
        self.project = os.getenv("GOOGLE_CLOUD_PROJECT", "thrasio-dev-ai-agent")
        self.project_id = self.project  # Add project_id alias for compatibility
        self.bigquery_project_id = os.getenv("GOOGLE_CLOUD__BIGQUERY_PROJECT_ID")


class Settings:
    """Application settings"""

    def __init__(self):
        # Nested configurations
        self.llm = LLMConfig()
        self.google_cloud = GoogleCloudConfig()

        # Direct properties for backward compatibility
        self.google_cloud_project = self.google_cloud.project
        self.bigquery_project_id = self.google_cloud.bigquery_project_id

        # LangSmith Configuration
        self.langchain_api_key = os.getenv("LANGCHAIN_API_KEY")
        self.langchain_project = os.getenv("LANGCHAIN_PROJECT", "thrasio iq fullstack")
        self.langchain_tracing_v2 = os.getenv("LANGCHAIN_TRACING_V2", "true").lower() == "true"


def get_settings() -> Settings:
    """Get application settings"""
    return Settings()