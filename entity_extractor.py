"""
实体抽取模块

支持三种抽取方式:
1. 规则匹配（正则 + 词典）
2. LLM 抽取（调用大模型）
3. jieba 分词 + 词性标注
"""

import re
from typing import Optional
from models import Entity, EntityType


# ============================================================
# 实体词典（可扩展）
# ============================================================

# 常见人名后缀
PERSON_SUFFIXES = ["先生", "女士", "教授", "博士", "总", "经理", "主任", "院长", "校长"]

# 常见组织后缀
ORG_SUFFIXES = ["公司", "集团", "大学", "学院", "研究所", "研究院", "基金会", "协会", "委员会", "局", "部", "院"]

# 常见地点后缀
LOC_SUFFIXES = ["省", "市", "区", "县", "镇", "村", "路", "街", "大道", "广场"]

# 技术关键词
TECH_KEYWORDS = [
    "Python", "Java", "JavaScript", "TypeScript", "Go", "Rust", "C++",
    "React", "Vue", "Angular", "Django", "FastAPI", "Flask", "Spring",
    "Docker", "Kubernetes", "K8s", "Redis", "MySQL", "PostgreSQL", "MongoDB",
    "TensorFlow", "PyTorch", "Keras", "Hugging Face", "OpenAI", "GPT",
    "Linux", "Nginx", "Apache", "Git", "GitHub", "GitLab",
    "机器学习", "深度学习", "自然语言处理", "NLP", "计算机视觉", "CV",
    "知识图谱", "图数据库", "Neo4j", "向量数据库", "RAG",
    "微服务", "容器化", "DevOps", "CI/CD", "云原生",
]


class EntityExtractor:
    """
    实体抽取器

    使用规则 + jieba 分词进行实体识别
    """

    def __init__(self):
        """初始化抽取器"""
        # 尝试加载 jieba
        try:
            import jieba
            import jieba.posseg as pseg
            self.jieba = jieba
            self.pseg = pseg
            self.has_jieba = True
        except ImportError:
            self.has_jieba = False

        # 编译正则模式
        self._compile_patterns()

    def _compile_patterns(self):
        """编译正则表达式模式"""
        self.patterns = {
            # 日期
            "date": re.compile(
                r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?'
                r'|\d{4}年\d{1,2}月'
            ),
            # 邮箱
            "email": re.compile(
                r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            ),
            # URL
            "url": re.compile(
                r'https?://[^\s<>"{}|\\^`\[\]]+'
            ),
            # 电话
            "phone": re.compile(
                r'1[3-9]\d{9}'
                r'|\d{3,4}-\d{7,8}'
            ),
            # 百分比
            "percent": re.compile(
                r'\d+\.?\d*%'
            ),
            # 金额
            "money": re.compile(
                r'[\$¥€£]\d+\.?\d*[亿万]?'
                r'|\d+\.?\d*[亿万]?元'
                r'|\d+\.?\d*[亿万]?美元'
            ),
            # 版本号
            "version": re.compile(
                r'v?\d+\.\d+(\.\d+)?'
            ),
        }

    def extract(self, text: str, doc_id: str = "") -> list[Entity]:
        """
        从文本中抽取实体

        参数:
            text: 输入文本
            doc_id: 文档 ID

        返回:
            实体列表
        """
        entities = []
        seen = set()

        # 1. 正则抽取（日期、邮箱、URL 等）
        regex_entities = self._extract_by_regex(text)
        for entity in regex_entities:
            if entity.name not in seen:
                entities.append(entity)
                seen.add(entity.name)

        # 2. jieba 分词抽取（人名、地名、机构名）
        if self.has_jieba:
            jieba_entities = self._extract_by_jieba(text)
            for entity in jieba_entities:
                if entity.name not in seen:
                    entity.source_doc_ids = [doc_id] if doc_id else []
                    entities.append(entity)
                    seen.add(entity.name)

        # 3. 技术关键词抽取
        tech_entities = self._extract_technologies(text)
        for entity in tech_entities:
            if entity.name not in seen:
                entity.source_doc_ids = [doc_id] if doc_id else []
                entities.append(entity)
                seen.add(entity.name)

        # 4. 基于规则的实体抽取（后缀匹配）
        rule_entities = self._extract_by_rules(text)
        for entity in rule_entities:
            if entity.name not in seen:
                entity.source_doc_ids = [doc_id] if doc_id else []
                entities.append(entity)
                seen.add(entity.name)

        return entities

    def _extract_by_regex(self, text: str) -> list[Entity]:
        """使用正则表达式抽取实体"""
        entities = []

        for pattern_name, pattern in self.patterns.items():
            matches = pattern.findall(text)
            for match in matches:
                # 根据模式确定实体类型
                if pattern_name == "date":
                    entity_type = EntityType.OTHER
                elif pattern_name == "email":
                    entity_type = EntityType.OTHER
                elif pattern_name == "url":
                    entity_type = EntityType.OTHER
                elif pattern_name == "phone":
                    entity_type = EntityType.OTHER
                elif pattern_name == "money":
                    entity_type = EntityType.OTHER
                else:
                    entity_type = EntityType.OTHER

                entities.append(Entity(
                    name=match,
                    entity_type=entity_type,
                    properties={"source": "regex", "pattern": pattern_name},
                    confidence=0.8,
                ))

        return entities

    def _extract_by_jieba(self, text: str) -> list[Entity]:
        """使用 jieba 分词抽取实体"""
        entities = []
        words = self.pseg.cut(text)

        for word, flag in words:
            if len(word) < 2:
                continue

            entity_type = None
            confidence = 0.7

            # nr: 人名
            if flag == "nr":
                entity_type = EntityType.PERSON
                confidence = 0.8
            # ns: 地名
            elif flag == "ns":
                entity_type = EntityType.LOCATION
                confidence = 0.8
            # nt: 机构名
            elif flag == "nt":
                entity_type = EntityType.ORGANIZATION
                confidence = 0.8
            # nz: 其他专名
            elif flag == "nz":
                entity_type = EntityType.CONCEPT
                confidence = 0.6

            if entity_type:
                entities.append(Entity(
                    name=word,
                    entity_type=entity_type,
                    properties={"source": "jieba", "pos": flag},
                    confidence=confidence,
                ))

        return entities

    def _extract_technologies(self, text: str) -> list[Entity]:
        """抽取技术关键词"""
        entities = []

        for tech in TECH_KEYWORDS:
            # 不区分大小写匹配
            if re.search(re.escape(tech), text, re.IGNORECASE):
                entities.append(Entity(
                    name=tech,
                    entity_type=EntityType.TECHNOLOGY,
                    properties={"source": "keyword"},
                    confidence=0.9,
                ))

        return entities

    def _extract_by_rules(self, text: str) -> list[Entity]:
        """基于规则抽取实体（后缀匹配）"""
        entities = []

        # 抽取组织（以组织后缀结尾）
        for suffix in ORG_SUFFIXES:
            pattern = rf'[\u4e00-\u9fa5]{{2,10}}{suffix}'
            matches = re.findall(pattern, text)
            for match in matches:
                entities.append(Entity(
                    name=match,
                    entity_type=EntityType.ORGANIZATION,
                    properties={"source": "rule", "suffix": suffix},
                    confidence=0.7,
                ))

        # 抽取地点（以地点后缀结尾）
        for suffix in LOC_SUFFIXES:
            pattern = rf'[\u4e00-\u9fa5]{{2,8}}{suffix}'
            matches = re.findall(pattern, text)
            for match in matches:
                entities.append(Entity(
                    name=match,
                    entity_type=EntityType.LOCATION,
                    properties={"source": "rule", "suffix": suffix},
                    confidence=0.7,
                ))

        return entities

    def extract_from_llm(self, text: str, api_key: str = None) -> list[Entity]:
        """
        使用 LLM 抽取实体（需要 API Key）

        这是一个预留接口，实际使用时需要配置 API Key
        """
        # TODO: 实现 LLM 抽取
        # prompt = f"""
        # 从以下文本中抽取实体，返回 JSON 格式:
        # {text}
        #
        # 返回格式:
        # [{{"name": "实体名", "type": "实体类型", "description": "描述"}}]
        # """
        pass


# ============================================================
# 快捷函数
# ============================================================

def extract_entities(text: str, doc_id: str = "") -> list[Entity]:
    """抽取实体的快捷函数"""
    extractor = EntityExtractor()
    return extractor.extract(text, doc_id)
