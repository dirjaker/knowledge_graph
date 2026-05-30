"""
查询引擎模块

支持自然语言问答、实体查询、路径查询
"""

import re
from typing import Optional
from models import (
    Entity, EntityType,
    Relation, RelationType,
    QueryRequest, QueryResponse,
    PathRequest,
)
from graph_store import GraphStore


class QueryEngine:
    """
    查询引擎

    支持:
    1. 实体查询: "张三是什么职位？"
    2. 关系查询: "张三和李四什么关系？"
    3. 路径查询: "张三和王五之间有什么联系？"
    4. 邻居查询: "张三认识哪些人？"
    """

    def __init__(self, graph_store: GraphStore):
        """
        初始化查询引擎

        参数:
            graph_store: 图谱存储实例
        """
        self.store = graph_store

        # 查询意图模式
        self._patterns = {
            "entity_info": [
                r'(.+?)是(什么|谁|哪个)',
                r'(.+?)的(职位|身份|角色)是',
                r'告诉我关于(.+?)的信息',
            ],
            "relation": [
                r'(.+?)和(.+?)(什么关系|有什么关系|关系是什么)',
                r'(.+?)与(.+?)的关系',
            ],
            "path": [
                r'(.+?)和(.+?)(之间|中间)(有什么联系|怎么联系|路径)',
                r'(.+?)到(.+?)(怎么走|路径|联系)',
            ],
            "neighbor": [
                r'(.+?)(认识|知道|了解)(哪些|什么)(人|组织)',
                r'(.+?)的(同事|朋友|下属|上级)是(谁|哪些人)',
                r'(.+?)(有哪些|有什么)(关系|联系)',
            ],
        }

    def query(self, request: QueryRequest) -> QueryResponse:
        """
        处理自然语言查询

        参数:
            request: 查询请求

        返回:
            查询响应
        """
        question = request.question.strip()

        # 识别查询意图
        intent, params = self._parse_intent(question)

        # 根据意图执行查询
        if intent == "entity_info":
            return self._query_entity_info(params)
        elif intent == "relation":
            return self._query_relation(params)
        elif intent == "path":
            return self._query_path(params, request.max_hops)
        elif intent == "neighbor":
            return self._query_neighbors(params, request.max_hops)
        else:
            # 默认：搜索实体
            return self._query_search(question, request.top_k)

    def _parse_intent(self, question: str) -> tuple[str, dict]:
        """
        解析查询意图

        返回:
            (intent, params)
        """
        for intent, patterns in self._patterns.items():
            for pattern in patterns:
                match = re.search(pattern, question)
                if match:
                    groups = match.groups()
                    params = {"entities": [g for g in groups if g and len(g) > 1]}
                    if params["entities"]:
                        return intent, params

        # 未识别到意图
        return "search", {"keyword": question}

    def _query_entity_info(self, params: dict) -> QueryResponse:
        """查询实体信息"""
        if not params.get("entities"):
            return QueryResponse(answer="请提供要查询的实体名称")

        entity_name = params["entities"][0]
        entity = self.store.get_entity(entity_name)

        if not entity:
            # 尝试模糊搜索
            results = self.store.search_entities(entity_name, limit=1)
            if results:
                entity = results[0]
            else:
                return QueryResponse(
                    answer=f"未找到实体: {entity_name}",
                    confidence=0.0,
                )

        # 获取关系
        relations = self.store.get_relations(entity.name, direction="both")

        # 构建回答
        answer_parts = [f"**{entity.name}**"]
        if entity.description:
            answer_parts.append(entity.description)
        answer_parts.append(f"类型: {entity.entity_type.value}")

        if relations:
            answer_parts.append("\n相关关系:")
            for rel in relations[:10]:
                if rel.source_entity == entity.name:
                    answer_parts.append(
                        f"  → {rel.relation_type.value} → {rel.target_entity}"
                    )
                else:
                    answer_parts.append(
                        f"  ← {rel.relation_type.value} ← {rel.source_entity}"
                    )

        return QueryResponse(
            answer="\n".join(answer_parts),
            entities=[entity],
            relations=relations[:10],
            confidence=entity.confidence,
        )

    def _query_relation(self, params: dict) -> QueryResponse:
        """查询两个实体之间的关系"""
        entities = params.get("entities", [])
        if len(entities) < 2:
            return QueryResponse(answer="请提供两个实体名称")

        e1, e2 = entities[0], entities[1]

        # 查找直接关系
        relations = self.store.get_relations(e1, direction="both")
        direct_relations = [
            r for r in relations
            if r.source_entity == e2 or r.target_entity == e2
        ]

        if direct_relations:
            rel = direct_relations[0]
            answer = f"**{e1}** 和 **{e2}** 之间的关系:\n"
            answer += f"  {rel.source_entity} → {rel.relation_type.value} → {rel.target_entity}"
            if rel.evidence:
                answer += f"\n\n证据: {rel.evidence}"

            return QueryResponse(
                answer=answer,
                relations=direct_relations,
                confidence=rel.confidence,
            )

        # 尝试路径查找
        path = self.store.find_path(e1, e2)
        if path:
            answer = f"**{e1}** 和 **{e2}** 之间没有直接关系，但存在路径:\n"
            answer += " → ".join(path)
            return QueryResponse(
                answer=answer,
                path=path,
                confidence=0.5,
            )

        return QueryResponse(
            answer=f"未找到 **{e1}** 和 **{e2}** 之间的关系",
            confidence=0.0,
        )

    def _query_path(self, params: dict, max_hops: int) -> QueryResponse:
        """查询路径"""
        entities = params.get("entities", [])
        if len(entities) < 2:
            return QueryResponse(answer="请提供起始和目标实体")

        source, target = entities[0], entities[1]
        path = self.store.find_path(source, target, max_depth=max_hops)

        if path:
            # 获取路径上的关系
            relations = []
            for i in range(len(path) - 1):
                rels = self.store.get_relations(path[i], direction="out")
                for rel in rels:
                    if rel.target_entity == path[i + 1]:
                        relations.append(rel)
                        break

            answer = f"从 **{source}** 到 **{target}** 的路径:\n"
            for i, node in enumerate(path):
                if i < len(relations):
                    answer += f"  {node} → {relations[i].relation_type.value} → "
                else:
                    answer += f"  {node}"

            return QueryResponse(
                answer=answer,
                path=path,
                relations=relations,
                confidence=0.7,
            )

        return QueryResponse(
            answer=f"未找到从 **{source}** 到 **{target}** 的路径",
            confidence=0.0,
        )

    def _query_neighbors(self, params: dict, max_hops: int) -> QueryResponse:
        """查询邻居"""
        if not params.get("entities"):
            return QueryResponse(answer="请提供实体名称")

        entity_name = params["entities"][0]
        entity = self.store.get_entity(entity_name)

        if not entity:
            return QueryResponse(
                answer=f"未找到实体: {entity_name}",
                confidence=0.0,
            )

        # 获取邻居
        neighbors = self.store.get_neighbors(entity_name, depth=max_hops)

        if neighbors["nodes"]:
            answer = f"**{entity_name}** 的关联实体:\n"
            for node in neighbors["nodes"][:20]:
                answer += f"  - {node['name']} ({node['entity_type']})\n"

            entities = [
                Entity(name=n["name"], entity_type=EntityType(n["entity_type"]))
                for n in neighbors["nodes"]
            ]

            return QueryResponse(
                answer=answer,
                entities=entities,
                confidence=0.8,
            )

        return QueryResponse(
            answer=f"**{entity_name}** 没有关联实体",
            confidence=0.0,
        )

    def _query_search(self, keyword: str, top_k: int) -> QueryResponse:
        """搜索实体"""
        entities = self.store.search_entities(keyword, limit=top_k)

        if entities:
            answer = f"搜索 \"{keyword}\" 的结果:\n"
            for entity in entities[:10]:
                desc = f" - {entity.description}" if entity.description else ""
                answer += f"  - {entity.name} ({entity.entity_type.value}){desc}\n"

            return QueryResponse(
                answer=answer,
                entities=entities,
                confidence=0.6,
            )

        return QueryResponse(
            answer=f"未找到与 \"{keyword}\" 相关的实体",
            confidence=0.0,
        )
