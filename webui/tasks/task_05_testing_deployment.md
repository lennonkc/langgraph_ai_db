# Task 05: 测试部署

## 任务概述
完成应用的全面测试、性能优化验证和生产环境部署准备，确保系统稳定可靠运行。

## 实施目标
- 实现完整的测试覆盖
- 验证生产环境兼容性
- 建立CI/CD流程
- 配置监控和日志系统
- 准备部署文档

## 技术实现

### 1. 测试框架搭建 (tests/test_framework.py)

```python
"""
Streamlit应用测试框架
使用Streamlit官方测试工具进行全面测试
"""

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest
import pandas as pd
import time
from typing import Dict, Any, List
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

class StreamlitTestSuite:
    """Streamlit测试套件"""

    def __init__(self):
        self.setup_test_environment()

    def setup_test_environment(self):
        """设置测试环境"""
        # 设置测试模式
        os.environ['STREAMLIT_TESTING'] = 'true'

    def test_main_app(self):
        """测试主应用"""
        at = AppTest.from_file("main.py")
        at.run()

        # 检查页面标题
        assert len(at.title) > 0
        assert "AI数据库分析师" in at.title[0].value

        # 检查基本组件
        assert len(at.sidebar) > 0
        assert len(at.markdown) > 0

    def test_chat_page(self):
        """测试聊天页面"""
        at = AppTest.from_file("pages/1_💬_Chat.py")
        at.run()

        # 检查聊天界面组件
        assert len(at.title) > 0
        assert "聊天" in at.title[0].value

        # 模拟用户输入
        if len(at.chat_input) > 0:
            at.chat_input[0].set_value("测试查询").run()

            # 检查是否有聊天消息
            assert len(at.chat_message) > 0

    def test_analysis_page(self):
        """测试分析页面"""
        at = AppTest.from_file("pages/2_📊_Analysis.py")

        # 设置测试数据
        test_data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10),
            'value': range(10),
            'category': ['A', 'B'] * 5
        })

        at.session_state['analysis_results'] = [{
            'title': '测试分析',
            'data': test_data,
            'success': True,
            'execution_time': 1.5
        }]

        at.run()

        # 检查分析结果显示
        assert len(at.dataframe) > 0

    def test_settings_page(self):
        """测试设置页面"""
        at = AppTest.from_file("pages/3_🔧_Settings.py")
        at.run()

        # 检查设置选项
        assert len(at.selectbox) > 0
        assert len(at.tabs) > 0

        # 测试设置保存
        if len(at.button) > 0:
            save_button = None
            for button in at.button:
                if "保存" in button.label:
                    save_button = button
                    break

            if save_button:
                save_button.click().run()

    def test_session_state_management(self):
        """测试Session State管理"""
        at = AppTest.from_file("main.py")

        # 设置测试状态
        at.session_state["test_key"] = "test_value"
        at.run()

        # 验证状态保持
        assert at.session_state["test_key"] == "test_value"

    def test_error_handling(self):
        """测试错误处理"""
        at = AppTest.from_file("main.py")

        # 模拟错误状态
        at.session_state["error_history"] = [{
            'timestamp': time.time(),
            'context': 'test',
            'error_type': 'TestError',
            'error_message': 'Test error message'
        }]

        at.run()

        # 检查应用是否正常处理错误
        assert len(at.error) == 0  # 不应该有未处理的错误

    def test_performance_metrics(self):
        """测试性能指标"""
        at = AppTest.from_file("pages/3_🔧_Settings.py")

        # 设置性能数据
        at.session_state["performance_metrics"] = {
            'response_times': [
                {'operation': 'test', 'duration': 1.0, 'timestamp': time.time()}
            ],
            'memory_usage': [
                {'rss': 100, 'vms': 200, 'timestamp': time.time()}
            ]
        }

        at.run()

        # 验证性能监控页面
        performance_tab_found = False
        for tab in at.tabs:
            if "性能监控" in tab.label:
                performance_tab_found = True
                break

        assert performance_tab_found

    def test_data_export_functionality(self):
        """测试数据导出功能"""
        at = AppTest.from_file("pages/2_📊_Analysis.py")

        # 设置测试数据
        test_data = pd.DataFrame({'col1': [1, 2, 3], 'col2': [4, 5, 6]})
        at.session_state['analysis_results'] = [{
            'data': test_data,
            'title': 'Test Export'
        }]

        at.run()

        # 检查导出按钮
        export_button_found = False
        for button in at.button:
            if "下载" in button.label or "导出" in button.label:
                export_button_found = True
                break

        assert export_button_found

def run_component_tests():
    """运行组件测试"""
    print("开始组件测试...")

    # 测试聊天组件
    test_chat_component()

    # 测试图表组件
    test_chart_component()

    # 测试工作流组件
    test_workflow_component()

    print("组件测试完成！")

def test_chat_component():
    """测试聊天组件"""
    from components.chat_interface import ChatInterface

    # 创建聊天组件实例
    chat = ChatInterface()

    # 测试初始化
    assert hasattr(chat, 'initialize_chat_state')

    # 测试消息添加
    chat.add_message("user", "测试消息")
    assert len(st.session_state.get('chat_messages', [])) > 0

def test_chart_component():
    """测试图表组件"""
    from components.chart_renderer import ChartRenderer

    # 创建图表组件实例
    chart_renderer = ChartRenderer()

    # 测试图表类型建议
    test_data = pd.DataFrame({
        'x': range(10),
        'y': range(10, 20),
        'category': ['A', 'B'] * 5
    })

    suggested_type = chart_renderer.auto_suggest_chart_type(test_data)
    assert suggested_type in chart_renderer.supported_charts

def test_workflow_component():
    """测试工作流组件"""
    from components.workflow_display import WorkflowDisplay

    # 创建工作流组件实例
    workflow = WorkflowDisplay()

    # 测试工作流启动
    test_steps = [
        {"name": "测试步骤1", "description": "测试描述", "status": "pending"}
    ]

    workflow.start_workflow(test_steps)
    assert st.session_state.get('workflow_status') == 'running'

def run_integration_tests():
    """运行集成测试"""
    print("开始集成测试...")

    # 测试LangGraph集成
    test_langgraph_integration()

    # 测试缓存系统
    test_cache_system()

    # 测试错误处理系统
    test_error_system()

    print("集成测试完成！")

def test_langgraph_integration():
    """测试LangGraph集成"""
    try:
        from utils.langgraph_integration import LangGraphIntegration

        # 创建集成实例
        integration = LangGraphIntegration()

        # 测试连接验证
        is_connected = integration.validate_connection()
        print(f"LangGraph连接状态: {is_connected}")

    except ImportError:
        print("LangGraph模块未安装，跳过集成测试")

def test_cache_system():
    """测试缓存系统"""
    from utils.cache_manager import CacheManager

    cache_manager = CacheManager()

    # 测试缓存功能
    test_data = pd.DataFrame({'test': [1, 2, 3]})
    cached_result = cache_manager.cache_query_results("SELECT * FROM test", {})

    assert isinstance(cached_result, pd.DataFrame)

def test_error_system():
    """测试错误处理系统"""
    from utils.error_handler import ErrorHandler

    error_handler = ErrorHandler()

    # 测试错误处理
    try:
        raise ValueError("测试错误")
    except ValueError as e:
        error_handler.handle_error(e, "测试上下文")

    # 检查错误是否被记录
    error_history = st.session_state.get('error_history', [])
    assert len(error_history) > 0

# Pytest测试类
class TestStreamlitApp:
    """Pytest测试类"""

    def setup_method(self):
        """测试设置"""
        # 清理session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]

    def test_app_initialization(self):
        """测试应用初始化"""
        test_suite = StreamlitTestSuite()
        test_suite.test_main_app()

    def test_chat_functionality(self):
        """测试聊天功能"""
        test_suite = StreamlitTestSuite()
        test_suite.test_chat_page()

    def test_analysis_functionality(self):
        """测试分析功能"""
        test_suite = StreamlitTestSuite()
        test_suite.test_analysis_page()

    def test_settings_functionality(self):
        """测试设置功能"""
        test_suite = StreamlitTestSuite()
        test_suite.test_settings_page()

    def test_session_management(self):
        """测试会话管理"""
        test_suite = StreamlitTestSuite()
        test_suite.test_session_state_management()

    def test_error_handling_system(self):
        """测试错误处理系统"""
        test_suite = StreamlitTestSuite()
        test_suite.test_error_handling()

if __name__ == "__main__":
    # 运行所有测试
    print("🧪 开始Streamlit应用测试")

    print("\n📱 运行应用测试...")
    test_suite = StreamlitTestSuite()
    test_suite.test_main_app()
    test_suite.test_chat_page()
    test_suite.test_analysis_page()
    test_suite.test_settings_page()

    print("\n🔧 运行组件测试...")
    run_component_tests()

    print("\n🔗 运行集成测试...")
    run_integration_tests()

    print("\n✅ 所有测试完成！")
```

### 2. 性能测试脚本 (tests/performance_tests.py)

```python
"""
性能测试脚本
测试应用在各种负载条件下的性能表现
"""

import time
import psutil
import pandas as pd
import streamlit as st
from concurrent.futures import ThreadPoolExecutor
import asyncio
from typing import Dict, List, Any
import matplotlib.pyplot as plt

class PerformanceTester:
    """性能测试器"""

    def __init__(self):
        self.results = []
        self.baseline_metrics = {}

    def run_load_test(self, concurrent_users: int = 5, duration: int = 60):
        """运行负载测试"""
        print(f"开始负载测试: {concurrent_users} 并发用户, {duration} 秒")

        start_time = time.time()
        end_time = start_time + duration

        # 记录基线指标
        self.record_baseline_metrics()

        # 并发用户模拟
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = []

            while time.time() < end_time:
                # 提交用户会话任务
                future = executor.submit(self.simulate_user_session)
                futures.append(future)

                time.sleep(1)  # 每秒一个新用户

            # 等待所有任务完成
            for future in futures:
                try:
                    result = future.result(timeout=30)
                    self.results.append(result)
                except Exception as e:
                    print(f"用户会话失败: {e}")

        # 分析结果
        self.analyze_performance_results()

    def simulate_user_session(self) -> Dict[str, Any]:
        """模拟用户会话"""
        session_start = time.time()

        try:
            # 模拟用户操作
            operations = [
                self.simulate_page_load,
                self.simulate_chat_interaction,
                self.simulate_data_query,
                self.simulate_chart_rendering
            ]

            operation_results = []
            for operation in operations:
                op_start = time.time()
                operation()
                op_duration = time.time() - op_start
                operation_results.append({
                    'operation': operation.__name__,
                    'duration': op_duration
                })

            session_duration = time.time() - session_start

            return {
                'session_duration': session_duration,
                'operations': operation_results,
                'success': True,
                'timestamp': session_start
            }

        except Exception as e:
            return {
                'session_duration': time.time() - session_start,
                'operations': [],
                'success': False,
                'error': str(e),
                'timestamp': session_start
            }

    def simulate_page_load(self):
        """模拟页面加载"""
        # 模拟页面初始化时间
        time.sleep(0.5)

    def simulate_chat_interaction(self):
        """模拟聊天交互"""
        # 模拟用户输入和AI响应
        time.sleep(1.0)

    def simulate_data_query(self):
        """模拟数据查询"""
        # 模拟数据库查询时间
        time.sleep(2.0)

        # 创建模拟数据
        data = pd.DataFrame({
            'id': range(1000),
            'value': range(1000, 2000),
            'category': ['A', 'B', 'C'] * 333 + ['A']
        })

        return data

    def simulate_chart_rendering(self):
        """模拟图表渲染"""
        # 模拟图表生成时间
        time.sleep(1.5)

    def record_baseline_metrics(self):
        """记录基线性能指标"""
        process = psutil.Process()

        self.baseline_metrics = {
            'cpu_percent': process.cpu_percent(),
            'memory_mb': process.memory_info().rss / 1024 / 1024,
            'threads': process.num_threads(),
            'timestamp': time.time()
        }

        print(f"基线指标: CPU={self.baseline_metrics['cpu_percent']:.1f}%, "
              f"内存={self.baseline_metrics['memory_mb']:.1f}MB")

    def analyze_performance_results(self):
        """分析性能测试结果"""
        if not self.results:
            print("无性能测试结果")
            return

        print("\n📊 性能测试结果分析:")

        # 成功率统计
        successful_sessions = [r for r in self.results if r['success']]
        success_rate = len(successful_sessions) / len(self.results)
        print(f"会话成功率: {success_rate:.1%}")

        # 响应时间统计
        session_durations = [r['session_duration'] for r in successful_sessions]
        if session_durations:
            avg_duration = sum(session_durations) / len(session_durations)
            max_duration = max(session_durations)
            min_duration = min(session_durations)

            print(f"平均会话时长: {avg_duration:.2f}s")
            print(f"最长会话时长: {max_duration:.2f}s")
            print(f"最短会话时长: {min_duration:.2f}s")

        # 操作性能统计
        self.analyze_operation_performance(successful_sessions)

        # 资源使用统计
        self.analyze_resource_usage()

    def analyze_operation_performance(self, sessions: List[Dict]):
        """分析操作性能"""
        operation_stats = {}

        for session in sessions:
            for op in session.get('operations', []):
                op_name = op['operation']
                op_duration = op['duration']

                if op_name not in operation_stats:
                    operation_stats[op_name] = []

                operation_stats[op_name].append(op_duration)

        print("\n🔧 操作性能统计:")
        for op_name, durations in operation_stats.items():
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            print(f"{op_name}: 平均{avg_duration:.2f}s, 最大{max_duration:.2f}s")

    def analyze_resource_usage(self):
        """分析资源使用情况"""
        try:
            process = psutil.Process()
            current_metrics = {
                'cpu_percent': process.cpu_percent(),
                'memory_mb': process.memory_info().rss / 1024 / 1024,
                'threads': process.num_threads()
            }

            print("\n💻 资源使用对比:")
            print(f"CPU使用率: {self.baseline_metrics['cpu_percent']:.1f}% → {current_metrics['cpu_percent']:.1f}%")
            print(f"内存使用: {self.baseline_metrics['memory_mb']:.1f}MB → {current_metrics['memory_mb']:.1f}MB")
            print(f"线程数: {self.baseline_metrics['threads']} → {current_metrics['threads']}")

        except Exception as e:
            print(f"资源使用分析错误: {e}")

    def run_stress_test(self, max_data_size: int = 100000):
        """运行压力测试"""
        print(f"开始压力测试: 最大数据量 {max_data_size} 行")

        data_sizes = [1000, 5000, 10000, 50000, max_data_size]
        stress_results = []

        for size in data_sizes:
            print(f"测试数据量: {size} 行")

            start_time = time.time()

            try:
                # 创建大数据集
                data = pd.DataFrame({
                    'id': range(size),
                    'value': range(size),
                    'category': ['A', 'B', 'C'] * (size // 3 + 1)
                })

                # 模拟数据处理
                processed_data = data.groupby('category').sum()

                # 模拟图表渲染
                time.sleep(0.1)

                processing_time = time.time() - start_time
                memory_usage = psutil.Process().memory_info().rss / 1024 / 1024

                stress_results.append({
                    'data_size': size,
                    'processing_time': processing_time,
                    'memory_usage': memory_usage,
                    'success': True
                })

                print(f"✅ 成功处理 {size} 行数据，耗时 {processing_time:.2f}s")

            except Exception as e:
                stress_results.append({
                    'data_size': size,
                    'processing_time': 0,
                    'memory_usage': 0,
                    'success': False,
                    'error': str(e)
                })

                print(f"❌ 处理 {size} 行数据失败: {e}")

        self.analyze_stress_results(stress_results)

    def analyze_stress_results(self, results: List[Dict]):
        """分析压力测试结果"""
        print("\n📈 压力测试结果:")

        successful_results = [r for r in results if r['success']]

        if successful_results:
            print("数据量 | 处理时间 | 内存使用")
            print("-" * 30)

            for result in successful_results:
                print(f"{result['data_size']:6d} | {result['processing_time']:8.2f}s | {result['memory_usage']:8.1f}MB")

            # 寻找性能瓶颈
            max_size = max(r['data_size'] for r in successful_results)
            print(f"\n最大可处理数据量: {max_size:,} 行")

def run_memory_leak_test(duration: int = 300):
    """运行内存泄漏测试"""
    print(f"开始内存泄漏测试，持续 {duration} 秒")

    memory_records = []
    start_time = time.time()

    while time.time() - start_time < duration:
        # 模拟应用操作
        simulate_app_operations()

        # 记录内存使用
        memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
        memory_records.append({
            'timestamp': time.time() - start_time,
            'memory_mb': memory_mb
        })

        time.sleep(10)  # 每10秒记录一次

    # 分析内存趋势
    analyze_memory_trend(memory_records)

def simulate_app_operations():
    """模拟应用操作"""
    # 模拟session state操作
    st.session_state['test_data'] = pd.DataFrame({
        'x': range(1000),
        'y': range(1000, 2000)
    })

    # 模拟缓存操作
    time.sleep(0.1)

    # 清理临时数据
    if 'test_data' in st.session_state:
        del st.session_state['test_data']

def analyze_memory_trend(records: List[Dict]):
    """分析内存趋势"""
    if len(records) < 2:
        print("内存记录不足，无法分析趋势")
        return

    initial_memory = records[0]['memory_mb']
    final_memory = records[-1]['memory_mb']
    memory_growth = final_memory - initial_memory

    print(f"\n🧠 内存泄漏测试结果:")
    print(f"初始内存: {initial_memory:.1f}MB")
    print(f"最终内存: {final_memory:.1f}MB")
    print(f"内存增长: {memory_growth:.1f}MB")

    if memory_growth > 50:  # 超过50MB增长认为可能有泄漏
        print("⚠️ 可能存在内存泄漏")
    else:
        print("✅ 未检测到明显内存泄漏")

if __name__ == "__main__":
    print("🚀 开始性能测试")

    # 创建性能测试器
    tester = PerformanceTester()

    # 运行不同类型的测试
    print("\n📊 负载测试")
    tester.run_load_test(concurrent_users=3, duration=30)

    print("\n💪 压力测试")
    tester.run_stress_test(max_data_size=50000)

    print("\n🧠 内存泄漏测试")
    run_memory_leak_test(duration=60)

    print("\n✅ 性能测试完成")
```

### 3. 部署配置文件

#### Docker配置 (Dockerfile)

```dockerfile
# 使用Python 3.11作为基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p .streamlit logs

# 复制Streamlit配置
COPY .streamlit/config.toml .streamlit/
COPY .streamlit/secrets.toml.example .streamlit/secrets.toml

# 暴露端口
EXPOSE 8501

# 健康检查
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# 启动命令
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

#### Docker Compose配置 (docker-compose.yml)

```yaml
version: '3.8'

services:
  streamlit-app:
    build: .
    ports:
      - "8501:8501"
    environment:
      - STREAMLIT_LOGGER_LEVEL=INFO
      - STREAMLIT_CLIENT_TOOLBAR_MODE=minimal
    volumes:
      - ./logs:/app/logs
      - ./.streamlit/secrets.toml:/app/.streamlit/secrets.toml
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # 可选：添加数据库服务
  # postgres:
  #   image: postgres:15
  #   environment:
  #     POSTGRES_DB: streamlit_app
  #     POSTGRES_USER: streamlit
  #     POSTGRES_PASSWORD: password
  #   volumes:
  #     - postgres_data:/var/lib/postgresql/data
  #   ports:
  #     - "5432:5432"

  # 可选：添加Redis缓存
  # redis:
  #   image: redis:7-alpine
  #   ports:
  #     - "6379:6379"
  #   volumes:
  #     - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

#### GitHub Actions配置 (.github/workflows/ci-cd.yml)

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Cache dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Run linting
      run: |
        pip install flake8
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
        flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

    - name: Run tests
      run: |
        pytest tests/ -v --cov=. --cov-report=xml

    - name: Upload coverage reports
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
    - uses: actions/checkout@v3

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2

    - name: Login to Docker Hub
      uses: docker/login-action@v2
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}

    - name: Build and push Docker image
      uses: docker/build-push-action@v4
      with:
        context: .
        push: true
        tags: |
          your-username/streamlit-app:latest
          your-username/streamlit-app:${{ github.sha }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
    - name: Deploy to production
      run: |
        echo "Deployment script would go here"
        # 实际部署命令，如 kubectl apply 或云平台部署命令
```

### 4. 监控和日志配置 (utils/monitoring.py)

```python
"""
监控和日志配置
提供应用监控、日志记录和告警功能
"""

import logging
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
import streamlit as st
import os

class MonitoringSystem:
    """监控系统"""

    def __init__(self):
        self.setup_logging()
        self.setup_metrics_collection()

    def setup_logging(self):
        """设置日志系统"""
        # 创建logs目录
        os.makedirs('logs', exist_ok=True)

        # 配置日志格式
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/app.log'),
                logging.StreamHandler()
            ]
        )

        self.logger = logging.getLogger('streamlit_monitoring')

    def setup_metrics_collection(self):
        """设置指标收集"""
        if 'monitoring_metrics' not in st.session_state:
            st.session_state.monitoring_metrics = {
                'page_views': {},
                'user_actions': [],
                'errors': [],
                'performance': []
            }

    def log_page_view(self, page_name: str):
        """记录页面访问"""
        timestamp = time.time()

        # 更新页面访问计数
        metrics = st.session_state.monitoring_metrics
        if page_name not in metrics['page_views']:
            metrics['page_views'][page_name] = 0
        metrics['page_views'][page_name] += 1

        # 记录日志
        self.logger.info(f"Page view: {page_name}")

    def log_user_action(self, action: str, details: Dict = None):
        """记录用户操作"""
        action_record = {
            'timestamp': time.time(),
            'action': action,
            'details': details or {},
            'session_id': st.session_state.get('session_id', 'unknown')
        }

        st.session_state.monitoring_metrics['user_actions'].append(action_record)

        # 限制记录数量
        if len(st.session_state.monitoring_metrics['user_actions']) > 1000:
            st.session_state.monitoring_metrics['user_actions'] = \
                st.session_state.monitoring_metrics['user_actions'][-1000:]

        self.logger.info(f"User action: {action}", extra={'details': details})

    def log_error(self, error: Exception, context: str = ""):
        """记录错误"""
        error_record = {
            'timestamp': time.time(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context,
            'session_id': st.session_state.get('session_id', 'unknown')
        }

        st.session_state.monitoring_metrics['errors'].append(error_record)

        # 限制记录数量
        if len(st.session_state.monitoring_metrics['errors']) > 100:
            st.session_state.monitoring_metrics['errors'] = \
                st.session_state.monitoring_metrics['errors'][-100:]

        self.logger.error(f"Error in {context}: {error}", exc_info=True)

    def log_performance_metric(self, metric_name: str, value: float, unit: str = ""):
        """记录性能指标"""
        metric_record = {
            'timestamp': time.time(),
            'metric_name': metric_name,
            'value': value,
            'unit': unit
        }

        st.session_state.monitoring_metrics['performance'].append(metric_record)

        # 限制记录数量
        if len(st.session_state.monitoring_metrics['performance']) > 500:
            st.session_state.monitoring_metrics['performance'] = \
                st.session_state.monitoring_metrics['performance'][-500:]

        self.logger.info(f"Performance metric: {metric_name} = {value} {unit}")

    def get_monitoring_dashboard(self) -> Dict[str, Any]:
        """获取监控仪表板数据"""
        metrics = st.session_state.monitoring_metrics

        current_time = time.time()
        hour_ago = current_time - 3600

        # 计算近一小时的统计数据
        recent_actions = [
            a for a in metrics['user_actions']
            if a['timestamp'] > hour_ago
        ]

        recent_errors = [
            e for e in metrics['errors']
            if e['timestamp'] > hour_ago
        ]

        dashboard_data = {
            'total_page_views': sum(metrics['page_views'].values()),
            'recent_actions_count': len(recent_actions),
            'recent_errors_count': len(recent_errors),
            'most_visited_page': max(
                metrics['page_views'].items(),
                key=lambda x: x[1],
                default=('无', 0)
            )[0],
            'error_rate': len(recent_errors) / max(len(recent_actions), 1),
            'uptime_hours': (current_time - st.session_state.get('app_start_time', current_time)) / 3600
        }

        return dashboard_data

    def export_logs(self, start_time: Optional[float] = None, end_time: Optional[float] = None) -> str:
        """导出日志"""
        metrics = st.session_state.monitoring_metrics

        # 过滤时间范围
        filtered_data = {}

        if start_time and end_time:
            filtered_data['user_actions'] = [
                a for a in metrics['user_actions']
                if start_time <= a['timestamp'] <= end_time
            ]
            filtered_data['errors'] = [
                e for e in metrics['errors']
                if start_time <= e['timestamp'] <= end_time
            ]
            filtered_data['performance'] = [
                p for p in metrics['performance']
                if start_time <= p['timestamp'] <= end_time
            ]
        else:
            filtered_data = metrics

        return json.dumps(filtered_data, indent=2, ensure_ascii=False)

# 全局监控实例
monitoring_system = MonitoringSystem()

def monitor_function(func_name: str):
    """函数监控装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time

                monitoring_system.log_performance_metric(
                    f"{func_name}_execution_time",
                    execution_time,
                    "seconds"
                )

                return result

            except Exception as e:
                monitoring_system.log_error(e, func_name)
                raise

        return wrapper
    return decorator
```

### 5. 部署检查清单 (deployment_checklist.md)

```markdown
# 部署检查清单

## 🔍 部署前检查

### 代码质量
- [ ] 所有测试通过
- [ ] 代码覆盖率 > 80%
- [ ] 无安全漏洞
- [ ] 性能测试通过
- [ ] 内存泄漏测试通过

### 配置检查
- [ ] 生产环境配置正确
- [ ] 敏感信息已移入环境变量
- [ ] 数据库连接配置正确
- [ ] 缓存配置优化
- [ ] 日志级别设置合适

### 安全检查
- [ ] 依赖包安全扫描通过
- [ ] API密钥安全存储
- [ ] 用户输入验证完整
- [ ] 错误信息不泄露敏感信息
- [ ] HTTPS配置正确

### 性能检查
- [ ] 页面加载时间 < 3秒
- [ ] 并发用户支持 > 50
- [ ] 内存使用 < 1GB
- [ ] CPU使用率 < 70%
- [ ] 缓存命中率 > 80%

## 🚀 部署步骤

### 1. 环境准备
```bash
# 创建部署目录
mkdir -p /opt/streamlit-app
cd /opt/streamlit-app

# 克隆代码
git clone <repository-url> .

# 设置环境变量
cp .env.example .env
vim .env
```

### 2. Docker部署
```bash
# 构建镜像
docker build -t streamlit-app:latest .

# 运行容器
docker-compose up -d

# 检查状态
docker-compose ps
docker-compose logs -f
```

### 3. 健康检查
```bash
# 检查应用状态
curl http://localhost:8501/_stcore/health

# 检查功能
curl http://localhost:8501/
```

### 4. 监控设置
```bash
# 配置日志轮转
sudo logrotate -d /etc/logrotate.d/streamlit-app

# 设置监控告警
# 配置Prometheus/Grafana等监控工具
```

## 📊 部署后验证

### 功能验证
- [ ] 主页正常加载
- [ ] 聊天功能正常
- [ ] 数据查询正常
- [ ] 图表渲染正常
- [ ] 设置页面正常

### 性能验证
- [ ] 响应时间正常
- [ ] 内存使用正常
- [ ] CPU使用正常
- [ ] 并发处理正常

### 监控验证
- [ ] 日志正常记录
- [ ] 指标正常收集
- [ ] 告警正常工作
- [ ] 健康检查正常

## 🔧 故障排除

### 常见问题
1. **应用无法启动**
   - 检查端口占用
   - 检查环境变量
   - 查看错误日志

2. **性能问题**
   - 检查资源使用
   - 优化数据库查询
   - 调整缓存配置

3. **功能异常**
   - 检查依赖版本
   - 验证配置文件
   - 查看应用日志

### 回滚计划
1. 停止当前版本
2. 恢复上一版本镜像
3. 验证功能正常
4. 更新负载均衡器
```

## 验收标准

### 测试验收
- [ ] 单元测试覆盖率 > 80%
- [ ] 集成测试全部通过
- [ ] 性能测试满足要求
- [ ] 用户验收测试通过
- [ ] 安全测试无高危漏洞

### 部署验收
- [ ] 生产环境部署成功
- [ ] 健康检查正常
- [ ] 监控系统正常
- [ ] 日志记录完整
- [ ] 备份恢复流程测试通过

### 用户体验验收
- [ ] 应用加载速度 < 3秒
- [ ] 功能操作流畅
- [ ] 错误处理友好
- [ ] 界面响应及时
- [ ] 数据展示准确

### 运维验收
- [ ] 部署文档完整
- [ ] 监控告警配置完成
- [ ] 日志轮转正常
- [ ] 备份策略执行
- [ ] 故障恢复流程测试

## 后续优化
完成此任务后，项目进入生产运行阶段，需要持续监控、优化和维护。