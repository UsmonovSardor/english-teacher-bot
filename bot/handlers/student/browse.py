"""Student lesson browsing."""
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from core import database as db
from bot.keyboards import student_lessons, student_cats


def _register(u):
    if u:
        name = f"{u.first_name or ''} {u.last_name or ''}".strip()
        db.upsert_student(u.id, u.username or "", name)


async def show_lessons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _register(update.effective_user)
    lessons = db.all_lessons()
    if update.callback_query:
        await update.callback_query.answer()

    if not lessons:
        text, kb = "📚 *Lingua Bot*\n\nNo lessons available yet. Check back soon!", None
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
        await update.callback_query.edit_message_text("Lesson not found."); return

    db.log(update.effective_user.id, lid, action="view")
    cats = db.available_categories(lid)

    badges = []
    if "test_quiz" in cats or "listening" in cats: badges.append("🎯 Interactive Quiz")
    badges.append("🎮 Games")
    badges.append("🔗 Web Resources")
    if any(c not in ("test_quiz","games","links") for c in cats):
        badges.append("📄 PDF Materials")

    await update.callback_query.edit_message_text(
        f"{lesson['emoji']} *{lesson['title']}*\n\n"
        + "  •  ".join(badges)
        + "\n\nChoose a section:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=student_cats(lid, cats))
