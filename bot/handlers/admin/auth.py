"""Admin authentication handlers."""
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
from core import database as db
from core.config import ADMIN_USERNAME, ADMIN_PASSWORD, State
from bot.keyboards import admin_main


async def admin_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cq = update.callback_query
    await cq.answer()
    if db.is_admin(update.effective_chat.id):
        from bot.handlers.admin.lessons import _show_main
        await _show_main(update, context)
        return ConversationHandler.END
    await cq.edit_message_text(
        "🔐 *Admin Login*\n\nEnter your *username*:",
        parse_mode=ParseMode.MARKDOWN)
    return State.LOGIN_USER


async def got_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["_u"] = update.message.text.strip()
    await update.message.reply_text("🔑 Enter your *password*:", parse_mode=ParseMode.MARKDOWN)
    return State.LOGIN_PASS


async def got_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uname = context.user_data.pop("_u", "")
    pwd   = update.message.text.strip()
    try: await update.message.delete()
    except: pass

    if uname == ADMIN_USERNAME and pwd == ADMIN_PASSWORD:
        db.set_admin(update.effective_chat.id, True)
        cnt = db.student_count()
        await update.effective_chat.send_message(
            f"✅ *Welcome, Admin!* 👋\n\n👥 {cnt} students registered",
            parse_mode=ParseMode.MARKDOWN, reply_markup=admin_main())
    else:
        await update.effective_chat.send_message(
            "❌ Wrong credentials. Use /start to try again.")
    return ConversationHandler.END


async def admin_logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.set_admin(update.effective_chat.id, False)
    await update.callback_query.answer("Logged out.")
    await update.callback_query.edit_message_text(
        "🚪 Logged out.\nUse /start to log in again.")
