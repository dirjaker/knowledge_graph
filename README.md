<div align="center">

<img src="assets/banner.svg" width="100%" alt="知识图谱系统">

<br>

### 🕸️ 知识图谱系统

[![Stars](https://img.shields.io/github/stars/dirjaker/knowledge_graph?style=flat-square&label=Stars&color=FFD700)](https://github.com/dirjaker/knowledge_graph/stargazers)
[![Forks](https://img.shields.io/github/forks/dirjaker/knowledge_graph?style=flat-square&label=Forks&color=4A90D9)](https://github.com/dirjaker/knowledge_graph/network/members)
[![Contributors](https://img.shields.io/github/contributors/dirjaker/knowledge_graph?style=flat-square&label=Contributors&color=8B4513)](https://github.com/dirjaker/knowledge_graph/graphs/contributors)
[![License](https://img.shields.io/github/license/dirjaker/knowledge_graph?style=flat-square&label=License&color=20B2AA)](https://github.com/dirjaker/knowledge_graph/blob/dev/LICENSE)

</div>

---

## ✨ 功能特性

| 功能 | 描述 |
|------|------|
| 📄 **文档解析** | 支持 PDF、Word、Markdown 等多格式文档解析 |
| 🏷️ **实体抽取** | 基于 LLM 的命名实体识别和分类 |
| 🔗 **关系抽取** | 自动识别实体间的语义关系 |
| 🎨 **图谱可视化** | 基于 D3.js 的交互式知识图谱展示 |
| 💬 **自然语言问答** | 用自然语言查询知识图谱中的信息 |
| 📊 **图谱统计** | 实体和关系的数量统计和分布分析 |


## 🚀 快速开始

```bash
# 克隆项目
git clone https://github.com/dirjaker/knowledge_graph.git
cd knowledge_graph

# 创建虚拟环境
conda create -n knowledge_graph python=3.12 -y
conda activate knowledge_graph

# 安装依赖
pip install -r requirements.txt

# 运行项目
python main.py
```

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| **后端** | FastAPI, SQLAlchemy |
| **图数据库** | Neo4j |
| **NLP** | LLM, spaCy |
| **前端** | D3.js, Vue.js |

## 📝 开发日志

- [x] 文档解析器
- [x] 实体抽取引擎
- [x] 关系抽取引擎
- [x] 图谱可视化
- [x] 自然语言问答
- [ ] 增量更新
- [ ] 多图谱管理
- [ ] 图谱导出

## 📄 许可证

[MIT License](LICENSE)

---

<div align="center">

🔗 **GitHub**: [dirjaker/knowledge_graph](https://github.com/dirjaker/knowledge_graph)

⭐ 如果这个项目对你有帮助，请给一个 Star 支持一下！

</div>
