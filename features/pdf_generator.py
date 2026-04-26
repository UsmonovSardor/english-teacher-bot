"""
Professional PDF generator — Lingua Bot.
Uses bundled DejaVu fonts for full Unicode support.
"""
import os, re, tempfile, unicodedata
from fpdf import FPDF
from fpdf.enums import XPos, YPos

_HERE     = os.path.dirname(os.path.abspath(__file__))
FONT_DIR  = os.path.join(_HERE, "fonts")
FONT_REG  = os.path.join(FONT_DIR, "DejaVuSans.ttf")
FONT_BOLD = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")
FONT_ITAL = os.path.join(FONT_DIR, "DejaVuSans-Oblique.ttf")

# ── Palette ──────────────────────────────────────────────────────────────────
P = {
    "dark":    (15,  23,  42),
    "white":   (255, 255, 255),
    "light":   (248, 250, 252),
    "muted":   (241, 245, 249),
    "gray":    (100, 116, 139),
    "border":  (226, 232, 240),
    "yellow":  (253, 224, 71),
    "green":   (34,  197, 94),
    "greenbg": (220, 252, 231),
    "bluebg":  (219, 234, 254),
    "blue":    (59,  130, 246),
    "red":     (239, 68,  68),
    "redbg":   (254, 226, 226),
}

CAT_COLORS = {
    "links":      (59,  130, 246),
    "visuals":    (139, 92,  246),
    "vocabulary": (5,   150, 105),
    "speaking":   (234, 88,  12),
    "listening":  (6,   182, 212),
    "writing":    (147, 51,  234),
    "games":      (239, 68,  68),
    "homework":   (245, 158, 11),
    "test_quiz":  (20,  184, 166),
}

CAT_EMOJI_TEXT = {
    "links": "LINKS", "visuals": "VISUALS", "vocabulary": "VOCABULARY",
    "speaking": "SPEAKING", "listening": "LISTENING", "writing": "WRITING",
    "games": "GAMES", "homework": "HOMEWORK", "test_quiz": "TEST & QUIZ",
}

def _clean(t: str) -> str:
    t = re.sub(r'\*\*(.+?)\*\*', r'\1', t)
    t = re.sub(r'\*(.+?)\*',     r'\1', t)
    t = t.replace('\u2013', '-').replace('\u2014', '--')
    t = t.replace('\u2018', "'").replace('\u2019', "'")
    t = t.replace('\u201c', '"').replace('\u201d', '"')
    # strip non-latin-plane chars (emoji etc)
    t = ''.join(c for c in t if ord(c) < 0x10000
                and unicodedata.category(c) not in ('So', 'Cs'))
    return t.strip()

def _is_tbl(line): return '|' in line and line.count('|') >= 2

def _parse_tbl(lines):
    rows = []
    for ln in lines:
        if '|' in ln:
            cells = [c.strip() for c in ln.strip().strip('|').split('|')]
            if any(cells): rows.append(cells)
    return rows


class LessonPDF(FPDF):

    def __init__(self, lesson_title, category, cat_label):
        super().__init__()
        self.lesson_title = _clean(lesson_title)[:52]
        self.category     = category
        self.cat_label    = _clean(cat_label)
        self.cc           = CAT_COLORS.get(category, (37, 99, 235))
        self.cat_name     = CAT_EMOJI_TEXT.get(category, category.upper())
        self.set_auto_page_break(auto=True, margin=24)
        self.set_margins(left=16, top=16, right=16)
        self.add_font("F",  "",  FONT_REG)
        self.add_font("F",  "B", FONT_BOLD)
        self.add_font("F",  "I", FONT_ITAL)

    # ── Header ───────────────────────────────────────────────────────────────
    def header(self):
        # gradient-like: two-tone top bar
        r, g, b = self.cc
        self.set_fill_color(r, g, b)
        self.rect(0, 0, 210, 14, "F")
        # Darker shade below
        dr, dg, db = max(r-30,0), max(g-30,0), max(b-30,0)
        self.set_fill_color(dr, dg, db)
        self.rect(0, 14, 210, 22, "F")

        # White diagonal accent
        self.set_fill_color(255, 255, 255)

        # Category badge on top bar
        self.set_xy(14, 2)
        self.set_font("F", "B", 9)
        self.set_text_color(*P["yellow"])
        self.cell(0, 10, f"  {self.cat_name}  ", align="L")

        # Bot name top-right
        self.set_xy(0, 2)
        self.set_text_color(*P["white"])
        self.set_font("F", "I", 8)
        self.cell(194, 10, "Lingua Bot", align="R")

        # Lesson title
        self.set_xy(14, 14)
        self.set_font("F", "B", 13)
        self.set_text_color(*P["white"])
        self.cell(0, 11, self.lesson_title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Section label
        self.set_x(14)
        self.set_font("F", "", 9)
        r2, g2, b2 = self.cc
        self.set_text_color(min(r2+180,255), min(g2+180,255), min(b2+180,255))
        self.cell(0, 6, self.cat_label, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # White divider
        self.set_fill_color(*P["white"])
        self.rect(0, 36, 210, 1.5, "F")
        self.ln(8)

    # ── Footer ───────────────────────────────────────────────────────────────
    def footer(self):
        self.set_y(-13)
        self.set_fill_color(*P["muted"])
        self.rect(0, self.get_y()-1, 210, 14, "F")
        # Bottom accent line
        self.set_fill_color(*self.cc)
        self.rect(0, self.get_y()-1, 210, 2, "F")
        self.set_font("F", "I", 7.5)
        self.set_text_color(*P["gray"])
        self.set_y(self.get_y()+2)
        self.cell(0, 6, f"Lingua Bot  |  {self.lesson_title}  |  Page {self.page_no()}", align="C")

    # ── Section heading ──────────────────────────────────────────────────────
    def h2(self, text: str):
        self.ln(4)
        y = self.get_y()
        # Left bar
        self.set_fill_color(*self.cc)
        self.rect(16, y, 3.5, 9, "F")
        # Light bg
        self.set_fill_color(*P["muted"])
        self.rect(19.5, y, 174.5, 9, "F")
        self.set_xy(23, y)
        self.set_font("F", "B", 11)
        self.set_text_color(*P["dark"])
        self.cell(0, 9, _clean(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)

    def h3(self, text: str):
        self.ln(2)
        self.set_font("F", "B", 10)
        self.set_text_color(*self.cc)
        self.cell(0, 7, _clean(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ── Body ─────────────────────────────────────────────────────────────────
    def body(self, text: str):
        self.set_font("F", "", 10)
        self.set_text_color(*P["dark"])
        self.multi_cell(0, 5.5, _clean(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(0.5)

    # ── Bullet ───────────────────────────────────────────────────────────────
    def bullet(self, text: str, level: int = 0):
        x = self.get_x() + level * 5
        y = self.get_y()
        r, g, b = self.cc
        self.set_fill_color(r, g, b)
        self.ellipse(x + 1, y + 2, 3, 3, "F")
        self.set_xy(x + 7, y)
        self.set_font("F", "", 10)
        self.set_text_color(*P["dark"])
        self.multi_cell(0, 5.5, _clean(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ── Numbered ─────────────────────────────────────────────────────────────
    def numbered(self, n: int, text: str):
        x, y = self.get_x(), self.get_y()
        # Number circle bg
        self.set_fill_color(*self.cc)
        self.ellipse(x, y, 7, 7, "F")
        self.set_font("F", "B", 8)
        self.set_text_color(*P["white"])
        self.set_xy(x, y - 0.5)
        self.cell(7, 7, str(n), align="C")
        self.set_xy(x + 10, y)
        self.set_font("F", "", 10)
        self.set_text_color(*P["dark"])
        self.multi_cell(0, 5.5, _clean(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ── MC option ────────────────────────────────────────────────────────────
    def mc_opt(self, label: str, text: str, is_answer: bool = False):
        x, y = self.get_x(), self.get_y()
        if is_answer:
            self.set_fill_color(*P["greenbg"])
            self.set_draw_color(*P["green"])
        else:
            self.set_fill_color(*P["muted"])
            self.set_draw_color(*P["border"])
        self.rounded_rect(x, y, 178, 7, 2, "FD")
        # Label circle
        self.set_fill_color(*(self.cc if not is_answer else P["green"]))
        self.ellipse(x + 2, y + 1, 5, 5, "F")
        self.set_font("F", "B", 8)
        self.set_text_color(*P["white"])
        self.set_xy(x + 2, y + 0.5)
        self.cell(5, 5, label, align="C")
        # Text
        self.set_font("F", "", 9)
        self.set_text_color(*(P["dark"] if not is_answer else (5, 100, 60)))
        self.set_xy(x + 10, y + 1)
        self.cell(166, 5.5, _clean(text)[:70])
        self.ln(8)

    # ── Answer box ───────────────────────────────────────────────────────────
    def answer_box(self, text: str):
        x, y = self.get_x(), self.get_y()
        # Green success box
        self.set_fill_color(*P["greenbg"])
        self.set_draw_color(*P["green"])
        self.rounded_rect(x, y, 178, 7, 2, "FD")
        self.set_fill_color(*P["green"])
        self.rect(x, y, 3, 7, "F")
        self.set_font("F", "B", 9)
        self.set_text_color(5, 100, 60)
        self.set_xy(x + 6, y + 1)
        self.cell(170, 5.5, _clean(text))
        self.ln(8)

    # ── Info / callout box ───────────────────────────────────────────────────
    def callout(self, text: str, style: str = "info"):
        palettes = {
            "info":    (P["bluebg"],  P["blue"],  P["blue"]),
            "success": (P["greenbg"], P["green"], (5,100,60)),
            "warning": ((255,251,235), (245,158,11), (120,77,5)),
        }
        bg, border, txt_col = palettes.get(style, palettes["info"])
        x, y = self.get_x(), self.get_y()
        clean = _clean(text)
        lines_est = max(1, len(clean)//70 + clean.count('\n') + 1)
        h = lines_est * 5.5 + 8
        self.set_fill_color(*bg)
        self.set_draw_color(*border)
        self.rounded_rect(x, y, 178, h, 3, "FD")
        self.set_fill_color(*border)
        self.rect(x, y, 3.5, h, "F")
        self.set_xy(x + 8, y + 4)
        self.set_font("F", "I", 9)
        self.set_text_color(*txt_col)
        self.multi_cell(168, 5.5, clean, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(3)

    # ── Table ─────────────────────────────────────────────────────────────────
    def draw_table(self, rows: list):
        if not rows:
            return
        ncols = max(len(r) for r in rows)
        avail = 178
        # First column wider if only 2 cols
        if ncols == 2:
            col_ws = [avail * 0.35, avail * 0.65]
        else:
            col_ws = [avail / ncols] * ncols

        for i, row in enumerate(rows):
            hdr = (i == 0)
            row_h = 7
            if hdr:
                self.set_fill_color(*self.cc)
                self.set_font("F", "B", 9)
                self.set_text_color(*P["white"])
            else:
                bg = P["muted"] if i % 2 == 0 else P["white"]
                self.set_fill_color(*bg)
                self.set_font("F", "", 9)
                self.set_text_color(*P["dark"])
            for j, cell in enumerate(row):
                w = col_ws[j] if j < len(col_ws) else col_ws[-1]
                self.cell(w, row_h, _clean(str(cell))[:45],
                           border=1, fill=True, align="C" if hdr else "L")
            self.ln(row_h)
        self.ln(4)

    # ── Divider ───────────────────────────────────────────────────────────────
    def divider(self):
        y = self.get_y() + 2
        self.set_draw_color(*P["border"])
        # Dashed style via segments
        x = 16
        while x < 194:
            self.line(x, y, min(x + 6, 194), y)
            x += 10
        self.ln(5)

    def rounded_rect(self, x, y, w, h, r, style=""):
        """Draw a rounded rectangle."""
        k = self.k
        hp = self.h
        if style == "F":
            op = "f"
        elif style in ("FD", "DF"):
            op = "B"
        else:
            op = "S"
        self._out((
            f"{(x + r) * k:.2f} {(hp - y) * k:.2f} m "
            f"{(x + w - r) * k:.2f} {(hp - y) * k:.2f} l "
            f"{(x + w) * k:.2f} {(hp - y) * k:.2f} {(x + w) * k:.2f} {(hp - y - r) * k:.2f} v "
            f"{(x + w) * k:.2f} {(hp - y - h + r) * k:.2f} l "
            f"{(x + w) * k:.2f} {(hp - y - h) * k:.2f} {(x + w - r) * k:.2f} {(hp - y - h) * k:.2f} v "
            f"{(x + r) * k:.2f} {(hp - y - h) * k:.2f} l "
            f"{x * k:.2f} {(hp - y - h) * k:.2f} {x * k:.2f} {(hp - y - h + r) * k:.2f} v "
            f"{x * k:.2f} {(hp - y - r) * k:.2f} l "
            f"{x * k:.2f} {(hp - y) * k:.2f} {(x + r) * k:.2f} {(hp - y) * k:.2f} v "
            f"{op}"
        ))


def _render_block(pdf: LessonPDF, block_text: str):
    lines = block_text.split("\n")
    tbl_buf = []
    num_n = 1

    for raw in lines:
        line = raw.strip()

        if _is_tbl(line):
            tbl_buf.append(line)
            continue
        else:
            if tbl_buf:
                pdf.draw_table(_parse_tbl(tbl_buf))
                tbl_buf = []

        if not line:
            pdf.ln(2)
            continue

        # H2 — full bold line
        if line.startswith("**") and line.endswith("**") and len(line) > 4:
            pdf.h2(line.strip("*"))
            num_n = 1

        # H3 — partial bold
        elif re.match(r"^\*\*.+\*\*\s+\S", line):
            pdf.h3(re.sub(r'\*\*', '', line.split("**")[1]))

        # Bullet
        elif re.match(r"^[-*]\s+", line):
            pdf.bullet(line[2:])

        # Sub-bullet
        elif re.match(r"^\s{2,}[-*]\s+", line):
            pdf.bullet(line.lstrip()[2:], level=1)

        # Numbered
        elif re.match(r"^\d+[\.\)]\s+\S", line):
            m = re.match(r"^(\d+)[\.\)]\s+(.*)", line)
            if m:
                pdf.numbered(int(m.group(1)), m.group(2))
                num_n = int(m.group(1)) + 1

        # MC option
        elif re.match(r"^[a-dA-D][\.\)]\s*\S", line):
            label = line[0].upper()
            pdf.mc_opt(label, line[2:].strip())

        # Answer key
        elif re.match(r"^\d+\s*[-\u2013]\s*[a-zA-Z]\b", line.strip()):
            pdf.answer_box(line)

        # Model / tip
        elif re.match(r"(?i)^(speaking model|example:|tip:|note:|remember:)", line):
            pdf.callout(line, "info")

        # Plain
        else:
            pdf.body(line)

    if tbl_buf:
        pdf.draw_table(_parse_tbl(tbl_buf))


def generate_lesson_pdf(lesson_title: str, category: str, cat_label: str,
                        content_blocks: list) -> str:
    pdf = LessonPDF(lesson_title, category, cat_label)
    pdf.add_page()
    for i, block in enumerate(content_blocks):
        _render_block(pdf, block)
        if i < len(content_blocks) - 1:
            pdf.divider()
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, prefix=f"{category}_")
    path = tmp.name; tmp.close()
    pdf.output(path)
    return path
