"""Admin authentication — no ConversationHandler, uses user_data state."""

import logging

from telegram import Update
from telegram.constants import ParseMode

from core import database as db
from core.config import ADMIN_USERNAME, ADMIN_PASSWORD
from bot.keyboards import admin_main

logger = logging.getLogger(__name__)


async def admin_entry_direct(update: Update, context):
    await update.callback_query.answer()

    if db.is_admin(update.effective_chat.id):
        from bot.handlers.admin.lessons import _show_main
        await _show_main(update, context)
        return

    context.user_data.clear()
    context.user_data["waiting_login_user"] = True

    await update.callback_query.edit_message_text(
        "🔐 *Admin Login*\n\nEnter your *username*:",
        parse_mode=ParseMode.MARKDOWN,
    )


async def process_username(update: Update, context):
    username = (update.message.text or "").strip()

    if not username:
        await update.message.reply_text("⚠️ Username cannot be empty.")
        context.user_data["waiting_login_user"] = True
        return

    context.user_data.pop("waiting_login_user", None)
    context.user_data["_admin_username"] = username
    context.user_data["waiting_login_pass"] = True

    await update.message.reply_text(
        "🔑 Enter your *password*:",
        parse_mode=ParseMode.MARKDOWN,
    )


async def process_password(update: Update, context):
    password = (update.message.text or "").strip()
    username = context.user_data.pop("_admin_username", "")

    context.user_data.pop("waiting_login_pass", None)

    try:
        await update.message.delete()
    except Exception:
        pass

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        db.set_admin(update.effective_chat.id, True)
        context.user_data.clear()

        cnt = db.student_count()

        await update.effective_chat.send_message(
            f"✅ *Welcome, Admin!* 👋\n\n👥 {cnt} students registered",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_main(),
        )
        return

    logger.warning("Failed admin login attempt: username='%s'", username)

    context.user_data.clear()
    context.user_data["waiting_login_user"] = True

    await update.effective_chat.send_message(
        "❌ *Wrong credentials.*\n\nPlease enter your *username* again:",
        parse_mode=ParseMode.MARKDOWN,
    )


async def admin_logout(update: Update, context):
    db.set_admin(update.effective_chat.id, False)
    context.user_data.clear()

    await update.callback_query.answer("Logged out.")
    await update.callback_query.edit_message_text(
        "🚪 Logged out.\n\nUse /start to log in again."
    )
