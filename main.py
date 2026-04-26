"""
Lingua Bot — main entry point.
Professional English learning Telegram bot.
"""
import logging
from telegram import Update, BotCommand, MenuButton, MenuButtonCommands
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters,
)
from core.config import BOT_TOKEN, State
from core import database as db
from bot.keyboards import start_kb
from bot.handlers import admin as A, student as S

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Commands ──────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context):
    u = update.effective_user
    name = u.first_name or "there"
    # Register student
    full = f"{u.first_name or ''} {u.last_name or ''}".strip()
    db.upsert_student(u.id, u.username or "", full)

    await update.message.reply_text(
        f"👋 *Hello, {name}!*\n\n"
        f"Welcome to *Lingua Bot* 🎓\n"
        f"Your personal English learning assistant.\n\n"
        f"Choose your role:",
        parse_mode="Markdown",
        reply_markup=start_kb())


async def cmd_menu(update: Update, context):
    """Show main menu."""
    await cmd_start(update, context)


async def cmd_lessons(update: Update, context):
    """Quick access to lessons."""
    class FakeQuery:
        async def answer(self): pass
        async def edit_message_text(self, *a, **kw):
            await update.message.reply_text(*a, **kw)
        message = update.message

    update.callback_query = FakeQuery()
    await S.show_lessons(update, context)


async def cmd_help(update: Update, context):
    await update.message.reply_text(
        "🤖 *Lingua Bot Help*\n\n"
        "📚 /lessons — Browse all lessons\n"
        "🏠 /menu — Main menu\n"
        "❓ /help — Show this message\n\n"
        "_Choose Student Zone to start learning or Admin Panel to manage content._",
        parse_mode="Markdown")


# ── Callback router ───────────────────────────────────────────────────────────

async def route(update: Update, context):
    data = update.callback_query.data

    # ── Student ──────────────────────────────────────────────────────────
    if data == "student":
        await S.show_lessons(update, context)
    elif data.startswith("sl_"):
        await S.show_lesson(update, context, int(data[3:]))
    elif data.startswith("sc_"):
        parts = data[3:].split("_", 1)
        await S.show_category(update, context, int(parts[0]), parts[1])
    elif data.startswith(("gstart_","gv_","gm_","gs_","glb_","ga_","gq_")):
        await S.handle_game(update, context, data)

    # ── Admin top ─────────────────────────────────────────────────────────
    elif data == "a_main":    await A._show_main(update, context)
    elif data == "a_logout":  await A.admin_logout(update, context)
    elif data == "a_analytics": await A.show_analytics(update, context)
    elif data == "a_leaderboard": await A.show_leaderboard(update, context)
    elif data == "a_lessons": await A.show_lessons(update, context)
    elif data == "a_new":     await A.new_lesson_start(update, context)

    # ── Admin lesson ──────────────────────────────────────────────────────
    elif data.startswith("al_"):
        lid = int(data[3:])
        await A.show_lesson(update, context, lid)
    elif data.startswith("aup_"):
        await A.upload_start(update, context, int(data[4:]))
    elif data.startswith("aec_"):
        await A.show_cats(update, context, int(data[4:]))
    elif data.startswith("aren_"):
        lid = int(data[5:])
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("✏️ Send the new lesson title:")
        context.user_data["rename_lid"] = lid
    elif data.startswith("adel_confirm_"):
        await A.delete_lesson_exec(update, context, int(data[13:]))
    elif data.startswith("adel_"):
        await A.delete_lesson_confirm(update, context, int(data[5:]))
    elif data.startswith("aqs_"):
        await A.show_quiz_stats(update, context, int(data[4:]))

    # ── Admin category ────────────────────────────────────────────────────
    elif data.startswith("acat_"):
        rest  = data[5:]
        lid, cat = rest.split("_", 1)
        await A.show_cat(update, context, int(lid), cat)
    elif data.startswith("aadd_"):
        rest  = data[5:]
        lid, cat = rest.split("_", 1)
        await A.add_content_start(update, context, int(lid), cat)
    elif data.startswith("aclr_"):
        rest  = data[5:]
        lid, cat = rest.split("_", 1)
        await A.clear_cat(update, context, int(lid), cat)
    elif data.startswith("aeit_"):
        await A.edit_item_start(update, context, int(data[5:]))
    elif data.startswith("adit_"):
        await A.del_item(update, context, int(data[5:]))


# ── General message router ────────────────────────────────────────────────────

async def general_msg(update: Update, context):
    if context.user_data.get("rename_lid"):
        await A.rename_lesson(update, context); return
    if context.user_data.get("edit_cid") or context.user_data.get("add_content"):
        await A.save_content(update, context); return
    if update.message.document and context.user_data.get("upload_lid"):
        await A.receive_doc(update, context); return


# ── App setup ─────────────────────────────────────────────────────────────────

async def post_init(app):
    """Set bot commands and menu button after startup."""
    commands = [
        BotCommand("start",   "Welcome screen"),
        BotCommand("menu",    "Main menu"),
        BotCommand("lessons", "Browse lessons"),
        BotCommand("help",    "How to use this bot"),
    ]
    await app.bot.set_my_commands(commands)
    await app.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    logger.info("Bot commands set.")


def build():
    db.init_db()
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # Login conversation
    login_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(A.admin_entry, pattern="^admin$")],
        states={
            State.LOGIN_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, A.got_username)],
            State.LOGIN_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, A.got_password)],
            State.ADD_LESSON: [MessageHandler(filters.TEXT & ~filters.COMMAND, A.new_lesson_save)],
            State.EDIT_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, A.save_content)],
        },
        fallbacks=[CommandHandler("start", cmd_start)],
        allow_reentry=True,
    )
    new_lesson_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(A.new_lesson_start, pattern="^a_new$")],
        states={State.ADD_LESSON: [MessageHandler(filters.TEXT & ~filters.COMMAND, A.new_lesson_save)]},
        fallbacks=[CommandHandler("start", cmd_start)],
        allow_reentry=True,
    )
    add_content_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(
            lambda u,c: A.add_content_start(u, c,
                int(u.callback_query.data[5:].split("_",1)[0]),
                u.callback_query.data[5:].split("_",1)[1]),
            pattern="^aadd_")],
        states={State.EDIT_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, A.save_content)]},
        fallbacks=[CommandHandler("start", cmd_start)],
        allow_reentry=True,
    )
    edit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(
            lambda u,c: A.edit_item_start(u, c, int(u.callback_query.data[5:])),
            pattern="^aeit_")],
        states={State.EDIT_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, A.save_content)]},
        fallbacks=[CommandHandler("start", cmd_start)],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("menu",    cmd_menu))
    app.add_handler(CommandHandler("lessons", cmd_lessons))
    app.add_handler(CommandHandler("help",    cmd_help))
    app.add_handler(login_conv)
    app.add_handler(new_lesson_conv)
    app.add_handler(add_content_conv)
    app.add_handler(edit_conv)
    app.add_handler(CallbackQueryHandler(route))
    app.add_handler(MessageHandler(filters.Document.ALL, A.receive_doc))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, general_msg))

    return app


if __name__ == "__main__":
    logger.info("🚀 Lingua Bot starting…")
    build().run_polling(allowed_updates=Update.ALL_TYPES)
