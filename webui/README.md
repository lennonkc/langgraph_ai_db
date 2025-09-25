## 项目概览

本计划书旨在为现有的LangGraph AI数据库分析师系统构建一个完整的前端界面，采用
Streamlit框架实现商业级别的用户交互体验。当前后端功能基本完成，包括问题分析、查询
生成、脚本执行、验证和可视化等核心流程。

## 技术架构选择

### 核心技术栈
- **前端框架**: Streamlit
- **后端集成**: 直接Python集成，无需额外API层
- **状态管理**: Streamlit Session State
- **UI组件**: Streamlit内置组件库 + 自定义组件
- **图表库**: Plotly, Altair, Matplotlib + 复用现有的可视化组件 (Vega, Mermaid, Mindmap)

### Streamlit 集成策略
- **st.chat_message**: 实现AI对话界面，支持流式输出
- **st.session_state**: 管理LangGraph工作流状态和进度
- **st.columns**: 构建响应式布局和多面板界面
- **st.rerun**: 实现实时状态更新和进度反馈
- **直接函数调用**: 无缝集成LangGraph节点和工作流

## 系统架构设计

### 前端与后端交互模式
```
Streamlit App → 直接调用 → LangGraph Workflow ↔ BigQuery
```

### 核心组件架构
1. **Main App**: Streamlit主应用程序入口
2. **Page Manager**: 多页面管理和路由
3. **Workflow Controller**: LangGraph工作流控制器
4. **Session Manager**: 会话状态和数据管理
5. **Chart Components**: 图表展示组件
6. **Progress Display**: 实时进度显示

## 实施计划总览

### 阶段 1: 基础搭建
- 项目初始化和Streamlit环境配置
- 多页面布局和导航设计

### 阶段 2: 核心界面
- AI聊天界面开发 (st.chat_message)
- 工作流可视化 (st.progress, st.status)

### 阶段 3: 功能集成
- LangGraph工作流直接集成
- 数据可视化组件集成
- 人工审查界面开发

### 阶段 4: 完善优化
- Session State管理和错误处理
- 性能优化和缓存策略

### 阶段 5: 测试部署
- 功能测试和集成验证
- 部署配置和上线

## 核心功能规划

### 1. AI助手聊天界面
- **组件**: st.chat_message + st.chat_input
- **功能**: 自然语言问题输入、流式对话、实时进度显示
- **交互流程**: 问题分析 → 查询生成 → 执行验证 → 结果展示

### 2. 工作流可视化
- **显示**: st.progress + st.status 显示当前执行步骤和状态
- **交互**: st.button 实现步骤跳转和重试机制

### 3. 数据审查界面
- **功能**: st.dataframe 查询结果预览、st.selectbox 图表类型选择
- **组件**: st.data_editor 交互式表格、st.tabs 多视图切换

### 4. 报告生成系统
- **输出**: st.download_button 下载功能、多格式导出
- **集成**: 现有可视化库 (Vega/Mermaid/Mindmap) + Plotly/Altair

## 技术实现要点

### Streamlit实现策略
1. **应用配置**:
   - 直接Python环境，无需额外运行时
   - 简化的错误处理和日志系统

2. **函数集成**:
   - 直接调用LangGraph工作流函数
   - 原生Python参数验证和结果处理

3. **状态管理**:
   - st.session_state 统一管理工作流和UI状态
   - st.rerun() 实现实时更新和进度反馈

### 用户体验设计
1. **渐进式交互**: 从简单查询到复杂分析的逐步引导
2. **智能推荐**: 基于历史查询和数据特征的建议
3. **错误恢复**: 友好的错误提示和重试机制
4. **响应式设计**: 适配桌面和移动设备

## 数据流设计

### 请求流程
```
用户输入 → Streamlit → 直接调用 → LangGraph → BigQuery → 结果处理 →
UI更新
```

### 状态管理
- **Session State**: st.session_state管理用户问题、分析历史、偏好设置
- **工作流状态**: 直接存储当前步骤、执行结果、错误信息
- **UI状态**: Streamlit组件状态自动管理、页面配置和显示模式

## 质量保证策略

### 错误处理
- 网络错误、API限制、数据处理异常的优雅降级
- 用户友好的错误信息和恢复建议

### 性能优化
- st.cache_data、st.cache_resource缓存机制
- st.fragment优化组件渲染
- 大数据集分页显示和动态加载

### 测试策略
- 单元测试: Python函数和LangGraph集成验证
- 集成测试: Streamlit组件交互验证
- 端到端测试: 完整工作流验证

## 部署和维护

### 开发环境
- Streamlit本地开发服务器
- 自动热重载和实时调试
- .streamlit/config.toml 配置管理

## 成功指标

### 功能指标
- [ ] 完整工作流程可执行
- [ ] 所有图表类型正常渲染
- [ ] 错误处理机制完善
- [ ] 响应时间在可接受范围内

### 用户体验指标
- [ ] 界面直观易用
- [ ] 交互响应及时
- [ ] 错误信息友好
- [ ] 功能覆盖完整

### 技术指标
- [ ] 代码质量达标
- [ ] 测试覆盖率充分
- [ ] 性能指标合格
- [ ] 兼容性良好

## 文件结构

```
webui/
├── README.md                          # 本文档
├── tasks/                             # 详细任务分解 (简化为5个)
│   ├── task_01_basic_setup.md        # 基础搭建
│   ├── task_02_core_interface.md     # 核心界面
│   ├── task_03_feature_integration.md # 功能集成
│   ├── task_04_optimization.md       # 完善优化
│   └── task_05_testing_deployment.md # 测试部署
└── implementation/                    # 实际实现文件 (执行时创建)
   ├── pages/                          # Streamlit多页面
   │   ├── 1_💬_Chat.py              # 聊天界面
   │   ├── 2_📊_Analysis.py          # 分析结果
   │   └── 3_🔧_Settings.py          # 设置页面
   ├── components/                     # 自定义组件
   │   ├── chat_interface.py          # 聊天组件
   │   ├── workflow_display.py        # 工作流显示
   │   └── chart_renderer.py          # 图表渲染
   ├── utils/                          # 工具函数
   │   ├── langgraph_integration.py   # LangGraph集成
   │   └── session_manager.py         # 会话管理
   ├── .streamlit/                     # Streamlit配置
   │   ├── config.toml                # 应用配置
   │   └── secrets.toml               # 密钥配置
   ├── requirements.txt                # Python依赖
   ├── main.py                         # 主应用入口
   └── README.md                       # 实现说明
```

## 注意事项

### 开发规范
- 所有代码、函数名、变量名使用英文
- 仅代码注释使用中文
- 严格遵循Python类型提示和代码规范
- 遵循Streamlit最佳实践和性能优化

### 集成要求
- 直接使用Python环境，无需额外框架学习
- 集成现有的BigQuery工具和错误处理机制
- 保持与现有LangGraph工作流的完全兼容性
- 确保商业级代码质量，不使用演示数据

### 性能要求
- Streamlit应用启动时间 < 5秒
- 页面交互响应时间 < 1秒
- 支持100k+ token的数据流式处理
- Session State和缓存优化