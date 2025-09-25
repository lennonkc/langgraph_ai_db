# Enhanced Debugging Support for LangSmith Integration
import os
import time
from datetime import datetime
from typing import Dict, Any, List
from config.langsmith_config import langsmith_config

class DebugSupport:
    """调试支持工具"""

    def __init__(self):
        self.debug_sessions = {}

    def start_debug_session(self, session_id: str, debug_level: str = "INFO"):
        """开始调试会话"""

        self.debug_sessions[session_id] = {
            "start_time": datetime.now(),
            "debug_level": debug_level,
            "events": [],
            "state_snapshots": [],
            "llm_interactions": []
        }

        # Configure enhanced logging for this session
        os.environ[f"DEBUG_SESSION_{session_id}"] = debug_level

    def log_debug_event(self, session_id: str, event_type: str, details: Dict[str, Any]):
        """记录调试事件"""

        if session_id in self.debug_sessions:
            event = {
                "timestamp": datetime.now().isoformat(),
                "type": event_type,
                "details": details
            }

            self.debug_sessions[session_id]["events"].append(event)

            # Also log to LangSmith for correlation
            try:
                langsmith_config.client.create_run(
                    name=f"debug_event_{event_type}",
                    run_type="tool",
                    inputs={"session_id": session_id, "event_type": event_type},
                    outputs=details,
                    project_name="ai-database-analyst"
                )
            except Exception as e:
                # Silently ignore LangSmith logging failures to avoid pipe errors
                pass

    def capture_state_snapshot(self, session_id: str, step_name: str, state: Dict[str, Any]):
        """捕获状态快照"""

        if session_id in self.debug_sessions:
            # Sanitize state for logging (remove sensitive data)
            sanitized_state = self.sanitize_state_for_logging(state)

            snapshot = {
                "timestamp": datetime.now().isoformat(),
                "step": step_name,
                "state": sanitized_state
            }

            self.debug_sessions[session_id]["state_snapshots"].append(snapshot)

    def generate_debug_report(self, session_id: str) -> Dict[str, Any]:
        """生成调试报告"""

        if session_id not in self.debug_sessions:
            return {"error": "Debug session not found"}

        session_data = self.debug_sessions[session_id]

        report = {
            "session_id": session_id,
            "debug_level": session_data["debug_level"],
            "session_duration": (datetime.now() - session_data["start_time"]).total_seconds(),
            "total_events": len(session_data["events"]),
            "state_snapshots_count": len(session_data["state_snapshots"]),
            "llm_interactions_count": len(session_data["llm_interactions"]),
            "events_timeline": session_data["events"],
            "final_state": session_data["state_snapshots"][-1] if session_data["state_snapshots"] else None,
            "error_summary": self.extract_error_summary(session_data["events"])
        }

        return report

    def sanitize_state_for_logging(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """清理状态数据用于日志记录"""

        # Remove or mask sensitive information
        sanitized = {}

        for key, value in state.items():
            if "api_key" in key.lower() or "secret" in key.lower():
                sanitized[key] = "***MASKED***"
            elif isinstance(value, str) and len(value) > 1000:
                sanitized[key] = value[:1000] + "...TRUNCATED"
            else:
                sanitized[key] = value

        return sanitized

    def extract_error_summary(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """提取错误摘要"""

        error_events = [e for e in events if e["type"] == "error"]

        if not error_events:
            return {"total_errors": 0}

        error_types = {}
        for event in error_events:
            error_type = event.get("details", {}).get("error_type", "unknown")
            error_types[error_type] = error_types.get(error_type, 0) + 1

        return {
            "total_errors": len(error_events),
            "error_types": error_types,
            "first_error": error_events[0],
            "last_error": error_events[-1]
        }

    def log_performance_issue(self, session_id: str, issue_type: str, details: Dict[str, Any]):
        """记录性能问题"""

        performance_event = {
            "session_id": session_id,
            "issue_type": issue_type,
            "details": details,
            "timestamp": datetime.now().isoformat(),
            "severity": self._assess_issue_severity(issue_type, details)
        }

        self.log_debug_event(session_id, "performance_issue", performance_event)

    def _assess_issue_severity(self, issue_type: str, details: Dict[str, Any]) -> str:
        """评估问题严重性"""

        severity_rules = {
            "slow_execution": lambda d: "critical" if d.get("execution_time", 0) > 300 else "warning",
            "high_cost": lambda d: "critical" if d.get("cost", 0) > 10 else "warning",
            "memory_usage": lambda d: "critical" if d.get("memory_mb", 0) > 2000 else "warning",
            "token_limit": lambda d: "critical" if d.get("tokens", 0) > 100000 else "warning"
        }

        rule = severity_rules.get(issue_type, lambda d: "info")
        return rule(details)

class LangSmithIntegrationMonitor:
    """LangSmith集成监控器"""

    def __init__(self):
        self.integration_status = {
            "client_connection": False,
            "project_access": False,
            "tracing_enabled": False,
            "last_check": None
        }

    def check_integration_health(self) -> Dict[str, Any]:
        """检查LangSmith集成健康状态"""

        health_report = {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "issues": []
        }

        try:
            # Test client connection
            client = langsmith_config.client

            # Try to create a test run
            test_run = client.create_run(
                name="health_check",
                run_type="tool",
                inputs={"test": "integration_health"},
                outputs={"status": "ok"},
                project_name="ai-database-analyst"
            )

            self.integration_status["client_connection"] = True
            self.integration_status["project_access"] = True

        except Exception as e:
            health_report["status"] = "degraded"
            health_report["issues"].append({
                "type": "connection_error",
                "message": str(e),
                "severity": "critical"
            })
            self.integration_status["client_connection"] = False

        # Check environment variables
        required_env_vars = [
            "LANGCHAIN_TRACING_V2",
            "LANGCHAIN_ENDPOINT",
            "LANGCHAIN_PROJECT",
            "LANGCHAIN_API_KEY"
        ]

        for var in required_env_vars:
            if not os.getenv(var):
                health_report["issues"].append({
                    "type": "missing_env_var",
                    "message": f"Missing environment variable: {var}",
                    "severity": "warning"
                })

        self.integration_status["last_check"] = datetime.now()

        return {
            "health_report": health_report,
            "integration_status": self.integration_status
        }

# Global debug support instance
debug_support = DebugSupport()
integration_monitor = LangSmithIntegrationMonitor()