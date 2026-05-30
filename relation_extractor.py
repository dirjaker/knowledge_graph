"""
关系抽取模块

从文本中抽取实体之间的关系
"""

import re
from typing import Optional
from models import Entity, Relation, RelationType, EntityType


# ============================================================
# 关系模式库
# ============================================================

# 关系触发词
RELATION_PATTERNS = {
    RelationType.WORKS_AT: [
        r'({subject}).*?在.*?({target}).*?工作',
        r'({subject}).*?任职于.*?({target})',
        r'({subject}).*?加入.*?({target})',
        r'({subject}).*?就职于.*?({target})',
    ],
    RelationType.CEO_OF: [
        r'({subject}).*?(?:是|担任|出任).*?({target}).*?(?:CEO|首席执行官|总裁)',
        r'({target}).*?(?:CEO|首席执行官|总裁).*?({subject})',
    ],
    RelationType.FOUNDED: [
        r'({subject}).*?(?:创立|创办|创建|成立).*?({target})',
        r'({target}).*?(?:由|被).*?({subject}).*?(?:创立|创办)',
    ],
    RelationType.LOCATED_IN: [
        r'({subject}).*?(?:位于|坐落在|在).*?({target})',
        r'({target}).*?(?:的|所属).*?({subject})',
    ],
    RelationType.INVESTED_IN: [
        r'({subject}).*?(?:投资|注资).*?({target})',
        r'({target}).*?(?:获得|接受).*?({subject}).*?投资',
    ],
    RelationType.USES: [
        r'({subject}).*?(?:使用|采用|基于|利用).*?({target})',
        r'({target}).*?(?:被|用于).*?({subject})',
    ],
    RelationType.CREATED: [
        r'({subject}).*?(?:开发|创造|设计|研发).*?({target})',
        r'({target}).*?(?:由|被).*?({subject}).*?(?:开发|创造)',
    ],
}


class RelationExtractor:
    """
    关系抽取器

    支持两种抽取方式:
    1. 共现分析: 同一句子中出现的实体建立关系
    2. 模式匹配: 基于预定义模式抽取关系
    """

    def __init__(self):
        """初始化抽取器"""
        self.window_size = 2  # 共现窗口大小（句子数）

    def extract(
        self,
        text: str,
        entities: list[Entity],
        doc_id: str = "",
    ) -> list[Relation]:
        """
        从文本中抽取关系

        参数:
            text: 输入文本
            entities: 已识别的实体列表
            doc_id: 文档 ID

        返回:
            关系列表
        """
        relations = []
        seen = set()

        # 分句
        sentences = self._split_sentences(text)

        # 1. 基于模式匹配抽取
        pattern_relations = self._extract_by_patterns(text, entities)
        for rel in pattern_relations:
            key = (rel.source_entity, rel.target_entity, rel.relation_type)
            if key not in seen:
                rel.source_doc_ids = [doc_id] if doc_id else []
                relations.append(rel)
                seen.add(key)

        # 2. 基于共现分析抽取
        cooccurrence_relations = self._extract_by_cooccurrence(sentences, entities)
        for rel in cooccurrence_relations:
            key = (rel.source_entity, rel.target_entity, rel.relation_type)
            if key not in seen:
                rel.source_doc_ids = [doc_id] if doc_id else []
                relations.append(rel)
                seen.add(key)

        return relations

    def _split_sentences(self, text: str) -> list[str]:
        """分句"""
        pattern = r'[。！？；\.\!\?\;]'
        sentences = re.split(pattern, text)
        return [s.strip() for s in sentences if s.strip()]

    def _extract_by_patterns(
        self,
        text: str,
        entities: list[Entity],
    ) -> list[Relation]:
        """基于模式匹配抽取关系"""
        relations = []

        # 构建实体名称集合
        entity_names = {e.name for e in entities}

        for rel_type, patterns in RELATION_PATTERNS.items():
            for pattern_template in patterns:
                # 替换 {subject} 和 {target} 为实体正则
                for e1 in entities:
                    for e2 in entities:
                        if e1.name == e2.name:
                            continue

                        # 构建具体模式
                        pattern = pattern_template.format(
                            subject=re.escape(e1.name),
                            target=re.escape(e2.name),
                        )

                        if re.search(pattern, text):
                            # 找到证据
                            match = re.search(pattern, text)
                            evidence = match.group(0) if match else ""

                            relations.append(Relation(
                                source_entity=e1.name,
                                target_entity=e2.name,
                                relation_type=rel_type,
                                confidence=0.8,
                                evidence=evidence,
                            ))

        return relations

    def _extract_by_cooccurrence(
        self,
        sentences: list[str],
        entities: list[Entity],
    ) -> list[Relation]:
        """
        基于共现分析抽取关系

        如果两个实体在同一句话（或相邻句子）中出现，
        则认为它们之间存在关系
        """
        relations = []
        entity_map = {e.name: e for e in entities}

        # 滑动窗口
        for i in range(len(sentences)):
            # 当前窗口内的句子
            window_end = min(i + self.window_size, len(sentences))
            window_text = " ".join(sentences[i:window_end])

            # 找出窗口内出现的实体
            window_entities = []
            for entity in entities:
                if entity.name in window_text:
                    window_entities.append(entity)

            # 为窗口内的实体两两建立关系
            for j in range(len(window_entities)):
                for k in range(j + 1, len(window_entities)):
                    e1 = window_entities[j]
                    e2 = window_entities[k]

                    # 推断关系类型
                    rel_type = self._infer_relation_type(e1, e2, window_text)

                    relations.append(Relation(
                        source_entity=e1.name,
                        target_entity=e2.name,
                        relation_type=rel_type,
                        confidence=0.5,
                        evidence=window_text[:200],
                    ))

        return relations

    def _infer_relation_type(
        self,
        e1: Entity,
        e2: Entity,
        context: str,
    ) -> RelationType:
        """
        根据实体类型和上下文推断关系类型
        """
        # 人物 + 组织 → 可能是工作关系
        if e1.entity_type == EntityType.PERSON and e2.entity_type == EntityType.ORGANIZATION:
            return RelationType.WORKS_AT

        # 组织 + 地点 → 可能是位于关系
        if e1.entity_type == EntityType.ORGANIZATION and e2.entity_type == EntityType.LOCATION:
            return RelationType.LOCATED_IN

        # 人物 + 地点 → 可能是位于关系
        if e1.entity_type == EntityType.PERSON and e2.entity_type == EntityType.LOCATION:
            return RelationType.LOCATED_IN

        # 技术 + 组织 → 可能是使用关系
        if e1.entity_type == EntityType.TECHNOLOGY and e2.entity_type == EntityType.ORGANIZATION:
            return RelationType.USES

        # 默认关系
        return RelationType.RELATED_TO

    def extract_from_llm(
        self,
        text: str,
        entities: list[Entity],
        api_key: str = None,
    ) -> list[Relation]:
        """
        使用 LLM 抽取关系（需要 API Key）

        这是一个预留接口
        """
        # TODO: 实现 LLM 抽取
        pass


# ============================================================
# 快捷函数
# ============================================================

def extract_relations(
    text: str,
    entities: list[Entity],
    doc_id: str = "",
) -> list[Relation]:
    """抽取关系的快捷函数"""
    extractor = RelationExtractor()
    return extractor.extract(text, entities, doc_id)
