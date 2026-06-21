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
| 🎨 **图谱可视化** | 基于 D3.js 的交互式力导向图谱，支持拖拽/缩放/搜索/过滤 |
| 💬 **智能问答** | LLM 驱动的自然语言查询，基于图谱上下文生成回答 |
| 📊 **图谱分析** | 中心性分析（度/介数/接近/PageRank）、社区发现、度分布 |
| 🎨 **多主题** | 深色/浅色/暖色/薄荷/紫罗兰 5 套主题，CSS 变量驱动 |
| ⚙️ **配置管理** | LLM 配置、图谱导入导出（JSON）、实体/关系增删改查 |
| 🔒 **安全防护** | 路径穿越防护、CORS 限制、文件大小控制 |

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
├── api.py                # FastAPI 路由（20+ API 端点）
├── config.py             # 配置管理（LLM/服务器/图谱参数）
├── config.yaml           # YAML 配置文件
├── database.py           # SQLite 数据库层（CRUD + 统计 + 导入导出）
├── llm_client.py         # LLM 调用封装（DeepSeek + Ollama 双模式）
├── graph_algorithms.py   # 图算法（中心性/社区发现/PageRank/路径）
├── graph_store.py        # 图谱存储（SQLite + NetworkX 内存图双层）
├── document_parser.py    # 文档解析器（PDF/Word/Markdown/TXT）
├── entity_extractor.py   # 实体抽取（正则 + jieba + 关键词 + 词典）
├── relation_extractor.py # 关系抽取（模式匹配 + 共现分析）
├── query_engine.py       # 查询引擎（正则意图识别 + 模糊搜索）
├── models.py             # Pydantic 数据模型
├── requirements.txt      # Python 依赖
├── templates/
│   └── index.html        # 前端 SPA（Vue3 + D3.js + ECharts）
├── static/
│   └── css/style.css     # 全局样式 + 5 套主题系统
├── assets/
│   └── banner.svg        # 项目 Banner
├── src/
│   ├── web/              # 独立 Web Dashboard（备用入口）
│   │   ├── app.py        # FastAPI 管理面板
│   │   └── static/
│   └── macos/            # macOS 桌面应用（py2app）
├── data/                 # SQLite 数据库 + 上传文件 + 配置
└── docs/                 # 项目文档 + UI 原型图
```

## 🖥️ 页面说明

| 页面 | 功能 |
|------|------|
| **图谱** | D3.js 力导向可视化，节点拖拽/悬停高亮/点击详情/展开邻居/搜索过滤 |
| **导入** | 文本粘贴 → LLM 异步分析 → 预览确认 → 导入图谱；文件上传；手动添加 |
| **查询** | 聊天式自然语言问答，LLM 基于图谱上下文生成回答 |
| **分析** | 统计仪表盘、实体/关系分布图、中心性 Top10、社区检测、度分布 |
| **设置** | LLM 配置（DeepSeek/Ollama）、图谱导入导出、实体/关系管理、数据库信息 |

## 🎨 主题系统

5 套预设主题，通过左下角图标一键切换：

| 主题 | 风格 |
|------|------|
| 深色 | 经典暗色，适合长时间使用 |
| 浅色 | 明亮清爽，适合白天环境 |
| 暖色 | 暖木色调，护眼舒适 |
| 薄荷 | 清新绿色调 |
| 紫罗兰 | 优雅紫色调 |

所有颜色通过 CSS 变量定义，无硬编码颜色值。

## 📡 API 概览

系统提供 20+ 个 REST API 端点，分为以下模块：

| 模块 | 端点 | 说明 |
|------|------|------|
| 文档导入 | `POST /api/documents/ingest-text` | 文本导入（异步 LLM 抽取） |
| | `POST /api/documents/upload` | 文件上传解析 |
| | `POST /api/documents/ingest-confirm` | 确认导入到图谱 |
| 实体 | `GET/POST/PUT/DELETE /api/entities` | 实体 CRUD |
| 关系 | `GET/POST/DELETE /api/relations` | 关系 CRUD |
| 图谱 | `GET /api/graph/data` | 获取图谱数据 |
| | `POST /api/graph/neighbors` | 获取节点邻居 |
| | `POST /api/graph/path` | 路径查找 |
| | `GET /api/graph/export` | 导出图谱（JSON） |
| | `POST /api/graph/import` | 导入图谱（JSON） |
| 查询 | `POST /api/query` | 自然语言查询 |
| 分析 | `GET /api/algorithms/centrality` | 中心性分析 |
| | `GET /api/algorithms/communities` | 社区发现 |
| 配置 | `GET/PUT /api/settings/llm` | LLM 配置管理 |

## 📝 开发日志

- [x] 文档解析器（PDF/Word/Markdown/TXT）
- [x] 实体抽取引擎（正则 + jieba + 关键词 + 词典四层策略）
- [x] 关系抽取引擎（模式匹配 + 共现分析）
- [x] 图谱存储（SQLite + NetworkX 双层架构）
- [x] D3.js 交互式图谱可视化
- [x] LLM 驱动的知识抽取（DeepSeek + Ollama）
- [x] LLM 驱动的自然语言问答
- [x] 图谱分析（中心性/社区发现/PageRank/度分布）
- [x] 多主题系统（5 套 CSS 变量主题）
- [x] 完整 Web 管理界面（5 个页面）
- [x] 异步导入任务处理
- [x] 安全加固（路径穿越防护/CORS 限制）
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
