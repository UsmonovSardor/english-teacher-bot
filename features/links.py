"""Smart educational links — custom first, YouTube + 3 standard."""
import re, urllib.parse
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from core import database as db

def _topic(lesson_id, fallback):
    rows = db.lesson_content(lesson_id)
    text = " ".join(r["body"] for r in rows)
    headings = re.findall(r'\*\*([^*]{5,60})\*\*', text)
    SKIP = {"answer key","reading answers","task","listening task","speaking",
            "homework","vocabulary","writing task","warm up","group work"}
    topics = []
    for h in headings:
        hl = h.lower().strip()
        if hl not in SKIP and not re.match(r"^task\s*\d", hl) and len(hl) > 5:
            topics.append(re.sub(r"[–\-:,\.]+", " ", h).strip())
            if len(topics) >= 2: break
    if topics: return " ".join(topics[:2])[:60]
    t = re.sub(r"^(amaliy|lesson|unit|chapter|week)\s*[\d]+\s*[-–:.]?\s*", "", fallback, flags=re.I)
    return re.sub(r"\([^)]*\)", "", t).strip()[:60] or fallback[:40]

async def send_links(update, lesson_id):
    lesson = db.get_lesson(lesson_id)
    if not lesson: await update.callback_query.answer("Dars topilmadi.", show_alert=True); return
    lesson = dict(lesson)
    topic   = _topic(lesson_id, lesson["title"])
    encoded = urllib.parse.quote_plus(topic)
    first   = urllib.parse.quote_plus(topic.split()[0] if topic.split() else topic)

    custom = []
    for row in db.category_content(lesson_id, "links"):
        body = row["body"].strip()
        if "|" in body:
            p = body.split("|",1); label = p[0].strip()[:20]; url = p[1].strip().split()[0]
        else:
            url = body.strip().split()[0] if body.strip() else ""
            if not url.startswith("http"): continue
            label = url.split("/")[2][:20] if "//" in url else url[:20]
        if url.startswith("http"): custom.append(InlineKeyboardButton(f"🔗 {label}", url=url))

    standard = [
        ("🎬 YouTube",   f"https://www.youtube.com/results?search_query={encoded}+english+lesson"),
        ("📖 Cambridge", f"https://dictionary.cambridge.org/search/english/direct/?q={first}"),
        ("🃏 Quizlet",   f"https://quizlet.com/search?query={encoded}&type=sets"),
        ("📻 BBC",       f"https://www.bbc.co.uk/learningenglish/english/search?q={encoded}"),
    ]

    text = (f"🔗 *O'quv resurslari*\n📘 _{lesson['title']}_\n\n"
            f"🔎 Mavzu: *{topic}*\n\nIstalgan havolani bosing:")
    buttons = []
    row = []
    for btn in custom:
        row.append(btn)
        if len(row) == 2: buttons.append(row); row = []
    if row: buttons.append(row)
    row = []
    for label, url in standard:
        row.append(InlineKeyboardButton(label, url=url))
        if len(row) == 2: buttons.append(row); row = []
    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton("📚 Darsga qaytish", callback_data=f"sl_{lesson_id}")])

    await update.callback_query.answer()
    try:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons))
    except:
        await update.effective_chat.send_message(text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons))
