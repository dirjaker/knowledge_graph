"""
知识图谱系统 - API路由

完整的REST API，包含：
- 文档导入（文本/文件）
- 实体CRUD
- 关系CRUD
- 图谱数据
- 智能查询
- 图算法分析
- 配置管理
"""

import json
import os
import uuid
import threading
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db
from llm_client import llm_client
from config import get_config, update_config, get_llm_config
from graph_algorithms import GraphAlgorithms

# ============================================================
# 初始化
# ============================================================

app = FastAPI(title="知识图谱系统", version="2.0.0")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost,http://127.0.0.1").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件
BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# 图算法（基于数据库）
graph_algorithms = None


def _get_algorithms():
    """延迟初始化图算法"""
    global graph_algorithms
    if graph_algorithms is None:
        # 需要一个GraphStore实例，这里用简单方式
        from graph_store import GraphStore
        store = GraphStore(str(BASE_DIR / "data" / "graph.db"))
        graph_algorithms = GraphAlgorithms(store)
    return graph_algorithms


# ============================================================
# 请求模型
# ============================================================

class TextIngestRequest(BaseModel):
    text: str
    title: str = "text_input"


class EntityRequest(BaseModel):
    name: str
    entity_type: str = "other"
    description: str = ""
    properties: dict = {}
    confidence: float = 1.0


class EntityUpdateRequest(BaseModel):
    entity_type: Optional[str] = None
    description: Optional[str] = None
    properties: Optional[dict] = None
    aliases: Optional[list] = None
    confidence: Optional[float] = None


class RelationRequest(BaseModel):
    source: str
    target: str
    relation_type: str = "related_to"
    evidence: str = ""
    weight: float = 1.0
    confidence: float = 1.0


class QueryRequest(BaseModel):
    question: str
    max_hops: int = 3
    top_k: int = 10


class PathRequest(BaseModel):
    source: str
    target: str
    max_depth: int = 5


class NeighborRequest(BaseModel):
    entity: str
    depth: int = 1


class LLMConfigRequest(BaseModel):
    provider: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class ConfirmImportRequest(BaseModel):
    task_id: str
    entities: list
    relations: list


# ============================================================
# 页面路由
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def index():
    """主页面"""
    html_path = BASE_DIR / "templates" / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>知识图谱系统</h1><p>templates/index.html 不存在</p>")


# ============================================================
# 文档导入 API
# ============================================================

@app.post("/api/documents/ingest-text")
async def ingest_text(request: TextIngestRequest):
    """文本导入 - 创建分析任务，后台异步抽取"""
    task_id = db.create_ingest_task("text", request.text)

    # 后台线程执行LLM抽取
    def _process():
        try:
            result = llm_client.extract_knowledge(request.text)
            if "error" in result:
                db.update_ingest_task(task_id, error=result["error"])
            else:
                db.update_ingest_task(
                    task_id,
                    status="completed",
                    entities=result.get("entities", []),
                    relations=result.get("relations", []),
                )
        except Exception as e:
            db.update_ingest_task(task_id, error=str(e))

    threading.Thread(target=_process, daemon=True).start()
    return {"task_id": task_id, "status": "processing"}


@app.post("/api/documents/ingest-confirm")
async def ingest_confirm(request: ConfirmImportRequest):
    """确认导入 - 将分析结果写入图谱"""
    imported_e = 0
    imported_r = 0

    for e in request.entities:
        db.add_entity(
            name=e.get("name", ""),
            entity_type=e.get("type", "other"),
            description=e.get("description", ""),
        )
        imported_e += 1

    for r in request.relations:
        db.add_relation(
            source=r.get("source", ""),
            target=r.get("target", ""),
            relation_type=r.get("type", "related_to"),
            evidence=r.get("evidence", ""),
        )
        imported_r += 1

    # 记录文档
    task = db.get_ingest_task(request.task_id)
    title = "文本导入"
    if task and task.get("input_text"):
        title = task["input_text"][:50]
    db.add_document(title=title, content="",
                    entity_count=imported_e, relation_count=imported_r)

    return {
        "imported_entities": imported_e,
        "imported_relations": imported_r,
    }


@app.get("/api/documents/task/{task_id}")
async def get_task(task_id: str):
    """获取导入任务状态"""
    task = db.get_ingest_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    return task


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """上传文件并分析"""
    # 保存文件
    from config import UPLOAD_DIR
    file_path = UPLOAD_DIR / file.filename
    content = await file.read()
    file_path.write_bytes(content)

    # 解析文本
    try:
        from document_parser import DocumentParser
        doc = DocumentParser.parse(str(file_path))
        text = doc.content
    except Exception as e:
        raise HTTPException(400, f"文件解析失败: {e}")

    # 创建任务
    task_id = db.create_ingest_task("file", text)

    def _process():
        try:
            result = llm_client.extract_knowledge(text)
            if "error" in result:
                db.update_ingest_task(task_id, error=result["error"])
            else:
                db.update_ingest_task(
                    task_id, status="completed",
                    entities=result.get("entities", []),
                    relations=result.get("relations", []),
                )
        except Exception as e:
            db.update_ingest_task(task_id, error=str(e))

    threading.Thread(target=_process, daemon=True).start()
    return {"task_id": task_id, "filename": file.filename, "status": "processing"}


# ============================================================
# 实体 API
# ============================================================

@app.get("/api/entities")
async def list_entities(
    keyword: str = "",
    entity_type: str = "",
    limit: int = 100,
    offset: int = 0,
):
    """列出/搜索实体"""
    return db.search_entities(keyword, entity_type, limit, offset)


@app.get("/api/entities/{name}")
async def get_entity(name: str):
    """获取实体详情"""
    entity = db.get_entity(name)
    if not entity:
        raise HTTPException(404, f"实体不存在: {name}")
    relations = db.get_relations(name)
    return {**entity, "relations": relations}


@app.post("/api/entities")
async def create_entity(request: EntityRequest):
    """创建实体"""
    entity_id = db.add_entity(
        name=request.name,
        entity_type=request.entity_type,
        description=request.description,
        properties=request.properties,
        confidence=request.confidence,
    )
    return {"id": entity_id, "name": request.name}


@app.put("/api/entities/{name}")
async def update_entity(name: str, request: EntityUpdateRequest):
    """更新实体"""
    entity = db.get_entity(name)
    if not entity:
        raise HTTPException(404, f"实体不存在: {name}")
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    db.update_entity(name, **updates)
    return {"status": "updated"}


@app.delete("/api/entities/{name}")
async def delete_entity(name: str):
    """删除实体"""
    if db.delete_entity(name):
        return {"status": "deleted"}
    raise HTTPException(404, f"实体不存在: {name}")


# ============================================================
# 关系 API
# ============================================================

@app.get("/api/relations")
async def list_relations(
    entity: str = "",
    relation_type: str = "",
    limit: int = 200,
):
    """列出关系"""
    return db.get_relations(entity, relation_type, limit)


@app.post("/api/relations")
async def create_relation(request: RelationRequest):
    """创建关系"""
    rel_id = db.add_relation(
        source=request.source,
        target=request.target,
        relation_type=request.relation_type,
        evidence=request.evidence,
        weight=request.weight,
        confidence=request.confidence,
    )
    return {"id": rel_id}


@app.delete("/api/relations/{rel_id}")
async def delete_relation(rel_id: str):
    """删除关系"""
    if db.delete_relation(rel_id):
        return {"status": "deleted"}
    raise HTTPException(404, f"关系不存在: {rel_id}")


# ============================================================
# 图谱数据 API
# ============================================================

@app.get("/api/graph/data")
async def get_graph_data(
    entity_types: str = "",
    relation_types: str = "",
    limit: int = 500,
):
    """获取图谱数据（节点+边）"""
    et = [t.strip() for t in entity_types.split(",") if t.strip()] if entity_types else None
    rt = [t.strip() for t in relation_types.split(",") if t.strip()] if relation_types else None
    return db.get_graph_data(et, rt, limit)


@app.get("/api/graph/search")
async def graph_search(q: str = ""):
    """搜索图谱节点"""
    if not q:
        return {"nodes": []}
    return {"nodes": db.search_entities(q, limit=20)}


@app.post("/api/graph/neighbors")
async def graph_neighbors(request: NeighborRequest):
    """获取节点邻居"""
    return db.get_entity_neighbors(request.entity, request.depth)


@app.post("/api/graph/path")
async def graph_path(request: PathRequest):
    """查找路径"""
    algorithms = _get_algorithms()
    result = algorithms.shortest_path(request.source, request.target)
    if result:
        return result
    return {"path": None, "message": "未找到路径"}


@app.get("/api/graph/export")
async def export_graph():
    """导出图谱"""
    return db.export_data()


@app.post("/api/graph/import")
async def import_graph(file: UploadFile = File(...)):
    """导入图谱"""
    content = await file.read()
    try:
        data = json.loads(content)
        return db.import_data(data)
    except json.JSONDecodeError:
        raise HTTPException(400, "无效的JSON文件")


@app.post("/api/graph/clear")
async def clear_graph():
    """清空图谱"""
    db.clear_all()
    global graph_algorithms
    graph_algorithms = None
    return {"status": "cleared"}


# ============================================================
# 智能查询 API
# ============================================================

@app.post("/api/query")
async def query_graph(request: QueryRequest):
    """自然语言查询"""
    # 获取相关上下文
    entities = db.search_entities(request.question, limit=20)
    context_parts = []

    for e in entities[:5]:
        relations = db.get_relations(e["name"])
        context_parts.append(f"实体: {e['name']} ({e['entity_type']}) - {e['description']}")
        for r in relations[:5]:
            context_parts.append(
                f"  {r['source']} --[{r['type']}]--> {r['target']}"
            )

    context = "\n".join(context_parts) if context_parts else "图谱中暂无相关数据"

    # 调用LLM回答
    try:
        answer = llm_client.answer_question(request.question, context)
    except Exception as e:
        answer = f"查询失败: {str(e)}"

    return {
        "answer": answer,
        "entities": entities[:10],
        "context_used": len(entities),
    }


# ============================================================
# 分析 API
# ============================================================

@app.get("/api/stats")
async def get_stats():
    """获取统计信息"""
    return db.get_stats()


@app.get("/api/algorithms/centrality")
async def get_centrality(method: str = "degree", top_k: int = 10):
    """中心性分析"""
    algorithms = _get_algorithms()
    if method == "degree":
        return algorithms.degree_centrality(top_k)
    elif method == "betweenness":
        return algorithms.betweenness_centrality(top_k)
    elif method == "closeness":
        return algorithms.closeness_centrality(top_k)
    elif method == "pagerank":
        return algorithms.pagerank(top_k)
    else:
        raise HTTPException(400, f"未知方法: {method}")


@app.get("/api/algorithms/communities")
async def detect_communities():
    """社区发现"""
    algorithms = _get_algorithms()
    return algorithms.detect_communities()


@app.get("/api/algorithms/important")
async def get_important_nodes(top_k: int = 10):
    """重要节点分析"""
    algorithms = _get_algorithms()
    return algorithms.get_important_nodes(top_k)


@app.get("/api/algorithms/stats")
async def get_algorithm_stats():
    """图算法统计"""
    algorithms = _get_algorithms()
    base_stats = db.get_stats()
    return {
        **base_stats,
        "density": algorithms.graph_density(),
        "components": len(algorithms.connected_components()),
        "degree_distribution": algorithms.degree_distribution(),
    }


# ============================================================
# 配置 API
# ============================================================

@app.get("/api/settings/llm")
async def get_llm_settings():
    """获取LLM配置"""
    cfg = get_llm_config()
    # 隐藏API Key
    if cfg.get("api_key"):
        key = cfg["api_key"]
        cfg["api_key_masked"] = key[:6] + "****" + key[-4:] if len(key) > 10 else "****"
    else:
        cfg["api_key_masked"] = ""
    return cfg


@app.put("/api/settings/llm")
async def update_llm_settings(request: LLMConfigRequest):
    """更新LLM配置"""
    updates = {}
    llm_cfg = {}
    for k, v in request.model_dump().items():
        if v is not None:
            llm_cfg[k] = v
    if llm_cfg:
        updates["llm"] = llm_cfg
    if updates:
        update_config(updates)
    return {"status": "updated"}


@app.post("/api/settings/llm/test")
async def test_llm_connection():
    """测试LLM连接"""
    return llm_client.test_connection()


@app.get("/api/settings/config")
async def get_full_config():
    """获取完整配置"""
    return get_config()


# ============================================================
# 数据库信息
# ============================================================

@app.get("/api/database/info")
async def get_database_info():
    """获取数据库信息"""
    from config import DB_PATH
    db_file = Path(DB_PATH)
    stats = db.get_stats()
    return {
        "path": str(db_file),
        "size_bytes": db_file.stat().st_size if db_file.exists() else 0,
        "size_human": _human_size(db_file.stat().st_size) if db_file.exists() else "0 B",
        **stats,
    }


def _human_size(size: int) -> str:
    """人类可读的文件大小"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


# ============================================================
# 健康检查
# ============================================================

@app.get("/api/health")
async def health():
    """健康检查"""
    from datetime import datetime
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
