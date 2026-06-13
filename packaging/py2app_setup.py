"""
知识图谱 - py2app 打包脚本

使用方法:
    pip install py2app
    python packaging/py2app_setup.py py2app

产出: dist/知识图谱系统.app
"""

from setuptools import setup

APP = ["src/macos/app.py"]
DATA_FILES = [
    ("src/web/static", ["src/web/static/index.html"]),
]

OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "CFBundleName": "知识图谱系统",
        "CFBundleDisplayName": "知识图谱系统",
        "CFBundleIdentifier": "com.dirjaker.knowledge-graph",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "10.15",
    },
    "packages": [
        "fastapi",
        "uvicorn",
        "pydantic",
        "starlette",
        "networkx",
        "jieba",
        "rich",
    ],
    "includes": [
        "src",
        "src.web",
        "src.web.app",
        "src.macos",
        "models",
        "graph_store",
        "query_engine",
        "graph_algorithms",
        "document_parser",
        "entity_extractor",
        "relation_extractor",
    ],
    "excludes": [
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "PIL",
        "pymupdf",
        "docx",
    ],
}

setup(
    name="知识图谱系统",
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
