"""
Document parser — converts .docx to structured category blocks.
Improved: detects category titles even when they are not real Word headings.
"""
import re
import logging
from docx import Document
from core.config import CATEGORY_KEYWORDS

logger = logging.getLogger(__name__)

SECTION_PATTERNS = {
    "test_quiz": re.compile(
        r"^(answer\s*key|answers?|reading\s*answers?|listening\s*answers?|"
        r"test|quiz|exam|task\s*\d+\s*[-–]\s*key)\b",
        re.I,
    ),
    "listening": re.compile(
        r"^(listening|listening\s*task|listening\s*activity|audio|track|recording)\b",
        re.I,
    ),
    "reading": re.compile(
        r"^(reading|reading\s*task|reading\s*passage|reading\s*text|"
        r"read\s*the\s*text|read\s*the\s*following|comprehension)\b",
        re.I,
    ),
    "vocabulary": re.compile(
        r"^(vocabulary|vocab|new\s*words|word\s*list|key\s*words|"
        r"glossary|match\s*the\s*words|definitions)\b",
        re.I,
    ),
    "speaking": re.compile(
        r"^(speaking|discussion|discuss|pair\s*work|group\s*work|role\s*play|debate)\b",
        re.I,
    ),
    "writing": re.compile(
        r"^(writing|writing\s*task|write|essay|paragraph|composition)\b",
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


def _is_heading(para) -> bool:
    text = para.text.strip()

    if not text:
        return False

    if para.style and para.style.name and para.style.name.startswith("Heading"):
        return True

    if len(text) > 120:
        return False

    bold_runs = [r for r in para.runs if r.text.strip()]
    if bold_runs and all(r.bold for r in bold_runs):
        return True

    if _classify_section_title(text):
        return True

    return False


def _clean_title(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^[#\-\*\•\d\.\)\s]+", "", text)
    text = text.strip(":：-–— ").strip()
    return text


def _classify_section_title(text: str) -> str | None:
    title = _clean_title(text)
    low = title.lower()

    priority = [
        "test_quiz",
        "listening",
        "reading",
        "vocabulary",
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
        keywords = CATEGORY_KEYWORDS.get(cat, [])
        for kw in keywords:
            if low == kw.lower() or low.startswith(kw.lower() + ":"):
                return cat

    return None


def parse_document(path: str) -> tuple[dict, str]:
    doc = Document(path)

    result: dict[str, list[str]] = {cat: [] for cat in CATEGORY_KEYWORDS}
    lesson_title = ""
    current_cat = None
    buffer: list[str] = []

    def flush():
        nonlocal buffer
        text = "\n".join(buffer).strip()
        if text and current_cat:
            result[current_cat].append(text)
        buffer = []

    for elem in doc.element.body:
        tag = elem.tag.split("}")[-1]

        if tag == "tbl":
            tbl = next((t for t in doc.tables if t._element is elem), None)
            if tbl:
                table_text = _table_to_text(tbl)
                if table_text:
                    buffer.append(table_text)
            continue

        para = next((p for p in doc.paragraphs if p._element is elem), None)
        if para is None:
            continue

        text = para.text.strip()
        if not text:
            continue

        detected = _classify_section_title(text)

        if detected:
            flush()
            current_cat = detected
            buffer.append(f"**{_clean_title(text)}**")
            continue

        if _is_heading(para):
            flush()
            detected = _classify_section_title(text)

            if detected:
                current_cat = detected
                buffer.append(f"**{_clean_title(text)}**")
            elif not lesson_title:
                lesson_title = _clean_title(text)
            else:
                if current_cat:
                    buffer.append(f"**{text}**")
            continue

        if current_cat:
            buffer.append(text)
        elif not lesson_title:
            lesson_title = text[:80]

    flush()

    result = {k: v for k, v in result.items() if v}

    links = []
    for blocks in result.values():
        for block in blocks:
            found = re.findall(r"https?://\S+|www\.\S+", block)
            links.extend([x.strip(".,;()[]{}") for x in found])

    if links:
        result["links"] = result.get("links", []) + links

    logger.info("Parsed '%s': categories=%s", lesson_title, list(result.keys()))
    return result, lesson_title or "Lesson"
