# Performance Monitoring and Alerting
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List
from config.langsmith_config import langsmith_config

class PerformanceMonitor:
    """性能监控器"""

    def __init__(self):
        self.metrics_buffer = []
        self.alert_thresholds = {
            "execution_time_seconds": 300,  # 5 minutes
            "cost_per_query": 5.0,  # $5
            "error_rate": 0.1,  # 10%
            "token_usage": 100000  # 100k tokens
        }

    def track_execution_metrics(self, session_id: str, metrics: Dict[str, Any]):
        """跟踪执行指标"""

        enhanced_metrics = {
            **metrics,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "environment": os.getenv("ENVIRONMENT", "production")
        }

        self.metrics_buffer.append(enhanced_metrics)

        # Check for alert conditions
        self.check_alert_conditions(enhanced_metrics)

        # Flush metrics to LangSmith periodically
        if len(self.metrics_buffer) >= 10:
            self.flush_metrics_to_langsmith()

    def check_alert_conditions(self, metrics: Dict[str, Any]):
        """检查警报条件"""

        alerts = []

        for metric_name, threshold in self.alert_thresholds.items():
            if metric_name in metrics:
                value = metrics[metric_name]

                if isinstance(value, (int, float)) and value > threshold:
                    alerts.append({
                        "metric": metric_name,
                        "value": value,
                        "threshold": threshold,
                        "severity": "warning" if value < threshold * 1.5 else "critical"
                    })

        if alerts:
            self.send_alerts(metrics["session_id"], alerts)

    def flush_metrics_to_langsmith(self):
        """将指标刷新到LangSmith"""

        try:
            for metric in self.metrics_buffer:
                langsmith_config.client.create_run(
                    name="performance_metric",
                    run_type="tool",
                    inputs={"metric_type": "performance"},
                    outputs=metric,
                    project_name="ai-database-analyst"
                )

            self.metrics_buffer.clear()

        except Exception as e:
            print(f"Failed to flush metrics to LangSmith: {e}")

    def send_alerts(self, session_id: str, alerts: List[Dict]):
        """发送警报"""

        alert_payload = {
            "session_id": session_id,
            "alert_count": len(alerts),
            "alerts": alerts,
            "timestamp": datetime.now().isoformat()
        }

        # Log alert to LangSmith
        langsmith_config.client.create_run(
            name="performance_alert",
            run_type="tool",
            inputs={"alert_type": "performance"},
            outputs=alert_payload,
            project_name="ai-database-analyst"
        )

    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """获取性能摘要"""

        # Filter recent metrics
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [
            m for m in self.metrics_buffer
            if datetime.fromisoformat(m["timestamp"]) > cutoff_time
        ]

        if not recent_metrics:
            return {"message": "No recent metrics available"}

        # Calculate summary statistics
        execution_times = [m.get("execution_time_seconds", 0) for m in recent_metrics]
        costs = [m.get("cost_per_query", 0) for m in recent_metrics]

        return {
            "period_hours": hours,
            "total_executions": len(recent_metrics),
            "avg_execution_time": sum(execution_times) / len(execution_times) if execution_times else 0,
            "max_execution_time": max(execution_times) if execution_times else 0,
            "avg_cost_per_query": sum(costs) / len(costs) if costs else 0,
            "total_cost": sum(costs),
            "success_rate": len([m for m in recent_metrics if m.get("success", False)]) / len(recent_metrics)
        }

class CostTracker:
    """成本跟踪器"""

    def __init__(self):
        self.daily_costs = {}
        self.cost_breakdown = {
            "llm_calls": 0.0,
            "bigquery_processing": 0.0,
            "total": 0.0
        }

    def track_llm_cost(self, operation: str, model: str, tokens: int, cost: float):
        """跟踪LLM成本"""

        today = datetime.now().strftime("%Y-%m-%d")

        if today not in self.daily_costs:
            self.daily_costs[today] = {"llm": 0.0, "bigquery": 0.0}

        self.daily_costs[today]["llm"] += cost
        self.cost_breakdown["llm_calls"] += cost
        self.cost_breakdown["total"] += cost

        # Log to LangSmith
        cost_record = {
            "operation": operation,
            "model": model,
            "tokens": tokens,
            "cost": cost,
            "date": today,
            "cumulative_daily_llm_cost": self.daily_costs[today]["llm"]
        }

        langsmith_config.client.create_run(
            name="llm_cost_tracking",
            run_type="tool",
            inputs={"cost_type": "llm"},
            outputs=cost_record,
            project_name="ai-database-analyst"
        )

    def track_bigquery_cost(self, query_id: str, bytes_processed: int, cost: float):
        """跟踪BigQuery成本"""

        today = datetime.now().strftime("%Y-%m-%d")

        if today not in self.daily_costs:
            self.daily_costs[today] = {"llm": 0.0, "bigquery": 0.0}

        self.daily_costs[today]["bigquery"] += cost
        self.cost_breakdown["bigquery_processing"] += cost
        self.cost_breakdown["total"] += cost

        # Log to LangSmith
        cost_record = {
            "query_id": query_id,
            "bytes_processed": bytes_processed,
            "cost": cost,
            "date": today,
            "cumulative_daily_bigquery_cost": self.daily_costs[today]["bigquery"]
        }

        langsmith_config.client.create_run(
            name="bigquery_cost_tracking",
            run_type="tool",
            inputs={"cost_type": "bigquery"},
            outputs=cost_record,
            project_name="ai-database-analyst"
        )

    def get_cost_summary(self, days: int = 7) -> Dict[str, Any]:
        """获取成本摘要"""

        recent_dates = [
            (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(days)
        ]

        recent_costs = {
            date: self.daily_costs.get(date, {"llm": 0.0, "bigquery": 0.0})
            for date in recent_dates
        }

        return {
            "period_days": days,
            "daily_breakdown": recent_costs,
            "total_period_cost": sum(
                day["llm"] + day["bigquery"]
                for day in recent_costs.values()
            ),
            "average_daily_cost": sum(
                day["llm"] + day["bigquery"]
                for day in recent_costs.values()
            ) / days,
            "cost_breakdown": self.cost_breakdown
        }

# Global instances
performance_monitor = PerformanceMonitor()
cost_tracker = CostTracker()