"""Student lesson browsing with registration check."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

from core import database as db
from bot.keyboards import student_lessons, student_cats
from bot.handlers.student.register import check_and_register


_BADGES = {
    "test_quiz": "🎯",
    "listening": "🎧",
    "reading": "📚",
    "speaking": "🗣",
    "vocabulary": "📖",
    "writing": "✍️",
    "homework": "📝",
    "visuals": "🖼",
}


def _lesson_text(lesson, cats):
    lesson = dict(lesson)
    topic = lesson.get("topic") or ""
    badges = [v for k, v in _BADGES.items() if k in cats] + ["🎮", "🔗"]
    line = "  ".join(badges[:6])

    return (
        f"{lesson['emoji']} *{lesson['title']}*\n"
        + (f"📌 _{topic}_\n" if topic else "")
        + f"\n{line}\n\nBo'limni tanlang:"
    )


async def show_lessons(update, context):
    ok = await check_and_register(update, context)
    if not ok:
        return

    u = update.effective_user
    student = db.get_student(u.id)

    name = (
        dict(student).get("full_name")
        or u.first_name
        or "Student"
    ) if student else (u.first_name or "Student")

    lessons = db.all_lessons()

    if update.callback_query:
        await update.callback_query.answer()

    if not lessons:
        text = f"📚 *Lingua Bot*\n\nSalom, *{name}*!\n\nHozircha darslar yo'q."
        kb = None
    else:
        text = f"📚 *Lingua Bot*\n\nSalom, *{name}*! Darsni tanlang:"
        kb = student_lessons(lessons)
        kb = InlineKeyboardMarkup(
            list(kb.inline_keyboard) + [
                [InlineKeyboardButton("👤 Mening profilim", callback_data="my_profile")]
            ]
        )

    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb
            )
        else:
            await update.effective_message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb
            )
    except Exception:
        await update.effective_chat.send_message(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb
        )


async def show_lesson(update, context, lid):
    ok = await check_and_register(update, context)
    if not ok:
        return

    await update.callback_query.answer()

    lesson = db.get_lesson(lid)
    if not lesson:
        await update.callback_query.answer("Dars topilmadi.", show_alert=True)
        return

    db.log(update.effective_user.id, lid, action="view")

    cats = db.available_categories(lid)
    text = _lesson_text(lesson, cats)
    kb = student_cats(lid, cats)

    try:
        await update.callback_query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb
        )
    except Exception:
        try:
            await update.callback_query.message.delete()
        except Exception:
            pass

        await update.effective_chat.send_message(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb
        )
