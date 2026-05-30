"""
知识图谱 - FastAPI 服务 + Web UI
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from models import (
    Entity, EntityType,
    Relation, RelationType,
    Document, DocumentType,
    QueryRequest, QueryResponse,
    GraphStats, PathRequest,
)
from graph_store import GraphStore
from query_engine import QueryEngine
from graph_algorithms import GraphAlgorithms
from document_parser import DocumentParser
from entity_extractor import EntityExtractor
from relation_extractor import RelationExtractor


# ============================================================
# 初始化
# ============================================================

app = FastAPI(title="知识图谱系统", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 核心组件
store = GraphStore("data/graph.db")
query_engine = QueryEngine(store)
algorithms = GraphAlgorithms(store)
parser = DocumentParser()
entity_extractor = EntityExtractor()
relation_extractor = RelationExtractor()


# ============================================================
# 请求模型
# ============================================================

class TextIngestRequest(BaseModel):
    """文本导入请求"""
    text: str
    title: str = "text_input"


class EntityRequest(BaseModel):
    """实体请求"""
    name: str
    entity_type: str = "other"
    description: str = ""
    properties: dict = {}


class RelationRequest(BaseModel):
    """关系请求"""
    source: str
    target: str
    relation_type: str = "related_to"
    evidence: str = ""
    weight: float = 1.0


# ============================================================
# API 路由
# ============================================================

@app.get("/api/health")
async def health():
    """健康检查"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


# ==================== 文档操作 ====================

@app.post("/api/documents/ingest")
async def ingest_text(request: TextIngestRequest):
    """
    导入文本，自动抽取实体和关系

    流程: 文本 → 分句 → 实体抽取 → 关系抽取 → 存储
    """
    # 解析文本
    doc = parser.parse_text(request.text, request.title)
    doc.id = str(uuid.uuid4())

    # 抽取实体
    entities = entity_extractor.extract(request.text, doc.id)

    # 抽取关系
    relations = relation_extractor.extract(request.text, entities, doc.id)

    # 存储实体
    for entity in entities:
        store.add_entity(entity)

    # 存储关系
    for relation in relations:
        store.add_relation(relation)

    # 更新文档统计
    doc.entity_count = len(entities)
    doc.relation_count = len(relations)

    return {
        "document_id": doc.id,
        "title": doc.title,
        "entities_extracted": len(entities),
        "relations_extracted": len(relations),
        "entities": [e.name for e in entities[:20]],
        "relations": [
            f"{r.source_entity} → {r.relation_type.value} → {r.target_entity}"
            for r in relations[:20]
        ],
    }


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    上传文档并解析

    支持: txt, md, pdf, docx
    """
    # 保存文件
    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / file.filename
    content = await file.read()
    file_path.write_bytes(content)

    # 解析文档
    try:
        doc = parser.parse(str(file_path))
        doc.id = str(uuid.uuid4())

        # 抽取实体和关系
        entities = entity_extractor.extract(doc.content, doc.id)
        relations = relation_extractor.extract(doc.content, entities, doc.id)

        # 存储
        for entity in entities:
            store.add_entity(entity)
        for relation in relations:
            store.add_relation(relation)

        doc.entity_count = len(entities)
        doc.relation_count = len(relations)

        return {
            "document_id": doc.id,
            "title": doc.title,
            "entities_extracted": len(entities),
            "relations_extracted": len(relations),
        }
    except Exception as e:
        raise HTTPException(400, f"解析文档失败: {str(e)}")


# ==================== 实体操作 ====================

@app.get("/api/entities")
async def list_entities(
    entity_type: Optional[str] = None,
    limit: int = 100,
):
    """列出实体"""
    etype = EntityType(entity_type) if entity_type else None
    entities = store.list_entities(entity_type=etype, limit=limit)
    return [e.model_dump() for e in entities]


@app.get("/api/entities/search")
async def search_entities(q: str, limit: int = 20):
    """搜索实体"""
    entities = store.search_entities(q, limit=limit)
    return [e.model_dump() for e in entities]


@app.get("/api/entities/{name}")
async def get_entity(name: str):
    """获取实体详情"""
    entity = store.get_entity(name)
    if not entity:
        raise HTTPException(404, f"实体不存在: {name}")

    # 获取关系
    relations = store.get_relations(name, direction="both")

    return {
        **entity.model_dump(),
        "relations": [r.model_dump() for r in relations],
    }


@app.post("/api/entities")
async def create_entity(request: EntityRequest):
    """创建实体"""
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
    """删除实体"""
    store.delete_entity(name)
    return {"status": "deleted"}


# ==================== 关系操作 ====================

@app.get("/api/relations")
async def list_relations(limit: int = 100):
    """列出关系"""
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
    """创建关系"""
    relation = Relation(
        source_entity=request.source,
        target_entity=request.target,
        relation_type=RelationType(request.relation_type),
        evidence=request.evidence,
        weight=request.weight,
    )
    rel_id = store.add_relation(relation)
    return {"id": rel_id}


# ==================== 图谱查询 ====================

@app.post("/api/query")
async def query_graph(request: QueryRequest):
    """自然语言查询"""
    response = query_engine.query(request)
    return response.model_dump()


@app.get("/api/graph/neighbors/{name}")
async def get_neighbors(name: str, depth: int = 1):
    """获取实体的邻居"""
    result = store.get_neighbors(name, depth=depth)
    return result


@app.post("/api/graph/path")
async def find_path(request: PathRequest):
    """查找路径"""
    path = store.find_path(request.source, request.target, request.max_depth)
    if path:
        return {"path": path, "length": len(path) - 1}
    return {"path": None, "message": "未找到路径"}


# ==================== 图算法 ====================

@app.get("/api/algorithms/centrality")
async def get_centrality(
    method: str = "degree",
    top_k: int = 10,
):
    """中心性分析"""
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
    """社区发现"""
    return algorithms.detect_communities()


@app.get("/api/algorithms/important")
async def get_important_nodes(top_k: int = 10):
    """重要节点分析"""
    return algorithms.get_important_nodes(top_k)


@app.get("/api/algorithms/stats")
async def get_graph_stats():
    """图统计"""
    stats = store.get_stats()
    return {
        **stats.model_dump(),
        "density": algorithms.graph_density(),
        "components": len(algorithms.connected_components()),
        "degree_distribution": algorithms.degree_distribution(),
    }


# ==================== 统计 ====================

@app.get("/api/stats")
async def get_stats():
    """获取统计信息"""
    return store.get_stats().model_dump()


@app.post("/api/clear")
async def clear_graph():
    """清空图谱"""
    store.clear()
    return {"status": "cleared"}


# ==================== 示例数据 ====================

@app.post("/api/demo/load")
async def load_demo_data():
    """加载示例数据"""
    demo_text = """
    张三是阿里巴巴的CEO，他在杭州工作。阿里巴巴是一家中国科技公司，总部位于杭州。
    李四是腾讯的副总裁，他在深圳工作。腾讯是中国最大的互联网公司之一。
    王五是北京大学的教授，他研究人工智能和机器学习。北京大学位于北京。
    赵六创立了字节跳动，字节跳动开发了抖音和今日头条。字节跳动总部位于北京。
    孙七在华为工作，华为是一家全球领先的通信技术公司，总部位于深圳。
    华为使用5G技术和人工智能技术。阿里巴巴使用云计算和大数据技术。
    腾讯使用微信和QQ平台。字节跳动使用推荐算法技术。
    张三和李四是大学同学。王五和赵六在同一个学术会议上认识。
    """

    # 抽取实体和关系
    entities = entity_extractor.extract(demo_text, "demo")
    relations = relation_extractor.extract(demo_text, entities, "demo")

    # 存储
    for entity in entities:
        store.add_entity(entity)
    for relation in relations:
        store.add_relation(relation)

    return {
        "entities_loaded": len(entities),
        "relations_loaded": len(relations),
        "entities": [e.name for e in entities],
    }


# ==================== Web UI ====================

@app.get("/", response_class=HTMLResponse)
async def web_ui():
    """Web 可视化界面"""
    return WEB_UI_HTML


# ============================================================
# Web UI HTML
# ============================================================

WEB_UI_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>知识图谱系统</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
:root {
  --bg: #0f0f0f; --surface: #1a1a1a; --border: #2a2a2a;
  --text: #e0e0e0; --text2: #888; --accent: #4a9eff;
  --green: #4caf50; --red: #f44336; --yellow: #ffc107;
}
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       background: var(--bg); color: var(--text); height: 100vh; display: flex; }

.sidebar { width: 300px; background: var(--surface); border-right: 1px solid var(--border);
           display: flex; flex-direction: column; }
.sidebar-header { padding: 16px; border-bottom: 1px solid var(--border); }
.sidebar-header h2 { font-size: 18px; color: var(--accent); margin-bottom: 12px; }
.btn { padding: 8px 16px; border: none; border-radius: 6px; cursor: pointer;
       font-size: 13px; transition: opacity 0.2s; }
.btn-primary { background: var(--accent); color: #fff; }
.btn-success { background: var(--green); color: #fff; }
.btn:hover { opacity: 0.9; }
.btn-block { width: 100%; }
.btn-sm { padding: 4px 8px; font-size: 12px; }
.input { width: 100%; padding: 8px 12px; background: var(--bg); border: 1px solid var(--border);
         border-radius: 6px; color: var(--text); font-size: 13px; }
textarea.input { min-height: 80px; resize: vertical; }

.tabs { display: flex; border-bottom: 1px solid var(--border); }
.tab { flex: 1; padding: 10px; text-align: center; cursor: pointer; font-size: 12px;
       border-bottom: 2px solid transparent; }
.tab.active { border-color: var(--accent); color: var(--accent); }
.tab-content { display: none; flex: 1; overflow-y: auto; padding: 12px; }
.tab-content.active { display: block; }

.entity-list { list-style: none; }
.entity-item { padding: 8px 10px; border-radius: 6px; cursor: pointer; margin-bottom: 4px;
               font-size: 13px; display: flex; align-items: center; gap: 8px; }
.entity-item:hover { background: var(--border); }
.entity-badge { padding: 2px 6px; border-radius: 4px; font-size: 10px; }
.badge-person { background: #e91e63; color: #fff; }
.badge-organization { background: #2196f3; color: #fff; }
.badge-location { background: #4caf50; color: #fff; }
.badge-technology { background: #ff9800; color: #fff; }
.badge-concept { background: #9c27b0; color: #fff; }
.badge-other { background: #607d8b; color: #fff; }

.main { flex: 1; display: flex; flex-direction: column; }
.toolbar { padding: 12px 20px; border-bottom: 1px solid var(--border);
           display: flex; align-items: center; gap: 12px; }
.graph-container { flex: 1; position: relative; }
canvas { width: 100%; height: 100%; }

.query-panel { position: absolute; bottom: 20px; left: 20px; right: 20px;
               background: var(--surface); border: 1px solid var(--border);
               border-radius: 8px; padding: 16px; max-height: 300px; overflow-y: auto; }
.query-input { display: flex; gap: 8px; margin-bottom: 12px; }
.query-input input { flex: 1; }
.query-result { font-size: 13px; line-height: 1.6; }

.stats-panel { position: absolute; top: 10px; right: 10px; background: var(--surface);
               border: 1px solid var(--border); border-radius: 8px; padding: 12px;
               font-size: 12px; min-width: 150px; }
.stat-item { padding: 4px 0; display: flex; justify-content: space-between; }
.stat-value { color: var(--accent); font-weight: bold; }

.detail-panel { position: absolute; top: 10px; right: 10px; background: var(--surface);
                border: 1px solid var(--border); border-radius: 8px; padding: 16px;
                width: 300px; max-height: 80vh; overflow-y: auto; display: none; }
.detail-panel.visible { display: block; }
.detail-header { font-size: 16px; font-weight: bold; margin-bottom: 12px; color: var(--accent); }
.detail-section { margin-bottom: 12px; }
.detail-section h4 { font-size: 12px; color: var(--text2); margin-bottom: 4px; }
</style>
</head>
<body>

<div class="sidebar">
  <div class="sidebar-header">
    <h2>🧠 知识图谱系统</h2>
    <div style="display:flex; gap:8px;">
      <button class="btn btn-primary btn-sm" onclick="loadDemo()">加载示例</button>
      <button class="btn btn-sm" onclick="clearGraph()" style="background:var(--red);color:#fff;">清空</button>
    </div>
  </div>

  <div class="tabs">
    <div class="tab active" data-tab="entities">实体</div>
    <div class="tab" data-tab="ingest">导入</div>
    <div class="tab" data-tab="analysis">分析</div>
  </div>

  <div id="tab-entities" class="tab-content active">
    <input class="input" placeholder="搜索实体..." id="entity-search"
           oninput="searchEntities(this.value)">
    <ul class="entity-list" id="entity-list"></ul>
  </div>

  <div id="tab-ingest" class="tab-content">
    <textarea class="input" id="ingest-text" placeholder="输入文本，自动抽取实体和关系..."></textarea>
    <input class="input" id="ingest-title" placeholder="标题（可选）" style="margin:8px 0;">
    <button class="btn btn-primary btn-block" onclick="ingestText()">抽取并导入</button>
    <div id="ingest-result" style="margin-top:12px; font-size:12px;"></div>
  </div>

  <div id="tab-analysis" class="tab-content">
    <button class="btn btn-primary btn-block" onclick="analyzeCentrality('degree')" style="margin-bottom:8px;">
      度中心性分析
    </button>
    <button class="btn btn-primary btn-block" onclick="analyzeCentrality('betweenness')" style="margin-bottom:8px;">
      介数中心性分析
    </button>
    <button class="btn btn-primary btn-block" onclick="analyzeCommunities()" style="margin-bottom:8px;">
      社区发现
    </button>
    <button class="btn btn-primary btn-block" onclick="analyzeImportant()" style="margin-bottom:8px;">
      重要节点分析
    </button>
    <div id="analysis-result" style="margin-top:12px; font-size:12px;"></div>
  </div>

  <div style="padding:12px; border-top:1px solid var(--border); font-size:11px; color:var(--text2);">
    <div id="stats-info">加载中...</div>
  </div>
</div>

<div class="main">
  <div class="toolbar">
    <span style="font-weight:bold;">图谱可视化</span>
    <span style="flex:1"></span>
    <button class="btn btn-sm" onclick="refreshGraph()">刷新</button>
  </div>

  <div class="graph-container">
    <canvas id="canvas"></canvas>

    <div class="stats-panel" id="stats-panel">
      <div class="stat-item"><span>实体</span><span class="stat-value" id="stat-entities">0</span></div>
      <div class="stat-item"><span>关系</span><span class="stat-value" id="stat-relations">0</span></div>
      <div class="stat-item"><span>密度</span><span class="stat-value" id="stat-density">0</span></div>
    </div>

    <div class="detail-panel" id="detail-panel">
      <div class="detail-header" id="detail-name"></div>
      <div id="detail-content"></div>
      <button class="btn btn-sm" onclick="closeDetail()" style="margin-top:8px;">关闭</button>
    </div>

    <div class="query-panel">
      <div class="query-input">
        <input class="input" id="query-input" placeholder="输入问题，如：张三和李四什么关系？"
               onkeypress="if(event.key==='Enter')sendQuery()">
        <button class="btn btn-primary" onclick="sendQuery()">查询</button>
      </div>
      <div class="query-result" id="query-result"></div>
    </div>
  </div>
</div>

<script>
const API = '';
let nodes = [];
let edges = [];
let selectedNode = null;
let draggingNode = null;
let dragOffset = { x: 0, y: 0 };
let graphData = { nodes: [], edges: [] };

const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');

const typeColors = {
  person: '#e91e63', organization: '#2196f3', location: '#4caf50',
  technology: '#ff9800', concept: '#9c27b0', event: '#00bcd4',
  product: '#795548', other: '#607d8b'
};

// 初始化
async function init() {
  resizeCanvas();
  setupTabs();
  await loadEntities();
  await loadStats();
  await loadGraph();
  draw();
}

function resizeCanvas() {
  const container = document.querySelector('.graph-container');
  canvas.width = container.clientWidth;
  canvas.height = container.clientHeight;
}

function setupTabs() {
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      tab.classList.add('active');
      document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
    });
  });
}

async function loadEntities() {
  const res = await fetch(API + '/api/entities?limit=200');
  const data = await res.json();
  renderEntityList(data);
}

function renderEntityList(entities) {
  const el = document.getElementById('entity-list');
  el.innerHTML = entities.map(e => `
    <li class="entity-item" onclick="selectEntity('${e.name}')">
      <span class="entity-badge badge-${e.entity_type}">${e.entity_type}</span>
      <span>${e.name}</span>
    </li>
  `).join('');
}

async function searchEntities(q) {
  if (!q) { await loadEntities(); return; }
  const res = await fetch(API + '/api/entities/search?q=' + encodeURIComponent(q));
  const data = await res.json();
  renderEntityList(data);
}

async function loadStats() {
  const res = await fetch(API + '/api/stats');
  const data = await res.json();
  document.getElementById('stat-entities').textContent = data.entity_count;
  document.getElementById('stat-relations').textContent = data.relation_count;
  document.getElementById('stats-info').textContent =
    `实体: ${data.entity_count} | 关系: ${data.relation_count}`;
}

async function loadGraph() {
  const res = await fetch(API + '/api/entities?limit=200');
  const entities = await res.json();
  const res2 = await fetch(API + '/api/relations?limit=200');
  const relations = await res2.json();

  // 构建图数据
  nodes = entities.map((e, i) => ({
    id: e.name, type: e.entity_type, x: 0, y: 0, vx: 0, vy: 0
  }));

  edges = relations.map(r => ({
    source: r.source, target: r.target, type: r.type
  }));

  // 初始化位置
  const cx = canvas.width / 2, cy = canvas.height / 2;
  nodes.forEach((n, i) => {
    const angle = (2 * Math.PI * i) / nodes.length;
    const r = Math.min(canvas.width, canvas.height) * 0.3;
    n.x = cx + r * Math.cos(angle);
    n.y = cy + r * Math.sin(angle);
  });
}

function draw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // 绘制边
  edges.forEach(edge => {
    const source = nodes.find(n => n.id === edge.source);
    const target = nodes.find(n => n.id === edge.target);
    if (!source || !target) return;

    ctx.strokeStyle = '#333';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(source.x, source.y);
    ctx.lineTo(target.x, target.y);
    ctx.stroke();

    // 箭头
    const angle = Math.atan2(target.y - source.y, target.x - source.x);
    const mx = (source.x + target.x) / 2;
    const my = (source.y + target.y) / 2;
    ctx.fillStyle = '#555';
    ctx.beginPath();
    ctx.moveTo(mx + 6 * Math.cos(angle), my + 6 * Math.sin(angle));
    ctx.lineTo(mx - 6 * Math.cos(angle - 0.5), my - 6 * Math.sin(angle - 0.5));
    ctx.lineTo(mx - 6 * Math.cos(angle + 0.5), my - 6 * Math.sin(angle + 0.5));
    ctx.fill();
  });

  // 绘制节点
  nodes.forEach(node => {
    const color = typeColors[node.type] || '#607d8b';
    const r = node === selectedNode ? 12 : 8;

    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
    ctx.fill();

    if (node === selectedNode) {
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    // 标签
    ctx.fillStyle = '#ccc';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(node.id, node.x, node.y + 20);
  });

  requestAnimationFrame(draw);
}

// 力导向布局
function forceLayout() {
  const k = 0.01;  // 弹簧系数
  const repulsion = 5000;

  // 斥力
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const dx = nodes[j].x - nodes[i].x;
      const dy = nodes[j].y - nodes[i].y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const force = repulsion / (dist * dist);
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      nodes[i].vx -= fx;
      nodes[i].vy -= fy;
      nodes[j].vx += fx;
      nodes[j].vy += fy;
    }
  }

  // 引力
  edges.forEach(edge => {
    const source = nodes.find(n => n.id === edge.source);
    const target = nodes.find(n => n.id === edge.target);
    if (!source || !target) return;

    const dx = target.x - source.x;
    const dy = target.y - source.y;
    const dist = Math.sqrt(dx * dx + dy * dy) || 1;
    const force = k * dist;
    const fx = (dx / dist) * force;
    const fy = (dy / dist) * force;
    source.vx += fx;
    source.vy += fy;
    target.vx -= fx;
    target.vy -= fy;
  });

  // 中心引力
  const cx = canvas.width / 2, cy = canvas.height / 2;
  nodes.forEach(node => {
    node.vx += (cx - node.x) * 0.001;
    node.vy += (cy - node.y) * 0.001;
  });

  // 更新位置
  nodes.forEach(node => {
    if (node === draggingNode) return;
    node.vx *= 0.9;  // 阻尼
    node.vy *= 0.9;
    node.x += node.vx;
    node.y += node.vy;

    // 边界检查
    node.x = Math.max(20, Math.min(canvas.width - 20, node.x));
    node.y = Math.max(20, Math.min(canvas.height - 20, node.y));
  });
}

setInterval(forceLayout, 50);

// 交互
canvas.addEventListener('mousedown', e => {
  const rect = canvas.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;

  selectedNode = null;
  for (const node of nodes) {
    const dx = x - node.x;
    const dy = y - node.y;
    if (dx * dx + dy * dy < 100) {
      selectedNode = node;
      draggingNode = node;
      dragOffset = { x: dx, y: dy };
      break;
    }
  }

  if (selectedNode) {
    showDetail(selectedNode.id);
  }
});

canvas.addEventListener('mousemove', e => {
  if (!draggingNode) return;
  const rect = canvas.getBoundingClientRect();
  draggingNode.x = e.clientX - rect.left - dragOffset.x;
  draggingNode.y = e.clientY - rect.top - dragOffset.y;
  draggingNode.vx = 0;
  draggingNode.vy = 0;
});

canvas.addEventListener('mouseup', () => { draggingNode = null; });

window.addEventListener('resize', () => { resizeCanvas(); });

async function selectEntity(name) {
  selectedNode = nodes.find(n => n.id === name);
  if (selectedNode) {
    showDetail(name);
    // 加载邻居
    const res = await fetch(API + '/api/graph/neighbors/' + encodeURIComponent(name));
    const data = await res.json();
    // 添加新节点
    data.nodes.forEach(n => {
      if (!nodes.find(nn => nn.id === n.name)) {
        nodes.push({
          id: n.name, type: n.entity_type,
          x: selectedNode.x + (Math.random() - 0.5) * 100,
          y: selectedNode.y + (Math.random() - 0.5) * 100,
          vx: 0, vy: 0
        });
      }
    });
    data.edges.forEach(e => {
      if (!edges.find(ee => ee.source === e.source && ee.target === e.target)) {
        edges.push(e);
      }
    });
  }
}

async function showDetail(name) {
  const res = await fetch(API + '/api/entities/' + encodeURIComponent(name));
  const data = await res.json();

  const panel = document.getElementById('detail-panel');
  const content = document.getElementById('detail-content');

  document.getElementById('detail-name').textContent = data.name;
  content.innerHTML = `
    <div class="detail-section">
      <h4>类型</h4>
      <span class="entity-badge badge-${data.entity_type}">${data.entity_type}</span>
    </div>
    ${data.description ? `<div class="detail-section"><h4>描述</h4><p>${data.description}</p></div>` : ''}
    <div class="detail-section">
      <h4>关系 (${data.relations?.length || 0})</h4>
      ${(data.relations || []).slice(0, 10).map(r =>
        `<div style="font-size:12px;padding:2px 0;">
          ${r.source_entity} → ${r.relation_type} → ${r.target_entity}
        </div>`
      ).join('')}
    </div>
  `;

  panel.classList.add('visible');
}

function closeDetail() {
  document.getElementById('detail-panel').classList.remove('visible');
}

// 查询
async function sendQuery() {
  const input = document.getElementById('query-input');
  const question = input.value.trim();
  if (!question) return;

  const res = await fetch(API + '/api/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question })
  });
  const data = await res.json();

  document.getElementById('query-result').innerHTML =
    data.answer.replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
}

// 导入文本
async function ingestText() {
  const text = document.getElementById('ingest-text').value;
  const title = document.getElementById('ingest-title').value || 'text_input';
  if (!text) return;

  const res = await fetch(API + '/api/documents/ingest', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, title })
  });
  const data = await res.json();

  document.getElementById('ingest-result').innerHTML = `
    <div style="color:var(--green);">✅ 抽取完成</div>
    <div>实体: ${data.entities_extracted} 个</div>
    <div>关系: ${data.relations_extracted} 个</div>
    <div style="margin-top:8px;">实体: ${data.entities.join(', ')}</div>
  `;

  await loadEntities();
  await loadStats();
  await loadGraph();
}

// 分析
async function analyzeCentrality(method) {
  const res = await fetch(API + '/api/algorithms/centrality?method=' + method + '&top_k=10');
  const data = await res.json();

  document.getElementById('analysis-result').innerHTML = `
    <div style="color:var(--accent);margin-bottom:8px;">${method} 中心性 Top 10</div>
    ${data.results.map((r, i) =>
      `<div>${i+1}. ${r.name}: ${r.centrality || r.score}</div>`
    ).join('')}
  `;
}

async function analyzeCommunities() {
  const res = await fetch(API + '/api/algorithms/communities');
  const data = await res.json();

  document.getElementById('analysis-result').innerHTML = `
    <div style="color:var(--accent);margin-bottom:8px;">
      社区发现 (${data.community_count} 个社区, 模块度: ${data.modularity})
    </div>
    ${data.communities.map((c, i) =>
      `<div style="margin-bottom:4px;">社区 ${i+1} (${c.size}个): ${c.nodes.join(', ')}</div>`
    ).join('')}
  `;
}

async function analyzeImportant() {
  const res = await fetch(API + '/api/algorithms/important?top_k=10');
  const data = await res.json();

  document.getElementById('analysis-result').innerHTML = `
    <div style="color:var(--accent);margin-bottom:8px;">重要节点 Top 10</div>
    ${data.map((r, i) =>
      `<div>${i+1}. ${r.name} (综合: ${r.score})</div>`
    ).join('')}
  `;
}

// 其他
async function loadDemo() {
  await fetch(API + '/api/demo/load', { method: 'POST' });
  await loadEntities();
  await loadStats();
  await loadGraph();
}

async function clearGraph() {
  if (!confirm('确定清空图谱？')) return;
  await fetch(API + '/api/clear', { method: 'POST' });
  nodes = [];
  edges = [];
  await loadEntities();
  await loadStats();
}

async function refreshGraph() {
  await loadGraph();
}

window.addEventListener('resize', resizeCanvas);
init();
</script>
</body>
</html>"""


# ============================================================
# 启动函数
# ============================================================

def run_server(host: str = "0.0.0.0", port: int = 8002):
    """启动服务"""
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_server()
