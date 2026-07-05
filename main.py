"""
知识图谱系统 - FastAPI 主入口

启动: python main.py
|或:   uvicorn api:app --host 0.0.0.0 --port 10002 --reload
"""

import uvicorn
from config import get_config


def main():
    cfg = get_config()
    host = cfg["server"]["host"]
    port = cfg["server"]["port"]
    print(f"\n  知识图谱系统启动中...")
    print(f"  地址: http://localhost:{port}")
    print(f"  API文档: http://localhost:{port}/docs\n")
    uvicorn.run("api:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    main()
