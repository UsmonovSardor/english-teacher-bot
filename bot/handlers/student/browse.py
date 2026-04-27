"""Student lesson browsing — premium design."""
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from core import database as db
from bot.keyboards import student_lessons, student_cats

_BADGES = {
    "test_quiz":  "🎯 Quiz",
    "listening":  "🎧 Audio",
    "reading":    "📚 Reading",
    "speaking":   "🗣 Speaking",
    "vocabulary": "📖 Vocab",
    "writing":    "✍️ Writing",
    "homework":   "📝 HW",
    "visuals":    "🖼 Visuals",
}

def _register(u):
    if u:
        name = f"{u.first_name or ''} {u.last_name or ''}".strip()
        db.upsert_student(u.id, u.username or "", name)

def _lesson_text(lesson, cats):
    # sqlite3.Row → dict for safe .get() usage
    lesson = dict(lesson)
    topic = lesson.get("topic") or ""
    badges = [v for k, v in _BADGES.items() if k in cats]
    badges += ["🎮 Games", "🔗 Resources"]
    line = "  •  ".join(badges[:5])
    return (
        f"{lesson['emoji']} *{lesson['title']}*\n"
        + (f"📌 _{topic}_\n" if topic else "")
        + f"\n{line}\n\nChoose a section:"
    )

async def show_lessons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _register(update.effective_user)
    lessons = db.all_lessons()
    if update.callback_query:
        await update.callback_query.answer()

    if not lessons:
        text = "📚 *Lingua Bot*\n\nNo lessons available yet. Check back soon!"
        kb   = None
    else:
        text = "📚 *Lingua Bot — English Learning*\n\nChoose a lesson:"
        kb   = student_lessons(lessons)

    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        else:
            await update.effective_message.reply_text(
                text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    except Exception:
        await update.effective_chat.send_message(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

async def show_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE, lid: int):
    _register(update.effective_user)
    await update.callback_query.answer()
    lesson = db.get_lesson(lid)
    if not lesson:
        await update.callback_query.answer("Lesson not found.", show_alert=True)
        return

    db.log(update.effective_user.id, lid, action="view")
    cats = db.available_categories(lid)
    text = _lesson_text(lesson, cats)
    kb   = student_cats(lid, cats)

    try:
        await update.callback_query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    except Exception:
        try:
            await update.callback_query.message.delete()
        except Exception:
            pass
        await update.effective_chat.send_message(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
