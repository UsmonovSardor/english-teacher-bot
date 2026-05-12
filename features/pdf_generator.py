"""
Professional PDF generator — Lingua Bot.
"""

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


def generate_lesson_pdf(
    lesson_title,
    category,
    cat_label,
    content_blocks,
):
    """
    Temporary safe PDF generator.
    Prevents bot crash if old generator was deleted.
    """

    from fpdf import FPDF
    import tempfile

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.add_page()

    color = CAT_COLORS.get(category, (37, 99, 235))

    pdf.set_fill_color(*color)
    pdf.rect(0, 0, 210, 25, "F")

    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 18)
    pdf.set_xy(10, 8)
    pdf.cell(0, 8, lesson_title)

    pdf.ln(30)

    pdf.set_text_color(0, 0, 0)

    for block in content_blocks:
        text = str(block).strip()

        if not text:
            continue

        pdf.set_font("Arial", "", 12)
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
}
