"""
LLM客户端封装

支持 DeepSeek API 和 Ollama 两种后端
"""

import json
import httpx
from typing import Optional
from config import get_llm_config


class LLMClient:
    """统一的LLM调用客户端"""

    def __init__(self):
        self._reload_config()

    def _reload_config(self):
        """重新加载配置"""
        cfg = get_llm_config()
        self.provider = cfg.get("provider", "deepseek")
        self.api_key = cfg.get("api_key", "")
        self.model = cfg.get("model", "deepseek-chat")
        self.base_url = cfg.get("base_url", "https://api.deepseek.com")
        self.temperature = cfg.get("temperature", 0.3)
        self.max_tokens = cfg.get("max_tokens", 4096)

    def chat(self, prompt: str, system: str = "") -> str:
        """
        调用LLM对话

        参数:
            prompt: 用户消息
            system: 系统提示词
        返回:
            LLM回复文本
        """
        self._reload_config()

        if self.provider == "ollama":
            return self._call_ollama(prompt, system)
        else:
            return self._call_deepseek(prompt, system)

    def _call_deepseek(self, prompt: str, system: str = "") -> str:
        """调用DeepSeek API（兼容OpenAI格式）"""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        with httpx.Client(timeout=120) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    def _call_ollama(self, prompt: str, system: str = "") -> str:
        """调用Ollama本地模型"""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        url = "http://localhost:11434/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.temperature,
            },
        }

        with httpx.Client(timeout=120) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["message"]["content"]

    def test_connection(self) -> dict:
        """测试LLM连接"""
        try:
            result = self.chat("你好，请回复'连接成功'", system="你是一个测试助手，只需回复指定内容。")
            return {"success": True, "message": result.strip()}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def extract_knowledge(self, text: str) -> dict:
        """
        从文本中抽取实体和关系

        返回: {"entities": [...], "relations": [...]}
        """
        system = """你是一个知识图谱实体和关系抽取专家。
请从用户提供的文本中抽取实体和关系，返回严格的JSON格式。

要求：
1. 实体类型包括：person(人物)、organization(组织)、location(地点)、concept(概念)、event(事件)、technology(技术)、product(产品)、other(其他)
2. 关系类型：works_at(工作于)、located_in(位于)、part_of(属于)、created(创造了)、uses(使用)、founded(创立了)、invested_in(投资了)、related_to(相关)、mentioned_in(提及于)、other(其他)
3. 每个实体必须有name、type、description字段
4. 每个关系必须有source、target、type、evidence字段
5. 只抽取文本中明确提到的实体和关系，不要推测
6. 实体名称要简洁，不要包含多余修饰词
7. description用一句话简要描述

返回格式（只返回JSON，不要其他文字）：
{
  "entities": [
    {"name": "实体名", "type": "实体类型", "description": "简要描述"}
  ],
  "relations": [
    {"source": "源实体", "target": "目标实体", "type": "关系类型", "evidence": "原文证据"}
  ]
}"""

        result = self.chat(text, system=system)

        # 解析JSON
        try:
            # 尝试提取JSON部分（LLM有时会加markdown代码块标记）
            json_str = result
            if "```json" in result:
                json_str = result.split("```json")[1].split("```")[0]
            elif "```" in result:
                json_str = result.split("```")[1].split("```")[0]
            return json.loads(json_str.strip())
        except (json.JSONDecodeError, IndexError):
            return {"entities": [], "relations": [], "error": "LLM返回格式解析失败", "raw": result}

    def answer_question(self, question: str, context: str = "") -> str:
        """
        基于图谱上下文回答问题

        参数:
            question: 用户问题
            context: 图谱上下文信息
        """
        system = """你是一个知识图谱问答助手。
根据提供的知识图谱数据回答用户问题。
如果图谱中没有相关信息，请如实说明。
回答要简洁、准确，使用中文。"""

        prompt = f"""知识图谱数据：
{context}

用户问题：{question}"""

        return self.chat(prompt, system=system)


# 全局实例
llm_client = LLMClient()
