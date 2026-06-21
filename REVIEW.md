# 代码审查报告 — knowledge_graph

**审查日期**: 2026-06-21  
**审查范围**: 安全漏洞、代码质量、依赖安全、配置问题、架构问题  
**文件数量**: 18 个 Python 源文件

---

## 🔴 致命问题

### 🔴-1 文件上传路径穿越漏洞
- **文件**: `api.py` 第 221 行
- **描述**: `file_path = UPLOAD_DIR / file.filename` 直接使用用户上传的文件名拼接路径，攻击者可通过 `../../etc/cron.d/evil` 等路径写入任意位置。
- **修复建议**: 使用 `Path(file.filename).name` 取纯文件名，或使用 `werkzeug.utils.secure_filename()` 清洗文件名，同时校验文件扩展名白名单。

### 🔴-2 CORS 配置允许所有来源（多处）
- **文件**: `api.py` 第 38 行, `src/web/app.py` 第 31 行
- **描述**: 两个 FastAPI 应用均设置 `allow_origins=["*"]`，且无任何认证机制，所有图谱数据可被任意网页读取和修改。
- **修复建议**: 限制 CORS 来源，添加 API Key 或 JWT 认证。

### 🔴-3 无任何身份认证
- **文件**: `api.py` 全部路由, `src/web/app.py` 全部路由
- **描述**: 所有 API 端点（创建/删除实体、清空图谱、导入数据等）完全开放，任何人都可以修改或删除数据。
- **修复建议**: 至少添加 API Key 中间件或 Basic Auth，关键操作（删除、清空）需要额外确认。

### 🔴-4 API Key 泄露风险
- **文件**: `api.py` 第 507-514 行
- **描述**: `GET /api/settings/llm` 返回 API Key 的前6位和后4位（`key[:6] + "****" + key[-4:]`），对于短密钥可能泄露足够多的信息。且该接口无认证保护。
- **修复建议**: 完全隐藏 API Key，只返回是否已配置（`"configured": true/false`）。

### 🔴-5 LLM 提示注入风险
- **文件**: `api.py` 第 417-444 行
- **描述**: 用户输入的 `question` 直接传递给 LLM 进行查询，无任何输入清洗或长度限制，存在提示注入（Prompt Injection）攻击风险。
- **修复建议**: 限制输入长度，对用户输入进行基本清洗，LLM 响应不应直接执行任何操作。

### 🔴-6 生产环境开启热重载
- **文件**: `main.py` 第 19 行
- **描述**: `uvicorn.run("api:app", ..., reload=True)` 在生产环境使用热重载有安全和性能风险。
- **修复建议**: 仅在开发模式启用 `reload`。

---

## 🟡 警告问题

### 🟡-1 默认绑定 0.0.0.0
- **文件**: `config.py` 第 33 行
- **描述**: 默认服务器配置 `"host": "0.0.0.0"` 会暴露到所有网络接口。
- **修复建议**: 默认改为 `"127.0.0.1"`。

### 🟡-2 裸 except 捕获（多处）
- **文件**: `graph_algorithms.py` 第 117、159、240、289、294 行
- **描述**: 多处使用 `except:` 而非 `except Exception:` 或具体异常类型，会吞掉 `KeyboardInterrupt`、`SystemExit` 等不应被捕获的异常。
- **修复建议**: 所有 `except:` 改为 `except Exception:`，并记录日志。

### 🟡-3 两套并行的数据库层
- **文件**: `database.py` (578行) vs `graph_store.py` (515行)
- **描述**: 两个模块都实现了 SQLite 存储层，`database.py` 用于 `api.py`，`graph_store.py` 用于 `src/web/app.py`，导致 schema 不完全一致（`database.py` 有 `updated_at` 列，`graph_store.py` 没有），维护困难。
- **修复建议**: 统一为一个数据库模块，`api.py` 和 `src/web/app.py` 共用。

### 🟡-4 全局单例无线程安全保护
- **文件**: `database.py` 第 578 行: `db = Database()`
- **描述**: 全局 `db` 实例在多线程（FastAPI + 后台处理线程）中共享，`_conn()` 上下文管理器每次创建新连接但没有连接池或线程本地存储，并发写入可能冲突。
- **修复建议**: 使用 `threading.local()` 管理连接，或引入连接池。

### 🟡-5 配置文件存储 API Key 明文
- **文件**: `config.py` 第 26 行
- **描述**: API Key 以明文 JSON 存储在 `data/config.json`，文件权限未限制。
- **修复建议**: 文件权限设为 `0o600`，或支持环境变量覆盖（`LLM_API_KEY`）。

### 🟡-6 上传文件未做大小限制
- **文件**: `api.py` 第 216-223 行
- **描述**: `upload_document` 端点直接将整个文件读入内存并写入磁盘，无大小限制，可能被用于 DoS 攻击。
- **修复建议**: 添加文件大小限制（如 10MB），使用 FastAPI 的 `UploadFile` 配合流式读取。

### 🟡-7 Pydantic 模型使用可变默认值
- **文件**: `api.py` 第 75 行: `properties: dict = {}`
- **描述**: 虽然 Pydantic 会深拷贝默认值，但使用 `Field(default_factory=dict)` 是更明确的做法。
- **修复建议**: 改为 `properties: dict = Field(default_factory=dict)`。

### 🟡-8 后台线程异常仅记录到数据库
- **文件**: `api.py` 第 151-164 行
- **描述**: 后台 LLM 抽取线程中的异常仅写入数据库任务记录，不会出现在日志中，难以排查问题。
- **修复建议**: 在 `except` 块中添加 `logger.error(...)` 调用。

### 🟡-9 无输入长度限制
- **文件**: `api.py` 第 66-67 行 (`TextIngestRequest`), 第 96-99 行 (`QueryRequest`)
- **描述**: `text` 和 `question` 字段无长度限制，超长输入可能耗尽 LLM API 额度或导致内存问题。
- **修复建议**: 使用 `Field(max_length=50000)` 等约束。

---

## 🔵 建议

### 🔵-1 `graph_algorithms.py` 中 PageRank 异常处理
- **文件**: `graph_algorithms.py` 第 115-118 行
- **描述**: PageRank 计算失败时静默返回空列表，不记录失败原因。
- **修复建议**: 添加 `logger.warning("PageRank 计算失败", exc_info=True)`。

### 🔵-2 entity_extractor.py 中的重复代码
- **文件**: `entity_extractor.py` 第 148-176 行
- **描述**: `_extract_by_regex` 中所有 `pattern_name` 分支都返回 `EntityType.OTHER`，switch 逻辑冗余。
- **修复建议**: 简化为直接使用 `EntityType.OTHER`，无需条件分支。

### 🔵-3 `models.py` 中 Pydantic 模型可变默认值
- **文件**: `models.py` 第 61 行: `properties: dict = {}`, 第 66 行: `source_doc_ids: list[str] = []`
- **描述**: Pydantic 会处理，但使用 `Field(default_factory=...)` 更规范。
- **修复建议**: 使用 `Field(default_factory=dict)` 和 `Field(default_factory=list)`。

### 🔵-4 文档解析器缺少文件类型校验
- **文件**: `document_parser.py` 第 26-57 行
- **描述**: `parse()` 方法接受任意文件路径，未校验文件类型是否在白名单内。
- **修复建议**: 添加允许的扩展名白名单校验。

---

## 总结评分

| 维度 | 评分 (满分10) | 说明 |
|------|:---:|------|
| **安全** | 3/10 | 路径穿越、无认证、API Key 泄露、CORS 全开、提示注入风险 |
| **质量** | 6/10 | 代码功能完整，但裸 except 多处、异常处理不完善、缺少输入验证 |
| **架构** | 5/10 | 两套并行数据库层导致维护混乱，API 层重复，全局单例无并发保护 |
