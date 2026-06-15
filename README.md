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
| 🏷️ **LLM实体抽取** | 基于 DeepSeek/Ollama 的智能实体识别和分类 |
| 🔗 **LLM关系抽取** | 自动识别实体间的语义关系，支持预览确认 |
| 🎨 **图谱可视化** | 基于 D3.js 的交互式力导向图谱，支持拖拽/缩放/搜索/过滤 |
| 💬 **智能问答** | 自然语言查询知识图谱，聊天式交互界面 |
| 📊 **图谱分析** | 中心性分析、社区发现、度分布、路径查找 |
| 🎨 **多主题** | 深色/浅色/暖色/薄荷/紫罗兰 5 套主题，一键切换 |
| ⚙️ **配置管理** | LLM配置、图谱导入导出、实体/关系增删改查 |

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

启动后访问 http://localhost:8002

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| **后端** | FastAPI, SQLite, NetworkX |
| **LLM** | DeepSeek API, Ollama (本地) |
| **前端** | Vue 3 (CDN), D3.js, 原生 CSS |
| **文档解析** | pymupdf, python-docx, jieba |

## 📁 项目结构

```
knowledge_graph/
├── api.py              # FastAPI 路由（20+ API 端点）
├── main.py             # 启动入口
├── config.py           # 配置管理
├── database.py         # SQLite 数据库层
├── llm_client.py       # LLM 调用封装（DeepSeek + Ollama）
├── graph_algorithms.py # 图算法（中心性/社区发现/PageRank）
├── graph_store.py      # 图谱存储（NetworkX 内存图）
├── document_parser.py  # 文档解析器
├── entity_extractor.py # 实体抽取（规则 + jieba）
├── relation_extractor.py # 关系抽取（模式匹配 + 共现分析）
├── models.py           # 数据模型
├── templates/
│   └── index.html      # 前端 SPA（Vue3 + D3.js）
├── static/
│   └── css/style.css   # 全局样式 + 主题系统
├── data/               # SQLite 数据库 + 上传文件
└── docs/               # 项目文档 + UI 原型图
```

## 🖥️ 页面说明

| 页面 | 功能 |
|------|------|
| **图谱** | D3.js 力导向可视化，节点拖拽/悬停高亮/点击详情/展开邻居/搜索过滤 |
| **导入** | 文本粘贴 → LLM 分析 → 预览确认 → 导入图谱；文件上传；手动添加 |
| **查询** | 聊天式自然语言问答，查询历史 |
| **分析** | 统计仪表盘、实体/关系分布图、中心性 Top10、社区检测 |
| **设置** | LLM 配置（DeepSeek/Ollama）、图谱导入导出、实体/关系管理 |

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

## 📝 开发日志

- [x] 文档解析器（PDF/Word/Markdown/TXT）
- [x] 实体抽取引擎（LLM + 规则双模式）
- [x] 关系抽取引擎（LLM + 模式匹配 + 共现分析）
- [x] 图谱存储（SQLite + NetworkX）
- [x] D3.js 交互式图谱可视化
- [x] 自然语言问答（LLM 驱动）
- [x] 图谱分析（中心性/社区发现/PageRank）
- [x] 多主题系统（5套主题）
- [x] 完整 Web 管理界面
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
