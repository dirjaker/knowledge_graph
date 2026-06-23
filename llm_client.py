"""
LLM客户端封装

支持 DeepSeek API 和 Ollama 两种后端
"""

import json
import logging
import httpx
from typing import Optional
from config import get_llm_config

logger = logging.getLogger(__name__)


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
            "response_format": {"type": "json_object"},
        }

        with httpx.Client(timeout=120) as client:
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                # 如果 response_format 不支持，去掉后重试
                payload.pop("response_format", None)
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
请从用户提供的文本中抽取实体和关系。

重要：你必须且只能返回一个合法的JSON对象，不要返回任何其他文字、解释或markdown标记。

要求：
1. 实体类型包括：person(人物)、organization(组织)、location(地点)、concept(概念)、event(事件)、technology(技术)、product(产品)、other(其他)
2. 关系类型：works_at(工作于)、located_in(位于)、part_of(属于)、created(创造了)、uses(使用)、founded(创立了)、invested_in(投资了)、related_to(相关)、mentioned_in(提及于)、other(其他)
3. 每个实体必须有name、type、description字段
4. 每个关系必须有source、target、type、evidence字段
5. 只抽取文本中明确提到的实体和关系，不要推测
6. 实体名称要简洁，不要包含多余修饰词
7. description用一句话简要描述
8. 返回的JSON必须以 { 开头，以 } 结尾

返回格式：
{"entities": [{"name": "实体名", "type": "实体类型", "description": "简要描述"}], "relations": [{"source": "源实体", "target": "目标实体", "type": "关系类型", "evidence": "原文证据"}]}"""

        # 带重试的抽取
        for attempt in range(2):
            result = self.chat(text, system=system)
            
            try:
                json_str = self._extract_json(result)
                parsed = json.loads(json_str)
                if "entities" not in parsed:
                    parsed["entities"] = []
                if "relations" not in parsed:
                    parsed["relations"] = []
                return parsed
            except (json.JSONDecodeError, IndexError, Exception) as e:
                if attempt == 0:
                    logger.warning(f"JSON解析失败(第{attempt+1}次): {e}, 重试中...")
                    continue
                logger.error(f"JSON解析失败(最终): {e}\n原始响应前500字: {result[:500]}")
                return {"entities": [], "relations": [], "error": f"LLM返回格式解析失败: {e}", "raw": result[:1000]}
        
        return {"entities": [], "relations": [], "error": "LLM返回格式解析失败: 未知错误"}

    def _extract_json(self, text: str) -> str:
        """从LLM响应中提取JSON字符串，处理各种格式"""
        text = text.strip()
        
        # 1. 尝试从 markdown 代码块提取
        for marker in ["```json\n", "```json", "```\n", "```"]:
            if marker in text:
                parts = text.split(marker, 1)
                if len(parts) > 1:
                    extracted = parts[1].split("```")[0].strip()
                    if extracted:
                        return self._fix_json(extracted)
        
        # 2. 尝试直接解析整个文本
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass
        
        # 3. 用正则找第一个 { 到最后一个 }
        first_brace = text.find('{')
        last_brace = text.rfind('}')
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            extracted = text[first_brace:last_brace + 1]
            return self._fix_json(extracted)
        
        raise ValueError("无法从响应中提取JSON")

    def _fix_json(self, text: str) -> str:
        """修复常见的JSON格式问题"""
        import re
        # 移除控制字符（除了换行和制表符）
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
        # 移除尾部逗号（在 } 或 ] 前面的逗号）
        text = re.sub(r',\s*([\]}])', r'\1', text)
        # 修复缺失逗号：} 后面紧跟 { 或 "（对象之间漏逗号）
        text = re.sub(r'\}\s*\n\s*\{', '},\n    {', text)
        text = re.sub(r'\}\s*\{', '},{', text)
        # 修复缺失逗号：] 后面紧跟 [ 或 "（数组之间漏逗号）
        text = re.sub(r'\]\s*\[', '],[', text)
        # 修复 "value" 后面直接跟 "key"（缺少逗号）
        text = re.sub(r'"\s*\n\s*"', '",\n    "', text)
        # 再次移除尾部逗号
        text = re.sub(r',\s*([\]}])', r'\1', text)
        text = text.strip()
        
        # 尝试解析，如果失败则修复截断的JSON
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            return self._fix_truncated_json(text)
    
    def _fix_truncated_json(self, text: str) -> str:
        """尝试修复被截断的JSON"""
        import re
        
        # 如果在字符串中间被截断，先关闭字符串并补全当前字段
        # 检查是否以冒号结尾（如 "type":）
        if re.search(r':\s*$', text):
            text = text.rstrip().rstrip(':') + '": "unknown"'
        elif text.endswith('"'):
            # 可能在值字符串中间
            pass
        elif re.search(r':\s*"$', text):
            # 如 "type": "val  — 值被截断
            text += '"'
        
        # 移除尾部逗号
        text = re.sub(r',\s*$', '', text)
        
        # 统计未闭合的括号
        open_braces = 0
        open_brackets = 0
        in_string = False
        escape_next = False
        
        for ch in text:
            if escape_next:
                escape_next = False
                continue
            if ch == '\\' and in_string:
                escape_next = True
                continue
            if ch == '"' and not escape_next:
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == '{':
                open_braces += 1
            elif ch == '}':
                open_braces -= 1
            elif ch == '[':
                open_brackets += 1
            elif ch == ']':
                open_brackets -= 1
        
        # 如果在字符串中间被截断，先关闭字符串
        if in_string:
            text += '"'
        
        # 移除尾部逗号
        text = re.sub(r',\s*$', '', text)
        
        # 闭合未关闭的括号
        text += ']' * max(0, open_brackets)
        text += '}' * max(0, open_braces)
        
        # 最终清理：再次移除可能产生的尾部逗号
        text = re.sub(r',\s*([\]}])', r'\1', text)
        
        return text

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
