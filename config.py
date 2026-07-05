"""
配置管理模块

管理LLM、数据库、服务器等所有配置项
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 基础路径
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "graph.db"
CONFIG_PATH = DATA_DIR / "config.json"

# 确保目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 默认配置
DEFAULT_CONFIG = {
    "llm": {
        "provider": "deepseek",         # deepseek / ollama
        "api_key": "",
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com",
        "temperature": 0.3,
        "max_tokens": 4096,
    },
    "server": {
        "host": "0.0.0.0",
        "port": 10002,
    },
    "graph": {
        "max_nodes": 500,               # 单次查询最大节点数
        "max_edges": 1000,              # 单次查询最大边数
        "default_layout": "force",      # force / circular / hierarchical / grid
    },
}


def load_config() -> dict:
    """加载配置，不存在则创建默认配置"""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            # 合并默认配置（补全新增字段）
            merged = _deep_merge(DEFAULT_CONFIG, saved)
            # 环境变量覆盖 API Key
            env_key = os.getenv("LLM_API_KEY")
            if env_key:
                merged["llm"]["api_key"] = env_key
            return merged
        except (json.JSONDecodeError, KeyError):
            pass
    # 写入默认配置
    save_config(DEFAULT_CONFIG)
    config = DEFAULT_CONFIG.copy()
    # 环境变量覆盖 API Key
    env_key = os.getenv("LLM_API_KEY")
    if env_key:
        config["llm"]["api_key"] = env_key
    return config


def save_config(config: dict):
    """保存配置到文件"""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def _deep_merge(default: dict, override: dict) -> dict:
    """深度合并字典，override优先"""
    result = default.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


# 全局配置实例
_config = None


def get_config() -> dict:
    """获取全局配置"""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def update_config(updates: dict):
    """更新配置"""
    global _config
    if _config is None:
        _config = load_config()
    # 防止脱敏值被写入 api_key
    llm = updates.get("llm", {})
    if llm.get("api_key") in ("***", "****", "未设置", ""):
        llm.pop("api_key", None)
    _config = _deep_merge(_config, updates)
    save_config(_config)
    return _config


def get_llm_config() -> dict:
    """获取LLM配置"""
    return get_config().get("llm", DEFAULT_CONFIG["llm"])
