# 开发指南

> 本文档面向开发者，介绍项目的开发环境搭建、代码规范、架构约定和贡献流程。

---

## 一、开发环境搭建

### 1.1 环境要求

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python | 3.11+ | 推荐 3.12 |
| conda | 任意 | 推荐用 conda 管理虚拟环境 |
| Ollama | 可选 | 本地 LLM 推理（替代 DeepSeek API） |

### 1.2 快速搭建

```bash
# 克隆仓库
git clone https://github.com/dirjaker/knowledge_graph.git
cd knowledge_graph

# 创建并激活虚拟环境
conda create -n knowledge_graph python=3.12 -y
conda activate knowledge_graph

# 安装依赖
pip install -r requirements.txt

# 可选：安装 PDF/Word 解析支持
pip install pymupdf python-docx

# 可选：安装社区发现算法
pip install python-louvain
```

### 1.3 依赖说明

**核心依赖**（requirements.txt）：

| 包 | 用途 |
|------|------|
| `fastapi` | Web 框架 |
| `uvicorn` | ASGI 服务器 |
| `httpx` | HTTP 客户端（调用 LLM API） |
| `pydantic` | 数据模型和验证 |
| `networkx` | 图数据结构和算法 |
| `jieba` | 中文分词和词性标注 |
| `python-multipart` | 文件上传支持 |

**可选依赖**：

| 包 | 用途 |
|------|------|
| `pymupdf` | PDF 文件解析 |
| `python-docx` | Word 文档解析 |
| `python-louvain` | Louvain 社区发现算法 |

### 1.4 启动项目

```bash
# 方式一：标准启动（推荐）
python main.py

# 方式二：直接运行 uvicorn
uvicorn api:app --host 0.0.0.0 --port 10001 --reload

# 方式三：启动独立管理面板
python src/web/app.py
```

启动后：
- 主界面：http://localhost:10001
- API 文档：http://localhost:10001/docs（Swagger UI）
- 管理面板：http://localhost:8002（独立入口）

---

## 二、配置管理

### 2.1 配置文件

系统使用 `data/config.json` 存储运行时配置，首次启动自动生成：

```json
{
  "llm": {
    "provider": "deepseek",
    "api_key": "",
    "model": "deepseek-chat",
    "base_url": "https://api.deepseek.com",
    "temperature": 0.3,
    "max_tokens": 4096
  },
  "server": {
    "host": "0.0.0.0",
    "port": 10001
  },
  "graph": {
    "max_nodes": 500,
    "max_edges": 1000,
    "default_layout": "force"
  }
}
```

**安全说明**：`data/config.json` 已加入 `.gitignore`，不会被提交到仓库。API Key 通过浏览器界面输入（设置 → LLM 模型设置），不硬编码在代码中。

### 2.2 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `CORS_ORIGINS` | CORS 允许的来源（逗号分隔） | `http://localhost,http://127.0.0.1` |

### 2.3 配置热更新

通过 API 修改配置后立即生效，无需重启：

```bash
# 更新 LLM 配置
curl -X PUT http://localhost:10001/api/settings/llm \
  -H "Content-Type: application/json" \
  -d '{"provider": "ollama", "model": "llama3"}'

# 测试 LLM 连接
curl -X POST http://localhost:10001/api/settings/llm/test
```

---

## 三、项目架构

### 3.1 模块职责

| 文件 | 职责 | 行数 |
|------|------|------|
| `main.py` | 启动入口 | 23 |
| `api.py` | FastAPI 路由定义，请求/响应模型，文档管理，配置管理 | 682 |
| `config.py` | 配置加载/保存/合并 | 101 |
| `database.py` | SQLite 数据库 CRUD + 统计 + 导入导出 + 级联删除 + 示例数据清除 | 663 |
| `llm_client.py` | LLM 调用封装（DeepSeek + Ollama，健壮 JSON 解析） | 292 |
| `models.py` | Pydantic 数据模型定义 | 146 |
| `entity_extractor.py` | 实体抽取（正则 + jieba + 关键词 + 词典） | 305 |
| `relation_extractor.py` | 关系抽取（模式匹配 + 共现分析） | 252 |
| `document_parser.py` | 文档解析（PDF/Word/MD/TXT） | 186 |
| `graph_store.py` | NetworkX 内存图 + SQLite 持久化 | 515 |
| `graph_algorithms.py` | 图分析算法 | 321 |
| `query_engine.py` | 正则意图识别查询引擎 | 293 |
| `templates/index.html` | 前端 SPA（Vue3 + D3.js Neon Glow 主题） | 1865 |
| `src/web/app.py` | 独立管理面板（备用入口） | 357 |

### 3.2 数据流

```
用户输入（文本/文件）
    │
    ▼
document_parser.py  → Document 对象
    │
    ▼
llm_client.py       → {"entities": [...], "relations": [...]}
    │                  （健壮 JSON 解析：三级提取 + 截断修复）
    │                  （或 entity_extractor.py + relation_extractor.py）
    ▼
database.py         → SQLite 持久化（关联 source_doc_ids）
    │
    ▼
api.py              → 返回给前端（支持 document_id 筛选）
```

### 3.3 双数据库层

项目存在两个数据库访问模块，注意区分：

| 模块 | 使用者 | 特点 |
|------|--------|------|
| `database.py` | `api.py`（主入口） | 返回 dict，有 `ingest_tasks` 表，支持异步任务，级联删除 |
| `graph_store.py` | `src/web/app.py` + `graph_algorithms.py` | 返回 Pydantic 模型，有 NetworkX 内存图 |

两者共享同一个 SQLite 文件 `data/graph.db`，Schema 基本一致（`database.py` 多了 `updated_at` 列和 `ingest_tasks` 表）。

### 3.4 LLM JSON 解析策略

`llm_client.py` 中实现了三级 JSON 提取 + 截断修复，确保 LLM 输出不稳定时仍能正确解析：

```
原始响应
    │
    ▼
第一级：正则提取 { ... } 或 [ ... ]
    │ (失败)
    ▼
第二级：提取 ```json ... ``` 代码块
    │ (失败)
    ▼
第三级：找第一个 { 到最后一个 }
    │
    ▼
修复阶段：_fix_json() + _fix_truncated_json()
    ├── 移除尾部多余逗号
    ├── 补全截断的字符串/数组/对象
    └── 修复缺失的逗号
```

---

## 四、代码规范

### 4.1 Python 风格

- 遵循 PEP 8
- 使用类型注解（Type Hints）
- 使用 Pydantic v2 模型做数据验证
- 字符串优先使用 f-string
- 使用 `pathlib.Path` 处理路径

### 4.2 命名约定

| 类型 | 约定 | 示例 |
|------|------|------|
| 模块文件 | snake_case | `entity_extractor.py` |
| 类名 | PascalCase | `EntityExtractor` |
| 函数/方法 | snake_case | `extract_entities` |
| 常量 | UPPER_SNAKE_CASE | `TECH_KEYWORDS` |
| 私有方法 | _前缀 | `_compile_patterns` |

### 4.3 文档字符串

每个模块、类、公共方法都需要 docstring：

```python
class EntityExtractor:
    """
    实体抽取器

    使用规则 + jieba 分词进行实体识别
    """

    def extract(self, text: str, doc_id: str = "") -> list[Entity]:
        """
        从文本中抽取实体

        参数:
            text: 输入文本
            doc_id: 文档 ID

        返回:
            实体列表
        """
```

### 4.4 错误处理

```python
# ✅ 好的做法：捕获具体异常
try:
    result = llm_client.extract_knowledge(text)
except httpx.TimeoutException:
    logger.error("LLM 调用超时")
except Exception as e:
    logger.error(f"LLM 调用失败: {e}")

# ❌ 避免：裸 except
try:
    ...
except:  # 会吞掉 KeyboardInterrupt 等
    pass
```

---

## 五、开发工作流

### 5.1 Git 分支

| 分支 | 用途 |
|------|------|
| `main` | 稳定版本 |
| `dev` | 开发分支 |
| `feature/*` | 功能分支 |
| `fix/*` | 修复分支 |

### 5.2 提交规范

```
<type>: <description>

type:
  feat:     新功能
  fix:      修复
  docs:     文档
  style:    格式
  refactor: 重构
  test:     测试
  chore:    构建/工具
```

示例：
```
feat: 添加 LLM 驱动的知识抽取
fix: 修复文件上传路径穿越漏洞
docs: 更新技术文档
```

### 5.3 添加新 API 端点

1. 在 `api.py` 中定义请求/响应模型（Pydantic）
2. 添加路由函数
3. 更新 `docs/技术文档.md` 和 `README.md`
4. 测试端点（使用 `/docs` Swagger UI）

```python
# 1. 定义模型
class MyRequest(BaseModel):
    name: str
    value: int = 0

# 2. 添加路由
@app.post("/api/my-endpoint")
async def my_endpoint(request: MyRequest):
    """端点说明"""
    return {"result": ...}
```

### 5.4 添加新图算法

1. 在 `graph_algorithms.py` 中添加方法
2. 在 `api.py` 中添加对应的 API 端点
3. 在前端 `templates/index.html` 中添加可视化

```python
# graph_algorithms.py
def my_algorithm(self, top_k: int = 10) -> list[dict]:
    """算法说明"""
    if self.graph.number_of_nodes() == 0:
        return []
    # 实现算法
    return [{"name": name, "score": score} for name, score in sorted_items]

# api.py
@app.get("/api/algorithms/my-algorithm")
async def get_my_algorithm(top_k: int = 10):
    algorithms = _get_algorithms()
    return algorithms.my_algorithm(top_k)
```

---

## 六、前端开发

### 6.1 技术栈

| 技术 | 引入方式 | 用途 |
|------|---------|------|
| Vue 3 | CDN | 响应式数据绑定和组件化 |
| D3.js | CDN | 力导向图谱可视化（Neon Glow 霓虹发光） |
| ECharts | CDN | 统计图表 |
| 原生 CSS | 本地文件 | 样式 + Neon Glow 主题变量 |

### 6.2 文件结构

```
templates/
  index.html          # 前端 SPA（所有 JS 内联，1865 行）
static/
  css/style.css       # 全局样式 + Neon Glow 主题变量
```

### 6.3 Neon Glow 主题系统

所有颜色通过 CSS 变量定义：

```css
:root {
    --bg-primary: #0b0d13;
    --bg-secondary: #12151c;
    --bg-card: #181b24;
    --text-primary: #d0d0d0;
    --text-secondary: #7a7f8a;
    --border-color: #1e2130;
    /* Neon Glow 色系 */
    --neon-blue: #4a9eff;
    --neon-green: #4aff8e;
    --neon-pink: #ff4a8d;
    --neon-orange: #ff8c4a;
    --neon-purple: #a855f7;
    --neon-cyan: #22d3ee;
    --neon-red: #ef4444;
    --neon-yellow: #facc15;
}
```

### 6.4 添加新主题

1. 在 `static/css/style.css` 中添加 `[data-theme="mytheme"]` 块
2. 在 `templates/index.html` 的主题切换逻辑中注册
3. 添加主题图标

---

## 七、测试

### 7.1 内置测试文档

项目在 `data/test_documents/` 下提供 4 篇行业分析文档，可用于功能测试：

| 文档 | 主题 | 实体数 | 关系数 |
|------|------|--------|--------|
| AI 产业全景报告.docx | 人工智能产业链 | ~60 | ~40 |
| 全球半导体产业链分析.docx | 半导体产业链 | ~50 | ~35 |
| 大模型技术发展报告.docx | 大语言模型技术 | ~45 | ~30 |
| 自动驾驶技术发展报告.docx | 自动驾驶技术 | ~95 | ~70 |

### 7.2 手动测试

```bash
# 启动服务
python main.py

# 测试健康检查
curl http://localhost:10001/api/health

# 测试文本导入
curl -X POST http://localhost:10001/api/documents/ingest-text \
  -H "Content-Type: application/json" \
  -d '{"text": "张三是阿里巴巴的CEO，他在杭州工作。"}'

# 测试查询
curl -X POST http://localhost:10001/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "张三是什么职位？"}'

# 测试图谱数据
curl http://localhost:10001/api/graph/data
```

### 7.3 API 文档

启动后访问 http://localhost:10001/docs 查看自动生成的 Swagger UI，可直接在页面上测试所有 API。

---

## 八、部署

### 8.1 开发环境

```bash
python main.py  # 默认端口 10001，启用热重载
```

### 8.2 生产环境

```bash
# 关闭热重载，限制绑定地址
uvicorn api:app --host 127.0.0.1 --port 10001 --workers 4

# 或使用 gunicorn
gunicorn api:app -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:10001
```

### 8.3 Docker（待实现）

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "10001"]
```

---

## 九、常见开发问题

### Q：修改配置后不生效？

A：`llm_client.py` 每次调用会重新加载配置（`_reload_config`），修改 `data/config.json` 后无需重启。但如果修改了 `config.py` 的代码，需要重启服务。

### Q：如何切换 LLM 后端？

A：通过 API 或直接修改 `data/config.json`：

```bash
# 切换到 Ollama
curl -X PUT http://localhost:10001/api/settings/llm \
  -H "Content-Type: application/json" \
  -d '{"provider": "ollama", "model": "llama3", "base_url": "http://localhost:11434"}'
```

### Q：数据库在哪里？

A：`data/graph.db`，SQLite 格式，可以用 `sqlite3` 命令行或 DB Browser 查看。

### Q：如何清空图谱数据？

A：
```bash
curl -X POST http://localhost:10001/api/graph/clear
```

### Q：两个入口（main.py 和 src/web/app.py）有什么区别？

A：都连接同一个数据库，但 `api.py` 使用 `database.py`（支持异步任务），`src/web/app.py` 使用 `graph_store.py`（支持 NetworkX 内存图）。建议使用 `main.py` 作为主入口。

### Q：LLM 返回的 JSON 解析失败怎么办？

A：`llm_client.py` 内置三级提取 + 截断修复，覆盖绝大多数 LLM 输出格式问题。如果仍失败，检查：
1. API Key 是否正确配置
2. 模型是否支持 JSON 输出
3. 文本是否过长导致截断（可调小 `max_tokens`）
