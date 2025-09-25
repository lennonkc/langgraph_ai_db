# Task 04: 完善优化

## 任务概述
优化Streamlit应用性能，完善Session State管理，增强错误处理机制，提升用户体验。

## 实施目标
- 实现高效的缓存策略
- 优化Session State管理
- 完善错误处理和恢复机制
- 提升应用响应速度
- 增强用户交互体验

## 技术实现

### 1. 缓存优化系统 (utils/cache_manager.py)

```python
"""
缓存管理模块
使用Streamlit最新的缓存功能优化性能
"""

import streamlit as st
import pandas as pd
import hashlib
import json
import time
from typing import Any, Dict, List, Optional, Callable
from functools import wraps
import logging

class CacheManager:
    """缓存管理器"""

    def __init__(self):
        self.setup_logging()

    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    @staticmethod
    @st.cache_data(ttl=3600, max_entries=100)  # 1小时缓存，最多100个条目
    def cache_query_results(sql_query: str, params: Dict = None) -> pd.DataFrame:
        """缓存查询结果"""
        try:
            # 这里将替换为实际的数据库查询
            # 现在返回模拟数据
            return pd.DataFrame({
                'id': range(1, 101),
                'value': range(100, 200),
                'category': ['A', 'B', 'C'] * 33 + ['A']
            })
        except Exception as e:
            st.error(f"查询缓存错误: {str(e)}")
            return pd.DataFrame()

    @staticmethod
    @st.cache_data(ttl=1800)  # 30分钟缓存
    def cache_chart_data(data_hash: str, chart_config: Dict) -> Dict:
        """缓存图表数据"""
        try:
            # 缓存图表配置和处理后的数据
            return {
                'config': chart_config,
                'processed_at': time.time(),
                'hash': data_hash
            }
        except Exception as e:
            st.error(f"图表缓存错误: {str(e)}")
            return {}

    @staticmethod
    @st.cache_resource  # 全局资源缓存
    def get_langgraph_connection():
        """缓存LangGraph连接"""
        try:
            # 这里将替换为实际的LangGraph连接
            from utils.langgraph_integration import LangGraphIntegration
            return LangGraphIntegration()
        except Exception as e:
            st.error(f"LangGraph连接缓存错误: {str(e)}")
            return None

    @staticmethod
    @st.cache_data(persist=True)  # 持久化缓存
    def cache_user_preferences(user_id: str) -> Dict:
        """缓存用户偏好设置"""
        try:
            # 从数据库或文件加载用户偏好
            default_preferences = {
                'theme': 'light',
                'language': 'zh',
                'chart_type': 'auto',
                'max_results': 1000,
                'auto_refresh': True
            }
            return default_preferences
        except Exception as e:
            st.error(f"用户偏好缓存错误: {str(e)}")
            return {}

    def generate_cache_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = str(args) + str(sorted(kwargs.items()))
        return hashlib.md5(key_data.encode()).hexdigest()

    def clear_cache_by_pattern(self, pattern: str):
        """按模式清理缓存"""
        try:
            # Streamlit 1.18+ 支持缓存清理
            st.cache_data.clear()
            st.toast(f"已清理缓存: {pattern}")
        except Exception as e:
            self.logger.error(f"缓存清理失败: {str(e)}")

    def get_cache_stats(self) -> Dict:
        """获取缓存统计信息"""
        try:
            # 实际实现需要根据Streamlit版本调整
            return {
                'cache_hits': 0,
                'cache_misses': 0,
                'cache_size': 0,
                'last_cleared': time.time()
            }
        except Exception as e:
            self.logger.error(f"获取缓存统计失败: {str(e)}")
            return {}

def smart_cache(func: Callable) -> Callable:
    """智能缓存装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 根据函数类型选择合适的缓存策略
        if 'query' in func.__name__.lower():
            return st.cache_data(ttl=3600)(func)(*args, **kwargs)
        elif 'chart' in func.__name__.lower():
            return st.cache_data(ttl=1800)(func)(*args, **kwargs)
        else:
            return st.cache_data(ttl=600)(func)(*args, **kwargs)
    return wrapper
```

### 2. 增强的Session State管理 (utils/enhanced_session_manager.py)

```python
"""
增强的Session State管理
提供更强大的状态管理功能
"""

import streamlit as st
import json
import time
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timedelta
import copy

class EnhancedSessionManager:
    """增强的Session State管理器"""

    def __init__(self):
        self.initialize_core_state()
        self.setup_state_persistence()

    def initialize_core_state(self):
        """初始化核心状态"""

        # 应用核心状态
        self.ensure_state('app_initialized', False)
        self.ensure_state('app_version', '1.0.0')
        self.ensure_state('session_start_time', time.time())

        # 用户状态
        self.ensure_state('user_id', 'anonymous')
        self.ensure_state('user_preferences', {})
        self.ensure_state('user_activity', [])

        # 聊天状态
        self.ensure_state('chat_messages', [])
        self.ensure_state('chat_context', {})
        self.ensure_state('active_conversation_id', None)

        # 工作流状态
        self.ensure_state('workflow_status', 'idle')
        self.ensure_state('workflow_results', [])
        self.ensure_state('workflow_errors', [])

        # 数据状态
        self.ensure_state('cached_queries', {})
        self.ensure_state('recent_datasets', [])
        self.ensure_state('chart_configurations', {})

    def ensure_state(self, key: str, default_value: Any):
        """确保状态键存在"""
        if key not in st.session_state:
            st.session_state[key] = default_value

    def get_state(self, key: str, default: Any = None) -> Any:
        """安全获取状态值"""
        return st.session_state.get(key, default)

    def set_state(self, key: str, value: Any, notify: bool = False):
        """设置状态值"""
        old_value = st.session_state.get(key)
        st.session_state[key] = value

        # 记录状态变更
        self.log_state_change(key, old_value, value)

        if notify:
            st.toast(f"状态已更新: {key}")

    def update_state(self, updates: Dict[str, Any], notify: bool = False):
        """批量更新状态"""
        for key, value in updates.items():
            self.set_state(key, value, notify=False)

        if notify:
            st.toast(f"已更新 {len(updates)} 个状态")

    def log_state_change(self, key: str, old_value: Any, new_value: Any):
        """记录状态变更日志"""
        change_log = {
            'timestamp': time.time(),
            'key': key,
            'old_value': str(old_value)[:100],  # 限制长度
            'new_value': str(new_value)[:100],
            'action': 'update'
        }

        # 添加到活动日志
        activity = self.get_state('user_activity', [])
        activity.append(change_log)

        # 保持日志在合理大小
        if len(activity) > 100:
            activity = activity[-100:]

        st.session_state['user_activity'] = activity

    def reset_state(self, keys: Optional[List[str]] = None, confirm: bool = True):
        """重置状态"""
        if confirm:
            if not st.button("⚠️ 确认重置状态"):
                return False

        if keys is None:
            # 重置所有状态
            for key in list(st.session_state.keys()):
                if not key.startswith('_'):  # 保留内部状态
                    del st.session_state[key]
            self.initialize_core_state()
        else:
            # 重置指定状态
            for key in keys:
                if key in st.session_state:
                    del st.session_state[key]

        st.toast("状态已重置")
        st.rerun()
        return True

    def setup_state_persistence(self):
        """设置状态持久化"""
        # 在真实环境中，这里可以集成数据库或文件存储
        pass

    def save_state_snapshot(self, name: str):
        """保存状态快照"""
        snapshot = {
            'name': name,
            'timestamp': time.time(),
            'state': copy.deepcopy(dict(st.session_state))
        }

        snapshots = self.get_state('state_snapshots', [])
        snapshots.append(snapshot)

        # 限制快照数量
        if len(snapshots) > 10:
            snapshots = snapshots[-10:]

        self.set_state('state_snapshots', snapshots)
        st.success(f"状态快照已保存: {name}")

    def load_state_snapshot(self, snapshot_name: str):
        """加载状态快照"""
        snapshots = self.get_state('state_snapshots', [])

        for snapshot in snapshots:
            if snapshot['name'] == snapshot_name:
                # 清理当前状态
                for key in list(st.session_state.keys()):
                    if not key.startswith('_'):
                        del st.session_state[key]

                # 加载快照状态
                for key, value in snapshot['state'].items():
                    if not key.startswith('_'):
                        st.session_state[key] = value

                st.success(f"状态快照已加载: {snapshot_name}")
                st.rerun()
                return True

        st.error(f"快照不存在: {snapshot_name}")
        return False

    def get_state_summary(self) -> Dict:
        """获取状态摘要"""
        total_keys = len(st.session_state)
        memory_usage = sum(len(str(v)) for v in st.session_state.values())

        return {
            'total_keys': total_keys,
            'memory_usage_bytes': memory_usage,
            'session_duration': time.time() - self.get_state('session_start_time', time.time()),
            'last_activity': max(
                activity.get('timestamp', 0)
                for activity in self.get_state('user_activity', [])
            ) if self.get_state('user_activity') else 0
        }

    def cleanup_expired_state(self, max_age_hours: int = 24):
        """清理过期状态"""
        current_time = time.time()
        cutoff_time = current_time - (max_age_hours * 3600)

        # 清理过期的缓存查询
        cached_queries = self.get_state('cached_queries', {})
        expired_keys = [
            key for key, data in cached_queries.items()
            if data.get('timestamp', 0) < cutoff_time
        ]

        for key in expired_keys:
            del cached_queries[key]

        if expired_keys:
            self.set_state('cached_queries', cached_queries)
            st.toast(f"已清理 {len(expired_keys)} 个过期缓存")

    def register_state_validator(self, key: str, validator: Callable):
        """注册状态验证器"""
        validators = self.get_state('state_validators', {})
        validators[key] = validator
        self.set_state('state_validators', validators)

    def validate_state(self, key: str, value: Any) -> bool:
        """验证状态值"""
        validators = self.get_state('state_validators', {})
        validator = validators.get(key)

        if validator:
            try:
                return validator(value)
            except Exception as e:
                st.error(f"状态验证失败 {key}: {str(e)}")
                return False

        return True  # 无验证器时默认通过

# 全局Session Manager实例
session_manager = EnhancedSessionManager()
```

### 3. 错误处理和恢复系统 (utils/error_handler.py)

```python
"""
错误处理和恢复系统
提供全面的错误处理、日志记录和自动恢复功能
"""

import streamlit as st
import traceback
import logging
import time
from typing import Any, Dict, List, Optional, Callable
from functools import wraps
from contextlib import contextmanager
import sys
from io import StringIO

class ErrorHandler:
    """错误处理器"""

    def __init__(self):
        self.setup_logging()
        self.initialize_error_state()

    def setup_logging(self):
        """设置日志系统"""
        # 创建logger
        self.logger = logging.getLogger('streamlit_app')
        self.logger.setLevel(logging.INFO)

        # 创建处理器
        if not self.logger.handlers:
            # 控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)

            # 格式器
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)

            self.logger.addHandler(console_handler)

    def initialize_error_state(self):
        """初始化错误状态"""
        if 'error_history' not in st.session_state:
            st.session_state.error_history = []

        if 'error_recovery_attempts' not in st.session_state:
            st.session_state.error_recovery_attempts = {}

        if 'error_notifications' not in st.session_state:
            st.session_state.error_notifications = True

    def handle_error(
        self,
        error: Exception,
        context: str = "应用执行",
        recovery_action: Optional[Callable] = None,
        user_friendly: bool = True
    ):
        """处理错误"""

        error_info = {
            'timestamp': time.time(),
            'context': context,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            'recovery_attempted': False
        }

        # 记录错误
        self.log_error(error_info)

        # 显示用户友好的错误信息
        if user_friendly:
            self.display_user_error(error_info)

        # 尝试自动恢复
        if recovery_action:
            try:
                recovery_action()
                error_info['recovery_attempted'] = True
                error_info['recovery_successful'] = True
                st.success("🔄 已自动恢复")
            except Exception as recovery_error:
                error_info['recovery_successful'] = False
                error_info['recovery_error'] = str(recovery_error)

        # 保存错误历史
        self.save_error_history(error_info)

    def log_error(self, error_info: Dict):
        """记录错误日志"""
        self.logger.error(
            f"错误发生在 {error_info['context']}: "
            f"{error_info['error_type']} - {error_info['error_message']}"
        )

        # 详细的调试信息
        self.logger.debug(f"完整错误信息: {error_info}")

    def display_user_error(self, error_info: Dict):
        """显示用户友好的错误信息"""

        error_type = error_info['error_type']
        context = error_info['context']

        # 根据错误类型提供友好提示
        if error_type == 'ConnectionError':
            st.error("""
            🌐 **网络连接错误**

            请检查：
            - 网络连接是否正常
            - 服务器是否可访问
            - 防火墙设置
            """)

        elif error_type == 'ValueError':
            st.error("""
            ⚠️ **数据值错误**

            可能的原因：
            - 输入数据格式不正确
            - 数据范围超出预期
            - 缺少必要的数据字段
            """)

        elif error_type == 'KeyError':
            st.error("""
            🔑 **数据字段错误**

            可能的原因：
            - 缺少必要的数据字段
            - 字段名称不匹配
            - 数据结构发生变化
            """)

        else:
            st.error(f"""
            ❌ **在 {context} 过程中发生错误**

            错误类型：{error_type}
            错误信息：{error_info['error_message']}
            """)

        # 提供解决建议
        self.show_error_suggestions(error_info)

    def show_error_suggestions(self, error_info: Dict):
        """显示错误解决建议"""

        with st.expander("🛠️ 解决建议"):
            st.markdown("""
            **常见解决方法：**

            1. 🔄 **刷新页面** - 重新加载应用
            2. 🧹 **清理缓存** - 清除浏览器缓存
            3. 📋 **检查输入** - 确认输入数据格式正确
            4. 🔗 **检查连接** - 确认网络和服务器连接
            5. 📞 **联系支持** - 如问题持续存在
            """)

            # 提供快速操作按钮
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("🔄 重新尝试"):
                    st.rerun()

            with col2:
                if st.button("🧹 清理缓存"):
                    st.cache_data.clear()
                    st.toast("缓存已清理")

            with col3:
                if st.button("📋 复制错误信息"):
                    error_text = f"""
                    错误时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(error_info['timestamp']))}
                    错误上下文: {error_info['context']}
                    错误类型: {error_info['error_type']}
                    错误信息: {error_info['error_message']}
                    """
                    st.code(error_text, language='text')

    def save_error_history(self, error_info: Dict):
        """保存错误历史"""
        st.session_state.error_history.append(error_info)

        # 限制历史记录大小
        if len(st.session_state.error_history) > 50:
            st.session_state.error_history = st.session_state.error_history[-50:]

    @contextmanager
    def error_boundary(self, context: str = "操作", recovery_action: Optional[Callable] = None):
        """错误边界上下文管理器"""
        try:
            yield
        except Exception as e:
            self.handle_error(e, context, recovery_action)

    def safe_execute(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        context: str = "函数执行",
        default_return=None
    ):
        """安全执行函数"""
        try:
            return func(*args, **(kwargs or {}))
        except Exception as e:
            self.handle_error(e, context)
            return default_return

    def render_error_dashboard(self):
        """渲染错误仪表板"""
        st.markdown("### 🚨 错误监控")

        error_history = st.session_state.get('error_history', [])

        if not error_history:
            st.success("✅ 当前会话无错误记录")
            return

        # 错误统计
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("总错误数", len(error_history))

        with col2:
            recent_errors = [
                e for e in error_history
                if time.time() - e['timestamp'] < 3600  # 最近1小时
            ]
            st.metric("最近1小时", len(recent_errors))

        with col3:
            error_types = {}
            for error in error_history:
                error_type = error['error_type']
                error_types[error_type] = error_types.get(error_type, 0) + 1

            most_common = max(error_types.items(), key=lambda x: x[1]) if error_types else ('无', 0)
            st.metric("最常见错误", most_common[0])

        # 错误详情
        st.markdown("#### 错误详情")

        for i, error in enumerate(reversed(error_history[-10:])):  # 显示最近10个错误
            with st.expander(
                f"错误 {len(error_history) - i}: {error['error_type']} - "
                f"{time.strftime('%H:%M:%S', time.localtime(error['timestamp']))}"
            ):
                st.write(f"**上下文**: {error['context']}")
                st.write(f"**错误信息**: {error['error_message']}")

                if error.get('recovery_attempted'):
                    if error.get('recovery_successful'):
                        st.success("✅ 自动恢复成功")
                    else:
                        st.error(f"❌ 自动恢复失败: {error.get('recovery_error', '未知')}")

                # 显示堆栈跟踪
                if st.checkbox(f"显示技术详情 {i}", key=f"show_trace_{i}"):
                    st.code(error['traceback'], language='python')

# 全局错误处理器实例
error_handler = ErrorHandler()

def safe_streamlit_function(context: str = "Streamlit操作"):
    """Streamlit函数安全装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_handler.handle_error(e, context)
                return None
        return wrapper
    return decorator
```

### 4. 性能监控组件 (utils/performance_monitor.py)

```python
"""
性能监控组件
监控应用性能指标并提供优化建议
"""

import streamlit as st
import time
import psutil
import sys
from typing import Dict, List, Any
from functools import wraps
from contextlib import contextmanager

class PerformanceMonitor:
    """性能监控器"""

    def __init__(self):
        self.initialize_metrics()

    def initialize_metrics(self):
        """初始化性能指标"""
        if 'performance_metrics' not in st.session_state:
            st.session_state.performance_metrics = {
                'page_loads': [],
                'function_calls': {},
                'memory_usage': [],
                'response_times': []
            }

    @contextmanager
    def measure_time(self, operation_name: str):
        """测量执行时间"""
        start_time = time.time()
        try:
            yield
        finally:
            end_time = time.time()
            duration = end_time - start_time
            self.record_timing(operation_name, duration)

    def record_timing(self, operation_name: str, duration: float):
        """记录时间测量"""
        timing_record = {
            'operation': operation_name,
            'duration': duration,
            'timestamp': time.time()
        }

        st.session_state.performance_metrics['response_times'].append(timing_record)

        # 限制记录数量
        if len(st.session_state.performance_metrics['response_times']) > 100:
            st.session_state.performance_metrics['response_times'] = \
                st.session_state.performance_metrics['response_times'][-100:]

    def monitor_memory_usage(self):
        """监控内存使用"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()

            memory_record = {
                'rss': memory_info.rss / 1024 / 1024,  # MB
                'vms': memory_info.vms / 1024 / 1024,  # MB
                'timestamp': time.time()
            }

            st.session_state.performance_metrics['memory_usage'].append(memory_record)

            # 限制记录数量
            if len(st.session_state.performance_metrics['memory_usage']) > 50:
                st.session_state.performance_metrics['memory_usage'] = \
                    st.session_state.performance_metrics['memory_usage'][-50:]

        except Exception as e:
            st.warning(f"内存监控错误: {str(e)}")

    def render_performance_dashboard(self):
        """渲染性能仪表板"""
        st.markdown("### ⚡ 性能监控")

        # 当前性能指标
        self.render_current_metrics()

        # 性能趋势
        self.render_performance_trends()

        # 性能建议
        self.render_performance_suggestions()

    def render_current_metrics(self):
        """渲染当前性能指标"""
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            # 内存使用
            try:
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                st.metric("内存使用", f"{memory_mb:.1f} MB")
            except:
                st.metric("内存使用", "N/A")

        with col2:
            # 平均响应时间
            response_times = st.session_state.performance_metrics['response_times']
            if response_times:
                avg_time = sum(r['duration'] for r in response_times[-10:]) / min(10, len(response_times))
                st.metric("平均响应时间", f"{avg_time:.2f}s")
            else:
                st.metric("平均响应时间", "N/A")

        with col3:
            # 会话时长
            session_start = st.session_state.get('session_start_time', time.time())
            session_duration = (time.time() - session_start) / 60  # 分钟
            st.metric("会话时长", f"{session_duration:.1f} min")

        with col4:
            # 缓存命中率
            cache_stats = self.get_cache_hit_rate()
            st.metric("缓存命中率", f"{cache_stats:.1%}")

    def get_cache_hit_rate(self) -> float:
        """获取缓存命中率"""
        # 这里需要根据实际的缓存实现来获取统计信息
        # 目前返回模拟数据
        return 0.85

    def render_performance_trends(self):
        """渲染性能趋势"""
        response_times = st.session_state.performance_metrics['response_times']

        if response_times:
            import pandas as pd
            import plotly.express as px

            # 准备数据
            df = pd.DataFrame(response_times)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')

            # 创建趋势图
            fig = px.line(
                df,
                x='timestamp',
                y='duration',
                title='响应时间趋势',
                labels={'duration': '响应时间 (秒)', 'timestamp': '时间'}
            )

            st.plotly_chart(fig, use_container_width=True)

    def render_performance_suggestions(self):
        """渲染性能建议"""
        st.markdown("#### 💡 性能优化建议")

        suggestions = self.generate_performance_suggestions()

        for suggestion in suggestions:
            st.info(suggestion)

    def generate_performance_suggestions(self) -> List[str]:
        """生成性能建议"""
        suggestions = []

        # 分析响应时间
        response_times = st.session_state.performance_metrics['response_times']
        if response_times:
            recent_times = [r['duration'] for r in response_times[-10:]]
            avg_time = sum(recent_times) / len(recent_times)

            if avg_time > 3.0:
                suggestions.append("⚠️ 响应时间较长，考虑优化数据查询或增加缓存")

            if max(recent_times) > 10.0:
                suggestions.append("🐌 检测到慢查询，建议优化SQL或增加索引")

        # 分析内存使用
        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024

            if memory_mb > 500:
                suggestions.append("💾 内存使用较高，考虑清理缓存或优化数据结构")

        except:
            pass

        # 分析会话时长
        session_start = st.session_state.get('session_start_time', time.time())
        session_hours = (time.time() - session_start) / 3600

        if session_hours > 2:
            suggestions.append("⏰ 长时间会话，建议重启应用以释放资源")

        # 默认建议
        if not suggestions:
            suggestions.append("✅ 当前性能表现良好")

        return suggestions

def performance_tracker(operation_name: str):
    """性能跟踪装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            monitor = PerformanceMonitor()
            with monitor.measure_time(operation_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator

# 全局性能监控器实例
performance_monitor = PerformanceMonitor()
```

### 5. 设置页面 (pages/3_🔧_Settings.py)

```python
"""
设置页面
提供应用配置、性能监控和错误管理功能
"""

import streamlit as st
from utils.enhanced_session_manager import session_manager
from utils.error_handler import error_handler
from utils.performance_monitor import performance_monitor
from utils.cache_manager import CacheManager

# 页面配置
st.set_page_config(
    page_title="系统设置",
    page_icon="🔧",
    layout="wide"
)

def main():
    """设置页面主逻辑"""

    st.title("🔧 系统设置")

    # 创建选项卡
    tab1, tab2, tab3, tab4 = st.tabs([
        "⚙️ 应用设置",
        "⚡ 性能监控",
        "🚨 错误管理",
        "🗃️ 数据管理"
    ])

    with tab1:
        render_app_settings()

    with tab2:
        render_performance_settings()

    with tab3:
        render_error_management()

    with tab4:
        render_data_management()

def render_app_settings():
    """渲染应用设置"""

    st.markdown("### ⚙️ 应用配置")

    # 用户偏好设置
    st.markdown("#### 👤 用户偏好")

    col1, col2 = st.columns(2)

    with col1:
        # 主题设置
        current_theme = session_manager.get_state('user_preferences', {}).get('theme', 'light')
        theme = st.selectbox(
            "界面主题",
            options=['light', 'dark', 'auto'],
            index=['light', 'dark', 'auto'].index(current_theme),
            help="选择应用界面主题"
        )

        # 语言设置
        current_language = session_manager.get_state('user_preferences', {}).get('language', 'zh')
        language = st.selectbox(
            "界面语言",
            options=['zh', 'en'],
            index=['zh', 'en'].index(current_language),
            format_func=lambda x: '中文' if x == 'zh' else 'English'
        )

    with col2:
        # 图表默认类型
        current_chart = session_manager.get_state('user_preferences', {}).get('chart_type', 'auto')
        chart_type = st.selectbox(
            "默认图表类型",
            options=['auto', 'line', 'bar', 'scatter', 'pie'],
            index=['auto', 'line', 'bar', 'scatter', 'pie'].index(current_chart),
            help="新查询的默认图表类型"
        )

        # 最大结果数
        current_max = session_manager.get_state('user_preferences', {}).get('max_results', 1000)
        max_results = st.number_input(
            "最大结果数",
            min_value=100,
            max_value=10000,
            value=current_max,
            step=100,
            help="查询返回的最大记录数"
        )

    # 保存设置
    if st.button("💾 保存设置", type="primary"):
        preferences = {
            'theme': theme,
            'language': language,
            'chart_type': chart_type,
            'max_results': max_results
        }
        session_manager.set_state('user_preferences', preferences, notify=True)

    # 系统信息
    st.markdown("#### ℹ️ 系统信息")

    system_info = session_manager.get_state_summary()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("会话状态数", system_info['total_keys'])

    with col2:
        session_duration = system_info['session_duration'] / 60  # 转换为分钟
        st.metric("会话时长", f"{session_duration:.1f} 分钟")

    with col3:
        memory_usage = system_info['memory_usage_bytes'] / 1024  # 转换为KB
        st.metric("内存使用", f"{memory_usage:.1f} KB")

def render_performance_settings():
    """渲染性能设置"""

    st.markdown("### ⚡ 性能监控")

    # 渲染性能仪表板
    performance_monitor.render_performance_dashboard()

    # 缓存管理
    st.markdown("#### 🗃️ 缓存管理")

    cache_manager = CacheManager()
    cache_stats = cache_manager.get_cache_stats()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("缓存命中次数", cache_stats.get('cache_hits', 0))

    with col2:
        st.metric("缓存未命中", cache_stats.get('cache_misses', 0))

    with col3:
        st.metric("缓存大小", f"{cache_stats.get('cache_size', 0)} MB")

    # 缓存操作
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🧹 清理数据缓存"):
            st.cache_data.clear()
            st.success("数据缓存已清理")

    with col2:
        if st.button("🔄 清理资源缓存"):
            st.cache_resource.clear()
            st.success("资源缓存已清理")

def render_error_management():
    """渲染错误管理"""

    st.markdown("### 🚨 错误管理")

    # 渲染错误仪表板
    error_handler.render_error_dashboard()

    # 错误设置
    st.markdown("#### ⚙️ 错误处理设置")

    # 错误通知设置
    error_notifications = st.checkbox(
        "显示错误通知",
        value=st.session_state.get('error_notifications', True),
        help="是否显示错误提示消息"
    )

    st.session_state.error_notifications = error_notifications

    # 自动恢复设置
    auto_recovery = st.checkbox(
        "启用自动恢复",
        value=st.session_state.get('auto_recovery', True),
        help="发生错误时尝试自动恢复"
    )

    st.session_state.auto_recovery = auto_recovery

    # 清理错误历史
    if st.button("🧹 清理错误历史"):
        st.session_state.error_history = []
        st.success("错误历史已清理")

def render_data_management():
    """渲染数据管理"""

    st.markdown("### 🗃️ 数据管理")

    # 会话状态管理
    st.markdown("#### 💾 会话状态")

    # 状态快照
    st.markdown("##### 📸 状态快照")

    snapshot_name = st.text_input("快照名称", placeholder="输入快照名称")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📸 创建快照") and snapshot_name:
            session_manager.save_state_snapshot(snapshot_name)

    with col2:
        # 显示现有快照
        snapshots = session_manager.get_state('state_snapshots', [])
        if snapshots:
            selected_snapshot = st.selectbox(
                "选择快照",
                options=[s['name'] for s in snapshots],
                format_func=lambda x: f"{x} ({time.strftime('%Y-%m-%d %H:%M', time.localtime([s for s in snapshots if s['name'] == x][0]['timestamp']))})"
            )

            if st.button("📥 加载快照"):
                session_manager.load_state_snapshot(selected_snapshot)

    # 数据导出
    st.markdown("##### 📤 数据导出")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📊 导出聊天历史"):
            chat_history = session_manager.get_state('chat_messages', [])
            if chat_history:
                import json
                export_data = json.dumps(chat_history, ensure_ascii=False, indent=2)
                st.download_button(
                    "💾 下载聊天历史",
                    data=export_data,
                    file_name=f"chat_history_{int(time.time())}.json",
                    mime="application/json"
                )
            else:
                st.info("暂无聊天历史")

    with col2:
        if st.button("📈 导出性能数据"):
            performance_data = session_manager.get_state('performance_metrics', {})
            if performance_data:
                import json
                export_data = json.dumps(performance_data, ensure_ascii=False, indent=2)
                st.download_button(
                    "💾 下载性能数据",
                    data=export_data,
                    file_name=f"performance_data_{int(time.time())}.json",
                    mime="application/json"
                )
            else:
                st.info("暂无性能数据")

    # 重置应用
    st.markdown("##### 🔄 重置应用")

    st.warning("⚠️ 重置操作将清除所有数据，请谨慎操作")

    reset_options = st.multiselect(
        "选择重置范围",
        options=['聊天历史', '性能数据', '错误历史', '用户设置', '缓存数据'],
        help="选择要重置的数据类型"
    )

    if st.button("🚨 执行重置", type="secondary"):
        if reset_options:
            reset_keys = []

            if '聊天历史' in reset_options:
                reset_keys.extend(['chat_messages', 'chat_context'])

            if '性能数据' in reset_options:
                reset_keys.append('performance_metrics')

            if '错误历史' in reset_options:
                reset_keys.append('error_history')

            if '用户设置' in reset_options:
                reset_keys.append('user_preferences')

            session_manager.reset_state(reset_keys, confirm=False)

            if '缓存数据' in reset_options:
                st.cache_data.clear()
                st.cache_resource.clear()

            st.success(f"已重置: {', '.join(reset_options)}")
        else:
            st.warning("请选择要重置的内容")

if __name__ == "__main__":
    main()
```

## 验收标准

### 功能验收
- [ ] 缓存系统提升响应速度
- [ ] Session State管理稳定可靠
- [ ] 错误处理和恢复机制完善
- [ ] 性能监控数据准确
- [ ] 设置页面功能完整

### 技术验收
- [ ] 使用Streamlit最新缓存API
- [ ] 内存使用控制在合理范围
- [ ] 错误日志记录完整
- [ ] 性能指标监控准确
- [ ] 代码质量符合标准

### 用户体验验收
- [ ] 应用响应速度 < 2秒
- [ ] 错误提示友好易懂
- [ ] 性能数据可视化清晰
- [ ] 设置操作简单直观
- [ ] 数据导出功能正常

## 后续任务
完成此任务后，进入**Task 05: 测试部署**阶段，进行全面测试和生产部署准备。