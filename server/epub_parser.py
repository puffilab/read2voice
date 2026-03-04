import os
import posixpath
import re
import tempfile
import warnings
import zipfile
from dataclasses import dataclass
from html import unescape
from typing import Iterable
from xml.etree import ElementTree as ET

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

try:
    from ebooklib import epub
    import ebooklib
except Exception:
    epub = None
    ebooklib = None

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

try:
    from docx import Document as DocxDocument
except Exception:
    DocxDocument = None


@dataclass
class Chapter:
    title: str
    text: str


def _html_to_text(content: str) -> str:
    if BeautifulSoup is not None:
        soup = BeautifulSoup(content, "html.parser")
        text = soup.get_text(" ", strip=True)
        text = re.sub(r"\s{2,}", " ", text)
        return text.strip()

    cleaned = re.sub(r"<script[\s\S]*?</script>", "", content, flags=re.IGNORECASE)
    cleaned = re.sub(r"<style[\s\S]*?</style>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = unescape(cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip()


def _extract_title(content: str, default_title: str) -> str:
    if BeautifulSoup is None:
        return default_title
    try:
        soup = BeautifulSoup(content, "html.parser")
        heading = soup.find(["h1", "h2", "h3", "title"])
        if heading and heading.get_text(strip=True):
            return heading.get_text(strip=True)
    except Exception:
        return default_title
    return default_title


def _parse_with_ebooklib(epub_path: str) -> list[Chapter]:
    if epub is None or ebooklib is None:
        return []
    chapters: list[Chapter] = []
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            book = epub.read_epub(epub_path)
        ordered_items = []
        seen_ids: set[str] = set()

        # Spine is the canonical reading order for EPUB.
        for entry in getattr(book, "spine", []) or []:
            item_id = entry[0] if isinstance(entry, (list, tuple)) and entry else str(entry)
            if not item_id or item_id in seen_ids:
                continue
            item = book.get_item_with_id(item_id)
            if item is None:
                continue
            if item.get_type() != ebooklib.ITEM_DOCUMENT:
                continue
            ordered_items.append(item)
            seen_ids.add(item_id)

        if not ordered_items:
            ordered_items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))

        for index, item in enumerate(ordered_items, start=1):
            try:
                content = item.get_content().decode("utf-8", errors="ignore")
            except Exception:
                content = str(item.get_content())

            title = _extract_title(content, f"Chapter {index}")
            text = _html_to_text(content)
            if text:
                chapters.append(Chapter(title=title, text=text))
    except Exception:
        return []
    return chapters


def _resolve_manifest_order_from_zip(zf: zipfile.ZipFile) -> list[str]:
    try:
        container_xml = zf.read("META-INF/container.xml")
        container_root = ET.fromstring(container_xml)
        rootfile_node = container_root.find(".//{*}rootfile")
        if rootfile_node is None:
            return []
        opf_path = rootfile_node.attrib.get("full-path", "").strip()
        if not opf_path:
            return []

        opf_xml = zf.read(opf_path)
        opf_root = ET.fromstring(opf_xml)
        opf_dir = posixpath.dirname(opf_path)

        manifest: dict[str, str] = {}
        for item in opf_root.findall(".//{*}manifest/{*}item"):
            item_id = (item.attrib.get("id") or "").strip()
            href = (item.attrib.get("href") or "").strip()
            media_type = (item.attrib.get("media-type") or "").strip().lower()
            if not item_id or not href:
                continue
            if media_type not in {"application/xhtml+xml", "text/html"} and not href.lower().endswith((".xhtml", ".html", ".htm")):
                continue
            full_path = posixpath.normpath(posixpath.join(opf_dir, href))
            manifest[item_id] = full_path

        ordered: list[str] = []
        for itemref in opf_root.findall(".//{*}spine/{*}itemref"):
            idref = (itemref.attrib.get("idref") or "").strip()
            if not idref:
                continue
            path = manifest.get(idref)
            if path:
                ordered.append(path)
        return ordered
    except Exception:
        return []


def _parse_with_zip(epub_path: str) -> list[Chapter]:
    chapters: list[Chapter] = []
    with zipfile.ZipFile(epub_path, "r") as zf:
        html_files = _resolve_manifest_order_from_zip(zf)
        if not html_files:
            html_files = [
                name
                for name in zf.namelist()
                if name.lower().endswith((".xhtml", ".html", ".htm"))
            ]
            html_files.sort()
        for index, name in enumerate(html_files, start=1):
            content = zf.read(name).decode("utf-8", errors="ignore")
            title = _extract_title(content, f"Chapter {index}")
            text = _html_to_text(content)
            if text:
                chapters.append(Chapter(title=title, text=text))
    return chapters


def parse_epub_bytes(data: bytes, original_name: str = "book.epub") -> list[Chapter]:
    suffix = os.path.splitext(original_name)[1] or ".epub"
    temp_path = ""
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
        temp_file.write(data)
        temp_file.flush()
        temp_path = temp_file.name
    try:
        chapters = _parse_with_ebooklib(temp_path)
        if chapters:
            return chapters
        return _parse_with_zip(temp_path)
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def parse_pdf_bytes(data: bytes, original_name: str = "book.pdf") -> list[Chapter]:
    if PdfReader is None:
        raise RuntimeError("pypdf is not installed")

    suffix = os.path.splitext(original_name)[1] or ".pdf"
    temp_path = ""
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
        temp_file.write(data)
        temp_file.flush()
        temp_path = temp_file.name
    try:
        reader = PdfReader(temp_path)
        chapters: list[Chapter] = []
        for index, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            cleaned = re.sub(r"\s{2,}", " ", text.replace("\r", "\n")).strip()
            if cleaned:
                chapters.append(Chapter(title=f"Page {index}", text=cleaned))
        return chapters
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def _decode_text_bytes(data: bytes) -> str:
    candidates = ["utf-8-sig", "utf-8", "utf-16", "gb18030", "big5", "shift_jis"]
    for enc in candidates:
        try:
            return data.decode(enc)
        except Exception:
            continue
    return data.decode("utf-8", errors="ignore")


def _chapter_from_plain_text(text: str, default_title: str = "Text") -> list[Chapter]:
    cleaned = text.replace("\r", "\n")
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    lines = [line.strip() for line in cleaned.split("\n")]
    lines = [line for line in lines if line]
    if not lines:
        return []

    chapters: list[Chapter] = []
    heading_re = re.compile(
        r"^(chapter\s+\d+|part\s+\d+|第[0-9一二三四五六七八九十百千零两〇]+[章节回卷部篇]).*",
        flags=re.IGNORECASE,
    )
    current_title = default_title
    buffer: list[str] = []

    for line in lines:
        if heading_re.match(line):
            if buffer:
                chapters.append(Chapter(title=current_title, text="\n".join(buffer).strip()))
                buffer = []
            current_title = line[:120]
            continue
        buffer.append(line)

    if buffer:
        chapters.append(Chapter(title=current_title, text="\n".join(buffer).strip()))

    if not chapters:
        return [Chapter(title=default_title, text="\n".join(lines))]
    return chapters


def parse_txt_bytes(data: bytes, original_name: str = "book.txt") -> list[Chapter]:
    text = _decode_text_bytes(data)
    base_name = os.path.splitext(os.path.basename(original_name))[0].strip() or "Text"
    return _chapter_from_plain_text(text, default_title=base_name)


def _read_docx_paragraphs_xml(docx_path: str) -> list[tuple[str, str]]:
    paragraphs: list[tuple[str, str]] = []
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    w_val = f"{{{ns['w']}}}val"
    with zipfile.ZipFile(docx_path, "r") as zf:
        xml = zf.read("word/document.xml")
    root = ET.fromstring(xml)
    for p in root.findall(".//w:body/w:p", ns):
        style_name = ""
        style_el = p.find("./w:pPr/w:pStyle", ns)
        if style_el is not None:
            style_name = (style_el.attrib.get(w_val) or style_el.attrib.get("w:val") or "").strip().lower()
        chunks: list[str] = []
        for t in p.findall(".//w:t", ns):
            if t.text:
                chunks.append(t.text)
        text = re.sub(r"\s{2,}", " ", "".join(chunks).strip())
        if text:
            paragraphs.append((text, style_name))
    return paragraphs


def parse_docx_bytes(data: bytes, original_name: str = "book.docx") -> list[Chapter]:
    suffix = os.path.splitext(original_name)[1] or ".docx"
    temp_path = ""
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
        temp_file.write(data)
        temp_file.flush()
        temp_path = temp_file.name
    try:
        paragraphs: list[tuple[str, str]] = []
        if DocxDocument is not None:
            try:
                doc = DocxDocument(temp_path)
                for para in doc.paragraphs:
                    text = re.sub(r"\s{2,}", " ", (para.text or "").strip())
                    if not text:
                        continue
                    style_name = ""
                    try:
                        style_name = (para.style.name or "").strip().lower()
                    except Exception:
                        style_name = ""
                    paragraphs.append((text, style_name))
            except Exception:
                paragraphs = _read_docx_paragraphs_xml(temp_path)
        else:
            paragraphs = _read_docx_paragraphs_xml(temp_path)

        chapters: list[Chapter] = []
        current_title = os.path.splitext(os.path.basename(original_name))[0].strip() or "Word Document"
        buffer: list[str] = []
        for text, style_name in paragraphs:
            if style_name.startswith("heading"):
                if buffer:
                    chapters.append(Chapter(title=current_title, text="\n".join(buffer).strip()))
                    buffer = []
                current_title = text[:120]
                continue
            buffer.append(text)

        if buffer:
            chapters.append(Chapter(title=current_title, text="\n".join(buffer).strip()))
        return chapters
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def parse_document_bytes(data: bytes, original_name: str) -> list[Chapter]:
    ext = os.path.splitext(original_name)[1].lower()
    if ext == ".epub":
        return parse_epub_bytes(data, original_name=original_name)
    if ext == ".pdf":
        return parse_pdf_bytes(data, original_name=original_name)
    if ext == ".txt":
        return parse_txt_bytes(data, original_name=original_name)
    if ext == ".docx":
        return parse_docx_bytes(data, original_name=original_name)
    if ext == ".doc":
        raise ValueError("Legacy .doc is not supported. Please convert it to .docx")
    raise ValueError("Unsupported document format")


def split_text_for_tts(text: str, max_chars: int = 3000) -> list[str]:
    text = text.replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text).strip()
    if not text:
        return []

    separators = re.compile(r"([。！？!?；;\n])")
    parts = separators.split(text)

    sentences: list[str] = []
    for i in range(0, len(parts), 2):
        core = parts[i].strip()
        if not core:
            continue
        mark = parts[i + 1] if i + 1 < len(parts) else ""
        sentence = f"{core}{mark}".strip()
        if sentence:
            sentences.append(sentence)

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for sentence in sentences:
        sentence_len = len(sentence)
        if sentence_len > max_chars:
            if current:
                chunks.append(" ".join(current))
                current = []
                current_len = 0
            for i in range(0, sentence_len, max_chars):
                chunks.append(sentence[i : i + max_chars])
            continue

        if current_len + sentence_len + 1 > max_chars and current:
            chunks.append(" ".join(current))
            current = [sentence]
            current_len = sentence_len
        else:
            current.append(sentence)
            current_len += sentence_len + 1

    if current:
        chunks.append(" ".join(current))
    return chunks


def chapter_preview(chapters: Iterable[Chapter], size: int = 180) -> list[dict]:
    out = []
    for i, chapter in enumerate(chapters):
        out.append(
            {
                "index": i,
                "title": chapter.title,
                "length": len(chapter.text),
                "preview": chapter.text[:size],
            }
        )
    return out
