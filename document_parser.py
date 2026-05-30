"""
文档解析模块

支持 PDF、Markdown、纯文本、Word 文档的解析
"""

import re
from pathlib import Path
from typing import Optional

from models import Document, DocumentType


class DocumentParser:
    """
    文档解析器

    支持格式:
    - PDF: 使用 pymupdf 提取文本
    - Markdown: 直接解析
    - 纯文本: 直接读取
    - Word: 使用 python-docx
    """

    @staticmethod
    def parse(file_path: str) -> Document:
        """
        解析文档

        参数:
            file_path: 文件路径

        返回:
            Document 对象
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        suffix = path.suffix.lower()
        doc_type = DocumentParser._get_doc_type(suffix)

        # 读取内容
        content = DocumentParser._read_content(path, doc_type)

        # 清洗文本
        content = DocumentParser._clean_text(content)

        # 生成标题
        title = path.stem

        return Document(
            title=title,
            content=content,
            doc_type=doc_type,
            file_path=str(path),
        )

    @staticmethod
    def _get_doc_type(suffix: str) -> DocumentType:
        """根据后缀获取文档类型"""
        mapping = {
            ".pdf": DocumentType.PDF,
            ".md": DocumentType.MARKDOWN,
            ".txt": DocumentType.TEXT,
            ".doc": DocumentType.WORD,
            ".docx": DocumentType.WORD,
        }
        return mapping.get(suffix, DocumentType.TEXT)

    @staticmethod
    def _read_content(path: Path, doc_type: DocumentType) -> str:
        """读取文件内容"""
        if doc_type == DocumentType.PDF:
            return DocumentParser._read_pdf(path)
        elif doc_type == DocumentType.WORD:
            return DocumentParser._read_word(path)
        else:
            # Markdown 和纯文本
            return path.read_text(encoding="utf-8")

    @staticmethod
    def _read_pdf(path: Path) -> str:
        """读取 PDF"""
        try:
            import fitz  # pymupdf
            doc = fitz.open(str(path))
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except ImportError:
            # 如果没有 pymupdf，返回提示
            return f"[PDF 文件: {path.name}，需要安装 pymupdf: pip install pymupdf]"

    @staticmethod
    def _read_word(path: Path) -> str:
        """读取 Word 文档"""
        try:
            from docx import Document as DocxDocument
            doc = DocxDocument(str(path))
            return "\n".join([p.text for p in doc.paragraphs])
        except ImportError:
            return f"[Word 文件: {path.name}，需要安装 python-docx: pip install python-docx]"

    @staticmethod
    def _clean_text(text: str) -> str:
        """
        清洗文本

        - 去除多余空白
        - 去除特殊字符
        - 标准化换行符
        """
        # 标准化换行符
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 去除多余空行
        text = re.sub(r"\n{3,}", "\n\n", text)

        # 去除行首行尾空白
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)

        return text.strip()

    @staticmethod
    def parse_text(text: str, title: str = "text_input") -> Document:
        """
        直接解析文本（不需要文件）

        参数:
            text: 文本内容
            title: 标题

        返回:
            Document 对象
        """
        content = DocumentParser._clean_text(text)
        return Document(
            title=title,
            content=content,
            doc_type=DocumentType.TEXT,
        )

    @staticmethod
    def split_sentences(text: str) -> list[str]:
        """
        分句

        支持中英文标点
        """
        # 中英文句号、问号、感叹号、分号
        pattern = r'[。！？；\.\!\?\;]'
        sentences = re.split(pattern, text)
        # 去除空句
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences

    @staticmethod
    def split_paragraphs(text: str) -> list[str]:
        """
        分段

        按空行分割
        """
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip()]


# ============================================================
# 快捷函数
# ============================================================

def parse_document(file_path: str) -> Document:
    """解析文档的快捷函数"""
    return DocumentParser.parse(file_path)


def parse_text(text: str, title: str = "text_input") -> Document:
    """解析文本的快捷函数"""
    return DocumentParser.parse_text(text, title)
