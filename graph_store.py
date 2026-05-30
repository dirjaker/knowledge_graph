"""
图谱存储模块

使用 SQLite + networkx 实现轻量级图谱存储
（可选升级到 Neo4j）
"""

import json
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Optional

import networkx as nx

from models import (
    Entity, EntityType,
    Relation, RelationType,
    Document, GraphStats,
)


class GraphStore:
    """
    图谱存储

    使用 SQLite 持久化 + networkx 内存图
    """

    def __init__(self, db_path: str = "data/graph.db"):
        """
        初始化存储

        参数:
            db_path: SQLite 数据库路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 内存中的图
        self.graph = nx.DiGraph()

        # 初始化数据库
        self._init_db()

        # 从数据库加载图到内存
        self._load_graph()

    @contextmanager
    def _get_conn(self):
        """获取数据库连接"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self):
        """初始化数据库表"""
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS entities (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    entity_type TEXT DEFAULT 'other',
                    properties TEXT DEFAULT '{}',
                    aliases TEXT DEFAULT '[]',
                    description TEXT DEFAULT '',
                    confidence REAL DEFAULT 1.0,
                    source_doc_ids TEXT DEFAULT '[]',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS relations (
                    id TEXT PRIMARY KEY,
                    source_entity TEXT NOT NULL,
                    target_entity TEXT NOT NULL,
                    relation_type TEXT DEFAULT 'related_to',
                    properties TEXT DEFAULT '{}',
                    weight REAL DEFAULT 1.0,
                    confidence REAL DEFAULT 1.0,
                    evidence TEXT DEFAULT '',
                    source_doc_ids TEXT DEFAULT '[]',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(source_entity, target_entity, relation_type)
                );

                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT,
                    doc_type TEXT DEFAULT 'text',
                    file_path TEXT DEFAULT '',
                    entity_count INTEGER DEFAULT 0,
                    relation_count INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
                CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
                CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source_entity);
                CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target_entity);
                CREATE INDEX IF NOT EXISTS idx_relations_type ON relations(relation_type);
            """)

    def _load_graph(self):
        """从数据库加载图到内存"""
        # 加载实体
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM entities").fetchall()
            for row in rows:
                self.graph.add_node(
                    row["name"],
                    entity_type=row["entity_type"],
                    properties=json.loads(row["properties"]),
                    confidence=row["confidence"],
                )

            # 加载关系
            rows = conn.execute("SELECT * FROM relations").fetchall()
            for row in rows:
                self.graph.add_edge(
                    row["source_entity"],
                    row["target_entity"],
                    relation_type=row["relation_type"],
                    weight=row["weight"],
                    confidence=row["confidence"],
                    evidence=row["evidence"],
                )

    # ==================== 实体操作 ====================

    def add_entity(self, entity: Entity) -> str:
        """
        添加实体

        如果已存在同名实体，更新属性
        """
        entity_id = entity.id or f"entity_{entity.name}"

        with self._get_conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO entities
                (id, name, entity_type, properties, aliases, description,
                 confidence, source_doc_ids)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entity_id,
                entity.name,
                entity.entity_type.value,
                json.dumps(entity.properties, ensure_ascii=False),
                json.dumps(entity.aliases, ensure_ascii=False),
                entity.description,
                entity.confidence,
                json.dumps(entity.source_doc_ids, ensure_ascii=False),
            ))

        # 更新内存图
        self.graph.add_node(
            entity.name,
            entity_type=entity.entity_type.value,
            properties=entity.properties,
            confidence=entity.confidence,
        )

        return entity_id

    def get_entity(self, name: str) -> Optional[Entity]:
        """获取实体"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM entities WHERE name = ?", (name,)
            ).fetchone()

            if row:
                return Entity(
                    id=row["id"],
                    name=row["name"],
                    entity_type=EntityType(row["entity_type"]),
                    properties=json.loads(row["properties"]),
                    aliases=json.loads(row["aliases"]),
                    description=row["description"],
                    confidence=row["confidence"],
                    source_doc_ids=json.loads(row["source_doc_ids"]),
                )
        return None

    def search_entities(self, keyword: str, limit: int = 20) -> list[Entity]:
        """搜索实体"""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM entities
                WHERE name LIKE ? OR description LIKE ?
                ORDER BY confidence DESC
                LIMIT ?
            """, (f"%{keyword}%", f"%{keyword}%", limit)).fetchall()

            return [
                Entity(
                    id=row["id"],
                    name=row["name"],
                    entity_type=EntityType(row["entity_type"]),
                    properties=json.loads(row["properties"]),
                    aliases=json.loads(row["aliases"]),
                    description=row["description"],
                    confidence=row["confidence"],
                    source_doc_ids=json.loads(row["source_doc_ids"]),
                )
                for row in rows
            ]

    def list_entities(
        self,
        entity_type: Optional[EntityType] = None,
        limit: int = 100,
    ) -> list[Entity]:
        """列出实体"""
        with self._get_conn() as conn:
            if entity_type:
                rows = conn.execute(
                    "SELECT * FROM entities WHERE entity_type = ? ORDER BY name LIMIT ?",
                    (entity_type.value, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM entities ORDER BY name LIMIT ?",
                    (limit,),
                ).fetchall()

            return [
                Entity(
                    id=row["id"],
                    name=row["name"],
                    entity_type=EntityType(row["entity_type"]),
                    properties=json.loads(row["properties"]),
                    aliases=json.loads(row["aliases"]),
                    description=row["description"],
                    confidence=row["confidence"],
                    source_doc_ids=json.loads(row["source_doc_ids"]),
                )
                for row in rows
            ]

    def delete_entity(self, name: str) -> bool:
        """删除实体及其相关关系"""
        with self._get_conn() as conn:
            # 删除相关关系
            conn.execute(
                "DELETE FROM relations WHERE source_entity = ? OR target_entity = ?",
                (name, name),
            )
            # 删除实体
            cursor = conn.execute(
                "DELETE FROM entities WHERE name = ?", (name,)
            )

        # 更新内存图
        if name in self.graph:
            self.graph.remove_node(name)

        return True

    # ==================== 关系操作 ====================

    def add_relation(self, relation: Relation) -> str:
        """
        添加关系

        如果已存在相同关系，增加权重
        """
        rel_id = relation.id or f"rel_{relation.source_entity}_{relation.target_entity}_{relation.relation_type}"

        with self._get_conn() as conn:
            # 检查是否已存在
            existing = conn.execute("""
                SELECT id, weight FROM relations
                WHERE source_entity = ? AND target_entity = ? AND relation_type = ?
            """, (
                relation.source_entity,
                relation.target_entity,
                relation.relation_type.value,
            )).fetchone()

            if existing:
                # 更新权重
                new_weight = existing["weight"] + 1
                conn.execute("""
                    UPDATE relations SET weight = ?, confidence = ?, evidence = ?
                    WHERE id = ?
                """, (new_weight, relation.confidence, relation.evidence, existing["id"]))
                rel_id = existing["id"]
            else:
                # 插入新关系
                conn.execute("""
                    INSERT INTO relations
                    (id, source_entity, target_entity, relation_type,
                     properties, weight, confidence, evidence, source_doc_ids)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rel_id,
                    relation.source_entity,
                    relation.target_entity,
                    relation.relation_type.value,
                    json.dumps(relation.properties, ensure_ascii=False),
                    relation.weight,
                    relation.confidence,
                    relation.evidence,
                    json.dumps(relation.source_doc_ids, ensure_ascii=False),
                ))

        # 更新内存图
        self.graph.add_edge(
            relation.source_entity,
            relation.target_entity,
            relation_type=relation.relation_type.value,
            weight=relation.weight,
            confidence=relation.confidence,
            evidence=relation.evidence,
        )

        return rel_id

    def get_relations(
        self,
        entity_name: str,
        direction: str = "both",
    ) -> list[Relation]:
        """
        获取实体的关系

        参数:
            entity_name: 实体名称
            direction: 方向 (out/in/both)
        """
        relations = []

        with self._get_conn() as conn:
            if direction in ("out", "both"):
                rows = conn.execute(
                    "SELECT * FROM relations WHERE source_entity = ?",
                    (entity_name,),
                ).fetchall()
                for row in rows:
                    relations.append(Relation(
                        id=row["id"],
                        source_entity=row["source_entity"],
                        target_entity=row["target_entity"],
                        relation_type=RelationType(row["relation_type"]),
                        properties=json.loads(row["properties"]),
                        weight=row["weight"],
                        confidence=row["confidence"],
                        evidence=row["evidence"],
                        source_doc_ids=json.loads(row["source_doc_ids"]),
                    ))

            if direction in ("in", "both"):
                rows = conn.execute(
                    "SELECT * FROM relations WHERE target_entity = ?",
                    (entity_name,),
                ).fetchall()
                for row in rows:
                    relations.append(Relation(
                        id=row["id"],
                        source_entity=row["source_entity"],
                        target_entity=row["target_entity"],
                        relation_type=RelationType(row["relation_type"]),
                        properties=json.loads(row["properties"]),
                        weight=row["weight"],
                        confidence=row["confidence"],
                        evidence=row["evidence"],
                        source_doc_ids=json.loads(row["source_doc_ids"]),
                    ))

        return relations

    # ==================== 图查询 ====================

    def get_neighbors(self, entity_name: str, depth: int = 1) -> dict:
        """
        获取实体的邻居

        参数:
            entity_name: 实体名称
            depth: 深度
        """
        if entity_name not in self.graph:
            return {"nodes": [], "edges": []}

        # BFS 获取邻居
        visited = set()
        nodes = []
        edges = []
        queue = [(entity_name, 0)]
        visited.add(entity_name)

        while queue:
            current, current_depth = queue.pop(0)

            if current_depth >= depth:
                continue

            # 获取邻居
            for neighbor in self.graph.successors(current):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, current_depth + 1))

                    # 添加节点
                    node_data = self.graph.nodes[neighbor]
                    nodes.append({
                        "name": neighbor,
                        "entity_type": node_data.get("entity_type", "other"),
                    })

                    # 添加边
                    edge_data = self.graph.edges[current, neighbor]
                    edges.append({
                        "source": current,
                        "target": neighbor,
                        "relation_type": edge_data.get("relation_type", "related_to"),
                    })

            # 也检查入边
            for neighbor in self.graph.predecessors(current):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, current_depth + 1))

                    node_data = self.graph.nodes[neighbor]
                    nodes.append({
                        "name": neighbor,
                        "entity_type": node_data.get("entity_type", "other"),
                    })

                    edge_data = self.graph.edges[neighbor, current]
                    edges.append({
                        "source": neighbor,
                        "target": current,
                        "relation_type": edge_data.get("relation_type", "related_to"),
                    })

        return {"nodes": nodes, "edges": edges}

    def find_path(
        self,
        source: str,
        target: str,
        max_depth: int = 5,
    ) -> Optional[list[str]]:
        """
        查找两个实体之间的最短路径
        """
        if source not in self.graph or target not in self.graph:
            return None

        try:
            path = nx.shortest_path(self.graph, source, target)
            return path
        except nx.NetworkXNoPath:
            # 尝试无向图
            try:
                path = nx.shortest_path(self.graph.to_undirected(), source, target)
                return path
            except nx.NetworkXNoPath:
                return None

    # ==================== 统计 ====================

    def get_stats(self) -> GraphStats:
        """获取图谱统计信息"""
        with self._get_conn() as conn:
            entity_count = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
            relation_count = conn.execute("SELECT COUNT(*) FROM relations").fetchone()[0]
            document_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

            # 各类型实体数量
            entity_types = {}
            rows = conn.execute(
                "SELECT entity_type, COUNT(*) as cnt FROM entities GROUP BY entity_type"
            ).fetchall()
            for row in rows:
                entity_types[row["entity_type"]] = row["cnt"]

            # 各类型关系数量
            relation_types = {}
            rows = conn.execute(
                "SELECT relation_type, COUNT(*) as cnt FROM relations GROUP BY relation_type"
            ).fetchall()
            for row in rows:
                relation_types[row["relation_type"]] = row["cnt"]

        # 计算平均度数
        avg_degree = 0
        if self.graph.number_of_nodes() > 0:
            avg_degree = sum(dict(self.graph.degree()).values()) / self.graph.number_of_nodes()

        return GraphStats(
            entity_count=entity_count,
            relation_count=relation_count,
            document_count=document_count,
            entity_types=entity_types,
            relation_types=relation_types,
            avg_degree=round(avg_degree, 2),
        )

    def clear(self):
        """清空图谱"""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM entities")
            conn.execute("DELETE FROM relations")
            conn.execute("DELETE FROM documents")

        self.graph.clear()
