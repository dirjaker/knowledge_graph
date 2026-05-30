"""
知识图谱项目 - 数据模型

实体(Entity)、关系(Relation)、文档(Document) 的核心数据结构
"""

from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from typing import Optional


# ============================================================
# 枚举类型
# ============================================================

class EntityType(str, Enum):
    """实体类型"""
    PERSON = "person"           # 人物
    ORGANIZATION = "organization"  # 组织
    LOCATION = "location"       # 地点
    CONCEPT = "concept"         # 概念
    EVENT = "event"             # 事件
    TECHNOLOGY = "technology"   # 技术
    PRODUCT = "product"         # 产品
    OTHER = "other"             # 其他


class RelationType(str, Enum):
    """关系类型"""
    WORKS_AT = "works_at"               # 工作于
    LOCATED_IN = "located_in"           # 位于
    PART_OF = "part_of"                 # 属于
    CREATED = "created"                 # 创造了
    USES = "uses"                       # 使用
    RELATED_TO = "related_to"           # 相关
    MENTIONED_IN = "mentioned_in"       # 提及于
    CEO_OF = "ceo_of"                   # CEO
    FOUNDED = "founded"                 # 创立了
    INVESTED_IN = "invested_in"         # 投资了
    OTHER = "other"                     # 其他


class DocumentType(str, Enum):
    """文档类型"""
    PDF = "pdf"
    MARKDOWN = "markdown"
    TEXT = "text"
    WORD = "word"


# ============================================================
# 核心模型
# ============================================================

class Entity(BaseModel):
    """实体"""
    id: Optional[str] = None
    name: str                           # 实体名称
    entity_type: EntityType = EntityType.OTHER
    properties: dict = {}               # 额外属性
    aliases: list[str] = []             # 别名
    description: str = ""               # 描述
    confidence: float = 1.0             # 置信度
    created_at: datetime = Field(default_factory=datetime.now)
    source_doc_ids: list[str] = []      # 来源文档

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, Entity):
            return self.name == other.name
        return False


class Relation(BaseModel):
    """关系"""
    id: Optional[str] = None
    source_entity: str                  # 源实体名称
    target_entity: str                  # 目标实体名称
    relation_type: RelationType = RelationType.OTHER
    properties: dict = {}               # 额外属性
    weight: float = 1.0                 # 权重（出现次数）
    confidence: float = 1.0             # 置信度
    evidence: str = ""                  # 证据文本
    source_doc_ids: list[str] = []      # 来源文档
    created_at: datetime = Field(default_factory=datetime.now)


class Document(BaseModel):
    """文档"""
    id: Optional[str] = None
    title: str                          # 文档标题
    content: str                        # 文档内容
    doc_type: DocumentType = DocumentType.TEXT
    file_path: str = ""                 # 文件路径
    entity_count: int = 0               # 实体数量
    relation_count: int = 0             # 关系数量
    created_at: datetime = Field(default_factory=datetime.now)


class Triple(BaseModel):
    """三元组 (主语, 谓语, 宾语)"""
    subject: str
    predicate: str
    obj: str
    confidence: float = 1.0
    evidence: str = ""


# ============================================================
# 请求/响应模型
# ============================================================

class QueryRequest(BaseModel):
    """查询请求"""
    question: str                       # 自然语言问题
    max_hops: int = 3                   # 最大跳数
    top_k: int = 10                     # 返回数量


class QueryResponse(BaseModel):
    """查询响应"""
    answer: str                         # 回答
    entities: list[Entity] = []         # 相关实体
    relations: list[Relation] = []      # 相关关系
    path: list[str] = []                # 推理路径
    confidence: float = 0.0             # 置信度


class GraphStats(BaseModel):
    """图谱统计"""
    entity_count: int = 0
    relation_count: int = 0
    document_count: int = 0
    entity_types: dict = {}             # 各类型实体数量
    relation_types: dict = {}           # 各类型关系数量
    avg_degree: float = 0.0             # 平均度数


class PathRequest(BaseModel):
    """路径查询请求"""
    source: str                         # 起始实体
    target: str                         # 目标实体
    max_depth: int = 5                  # 最大深度
