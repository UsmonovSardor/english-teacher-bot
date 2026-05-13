"""
Professional PDF generator — Lingua Bot.
"""

from pathlib import Path
import tempfile
import re
from fpdf import FPDF


CAT_COLORS = {
    "links": (59, 130, 246),
    "visuals": (139, 92, 246),
    "vocabulary": (5, 150, 105),
    "grammar": (37, 99, 235),
    "speaking": (234, 88, 12),
    "listening": (6, 182, 212),
    "reading": (37, 99, 235),
    "writing": (147, 51, 234),
    "games": (239, 68, 68),
    "homework": (245, 158, 11),
    "test_quiz": (20, 184, 166),
}

CAT_NAMES = {
    "links": "LINKS",
    "visuals": "VISUALS",
    "vocabulary": "VOCABULARY",
    "grammar": "GRAMMAR",
    "speaking": "SPEAKING",
    "listening": "LISTENING",
    "reading": "READING",
    "writing": "WRITING",
    "games": "GAMES",
    "homework": "HOMEWORK",
    "test_quiz": "TEST & QUIZ",
}


BASE_DIR = Path(__file__).resolve().parent.parent
FONT_PATH = BASE_DIR / "fonts" / "DejaVuSans.ttf"


def safe_text(text):
    text = str(text or "")

    replacements = {
        "📚": "",
        "🎧": "",
        "✍️": "",
        "📖": "",
        "🔗": "",
        "🖼": "",
        "🎮": "",
        "📝": "",
        "📋": "",
        "🗣": "",
        "🏆": "",
        "👨‍💼": "",
        "👥": "",
        "✅": "",
        "❌": "",
        "⚠️": "",
        "⬅️": "",
        "➕": "",
        "🗑": "",
        "📊": "",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"[\U00010000-\U0010ffff]", "", text)
    text = text.replace("\r", "")

    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line:
            lines.append(line)

    return "\n".join(lines).strip()


def get_block_text(block):
    if isinstance(block, dict):
        return block.get("content") or block.get("text") or ""

    return block


def generate_lesson_pdf(
    lesson_title,
    category,
    cat_label,
    content_blocks,
):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    if FONT_PATH.exists():
        pdf.add_font("DejaVu", "", str(FONT_PATH), uni=True)
        FONT = "DejaVu"
    else:
        FONT = "Arial"

    color = CAT_COLORS.get(category, (37, 99, 235))
    cat_name = CAT_NAMES.get(category, safe_text(cat_label).upper())

    pdf.set_fill_color(*color)
    pdf.rect(0, 0, 210, 28, "F")

    pdf.set_text_color(255, 255, 255)
    pdf.set_font(FONT, "", 18)
    pdf.set_xy(10, 7)
    pdf.cell(0, 8, safe_text(lesson_title), ln=True)

    pdf.set_font(FONT, "", 11)
    pdf.set_x(10)
    pdf.cell(0, 8, safe_text(cat_name), ln=True)

    pdf.ln(18)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font(FONT, "", 12)

    if not content_blocks:
        pdf.multi_cell(0, 8, "No content added yet.")
    else:
        for block in content_blocks:
            raw_text = get_block_text(block)
            text = safe_text(raw_text)

            if not text:
                continue

            pdf.multi_cell(0, 8, text)
            pdf.ln(3)

    tmp = tempfile.NamedTemporaryFile(
        suffix=".pdf",
        delete=False,
    )

    path = tmp.name
    tmp.close()

    pdf.output(path)

    return path
