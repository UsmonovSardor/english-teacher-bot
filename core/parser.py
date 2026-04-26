"""
Document parser — converts .docx to structured category blocks.
Key fix: Reading content goes to test_quiz, not listening.
"""
import re, logging
from docx import Document
from core.config import CATEGORY_KEYWORDS

logger = logging.getLogger(__name__)

# Headings that explicitly mark a new category boundary
SECTION_PATTERNS = {
    "listening":  re.compile(r"listening\s*(task|:|\d)", re.I),
    "test_quiz":  re.compile(r"(reading|answer\s*key|reading\s*answer|task\s*\d+\s*[-–])", re.I),
    "speaking":   re.compile(r"speaking", re.I),
    "vocabulary": re.compile(r"vocabulary|vocab|match the words", re.I),
    "homework":   re.compile(r"homework|home\s*task|assignment", re.I),
    "writing":    re.compile(r"writing", re.I),
    "games":      re.compile(r"\bgame\b|\bpuzzle\b", re.I),
    "visuals":    re.compile(r"visual|image|video|watch", re.I),
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
    t = text.lower()
    # Priority order matters — test_quiz before listening to catch "Reading"
    for cat in ("test_quiz", "listening", "speaking", "vocabulary",
                "homework", "writing", "games", "visuals", "links"):
        pat = SECTION_PATTERNS.get(cat)
        if pat and pat.search(t):
            return cat
        kws = CATEGORY_KEYWORDS.get(cat, [])
        if any(kw in t for kw in kws):
            return cat
    return None


def parse_document(path: str) -> tuple[dict, str]:
    """
    Returns (category_dict, lesson_title).
    category_dict = {cat: [text_block, ...]}
    """
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

    # Remove empty categories
    result = {k: v for k, v in result.items() if v}

    # Extract URLs to links category
    links = []
    for blocks in result.values():
        for block in blocks:
            for word in block.split():
                if word.startswith("http"):
                    links.append(word.strip(".,;()"))
    if links:
        result["links"] = result.get("links", []) + links

    return result, lesson_title or "Lesson"
