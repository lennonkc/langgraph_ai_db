# AI Database Analyst - LangGraph Workflow

本仓库包含一个基于 LangGraph 构建的 AI 数据库分析师项目。该项目能够理解用户的自然语言问题，自动生成并执行 SQL 查询，对结果进行验证和可视化，并支持人工审查，最终生成一份完整的分析报告。

## 核心功能

- **自然语言理解**: 利用语义匹配技术，理解用户提问并匹配到预设的查询模板或分析意图。
- **动态查询生成**: 基于大语言模型（LLM）和多步思考，动态构建复杂的 SQL 查询计划。
- **安全执行**: 在执行查询前进行 "Dry Run" 检查，预估查询成本和影响，确保数据库操作的安全性。
- **结果自动验证**: 对查询结果进行自动化验证，检查数据一致性、完整性和逻辑正确性。
- **交互式人工审查**: 在关键步骤暂停工作流，由用户审查、修改或批准查询和结果。
- **智能可视化**: 根据查询结果和用户偏好，自动生成图表（如表格、条形图、折线图等）和分析报告。
- **全流程监控**: 集成 LangSmith，实现对工作流每一步的端到端跟踪、性能监控和成本追踪。
- **强大的错误处理**: 内置了重试、熔断和恢复机制，能够优雅地处理查询错误、API 超时等多种异常情况。

## 技术栈

- **核心框架**: [LangGraph](https://github.com/langchain-ai/langgraph) - 用于构建可组合、有状态的多 Agent 工作流。
- **大语言模型 (LLM)**: Google Gemini Pro (通过 Vertex AI)
- **数据库**: Google BigQuery
- **监控与调试**: [LangSmith](https://www.langchain.com/langsmith)
- **Python 库**: `langchain`, `structlog`, `dotenv`, `pandas` 等。

## 项目结构

```
.
├── flows/                  # 各个子工作流模块
│   ├── semantic_matching_flow.py   # 语义匹配
│   ├── chief_architect_flow.py     # 查询生成
│   ├── dry_run_safety.py           # 安全执行
│   ├── script_validation_flow.py   # 结果验证
│   ├── human_review_flow.py        # 人工审查
│   └── visualization_flow.py       # 可视化报告
├── config/                 # 配置文件
│   ├── langsmith_config.py         # LangSmith 配置
│   └── prompt_templates.py         # Prompt 模板
├── monitoring/             # 监控与追踪模块
├── error_handling/         # 错误处理模块
├── tools/                  # BigQuery、可视化等工具
├── webui/                  # (可选) Streamlit Web 界面
├── main_workflow.py        # 主工作流入口
├── requirements.txt        # Python 依赖
└── README.md               # 项目文档
```

## 安装与启动

1.  **克隆仓库**
    ```bash
    git clone <your-repo-url>
    cd <your-repo-name>
    ```

2.  **创建并激活虚拟环境**
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

3.  **安装依赖**
    ```bash
    pip install -r requirements.txt
    ```

4.  **配置环境变量**
    复制 `.env.example` 文件为 `.env`，并填入您的 Google Cloud、BigQuery 和 LangSmith API 密钥等信息。
    ```bash
    cp .env.example .env
    # 编辑 .env 文件
    ```

5.  **启动 LangGraph Studio**
    项目通过 LangGraph Studio 进行开发和调试。
    ```bash
    langgraph dev
    ```
    启动后，访问 `http://localhost:port` 即可与 AI 数据分析师进行交互。

## BigQuery 对接与验证

项目通过 Google Cloud 的标准认证流程与 BigQuery 对接。以下是详细的配置和验证步骤。

### 1. 认证方式

本应用使用 **Application Default Credentials (ADC)** 机制进行认证。这意味着您有以下几种方式来提供凭证：

- **gcloud CLI (推荐)**: 在您的本地开发环境中，通过 `gcloud` 工具进行认证。
  ```bash
  gcloud auth application-default login
  ```
  执行此命令后，您的凭证将保存在本地，应用程序会自动读取并使用它们。

- **服务账号 (Service Account)**: 在生产环境或 CI/CD 中，推荐使用服务账号。
  1.  在 Google Cloud Console 中创建一个服务账号，并授予其 `BigQuery User` 和 `BigQuery Job User` 角色。
  2.  下载该服务账号的 JSON 密钥文件。
  3.  设置环境变量 `GOOGLE_APPLICATION_CREDENTIALS` 指向该 JSON 文件的路径。
      ```bash
      export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/keyfile.json"
      ```

### 2. 配置项目和数据集

在 `.env` 文件中，您需要配置以下与 BigQuery 相关的变量：

- `GOOGLE_CLOUD_PROJECT`: 您的 Google Cloud 项目 ID。
- `GOOGLE_CLOUD__BIGQUERY_PROJECT_ID`: 您的 BigQuery 项目 ID (通常与 `GOOGLE_CLOUD_PROJECT` 相同)。
- `BIGQUERY_DATASET`: 您希望查询的 BigQuery 数据集名称 (例如 `reporting_us`)。

### 3. 验证连接

项目提供了一个内置的脚本来验证与 BigQuery 的连接、查询语法和执行。在完成上述配置后，您可以运行 `tools/bigquery_tools.py` 来进行验证：

```bash
python tools/bigquery_tools.py
```

这个脚本会执行以下操作：

1.  **语法验证**: 对一个示例 SQL 查询进行语法检查。
2.  **成本估算**: 对查询进行 "Dry Run"，估算将处理的数据量和费用。
3.  **查询执行**: 实际执行查询并返回前 5 条结果作为示例。

如果所有步骤都显示 `✅ PASSED`，则表示您已成功配置并连接到 BigQuery。

## 工作流详解

项目的主工作流 (`main_workflow.py`) 是一个状态图 (StateGraph)，定义了从接收用户问题到生成最终报告的完整流程。

1.  **`initialize_session`**: 初始化会话，设置 LangSmith 追踪。
2.  **`analyze_question`**: 调用 `semantic_matching_flow`，分析用户问题，匹配相似查询，并给出置信度分数。
3.  **路由决策 (分析后)**:
    - **高置信度**: 直接进入查询生成。
    - **中置信度**: 尝试生成查询，但会加入更多上下文。
    - **低置信度**: 请求用户澄清问题。
4.  **`generate_query`**: 调用 `chief_architect_flow`，根据分析结果生成 SQL 查询。如果需要，会进行多步规划。
5.  **`execute_script`**: 调用 `dry_run_safety`，先进行 Dry Run 检查，通过后再执行查询。
6.  **路由决策 (执行后)**:
    - **成功**: 进入结果验证。
    - **失败 (可恢复)**: 返回 `generate_query` 步骤重试。
    - **失败 (不可恢复)**: 进入错误处理。
7.  **`validate_results`**: 调用 `script_validation_flow`，对查询结果的正确性和合理性进行验证。
8.  **`explain_results`**: 使用 LLM 生成对结果的自然语言解释和数据样本表格。
9.  **`human_review`**: **工作流暂停**，等待用户审查结果、解释和图表建议。用户可以批准、请求修改或要求重新生成。
10. **`generate_visualization`**: 根据用户的选择和偏好，调用 `visualization_flow` 生成最终的 HTML 分析报告。
11. **`finalize_workflow`**: 标记工作流成功结束。
12. **`handle_error`**: 统一的错误处理节点，记录详细错误信息并终止工作流。

这个模块化的设计使得每个步骤都可以独立开发、测试和优化，同时保证了整个工作流的健壮性和可扩展性。