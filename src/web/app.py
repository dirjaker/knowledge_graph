"""
知识图谱 - Web Dashboard 管理界面
FastAPI 服务，提供图谱管理的 REST API 和可视化面板

注意: 知识图谱的核心 API 已在 api.py 中实现。
本模块提供独立的管理 Dashboard 层。
"""

import sys
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

# 确保项目根目录在 sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ============================================================
# 初始化
# ============================================================

app = FastAPI(title="知识图谱管理面板", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 尝试导入核心组件
try:
    from graph_store import GraphStore
    from query_engine import QueryEngine
    from graph_algorithms import GraphAlgorithms
    from models import Entity, EntityType, Relation, RelationType, QueryRequest

    store = GraphStore("data/graph.db")
    query_engine = QueryEngine(store)
    algorithms = GraphAlgorithms(store)
    HAS_CORE = True
except ImportError as e:
    HAS_CORE = False
    _import_error = str(e)


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


class RelationRequest(BaseModel):
    source: str
    target: str
    relation_type: str = "related_to"
    evidence: str = ""
    weight: float = 1.0


class QueryInput(BaseModel):
    question: str
    max_hops: int = 3
    top_k: int = 10


class PathInput(BaseModel):
    source: str
    target: str
    max_depth: int = 5


# ============================================================
# API 路由
# ============================================================

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "has_core": HAS_CORE,
        "timestamp": datetime.now().isoformat(),
    }


# ---- 统计 ----

@app.get("/api/stats")
async def get_stats():
    """获取图谱统计"""
    if not HAS_CORE:
        return {"error": "核心模块未加载", "detail": _import_error}
    stats = store.get_stats()
    return {
        **stats.model_dump(),
        "density": algorithms.graph_density(),
        "components": len(algorithms.connected_components()),
    }


# ---- 实体 ----

@app.get("/api/entities")
async def list_entities(entity_type: Optional[str] = None, limit: int = 100):
    if not HAS_CORE:
        return []
    etype = EntityType(entity_type) if entity_type else None
    entities = store.list_entities(entity_type=etype, limit=limit)
    return [e.model_dump() for e in entities]


@app.get("/api/entities/search")
async def search_entities(q: str, limit: int = 20):
    if not HAS_CORE:
        return []
    entities = store.search_entities(q, limit=limit)
    return [e.model_dump() for e in entities]


@app.post("/api/entities")
async def create_entity(request: EntityRequest):
    if not HAS_CORE:
        raise HTTPException(500, "核心模块未加载")
    entity = Entity(
        name=request.name,
        entity_type=EntityType(request.entity_type),
        description=request.description,
        properties=request.properties,
    )
    entity_id = store.add_entity(entity)
    return {"id": entity_id, "name": entity.name}


@app.delete("/api/entities/{name}")
async def delete_entity(name: str):
    if not HAS_CORE:
        raise HTTPException(500, "核心模块未加载")
    store.delete_entity(name)
    return {"status": "deleted"}


# ---- 关系 ----

@app.get("/api/relations")
async def list_relations(limit: int = 100):
    if not HAS_CORE:
        return []
    with store._get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM relations ORDER BY weight DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "source": row["source_entity"],
            "target": row["target_entity"],
            "type": row["relation_type"],
            "weight": row["weight"],
            "evidence": row["evidence"],
        }
        for row in rows
    ]


@app.post("/api/relations")
async def create_relation(request: RelationRequest):
    if not HAS_CORE:
        raise HTTPException(500, "核心模块未加载")
    relation = Relation(
        source_entity=request.source,
        target_entity=request.target,
        relation_type=RelationType(request.relation_type),
        evidence=request.evidence,
        weight=request.weight,
    )
    rel_id = store.add_relation(relation)
    return {"id": rel_id}


# ---- 查询 ----

@app.post("/api/query")
async def query_graph(request: QueryInput):
    if not HAS_CORE:
        raise HTTPException(500, "核心模块未加载")
    qr = QueryRequest(question=request.question, max_hops=request.max_hops, top_k=request.top_k)
    response = query_engine.query(qr)
    return response.model_dump()


@app.get("/api/graph/neighbors/{name}")
async def get_neighbors(name: str, depth: int = 1):
    if not HAS_CORE:
        raise HTTPException(500, "核心模块未加载")
    return store.get_neighbors(name, depth=depth)


@app.post("/api/graph/path")
async def find_path(request: PathInput):
    if not HAS_CORE:
        raise HTTPException(500, "核心模块未加载")
    path = store.find_path(request.source, request.target, request.max_depth)
    if path:
        return {"path": path, "length": len(path) - 1}
    return {"path": None, "message": "未找到路径"}


# ---- 图算法 ----

@app.get("/api/algorithms/centrality")
async def get_centrality(method: str = "degree", top_k: int = 10):
    if not HAS_CORE:
        raise HTTPException(500, "核心模块未加载")
    if method == "degree":
        result = algorithms.degree_centrality(top_k)
    elif method == "betweenness":
        result = algorithms.betweenness_centrality(top_k)
    elif method == "closeness":
        result = algorithms.closeness_centrality(top_k)
    elif method == "pagerank":
        result = algorithms.pagerank(top_k)
    else:
        raise HTTPException(400, f"未知方法: {method}")
    return {"method": method, "results": result}


@app.get("/api/algorithms/communities")
async def detect_communities():
    if not HAS_CORE:
        raise HTTPException(500, "核心模块未加载")
    return algorithms.detect_communities()


@app.get("/api/algorithms/important")
async def get_important_nodes(top_k: int = 10):
    if not HAS_CORE:
        raise HTTPException(500, "核心模块未加载")
    return algorithms.get_important_nodes(top_k)


# ---- 文档导入 ----

@app.post("/api/documents/ingest")
async def ingest_text(request: TextIngestRequest):
    if not HAS_CORE:
        raise HTTPException(500, "核心模块未加载")
    import uuid
    from document_parser import DocumentParser
    from entity_extractor import EntityExtractor
    from relation_extractor import RelationExtractor

    parser = DocumentParser()
    entity_ext = EntityExtractor()
    relation_ext = RelationExtractor()

    doc = parser.parse_text(request.text, request.title)
    doc.id = str(uuid.uuid4())

    entities = entity_ext.extract(request.text, doc.id)
    relations = relation_ext.extract(request.text, entities, doc.id)

    for entity in entities:
        store.add_entity(entity)
    for relation in relations:
        store.add_relation(relation)

    return {
        "document_id": doc.id,
        "entities_extracted": len(entities),
        "relations_extracted": len(relations),
    }


@app.post("/api/demo/load")
async def load_demo_data():
    """加载示例数据"""
    if not HAS_CORE:
        raise HTTPException(500, "核心模块未加载")
    import uuid
    from entity_extractor import EntityExtractor
    from relation_extractor import RelationExtractor

    entity_ext = EntityExtractor()
    relation_ext = RelationExtractor()

    demo_text = """
    张三是阿里巴巴的CEO，他在杭州工作。阿里巴巴是一家中国科技公司，总部位于杭州。
    李四是腾讯的副总裁，他在深圳工作。腾讯是中国最大的互联网公司之一。
    王五是北京大学的教授，他研究人工智能和机器学习。北京大学位于北京。
    赵六创立了字节跳动，字节跳动开发了抖音和今日头条。字节跳动总部位于北京。
    """

    entities = entity_ext.extract(demo_text, "demo")
    relations = relation_ext.extract(demo_text, entities, "demo")

    for entity in entities:
        store.add_entity(entity)
    for relation in relations:
        store.add_relation(relation)

    return {
        "entities_loaded": len(entities),
        "relations_loaded": len(relations),
    }


@app.post("/api/clear")
async def clear_graph():
    if not HAS_CORE:
        raise HTTPException(500, "核心模块未加载")
    store.clear()
    return {"status": "cleared"}


# ============================================================
# Web UI
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def web_ui():
    html_path = Path(__file__).parent / "static" / "index.html"
    return html_path.read_text(encoding="utf-8")


# ============================================================
# 启动入口
# ============================================================

def run_server(host: str = "0.0.0.0", port: int = 8002):
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_server()
