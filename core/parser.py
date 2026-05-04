"""
Document parser — converts .docx and .pdf files to structured category blocks.
"""
import os
import re
import logging
from docx import Document
from core.config import CATEGORY_KEYWORDS

logger = logging.getLogger(__name__)


SECTION_PATTERNS = {
    "test_quiz": re.compile(
        r"^(answer\s*key|answers?|reading\s*answer\s*sheet|listening\s*answer\s*sheet|test|quiz|exam)\b",
        re.I,
    ),
    "listening": re.compile(
        r"^(part\s*4\.?\s*listening|listening|audio|track|recording|listen\s+and|listen\s+to)\b",
        re.I,
    ),
    "vocabulary": re.compile(
        r"^(part\s*2|words|definitions|vocabulary|vocab|new\s*words|word\s*list|key\s*words|glossary|useful\s*words)\b",
        re.I,
    ),
    "reading": re.compile(
        r"^(part\s*3|reading|reading\s*task|reading\s*passage|reading\s*text|read\s*the\s*text|data\s*processing\s*day)\b",
        re.I,
    ),
    "speaking": re.compile(
        r"^(part\s*1|speaking|discussion|discuss|pair\s*work|group\s*work|role\s*play|debate|presentation)\b",
        re.I,
    ),
    "writing": re.compile(
        r"^(writing|writing\s*task|write|essay|paragraph|composition|critical\s*thinking)\b",
        re.I,
    ),
    "homework": re.compile(
        r"^(homework|home\s*task|assignment|at\s*home)\b",
        re.I,
    ),
    "games": re.compile(
        r"^(game|games|puzzle|crossword|bingo|fun\s*activity)\b",
        re.I,
    ),
    "visuals": re.compile(
        r"^(visuals?|image|picture|photo|diagram|chart|video|watch)\b",
        re.I,
    ),
    "links": re.compile(
        r"^(links?|url|website|www|https?://)\b",
        re.I,
    ),
}


def _table_to_text(table) -> str:
    rows = []
    for row in table.rows:
        cells = [c.text.strip() for c in row.cells if c.text.strip()]
        if cells:
            rows.append(" | ".join(cells))
    return "\n".join(rows)


def _clean_title(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^[#\-\*\•\d\.\)\s]+", "", text)
    text = text.strip(":：-–— ").strip()
    return text


def _classify_section_title(text: str) -> str | None:
    title = _clean_title(text)
    if not title:
        return None

    low = title.lower().strip()
    if len(low) > 160:
        return None

    priority = [
        "test_quiz",
        "listening",
        "vocabulary",
        "reading",
        "speaking",
        "writing",
        "homework",
        "games",
        "visuals",
        "links",
    ]

    for cat in priority:
        pattern = SECTION_PATTERNS.get(cat)
        if pattern and pattern.search(low):
            return cat

    for cat in priority:
        for kw in CATEGORY_KEYWORDS.get(cat, []):
            kw_low = kw.lower().strip()
            if low == kw_low or low.startswith(kw_low + ":"):
                return cat

    return None


def _looks_like_heading_line(text: str) -> bool:
    clean = _clean_title(text)
    if not clean:
        return False

    if _classify_section_title(clean):
        return True

    if len(clean) > 120:
        return False

    words = clean.split()

    if len(words) <= 8 and clean.endswith(":"):
        return True

    if len(words) <= 7 and clean.isupper():
        return True

    return False


def _is_heading(para) -> bool:
    text = para.text.strip()
    if not text:
        return False

    if para.style and para.style.name and para.style.name.startswith("Heading"):
        return True

    if _looks_like_heading_line(text):
        return True

    bold_runs = [r for r in para.runs if r.text.strip()]
    if bold_runs and all(r.bold for r in bold_runs) and len(text) <= 120:
        return True

    return False


def _extract_docx_blocks(path: str) -> tuple[list[tuple[str, str]], str]:
    doc = Document(path)
    items: list[tuple[str, str]] = []
    lesson_title = ""

    for elem in doc.element.body:
        tag = elem.tag.split("}")[-1]

        if tag == "tbl":
            tbl = next((t for t in doc.tables if t._element is elem), None)
            if tbl:
                table_text = _table_to_text(tbl)
                if table_text:
                    items.append(("text", table_text))
            continue

        para = next((p for p in doc.paragraphs if p._element is elem), None)
        if para is None:
            continue

        text = para.text.strip()
        if not text:
            continue

        detected = _classify_section_title(text)

        if not lesson_title and not detected and "lesson" in text.lower():
            lesson_title = _clean_title(text)
            continue

        kind = "heading" if _is_heading(para) or detected else "text"
        items.append((kind, text))

    return items, lesson_title


def _extract_pdf_blocks(path: str) -> tuple[list[tuple[str, str]], str]:
    text = ""

    try:
        import pdfplumber
        pages = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    pages.append(page_text)
        text = "\n".join(pages)

    except Exception:
        try:
            from pypdf import PdfReader
        except Exception:
            from PyPDF2 import PdfReader

        reader = PdfReader(path)
        pages = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages.append(page_text)
        text = "\n".join(pages)

    lines = []
    for raw in text.splitlines():
        line = re.sub(r"\s+", " ", raw.strip())
        if line:
            lines.append(line)

    items: list[tuple[str, str]] = []
    lesson_title = ""

    for line in lines:
        detected = _classify_section_title(line)

        if not lesson_title and not detected and "lesson" in line.lower() and len(line) <= 120:
            lesson_title = _clean_title(line)

        kind = "heading" if detected or _looks_like_heading_line(line) else "text"
        items.append((kind, line))

    return items, lesson_title


def _split_items_to_categories(items: list[tuple[str, str]], lesson_title: str) -> tuple[dict, str]:
    result: dict[str, list[str]] = {cat: [] for cat in CATEGORY_KEYWORDS}

    current_cat = None
    buffer: list[str] = []

    def flush():
        nonlocal buffer
        text = "\n".join(buffer).strip()
        if text and current_cat:
            result[current_cat].append(text)
        buffer = []

    for kind, text in items:
        clean = _clean_title(text)
        detected = _classify_section_title(clean)

        if detected:
            flush()
            current_cat = detected
            buffer.append(f"**{clean}**")
            continue

        if kind == "heading":
            if current_cat:
                buffer.append(f"**{clean}**")
            elif not lesson_title:
                lesson_title = clean[:80]
            continue

        if current_cat:
            buffer.append(text)
        elif not lesson_title:
            lesson_title = clean[:80]

    flush()

    result = {k: v for k, v in result.items() if v}

    links = []
    for blocks in result.values():
        for block in blocks:
            found = re.findall(r"https?://\S+|www\.\S+", block)
            links.extend([x.strip(".,;()[]{}") for x in found])

    if links:
        result["links"] = result.get("links", []) + links

    return result, lesson_title or "Lesson"


def parse_document(path: str) -> tuple[dict, str]:
    ext = os.path.splitext(path)[1].lower()

    if ext == ".docx":
        items, lesson_title = _extract_docx_blocks(path)
    elif ext == ".pdf":
        items, lesson_title = _extract_pdf_blocks(path)
    else:
        raise ValueError("Unsupported file type. Please upload .docx or .pdf")

    result, lesson_title = _split_items_to_categories(items, lesson_title)

    logger.info("Parsed '%s': categories=%s", lesson_title, list(result.keys()))
    return result, lesson_title
