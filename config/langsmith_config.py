# LangSmith Configuration Management
import os
from langsmith import Client

class LangSmithConfig:
    """LangSmith配置管理器"""

    def __init__(self):
        self.setup_environment()
        self.client = Client()

    def setup_environment(self):
        """设置LangSmith环境变量"""
        required_vars = {
            "LANGCHAIN_TRACING_V2": "true",
            "LANGCHAIN_ENDPOINT": "https://api.smith.langchain.com",
            "LANGCHAIN_PROJECT": "ai-database-analyst",
            "LANGCHAIN_API_KEY": os.getenv("LANGSMITH_API_KEY")
        }

        for var, value in required_vars.items():
            if var not in os.environ:
                if value:
                    os.environ[var] = value
                else:
                    raise ValueError(f"Missing required environment variable: {var}")

    def create_project_if_not_exists(self, project_name: str):
        """创建项目（如果不存在）"""
        try:
            self.client.create_project(project_name=project_name)
        except Exception:
            # Project might already exist
            pass

    def setup_session_tracking(self, session_id: str):
        """设置会话级别跟踪"""
        os.environ["LANGCHAIN_SESSION"] = session_id
        return session_id

# Initialize global config
langsmith_config = LangSmithConfig()