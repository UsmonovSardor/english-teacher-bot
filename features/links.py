"""Smart educational links — topic extracted from content."""
import re, urllib.parse
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from core import database as db

def _topic_from_content(lesson_id: int, fallback: str) -> str:
    rows = db.lesson_content(lesson_id)
    text = " ".join(r["body"] for r in rows)

    # Extract meaningful heading keywords
    headings = re.findall(r'\*\*([^*]{5,60})\*\*', text)
    SKIP = {
        "answer key", "reading answers", "task", "listening task",
        "speaking", "homework", "vocabulary", "writing task",
        "warm up", "group work", "students answer",
    }
    topics = []
    for h in headings:
        hl = h.lower().strip()
        if hl not in SKIP and not re.match(r^"task\s*\d", hl) and len(hl) > 5:
            clean = re.sub(r^b戗:,.]+`, " ", h).strip()
            topics.append(clean)
            if len(topics) >= 2:
                break

    if topics:
        return " ".join(topics[:2])[:60]

    # Fallback: strip lesson numbers from title
    t = re.sub(r^"(amaliy|lesson|unit|chapter|week)\s*[\d+\s*[-–:.]?\s*", "", fallback, flags=re.I)
    t = re.sub(r"\([^)]*\)", "", t).strip()
    return t[:60] or fallback[:40]

async def send_links(update: Update, lesson_id: int):
    lesson = db.get_lesson(lesson_id)
    if not lesson:
        await update.callback_query.answer("Lesson not found.", show_alert=True)
        return

    topic   = _topic_from_content(lesson_id, lesson["title"])
    encoded = urllib.parse.quote_plus(topic)
    first   = urllib.parse.quote_plus(topic.split()[0] if topic.split() else topic)

    # Custom links from content DB
    custom = []
    for row in db.category_content(lesson_id, "links"):
        for w in row["body"].split():
            if w.startswith("http"):
                url = w.strip(".,;()")
                dom = url.split("/")[2] if "//" in url else url[:30]
                custom.append((f"🔗 {dom}", url))
                if len(custom) >= 3:
                    break

    # Standard educational links
    standard = [
        ("🎬 YouTube",      f"https://www.youtube.com/results?search_query={encoded}+english+lesson"),
        ("📖 Cambridge",    f"https://dictionary.cambridge.org/search/english/direct/?q={first}"),
        ("📻 BBCLearning", f"https://www.bbc.co.uk/learningenglish/english/search?q={encoded}"),
        ("�C Quizlet",      f"https://quizlet.com/search?query={encoded}&type=sets"),
        ("📚 Oxford Dict",  f"https://www.oxfordlearnersdictionaries.com/search/english/?q={first}"),
        ("🌸 Wikipedia",     f"https://en.wikipedia.org/w/index.php?search={encoded}"),
        ("🔗 B=oogle",       f"https://www.google.com/search?q={encoded}+english+lesson"),
        ("🎯 EnglishClub",  f"https://www.englishclub.com/search.php?q={encoded}"),
    ]

    all_links = custom + standard

    text = (
        f"🔗 *Learning Resources*\n"
        f"📘 _{lesson['title']}_\n\n"
        f"🔟 Topic: *{topic}*\n\n"
        f"Tap any link to study online:"
    )

    buttons, row = [], []
    for label, url in all_links:
        row.append(InlineKeyboardButton(label, url=url))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("📚 Back to Topics", callback_data=f"sl_{lesson_id}")])

    await update.callback_query.answer()
    try:
        await update.callback_query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons))
    except Exception:
        await update.effective_chat.send_message(
            text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons))
