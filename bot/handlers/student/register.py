"""Student registration — one-time on first entry."""
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from core import database as db

logger = logging.getLogger(__name__)


async def check_and_register(update, context):
    u = update.effective_user

    if not u:
        return True

    name = f"{u.first_name or ''} {u.last_name or ''}".strip()
    db.upsert_student(u.id, u.username or "", name)

    if db.is_registered(u.id):
        return True

    await start_registration(update, context)
    return False


async def start_registration(update, context):
    u = update.effective_user
    context.user_data["reg_step"] = "full_name"

    text = (
        f"👋 *Hello, {u.first_name}!*\n\n"
        "📚 Welcome to *Lingua Bot*!\n\n"
        "To use the bot, you need to register once.\n\n"
        "📝 *Enter your full name:*\n"
        "_First name Last name, for example: Sardor Usmonov_"
    )

    if update.callback_query:
        await update.callback_query.answer()

        try:
            await update.callback_query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception:
            await update.effective_chat.send_message(
                text,
                parse_mode=ParseMode.MARKDOWN,
            )

    else:
        await update.effective_chat.send_message(
            text,
            parse_mode=ParseMode.MARKDOWN,
        )


async def handle_registration_text(update, context):
    step = context.user_data.get("reg_step")

    if not step:
        return False

    text = update.message.text.strip()

    if step == "full_name":
        if len(text) < 3:
            await update.message.reply_text(
                "⚠️ Please enter your full name, at least 3 characters."
            )
            return True

        context.user_data["reg_full_name"] = text
        context.user_data["reg_step"] = "group"

        await update.message.reply_text(
            f"✅ *{text}*\n\n"
            "📚 *Which group are you in?*\n"
            "_Enter your group name, for example: IDU-25-1_",
            parse_mode=ParseMode.MARKDOWN,
        )

        return True

    if step == "group":
        if len(text) < 1:
            await update.message.reply_text("⚠️ Please enter your group name.")
            return True

        full_name = context.user_data.pop("reg_full_name", "")
        context.user_data.pop("reg_step", None)

        db.register_student(update.effective_user.id, full_name, text)

        await update.message.reply_text(
            f"🎉 *Registration completed!*\n\n"
            f"👤 Name: *{full_name}*\n"
            f"📚 Group: *{text}*\n\n"
            "Start learning:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("📚 View lessons", callback_data="student")]]
            ),
        )

        return True

    return False


async def show_profile(update, context):
    await update.callback_query.answer()

    u = update.effective_user
    student = db.get_student(u.id)

    if not student:
        await update.callback_query.answer("Profile not found.", show_alert=True)
        return

    student = dict(student)
    stats = db.student_stats(u.id)

    name = student.get("full_name") or u.first_name or "Unknown"
    group = student.get("group_name") or "Not specified"
    joined = (student.get("joined_at") or "")[:10]

    text = (
        "👤 *My Profile*\n\n"
        f"📛 Name: *{name}*\n"
        f"📚 Group: *{group}*\n"
        f"📅 Joined: *{joined}*\n\n"
        "📊 *Statistics:*\n"
        f"👁 Viewed: *{stats['views']}* times\n"
        f"📝 Submitted: *{stats['tasks']}* tasks\n"
        f"🎯 Quizzes: *{stats['quiz_count']}* | Average: *{stats['avg_score']}%*"
    )

    await update.callback_query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🏠 Home", callback_data="student")]]
        ),
    )
