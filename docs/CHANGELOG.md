# 更新日志

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

---

## [2.0.0] - 2026-06-21

### 🚀 重大升级

#### 新增
- **LLM 驱动的知识抽取**：集成 DeepSeek API 和 Ollama，支持从文本自动抽取实体和关系
- **LLM 智能问答**：`/api/query` 端点基于图谱上下文调用 LLM 生成自然语言回答
- **异步导入任务**：文档导入采用异步任务模式，避免 LLM 调用阻塞 API 响应
- **LLM 客户端模块** (`llm_client.py`)：统一封装 DeepSeek/Ollama 双后端调用
- **导入任务表** (`ingest_tasks`)：支持任务状态流转（processing → completed/failed）
- **确认导入端点** (`/api/documents/ingest-confirm`)：用户预览抽取结果后确认导入
- **数据库信息端点** (`/api/database/info`)：查看数据库路径、大小、统计
- **健康检查端点** (`/api/health`)
- **配置热更新**：通过 API 修改 LLM 配置后立即生效

#### 安全加固
- **路径穿越防护**：文件上传使用 `os.path.realpath` 校验，防止 `../../` 攻击
- **CORS 限制**：默认限制为本地访问，支持 `CORS_ORIGINS` 环境变量配置
- **API Key 脱敏**：`GET /api/settings/llm` 返回脱敏后的 API Key

#### 改进
- **API 版本升级**至 v2.0.0
- **Pydantic v2** 兼容：使用 `model_dump()` 替代 `dict()`
- **CORS 配置**：从硬编码 `["*"]` 改为环境变量可控
- **数据库层重构** (`database.py`)：新增 `updated_at` 字段、导入导出功能、WAL 模式
- **API 路由重构**：统一请求/响应模型，更清晰的模块划分
- **默认端口**：从 8002 改为 10001

#### 文档
- 新增 `REVIEW.md` 代码审查报告
- 新增 `docs/DEVELOPMENT.md` 开发指南
- 新增 `docs/CHANGELOG.md` 更新日志
- 更新 `README.md` 功能特性和 API 概览
- 更新 `docs/技术文档.md` 反映 v2.0 架构

---

## [1.0.0] - 2026-06-15

### 🎉 首个正式版本

#### 核心功能
- **文档解析器**：支持 PDF（pymupdf）、Word（python-docx）、Markdown、纯文本
- **实体抽取引擎**：四层策略（正则 → jieba → 关键词 → 词典），支持 8 种实体类型
- **关系抽取引擎**：模式匹配 + 共现分析，支持 11 种关系类型
- **图谱存储**：SQLite 持久化 + NetworkX 内存图双层架构
- **查询引擎**：正则意图识别，支持实体查询、关系查询、路径查询、邻居查询
- **图算法**：度中心性、介数中心性、接近中心性、PageRank、社区发现（Louvain）
- **D3.js 可视化**：力导向图谱，支持拖拽/缩放/搜索/过滤/点击详情
- **5 套主题系统**：深色/浅色/暖色/薄荷/紫罗兰，CSS 变量驱动
- **完整 Web 管理界面**：图谱/导入/查询/分析/设置 5 个页面
- **REST API**：20+ 端点，覆盖实体/关系/图谱/查询/分析/配置

#### 技术栈
- 后端：FastAPI, SQLite, NetworkX, jieba, Pydantic
- 前端：Vue 3 (CDN), D3.js, ECharts, 原生 CSS
- 文档解析：pymupdf, python-docx

---

## [未发布]

### 计划功能
- [ ] 增量更新（增量导入文档，不重复抽取已有实体）
- [ ] 多图谱管理（支持创建/切换多个知识图谱）
- [ ] 图谱导出（PDF/PNG/SVG 格式导出可视化结果）
- [ ] 向量相似度搜索（基于 embedding 的语义消歧）
- [ ] WebSocket 实时推送（导入进度实时通知）
- [ ] 用户认证（API Key / JWT）
- [ ] Docker 部署支持
- [ ] 单元测试覆盖
