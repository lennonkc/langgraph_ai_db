# Configuration package for AI Database Analyst
from .langsmith_config import LangSmithConfig, langsmith_config

def get_settings():
    """Get application settings - re-export from root config"""
    import sys
    import os

    # Add parent directory to path temporarily
    parent_dir = os.path.dirname(os.path.dirname(__file__))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    try:
        import config as root_config
        return root_config.get_settings()
    except ImportError:
        # Fallback if root config is not available
        from .langsmith_config import LangSmithConfig
        return LangSmithConfig()

__all__ = ['LangSmithConfig', 'langsmith_config', 'get_settings']