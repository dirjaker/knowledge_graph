# 🧠 知识图谱系统

从文档自动构建知识图谱，支持可视化探索和自然语言问答。

## ✨ 特性

- 📄 **文档解析** — 支持 PDF、Markdown、Word、纯文本
- 🔍 **实体抽取** — 规则匹配 + jieba 分词 + 关键词识别
- 🔗 **关系抽取** — 模式匹配 + 共现分析
- 📊 **图谱存储** — SQLite + networkx（可升级 Neo4j）
- 💬 **自然语言问答** — 实体查询、关系查询、路径查询
- 🎨 **图谱可视化** — 力导向图，可拖拽、缩放、点击
- 📈 **图算法** — 中心性分析、社区发现、PageRank
- 🌐 **Web UI** — 内嵌可视化界面

## 🚀 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动服务
python api.py

# 3. 访问 Web UI
# http://localhost:8002

# 4. 加载示例数据
# 点击 "加载示例" 按钮
```

## 📖 API 文档

### 文档操作

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/documents/ingest` | POST | 导入文本，自动抽取实体和关系 |
| `/api/documents/upload` | POST | 上传文档并解析 |

### 实体操作

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/entities` | GET | 列出实体 |
| `/api/entities/search?q=xxx` | GET | 搜索实体 |
| `/api/entities/{name}` | GET | 获取实体详情 |
| `/api/entities` | POST | 创建实体 |
| `/api/entities/{name}` | DELETE | 删除实体 |

### 关系操作

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/relations` | GET | 列出关系 |
| `/api/relations` | POST | 创建关系 |

### 图谱查询

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/query` | POST | 自然语言查询 |
| `/api/graph/neighbors/{name}` | GET | 获取邻居节点 |
| `/api/graph/path` | POST | 查找路径 |

### 图算法

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/algorithms/centrality?method=degree` | GET | 中心性分析 |
| `/api/algorithms/communities` | GET | 社区发现 |
| `/api/algorithms/important` | GET | 重要节点分析 |
| `/api/algorithms/stats` | GET | 图统计 |

## 🎯 使用示例

### 1. 导入文本

```bash
curl -X POST http://localhost:8002/api/documents/ingest \
  -H "Content-Type: application/json" \
  -d '{"text": "张三是阿里巴巴的CEO，他在杭州工作。阿里巴巴是一家中国科技公司。"}'
```

### 2. 自然语言查询

```bash
# 查询实体信息
curl -X POST http://localhost:8002/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "张三是什么职位？"}'

# 查询关系
curl -X POST http://localhost:8002/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "张三和阿里巴巴什么关系？"}'

# 路径查询
curl -X POST http://localhost:8002/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "张三和李四之间有什么联系？"}'
```

### 3. 图算法分析

```bash
# 度中心性分析
curl http://localhost:8002/api/algorithms/centrality?method=degree&top_k=10

# 社区发现
curl http://localhost:8002/api/algorithms/communities

# 重要节点
curl http://localhost:8002/api/algorithms/important?top_k=10
```

## 🏗️ 架构

```
┌─────────────────────────────────────────────────────────┐
│                      用户界面层                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ 图谱可视化    │  │ 自然语言问答  │  │ 文档管理     │  │
│  │ (Canvas)     │  │ (Chat UI)    │  │ (上传/搜索)  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│                    API 服务层 (FastAPI)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ 图谱 CRUD    │  │ 问答引擎     │  │ 文档解析     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│                    核心引擎层                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ 实体抽取      │  │ 关系抽取     │  │ 图谱推理     │  │
│  │ (NER)        │  │ (RE)         │  │ (多跳推理)   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ 实体消歧      │  │ 关系分类     │  │ 图算法       │  │
│  │ (链接预测)    │  │ (分类器)     │  │ (中心性/社区)│  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│                    存储层                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ SQLite       │  │ networkx     │  │ 文件存储     │  │
│  │ (持久化)      │  │ (内存图)     │  │ (文档)       │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## 📁 项目结构

```
knowledge_graph/
├── models.py              # 数据模型（实体、关系、文档）
├── document_parser.py     # 文档解析（PDF/Word/MD）
├── entity_extractor.py    # 实体抽取（规则 + jieba）
├── relation_extractor.py  # 关系抽取（模式 + 共现）
├── graph_store.py         # 图谱存储（SQLite + networkx）
├── query_engine.py        # 查询引擎（自然语言问答）
├── graph_algorithms.py    # 图算法（中心性、社区、PageRank）
├── api.py                 # FastAPI 服务 + Web UI
├── config.yaml            # 配置文件
├── requirements.txt       # 依赖
└── README.md              # 文档
```

## 🧩 实体类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `person` | 人物 | 张三、李四 |
| `organization` | 组织 | 阿里巴巴、腾讯 |
| `location` | 地点 | 杭州、北京 |
| `technology` | 技术 | Python、机器学习 |
| `concept` | 概念 | 人工智能、深度学习 |
| `event` | 事件 | 会议、发布会 |
| `product` | 产品 | 微信、抖音 |

## 🔗 关系类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `works_at` | 工作于 | 张三 → 阿里巴巴 |
| `located_in` | 位于 | 阿里巴巴 → 杭州 |
| `ceo_of` | CEO | 张三 → 阿里巴巴 |
| `founded` | 创立 | 赵六 → 字节跳动 |
| `uses` | 使用 | 阿里巴巴 → 云计算 |
| `created` | 创造 | 字节跳动 → 抖音 |
| `related_to` | 相关 | 张三 → 李四 |

## 🔧 图算法

| 算法 | 说明 | API |
|------|------|-----|
| 度中心性 | 连接数最多的节点 | `/api/algorithms/centrality?method=degree` |
| 介数中心性 | 最重要的"桥梁"节点 | `/api/algorithms/centrality?method=betweenness` |
| 接近中心性 | 最"中心"的节点 | `/api/algorithms/centrality?method=closeness` |
| PageRank | 最重要的节点 | `/api/algorithms/centrality?method=pagerank` |
| 社区发现 | 图中的社区结构 | `/api/algorithms/communities` |

## 📊 技术栈

- **后端**: FastAPI + SQLite + networkx
- **NLP**: jieba (分词) + 正则表达式
- **图算法**: networkx
- **文档解析**: pymupdf + python-docx
- **可视化**: Canvas (原生 JavaScript)

## 📄 License

MIT
