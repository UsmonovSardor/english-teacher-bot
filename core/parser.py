"""
Document parser — converts .docx to structured category blocks.
Reading content → 'reading' category. Answer keys → 'test_quiz'.
"""
import re, logging
from docx import Document
from core.config import CATEGORY_KEYWORDS

logger = logging.getLogger(__name__)

SECTION_PATTERNS = {
    "test_quiz":  re.compile(
        r"(answer\s*key|reading\s*answer[s]?|listening\s*answer[s]?|"
        r"task\s*\d+\s*[-–]\s*key|quiz|exam\s*answer)", re.I),
    "reading":    re.compile(
        r"(reading\s*(task|passage|text|activity|comprehension)|"
        r"read\s*the\s*(text|following|passage)|reading\s*:)", re.I),
    "listening":  re.compile(r"listening\s*(task|:|activity|\d)", re.I),
    "speaking":   re.compile(r"speaking", re.I),
    "vocabulary": re.compile(r"(vocabulary|vocab|match\s*the\s*words|word\s*list|key\s*words)", re.I),
    "homework":   re.compile(r"(homework|home\s*task|assignment)", re.I),
    "writing":    re.compile(r"writing\s*(task|activity|:)?", re.I),
    "games":      re.compile(r"(\bgame\b|\bpuzzle\b|fun\s*activity|crossword)", re.I),
    "visuals":    re.compile(r"(visual|image|video|watch|diagram|chart)", re.I),
}


def _table_to_text(table) -> str:
    rows = []
    for row in table.rows:
        cells = [c.text.strip() for c in row.cells]
        rows.append(" | ".join(cells))
    return "\n".join(rows)


def _is_heading(para) -> bool:
    if para.style.name.startswith("Heading"):
        return True
    text = para.text.strip()
    if not text or len(text) > 150:
        return False
    bold_runs = [r for r in para.runs if r.text.strip()]
    return bool(bold_runs) and all(r.bold for r in bold_runs)


def _classify_heading(text: str) -> str | None:
    t = text.lower().strip()
    priority = ["test_quiz", "reading", "listening", "speaking",
                "vocabulary", "homework", "writing", "games", "visuals", "links"]
    for cat in priority:
        pat = SECTION_PATTERNS.get(cat)
        if pat and pat.search(t):
            return cat
        kws = CATEGORY_KEYWORDS.get(cat, [])
        if any(kw.lower() in t for kw in kws):
            return cat
    return None


def parse_document(path: str) -> tuple[dict, str]:
    doc = Document(path)
    result: dict[str, list[str]] = {cat: [] for cat in CATEGORY_KEYWORDS}
    lesson_title = ""
    current_cat  = None
    buffer: list[str] = []

    def flush():
        text = "\n".join(buffer).strip()
        if text and current_cat:
            result[current_cat].append(text)
        buffer.clear()

    for elem in doc.element.body:
        tag = elem.tag.split("}")[-1]
        if tag == "tbl":
            tbl = next((t for t in doc.tables if t._element is elem), None)
            if tbl:
                buffer.append(_table_to_text(tbl))
            continue
        para = next((p for p in doc.paragraphs if p._element is elem), None)
        if para is None:
            continue
        text = para.text.strip()
        if not text:
            continue
        if _is_heading(para):
            flush()
            detected = _classify_heading(text)
            if detected:
                current_cat = detected
            elif not lesson_title:
                lesson_title = text
            buffer.append(f"**{text}**")
        else:
            buffer.append(text)

    flush()
    result = {k: v for k, v in result.items() if v}

    links = []
    for blocks in result.values():
        for block in blocks:
            for word in block.split():
                if word.startswith("http"):
                    links.append(word.strip(".,;()"))
    if links:
        result["links"] = result.get("links", []) + links

    logger.info("Parsed '%s': categories=%s", lesson_title, list(result.keys()))
    return result, lesson_title or "Lesson"
