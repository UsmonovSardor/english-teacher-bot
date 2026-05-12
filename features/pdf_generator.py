"""
Professional PDF generator — Lingua Bot.
Unicode supported with bundled DejaVu fonts.
"""

import os
import re
import tempfile
import unicodedata

from fpdf import FPDF
from fpdf.enums import XPos, YPos


_HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(os.path.dirname(_HERE), "fonts")
FONT_REG = os.path.join(FONT_DIR, "DejaVuSans.ttf")
FONT_BOLD = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")
FONT_ITAL = os.path.join(FONT_DIR, "DejaVuSans-Oblique.ttf")


P = {
    "dark": (15, 23, 42),
    "white": (255, 255, 255),
    "light": (248, 250, 252),
    "muted": (241, 245, 249),
    "gray": (100, 116, 139),
    "border": (226, 232, 240),
    "yellow": (253, 224, 71),
    "green": (16, 185, 129),
    "blue": (59, 130, 246),
    "red": (239, 68, 68),
}

CAT_COLORS = {
    "links": (59, 130, 246),
    "visuals": (139, 92, 246),
    "vocabulary": (5, 150, 105),
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
    "speaking": "SPEAKING",
    "listening": "LISTENING",
    "reading": "READING",
    "writing": "WRITING",
    "games": "GAMES",
    "homework": "HOMEWORK",
    "test_quiz": "TEST & QUIZ",
}


def _clean(text: str) -> str:
    text = str(text or "")
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = "".join(
        c for c in text
        if ord(c) < 0x10000 and unicodedata.category(c) not in ("So", "Cs")
    )
    return text.strip()


def _is_table(line: str) -> bool:
    return "|" in line and line.count("|") >= 2


def _parse_table(lines):
    rows = []
    for line in lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if any(cells):
            rows.append(cells)
    return rows


class LessonPDF(FPDF):
    def __init__(self, lesson_title, category, cat_label):
        super().__init__("P", "mm", "A4")
        self.lesson_title = _clean(lesson_title)[:55] or "Lesson"
        self.category = category
        self.cat_label = _clean(cat_label) or category.title()
        self.cc = CAT_COLORS.get(category, (37, 99, 235))
        self.cat_name = CAT_NAMES.get(category, category.upper())

        self.set_auto_page_break(auto=True, margin=22)
        self.set_margins(left=16, top=18, right=16)

        self.add_font("F", "", FONT_REG)
        self.add_font("F", "B", FONT_BOLD)
        self.add_font("F", "I", FONT_ITAL)

    def header(self):
        r, g, b = self.cc

        self.set_fill_color(r, g, b)
        self.rect(0, 0, 210, 15, "F")

        self.set_fill_color(max(r - 35, 0), max(g - 35, 0), max(b - 35, 0))
        self.rect(0, 15, 210, 25, "F")

        self.set_xy(14, 3)
        self.set_font("F", "B", 8)
        self.set_text_color(*P["yellow"])
        self.cell(80, 7, self.cat_name, align="L")

        self.set_xy(0, 3)
        self.set_font("F", "I", 8)
        self.set_text_color(*P["white"])
        self.cell(194, 7, "Lingua Bot", align="R")

        self.set_xy(14, 17)
        self.set_font("F", "B", 14)
        self.set_text_color(*P["white"])
        self.cell(0, 8, self.lesson_title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        self.set_x(14)
        self.set_font("F", "", 9)
        self.set_text_color(220, 252, 231)
        self.cell(0, 6, self.cat_label, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        self.set_fill_color(*P["white"])
        self.rect(0, 40, 210, 1.2, "F")
        self.ln(10)

    def footer(self):
        self.set_y(-14)
        self.set_fill_color(*P["muted"])
        self.rect(0, self.get_y() - 1, 210, 15, "F")

        self.set_fill_color(*self.cc)
        self.rect(0, self.get_y() - 1, 210, 2, "F")

        self.set_y(self.get_y() + 3)
        self.set_font("F", "I", 7.5)
        self.set_text_color(*P["gray"])
        self.cell(
            0,
            6,
            f"Lingua Bot  |  {self.lesson_title}  |  Page {self.page_no()}",
            align="C",
        )

    def h2(self, text):
        self.ln(4)
        y = self.get_y()

        self.set_fill_color(*self.cc)
        self.rect(16, y, 4, 9, "F")

        self.set_fill_color(*P["muted"])
        self.rect(20, y, 174, 9, "F")

        self.set_xy(24, y)
        self.set_font("F", "B", 11)
        self.set_text_color(*P["dark"])
        self.cell(0, 9, _clean(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)

    def h3(self, text):
        self.ln(2)
        self.set_font("F", "B", 10)
        self.set_text_color(*self.cc)
        self.cell(0, 7, _clean(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def body(self, text):
        self.set_font("F", "", 10)
        self.set_text_color(*P["dark"])
        self.multi_cell(0, 5.7, _clean(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def bullet(self, text, level=0):
        x = self.get_x() + level * 6
        y = self.get_y()

        self.set_fill_color(*self.cc)
        self.ellipse(x + 1, y + 2.2, 2.3, 2.3, "F")

        self.set_xy(x + 6, y)
        self.set_font("F", "", 10)
        self.set_text_color(*P["dark"])
        self.multi_cell(0, 5.7, _clean(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def numbered(self, n, text):
        x, y = self.get_x(), self.get_y()

        self.set_fill_color(*self.cc)
        self.ellipse(x, y, 7, 7, "F")

        self.set_font("F", "B", 8)
        self.set_text_color(*P["white"])
        self.set_xy(x, y - 0.3)
        self.cell(7, 7, str(n), align="C")

        self.set_xy(x + 10, y)
        self.set_font("F", "", 10)
        self.set_text_color(*P["dark"])
        self.multi_cell(0, 5.7, _clean(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def callout(self, text):
        x, y = self.get_x(), self.get_y()
        clean = _clean(text)
        h = max(12, (len(clean) // 75 + clean.count("\n") + 1) * 5.6 + 6)

        self.set_fill_color(239, 246, 255)
        self.set_draw_color(*P["blue"])
        self.rounded_rect(x, y, 178, h, 3, "FD")

        self.set_fill_color(*P["blue"])
        self.rect(x, y, 3, h, "F")

        self.set_xy(x + 7, y + 4)
        self.set_font("F", "I", 9)
        self.set_text_color(30, 64, 175)
        self.multi_cell(166, 5.5, clean, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(3)

    def draw_table(self, rows):
        if not rows:
            return

        ncols = max(len(r) for r in rows)
        avail = 178
        col_ws = [avail / ncols] * ncols

        for i, row in enumerate(rows):
            is_header = i == 0
            self.set_font("F", "B" if is_header else "", 8.5)

            if is_header:
                self.set_fill_color(*self.cc)
                self.set_text_color(*P["white"])
            else:
                self.set_fill_color(*(P["muted"] if i % 2 == 0 else P["white"]))
                self.set_text_color(*P["dark"])

            for j in range(ncols):
                cell = row[j] if j < len(row) else ""
                self.cell(
                    col_ws[j],
                    7,
                    _clean(cell)[:42],
                    border=1,
                    fill=True,
                    align="C" if is_header else "L",
                )
            self.ln(7)

        self.ln(4)

    def divider(self):
        y = self.get_y() + 2
        self.set_draw_color(*P["border"])

        x = 16
        while x < 194:
            self.line(x, y, min(x + 6, 194), y)
            x += 10

        self.ln(6)

    def rounded_rect(self, x, y, w, h, r, style=""):
        k = self.k
        hp = self.h
        op = "f" if style == "F" else "B" if style in ("FD", "DF") else "S"

        self._out(
            f"{(x+r)*k:.2f} {(hp-y)*k:.2f} m "
            f"{(x+w-r)*k:.2f} {(hp-y)*k:.2f} l "
            f"{(x+w)*k:.2f} {(hp-y)*k:.2f} {(x+w)*k:.2f} {(hp-y-r)*k:.2f} v "
            f"{(x+w)*k:.2f} {(hp-y-h+r)*k:.2f} l "
            f"{(x+w)*k:.2f} {(hp-y-h)*k:.2f} {(x+w-r)*k:.2f} {(hp-y-h)*k:.2f} v "
            f"{(x+r)*k:.2f} {(hp-y-h)*k:.2f} l "
            f"{x*k:.2f} {(hp-y-h)*k:.2f} {x*k:.2f} {(hp-y-h+r)*k:.2f} v "
            f"{x*k:.2f} {(hp-y-r)*k:.2f} l "
            f"{x*k:.2f} {(hp-y)*k:.2f} {(x+r)*k:.2f} {(hp-y)*k:.2f} v "
            f"{op}"
        )


def _render_block(pdf, block_text):
    lines = str(block_text or "").split("\n")
    tbl = []

    for raw in lines:
        line = raw.strip()

        if _is_table(line):
            tbl.append(line)
            continue

        if tbl:
            pdf.draw_table(_parse_table(tbl))
            tbl = []

        if not line:
            pdf.ln(2)
            continue

        if line.startswith("**") and line.endswith("**") and len(line) > 4:
            pdf.h2(line.strip("*"))
        elif re.match(r"^\*\*.+\*\*", line):
            pdf.h3(re.sub(r"\*", "", line))
        elif re.match(r"^[-•*]\s+", line):
            pdf.bullet(re.sub(r"^[-•*]\s+", "", line))
        elif re.match(r"^\s{2,}[-•*]\s+", raw):
            pdf.bullet(re.sub(r"^[-•*]\s+", "", line), level=1)
        elif re.match(r"^\d+[\.\)]\s+\S", line):
            m = re.match(r"^(\d+)[\.\)]\s+(.*)", line)
            pdf.numbered(int(m.group(1)), m.group(2))
        elif re.match(r"(?i)^(tip:|note:|remember:|example:|speaking model)", line):
            pdf.callout(line)
        else:
            pdf.body(line)

    if tbl:
        pdf.draw_table(_parse_table(tbl))


def generate_lesson_pdf(lesson_title, category, cat_label, content_blocks):
    pdf = LessonPDF(lesson_title, category, cat_label)
    pdf.add_page()

    for i, block in enumerate(content_blocks):
        _render_block(pdf, block)

        if i < len(content_blocks) - 1:
            pdf.divider()

    tmp = tempfile.NamedTemporaryFile(
        suffix=".pdf",
        delete=False,
        prefix=f"{category}_",
    )
    path = tmp.name
    tmp.close()

    pdf.output(path)
    return path
