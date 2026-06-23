"""
数据库层

SQLite数据库操作，管理实体、关系、文档、图谱元数据
"""

import json
import sqlite3
import uuid
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

from config import DB_PATH


class Database:
    """SQLite数据库管理"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _conn(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        """初始化数据库表"""
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS entities (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    entity_type TEXT DEFAULT 'other',
                    description TEXT DEFAULT '',
                    properties TEXT DEFAULT '{}',
                    aliases TEXT DEFAULT '[]',
                    confidence REAL DEFAULT 1.0,
                    source_doc_ids TEXT DEFAULT '[]',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
                    content TEXT DEFAULT '',
                    doc_type TEXT DEFAULT 'text',
                    file_path TEXT DEFAULT '',
                    entity_count INTEGER DEFAULT 0,
                    relation_count INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS ingest_tasks (
                    id TEXT PRIMARY KEY,
                    status TEXT DEFAULT 'processing',
                    input_type TEXT DEFAULT 'text',
                    input_text TEXT DEFAULT '',
                    entities_json TEXT DEFAULT '[]',
                    relations_json TEXT DEFAULT '[]',
                    error TEXT DEFAULT '',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
                CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
                CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source_entity);
                CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target_entity);
                CREATE INDEX IF NOT EXISTS idx_relations_type ON relations(relation_type);
            """)

    # ==================== 实体操作 ====================

    def add_entity(self, name: str, entity_type: str = "other",
                   description: str = "", properties: dict = None,
                   confidence: float = 1.0, source_doc_ids: list = None) -> str:
        """添加或更新实体，返回实体ID"""
        entity_id = f"e_{uuid.uuid4().hex[:12]}"
        with self._conn() as conn:
            existing = conn.execute(
                "SELECT id FROM entities WHERE name = ?", (name,)
            ).fetchone()
            if existing:
                entity_id = existing["id"]
                conn.execute("""
                    UPDATE entities SET entity_type=?, description=?,
                    properties=?, confidence=?, source_doc_ids=?,
                    updated_at=CURRENT_TIMESTAMP WHERE id=?
                """, (
                    entity_type, description,
                    json.dumps(properties or {}, ensure_ascii=False),
                    confidence,
                    json.dumps(source_doc_ids or [], ensure_ascii=False),
                    entity_id
                ))
            else:
                conn.execute("""
                    INSERT INTO entities (id, name, entity_type, description,
                    properties, confidence, source_doc_ids)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    entity_id, name, entity_type, description,
                    json.dumps(properties or {}, ensure_ascii=False),
                    confidence,
                    json.dumps(source_doc_ids or [], ensure_ascii=False),
                ))
        return entity_id

    def get_entity(self, name: str) -> Optional[dict]:
        """按名称获取实体"""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM entities WHERE name = ?", (name,)
            ).fetchone()
            if row:
                return self._row_to_entity(row)
        return None

    def get_entity_by_id(self, entity_id: str) -> Optional[dict]:
        """按ID获取实体"""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM entities WHERE id = ?", (entity_id,)
            ).fetchone()
            if row:
                return self._row_to_entity(row)
        return None

    def search_entities(self, keyword: str = "", entity_type: str = "",
                        document_id: str = "",
                        limit: int = 100, offset: int = 0) -> list[dict]:
        """搜索实体，支持按文档ID筛选"""
        conditions = []
        params = []
        if keyword:
            conditions.append("(name LIKE ? OR description LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        if entity_type:
            conditions.append("entity_type = ?")
            params.append(entity_type)
        if document_id:
            # source_doc_ids 是 JSON 数组，用 LIKE 匹配包含该 document_id 的记录
            conditions.append("source_doc_ids LIKE ?")
            params.append(f'%"{document_id}"%')
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.extend([limit, offset])

        with self._conn() as conn:
            rows = conn.execute(f"""
                SELECT * FROM entities {where}
                ORDER BY updated_at DESC LIMIT ? OFFSET ?
            """, params).fetchall()
            return [self._row_to_entity(r) for r in rows]

    def count_entities(self, entity_type: str = "", document_id: str = "") -> int:
        """统计实体数量，支持按文档ID筛选"""
        conditions = []
        params = []
        if entity_type:
            conditions.append("entity_type = ?")
            params.append(entity_type)
        if document_id:
            conditions.append("source_doc_ids LIKE ?")
            params.append(f'%"{document_id}"%')
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with self._conn() as conn:
            row = conn.execute(f"SELECT COUNT(*) FROM entities {where}", params).fetchone()
            return row[0]

    def delete_entity(self, name: str) -> bool:
        """删除实体及其相关关系"""
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM relations WHERE source_entity=? OR target_entity=?",
                (name, name)
            )
            cursor = conn.execute("DELETE FROM entities WHERE name=?", (name,))
            return cursor.rowcount > 0

    def update_entity(self, name: str, **kwargs) -> bool:
        """更新实体字段"""
        allowed = {"entity_type", "description", "properties", "aliases", "confidence"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False
        if "properties" in updates and isinstance(updates["properties"], dict):
            updates["properties"] = json.dumps(updates["properties"], ensure_ascii=False)
        if "aliases" in updates and isinstance(updates["aliases"], list):
            updates["aliases"] = json.dumps(updates["aliases"], ensure_ascii=False)
        set_clause = ", ".join(f"{k}=?" for k in updates)
        values = list(updates.values()) + [name]
        with self._conn() as conn:
            conn.execute(
                f"UPDATE entities SET {set_clause}, updated_at=CURRENT_TIMESTAMP WHERE name=?",
                values
            )
        return True

    # ==================== 关系操作 ====================

    def add_relation(self, source: str, target: str,
                     relation_type: str = "related_to",
                     evidence: str = "", weight: float = 1.0,
                     confidence: float = 1.0,
                     source_doc_ids: list = None) -> str:
        """添加或累加关系"""
        with self._conn() as conn:
            existing = conn.execute("""
                SELECT id, weight FROM relations
                WHERE source_entity=? AND target_entity=? AND relation_type=?
            """, (source, target, relation_type)).fetchone()

            if existing:
                new_weight = existing["weight"] + weight
                conn.execute("""
                    UPDATE relations SET weight=?, confidence=?, evidence=?
                    WHERE id=?
                """, (new_weight, confidence, evidence, existing["id"]))
                return existing["id"]
            else:
                rel_id = f"r_{uuid.uuid4().hex[:12]}"
                conn.execute("""
                    INSERT INTO relations (id, source_entity, target_entity,
                    relation_type, weight, confidence, evidence, source_doc_ids)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rel_id, source, target, relation_type,
                    weight, confidence, evidence,
                    json.dumps(source_doc_ids or [], ensure_ascii=False),
                ))
                return rel_id

    def get_relations(self, entity_name: str = "",
                      relation_type: str = "",
                      document_id: str = "",
                      limit: int = 200) -> list[dict]:
        """获取关系列表"""
        conditions = []
        params = []
        if entity_name:
            conditions.append("(source_entity=? OR target_entity=?)")
            params.extend([entity_name, entity_name])
        if relation_type:
            conditions.append("relation_type=?")
            params.append(relation_type)
        if document_id:
            conditions.append("source_doc_ids LIKE ?")
            params.append(f'%"{document_id}"%')
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)

        with self._conn() as conn:
            rows = conn.execute(f"""
                SELECT * FROM relations {where}
                ORDER BY weight DESC LIMIT ?
            """, params).fetchall()
            return [self._row_to_relation(r) for r in rows]

    def delete_relation(self, rel_id: str) -> bool:
        """删除关系"""
        with self._conn() as conn:
            cursor = conn.execute("DELETE FROM relations WHERE id=?", (rel_id,))
            return cursor.rowcount > 0

    def count_relations(self) -> int:
        """统计关系数量"""
        with self._conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM relations").fetchone()[0]

    # ==================== 图谱数据 ====================

    def get_graph_data(self, entity_types: list = None,
                       relation_types: list = None,
                       limit: int = 500) -> dict:
        """获取图谱数据（节点+边）"""
        with self._conn() as conn:
            # 获取实体
            if entity_types:
                placeholders = ",".join("?" * len(entity_types))
                entity_rows = conn.execute(f"""
                    SELECT * FROM entities WHERE entity_type IN ({placeholders})
                    LIMIT ?
                """, list(entity_types) + [limit]).fetchall()
            else:
                entity_rows = conn.execute(
                    "SELECT * FROM entities LIMIT ?", (limit,)
                ).fetchall()

            entity_names = {r["name"] for r in entity_rows}

            # 获取相关关系
            rel_rows = conn.execute(
                "SELECT * FROM relations", ()
            ).fetchall()

        # 过滤只保留两端都在可见实体中的关系
        nodes = [self._row_to_entity(r) for r in entity_rows]
        edges = []
        for r in rel_rows:
            if r["source_entity"] in entity_names and r["target_entity"] in entity_names:
                if relation_types and r["relation_type"] not in relation_types:
                    continue
                edges.append(self._row_to_relation(r))

        return {"nodes": nodes, "edges": edges}

    def get_entity_neighbors(self, name: str, depth: int = 1) -> dict:
        """获取实体的邻居"""
        visited = {name}
        frontier = {name}
        all_nodes = {}
        all_edges = []

        with self._conn() as conn:
            for _ in range(depth):
                next_frontier = set()
                for entity_name in frontier:
                    # 获取该实体信息
                    row = conn.execute(
                        "SELECT * FROM entities WHERE name=?", (entity_name,)
                    ).fetchone()
                    if row:
                        all_nodes[entity_name] = self._row_to_entity(row)

                    # 获取相关关系
                    rows = conn.execute("""
                        SELECT * FROM relations
                        WHERE source_entity=? OR target_entity=?
                    """, (entity_name, entity_name)).fetchall()

                    for r in rows:
                        all_edges.append(self._row_to_relation(r))
                        other = r["target_entity"] if r["source_entity"] == entity_name else r["source_entity"]
                        if other not in visited:
                            next_frontier.add(other)
                            visited.add(other)

                frontier = next_frontier

            # 补充最终frontier的节点信息
            for entity_name in frontier:
                row = conn.execute(
                    "SELECT * FROM entities WHERE name=?", (entity_name,)
                ).fetchone()
                if row:
                    all_nodes[entity_name] = self._row_to_entity(row)

        # 去重边
        seen_edges = set()
        unique_edges = []
        for e in all_edges:
            key = (e["source"], e["target"], e["type"])
            if key not in seen_edges:
                seen_edges.add(key)
                unique_edges.append(e)

        return {
            "nodes": list(all_nodes.values()),
            "edges": unique_edges,
        }

    # ==================== 文档操作 ====================

    def add_document(self, title: str, content: str = "",
                     doc_type: str = "text",
                     entity_count: int = 0,
                     relation_count: int = 0) -> str:
        """添加文档记录"""
        doc_id = f"d_{uuid.uuid4().hex[:12]}"
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO documents (id, title, content, doc_type,
                entity_count, relation_count) VALUES (?, ?, ?, ?, ?, ?)
            """, (doc_id, title, content, doc_type, entity_count, relation_count))
        return doc_id

    def count_documents(self) -> int:
        """统计文档数量"""
        with self._conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

    # ==================== 导入任务 ====================

    def create_ingest_task(self, input_type: str = "text",
                           input_text: str = "", filename: str = "") -> str:
        """创建导入任务"""
        task_id = f"t_{uuid.uuid4().hex[:12]}"
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO ingest_tasks (id, status, input_type, input_text, filename)
                VALUES (?, 'processing', ?, ?, ?)
            """, (task_id, input_type, input_text, filename))
        return task_id

    def update_ingest_task(self, task_id: str, status: str = None,
                           entities: list = None, relations: list = None,
                           error: str = None):
        """更新导入任务状态"""
        with self._conn() as conn:
            if status:
                conn.execute(
                    "UPDATE ingest_tasks SET status=? WHERE id=?",
                    (status, task_id)
                )
            if entities is not None:
                conn.execute(
                    "UPDATE ingest_tasks SET entities_json=? WHERE id=?",
                    (json.dumps(entities, ensure_ascii=False), task_id)
                )
            if relations is not None:
                conn.execute(
                    "UPDATE ingest_tasks SET relations_json=? WHERE id=?",
                    (json.dumps(relations, ensure_ascii=False), task_id)
                )
            if error is not None:
                conn.execute(
                    "UPDATE ingest_tasks SET error=?, status='failed' WHERE id=?",
                    (error, task_id)
                )

    def get_ingest_task(self, task_id: str) -> Optional[dict]:
        """获取导入任务"""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM ingest_tasks WHERE id=?", (task_id,)
            ).fetchone()
            if row:
                return {
                    "id": row["id"],
                    "status": row["status"],
                    "input_type": row["input_type"],
                    "input_text": row["input_text"],
                    "filename": row["filename"] if "filename" in row.keys() else "",
                    "entities": json.loads(row["entities_json"]),
                    "relations": json.loads(row["relations_json"]),
                    "error": row["error"],
                    "created_at": row["created_at"],
                }
        return None

    # ==================== 统计 ====================

    def get_stats(self) -> dict:
        """获取图谱统计信息"""
        with self._conn() as conn:
            entity_count = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
            relation_count = conn.execute("SELECT COUNT(*) FROM relations").fetchone()[0]
            document_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

            # 实体类型分布
            entity_types = {}
            for row in conn.execute(
                "SELECT entity_type, COUNT(*) as cnt FROM entities GROUP BY entity_type"
            ).fetchall():
                entity_types[row["entity_type"]] = row["cnt"]

            # 关系类型分布
            relation_types = {}
            for row in conn.execute(
                "SELECT relation_type, COUNT(*) as cnt FROM relations GROUP BY relation_type"
            ).fetchall():
                relation_types[row["relation_type"]] = row["cnt"]

        # 平均度数
        avg_degree = 0
        if entity_count > 0:
            avg_degree = round(relation_count * 2 / entity_count, 2)

        return {
            "entity_count": entity_count,
            "relation_count": relation_count,
            "document_count": document_count,
            "entity_types": entity_types,
            "relation_types": relation_types,
            "avg_degree": avg_degree,
        }

    def clear_all(self):
        """清空所有数据"""
        with self._conn() as conn:
            conn.execute("DELETE FROM relations")
            conn.execute("DELETE FROM entities")
            conn.execute("DELETE FROM documents")
            conn.execute("DELETE FROM ingest_tasks")

    def clear_demo_data(self):
        """清除示例数据（source_doc_ids 包含 'demo' 的记录）"""
        with self._conn() as conn:
            conn.execute("DELETE FROM relations WHERE source_doc_ids LIKE '%\"demo\"%'")
            conn.execute("DELETE FROM entities WHERE source_doc_ids LIKE '%\"demo\"%'")

    def export_data(self) -> dict:
        """导出全部数据"""
        with self._conn() as conn:
            entities = [self._row_to_entity(r)
                        for r in conn.execute("SELECT * FROM entities").fetchall()]
            relations = [self._row_to_relation(r)
                         for r in conn.execute("SELECT * FROM relations").fetchall()]
        return {"entities": entities, "relations": relations, "version": "1.0"}

    def import_data(self, data: dict) -> dict:
        """导入数据"""
        entities = data.get("entities", [])
        relations = data.get("relations", [])
        imported_e = 0
        imported_r = 0

        for e in entities:
            self.add_entity(
                name=e["name"],
                entity_type=e.get("entity_type", "other"),
                description=e.get("description", ""),
                properties=e.get("properties", {}),
                confidence=e.get("confidence", 1.0),
            )
            imported_e += 1

        for r in relations:
            self.add_relation(
                source=r["source"],
                target=r["target"],
                relation_type=r.get("relation_type", "related_to"),
                evidence=r.get("evidence", ""),
                weight=r.get("weight", 1.0),
                confidence=r.get("confidence", 1.0),
            )
            imported_r += 1

        return {"imported_entities": imported_e, "imported_relations": imported_r}

    # ==================== 工具方法 ====================

    @staticmethod
    def _row_to_entity(row) -> dict:
        """将数据库行转换为实体字典"""
        return {
            "id": row["id"],
            "name": row["name"],
            "entity_type": row["entity_type"],
            "description": row["description"] or "",
            "properties": json.loads(row["properties"]) if row["properties"] else {},
            "aliases": json.loads(row["aliases"]) if row["aliases"] else [],
            "confidence": row["confidence"],
            "source_doc_ids": json.loads(row["source_doc_ids"]) if row["source_doc_ids"] else [],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"] if "updated_at" in row.keys() else row["created_at"],
        }

    @staticmethod
    def _row_to_relation(row) -> dict:
        """将数据库行转换为关系字典"""
        return {
            "id": row["id"],
            "source": row["source_entity"],
            "target": row["target_entity"],
            "type": row["relation_type"],
            "weight": row["weight"],
            "confidence": row["confidence"],
            "evidence": row["evidence"] or "",
            "properties": json.loads(row["properties"]) if row["properties"] else {},
            "source_doc_ids": json.loads(row["source_doc_ids"]) if row["source_doc_ids"] else [],
            "created_at": row["created_at"],
        }



    def list_documents(self) -> list:
        """列出所有文档"""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM documents ORDER BY created_at DESC"
            ).fetchall()
            return [
                {
                    "id": row["id"],
                    "filename": row["title"],
                    "status": "done",
                    "entity_count": row["entity_count"],
                    "relation_count": row["relation_count"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

    def get_document(self, doc_id: str):
        """获取文档详情"""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM documents WHERE id=?", (doc_id,)
            ).fetchone()
            if row:
                return {
                    "id": row["id"],
                    "filename": row["title"],
                    "content": row["content"],
                    "doc_type": row["doc_type"],
                    "entity_count": row["entity_count"],
                    "relation_count": row["relation_count"],
                    "created_at": row["created_at"],
                }
        return None

    def delete_document(self, doc_id: str) -> bool:
        """删除文档及其关联的实体和关系"""
        with self._conn() as conn:
            # 删除该文档关联的实体和关系
            conn.execute("DELETE FROM relations WHERE source_doc_ids LIKE ?",
                         (f'%"{doc_id}"%',))
            conn.execute("DELETE FROM entities WHERE source_doc_ids LIKE ?",
                         (f'%"{doc_id}"%',))
            # 删除文档记录
            cursor = conn.execute("DELETE FROM documents WHERE id=?", (doc_id,))
            return cursor.rowcount > 0

    def update_relation(self, source: str, target: str, relation_type: str):
        """更新关系类型"""
        with self._conn() as conn:
            conn.execute(
                "UPDATE relations SET relation_type=? WHERE source_entity=? AND target_entity=?",
                (relation_type, source, target),
            )

    def delete_relation_by_entities(self, source: str, target: str):
        """通过实体删除关系"""
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM relations WHERE source_entity=? AND target_entity=?",
                (source, target),
            )


# 全局数据库实例
db = Database()
