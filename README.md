<div align="center">

<img src="assets/banner.svg" width="100%" alt="知识图谱系统">

<br>

### 🕸️ 知识图谱系统

[![Stars](https://img.shields.io/github/stars/dirjaker/knowledge_graph?style=flat-square&label=Stars&color=FFD700)](https://github.com/dirjaker/knowledge_graph/stargazers)
[![Forks](https://img.shields.io/github/forks/dirjaker/knowledge_graph?style=flat-square&label=Forks&color=4A90D9)](https://github.com/dirjaker/knowledge_graph/network/members)
[![Contributors](https://img.shields.io/github/contributors/dirjaker/knowledge_graph?style=flat-square&label=Contributors&color=8B4513)](https://github.com/dirjaker/knowledge_graph/graphs/contributors)
[![License](https://img.shields.io/github/license/dirjaker/knowledge_graph?style=flat-square&label=License&color=20B2AA)](https://github.com/dirjaker/knowledge_graph/blob/dev/LICENSE)

</div>

---

## ✨ 功能特性

| 功能 | 描述 |
|------|------|
| 📄 **文档导入** | 文本粘贴、文件上传（PDF/Word/Markdown/TXT）、手动添加 |
| 🤖 **LLM 实体抽取** | 基于 DeepSeek / Ollama 的智能实体识别，支持异步任务处理 |
| 🔗 **LLM 关系抽取** | 自动识别实体间的语义关系，预览确认后导入图谱 |
| 📂 **多文档管理** | 上传、查看、删除文档；删除时级联清理关联实体和关系 |
| 🔍 **按文档筛选** | 左侧面板多选文档，实时过滤显示关联实体和关系 |
| 🌐 **全局视图** | 一键切换全局视图，显示所有文档的实体和关系 |
| 🎨 **图谱可视化** | D3.js 力导向图谱，Neon Glow 深色科技感主题，霓虹发光节点，浅灰网格背景 |
| 💬 **智能问答** | LLM 驱动的自然语言查询，基于图谱上下文生成回答 |
| 📊 **图谱分析** | 中心性分析（度/介数/接近/PageRank）、社区发现、度分布 |
| 🎨 **Neon Glow 主题** | 霓虹发光科技感 UI，8 种霓虹色节点，SVG glow filter |
| ⚙️ **配置管理** | LLM 配置（API Key 界面输入，config.json 存储，gitignore 防泄漏）、图谱导入导出 |
| 🔒 **安全防护** | 路径穿越防护、CORS 限制、文件大小控制、API Key 脱敏 |
| 🧪 **测试文档集** | 内置 4 篇行业分析文档（AI 产业、半导体、大模型、自动驾驶），开箱即用 |

## 🚀 快速开始

```bash
# 克隆项目
git clone https://github.com/dirjaker/knowledge_graph.git
cd knowledge_graph

# 创建虚拟环境
conda create -n knowledge_graph python=3.12 -y
conda activate knowledge_graph

# 安装依赖
pip install -r requirements.txt

# 运行项目
python main.py
```

启动后访问 http://localhost:10001

API 文档自动生成于 http://localhost:10001/docs

### 配置 LLM

1. 点击左下角 **⚙️ 设置** → **LLM 模型设置**
2. 输入 API Key（支持 DeepSeek / Ollama）
3. 点击保存，配置存储在 `data/config.json`（已加入 `.gitignore`）

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| **后端** | FastAPI, SQLite, NetworkX |
| **LLM** | DeepSeek API, Ollama（本地部署） |
| **前端** | Vue 3 (CDN), D3.js, ECharts, 原生 CSS |
| **文档解析** | pymupdf (PDF), python-docx (Word), jieba (分词) |
| **HTTP 客户端** | httpx |

## 📁 项目结构

```
knowledge_graph/
├── main.py               # 启动入口
├── api.py                # FastAPI 路由（25+ API 端点）
├── config.py             # 配置管理（LLM/服务器/图谱参数）
├── config.yaml           # YAML 配置文件
├── database.py           # SQLite 数据库层（CRUD + 统计 + 导入导出 + 级联删除）
├── llm_client.py         # LLM 调用封装（DeepSeek + Ollama 双模式，健壮 JSON 解析）
├── graph_algorithms.py   # 图算法（中心性/社区发现/PageRank/路径）
├── graph_store.py        # 图谱存储（SQLite + NetworkX 内存图双层）
├── document_parser.py    # 文档解析器（PDF/Word/Markdown/TXT）
├── entity_extractor.py   # 实体抽取（正则 + jieba + 关键词 + 词典）
├── relation_extractor.py # 关系抽取（模式匹配 + 共现分析）
├── query_engine.py       # 查询引擎（正则意图识别 + 模糊搜索）
├── models.py             # Pydantic 数据模型
├── requirements.txt      # Python 依赖
├── .gitignore            # 忽略 data/config.json 等敏感文件
├── templates/
│   └── index.html        # 前端 SPA（Vue3 + D3.js Neon Glow 主题）
├── static/
│   └── css/style.css     # 全局样式 + Neon Glow 主题变量
├── assets/
│   └── banner.svg        # 项目 Banner
├── data/
│   ├── test_documents/   # 4 篇内置测试文档（.docx）
│   ├── config.json       # 运行时配置（gitignore）
│   └── graph.db          # SQLite 数据库（gitignore）
├── src/
│   ├── web/              # 独立 Web Dashboard（备用入口）
│   │   ├── app.py        # FastAPI 管理面板
│   │   └── static/
│   └── macos/            # macOS 桌面应用（py2app）
└── docs/                 # 项目文档 + UI 原型图
```

## 🖥️ 页面说明

| 页面 | 功能 |
|------|------|
| **图谱** | D3.js 力导向可视化，Neon Glow 霓虹发光节点，浅灰网格背景，节点拖拽/悬停高亮/点击详情弹窗/展开邻居/搜索过滤 |
| **文档管理** | 左侧面板多选文档筛选，上传/删除文档（级联清理），全局视图切换 |
| **导入** | 文本粘贴 → LLM 异步分析 → 预览确认 → 导入图谱；文件上传；手动添加 |
| **查询** | 聊天式自然语言问答，LLM 基于图谱上下文生成回答 |
| **分析** | 统计仪表盘、实体/关系分布图、中心性 Top10、社区检测、度分布 |
| **设置** | LLM 配置（DeepSeek/Ollama）、图谱导入导出、实体/关系管理、数据库信息 |

## 🎨 Neon Glow 主题系统

Neon Glow 深色科技感主题，专为知识图谱可视化设计：

| 特性 | 说明 |
|------|------|
| **背景** | 深色 (#0b0d13) + 浅灰十字网格 (40px 间距) |
| **节点** | 8 种霓虹色（蓝/绿/粉/橙/紫/青/红/黄），SVG glow 滤镜发光 |
| **文字** | 半透明白色标签，跟随节点霓虹色 |
| **边** | 渐变色连线，半透明样式 |
| **控件** | 毛玻璃背景，霓虹边框，布局选择器在顶部信息栏，缩放控件在左下角 |
| **弹窗** | 居中详情面板，半透明遮罩，不遮挡图谱 |

## 📡 API 概览

系统提供 25+ 个 REST API 端点，分为以下模块：

| 模块 | 端点 | 说明 |
|------|------|------|
| 文档导入 | `POST /api/documents/ingest-text` | 文本导入（异步 LLM 抽取） |
| | `POST /api/documents/upload` | 文件上传解析 |
| | `POST /api/documents/ingest-confirm` | 确认导入到图谱 |
| | `DELETE /api/documents/{id}` | 删除文档（级联清理实体/关系） |
| 实体 | `GET/POST/PUT/DELETE /api/entities` | 实体 CRUD（支持 `document_id` 筛选） |
| 关系 | `GET/POST/DELETE /api/relations` | 关系 CRUD（支持 `document_id` 筛选） |
| 图谱 | `GET /api/graph/data` | 获取图谱数据 |
| | `POST /api/graph/neighbors` | 获取节点邻居 |
| | `POST /api/graph/path` | 路径查找 |
| | `GET /api/graph/export` | 导出图谱（JSON） |
| | `POST /api/graph/import` | 导入图谱（JSON） |
| 查询 | `POST /api/query` | 自然语言查询 |
| 分析 | `GET /api/algorithms/centrality` | 中心性分析 |
| | `GET /api/algorithms/communities` | 社区发现 |
| 配置 | `GET/PUT /api/settings/llm` | LLM 配置管理（API Key 脱敏） |

## 📝 开发日志

- [x] 文档解析器（PDF/Word/Markdown/TXT）
- [x] 实体抽取引擎（正则 + jieba + 关键词 + 词典四层策略）
- [x] 关系抽取引擎（模式匹配 + 共现分析）
- [x] 图谱存储（SQLite + NetworkX 双层架构）
- [x] D3.js 交互式图谱可视化
- [x] LLM 驱动的知识抽取（DeepSeek + Ollama）
- [x] LLM 驱动的自然语言问答
- [x] 图谱分析（中心性/社区发现/PageRank/度分布）
- [x] Neon Glow 深色科技感主题（霓虹发光 + 浅灰网格）
- [x] 完整 Web 管理界面（6 个页面）
- [x] 异步导入任务处理
- [x] 安全加固（路径穿越防护/CORS 限制/API Key 脱敏）
- [x] 多文档管理（上传/删除/级联清理/按文档筛选）
- [x] LLM JSON 解析健壮性优化（三级提取 + 截断修复 + 格式纠正）
- [x] 内置测试文档集（AI 产业/半导体/大模型/自动驾驶）
- [ ] 增量更新
- [ ] 多图谱管理
- [ ] 图谱导出（PDF/PNG）

## 📄 许可证

[MIT License](LICENSE)

---

<div align="center">

🔗 **GitHub**: [dirjaker/knowledge_graph](https://github.com/dirjaker/knowledge_graph)

⭐ 如果这个项目对你有帮助，请给一个 Star 支持一下！

</div>
