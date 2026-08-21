# -*- coding: utf-8 -*-
"""위기판독 첨부 파일(이미지/문서)의 형식 판별과 본문 추출.

Gemini 는 이미지와 PDF 는 바이트 그대로 읽지만 DOCX 는 읽지 못한다.
그래서 DOCX 는 여기서 텍스트를 뽑아 프롬프트에 붙인다.
python-docx 를 새로 깔지 않고 표준 라이브러리로 처리한다(DOCX 는 XML 이 든 zip).
"""

import io
import zipfile
from pathlib import Path
from xml.etree import ElementTree

PDF_CONTENT_TYPE = "application/pdf"
DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)

IMAGE_CONTENT_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
DOCUMENT_CONTENT_TYPES = frozenset({PDF_CONTENT_TYPE, DOCX_CONTENT_TYPE})

# 브라우저가 application/octet-stream 을 보내는 경우가 있어 확장자로도 판별한다.
CONTENT_TYPE_BY_SUFFIX = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".pdf": PDF_CONTENT_TYPE,
    ".docx": DOCX_CONTENT_TYPE,
}

SUFFIX_BY_CONTENT_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    PDF_CONTENT_TYPE: ".pdf",
    DOCX_CONTENT_TYPE: ".docx",
}

MAX_UPLOAD_SIZE = 10 * 1024 * 1024

# 파일 앞부분만 봐도 형식이 드러난다. content_type 을 그대로 믿지 않기 위한 확인용.
MAGIC_PREFIXES = {
    PDF_CONTENT_TYPE: b"%PDF-",
    DOCX_CONTENT_TYPE: b"PK\x03\x04",
}

# 프롬프트가 지나치게 길어지지 않도록 자른다.
MAX_DOCUMENT_TEXT_LENGTH = 20000

WORD_NAMESPACE = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def resolve_content_type(uploaded_file):
    """업로드 파일의 형식을 정한다. 모르는 형식이면 빈 문자열."""
    raw = getattr(uploaded_file, "content_type", "") or ""
    content_type = raw.split(";")[0].strip().lower()

    if content_type in IMAGE_CONTENT_TYPES or content_type in DOCUMENT_CONTENT_TYPES:
        return content_type

    suffix = Path(getattr(uploaded_file, "name", "") or "").suffix.lower()
    return CONTENT_TYPE_BY_SUFFIX.get(suffix, "")


def has_expected_magic(content_type, head):
    """문서 파일이 확장자만 바꾼 것이 아닌지 앞부분으로 확인한다."""
    prefix = MAGIC_PREFIXES.get(content_type)

    if prefix is None:
        return True

    return bool(head) and head.startswith(prefix)


def read_head(uploaded_file, size=8):
    uploaded_file.seek(0)
    head = uploaded_file.read(size)
    uploaded_file.seek(0)
    return head


def extract_docx_text(data):
    """DOCX 본문 텍스트를 뽑는다. 읽을 수 없으면 빈 문자열.

    표 안의 문단도 w:p 로 표현되므로 함께 잡힌다.
    """
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except (zipfile.BadZipFile, ValueError):
        return ""

    with archive:
        if "word/document.xml" not in archive.namelist():
            return ""

        try:
            root = ElementTree.fromstring(archive.read("word/document.xml"))
        except (ElementTree.ParseError, KeyError):
            return ""

    paragraphs = []

    for paragraph in root.iter(f"{WORD_NAMESPACE}p"):
        text = "".join(
            node.text or "" for node in paragraph.iter(f"{WORD_NAMESPACE}t")
        )

        if text.strip():
            paragraphs.append(text.strip())

    return "\n".join(paragraphs)[:MAX_DOCUMENT_TEXT_LENGTH]
