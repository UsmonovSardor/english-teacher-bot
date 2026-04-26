"""Lingua Bot — absolute minimal debug version."""
import logging, sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from core.config import BOT_TOKEN
from core import database as db

# Force stdout logging
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.DEBUG,
    stream=sys.stdout,
    force=True
)
logger = logging.getLogger(__name__)


async def cmd_start(update: Update, context):
    print(f"PRINT: /start from {update.effective_user.id}", flush=True)
    logger.warning("!!! /start received from user_id=%s", update.effective_user.id)
    u = update.effective_user
    try:
        db.upsert_student(u.id, u.username or "", f"{u.first_name or ''} {u.last_name or ''}".strip())
    except Exception as e:
        logger.error("DB error: %s", e)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("👨‍💼 Admin Panel",  callback_data="admin"),
         InlineKeyboardButton("📚 Student Zone", callback_data="student")],
    ])
    await update.message.reply_text(
        f"👋 *Hello, {u.first_name}!*\n\n"
        "Welcome to *Lingua Bot* 🎓\nChoose your role:",
        parse_mode="Markdown", reply_markup=kb)
    print(f"PRINT: reply sent to {u.id}", flush=True)


async def any_message(update: Update, context):
    print(f"PRINT: ANY_MESSAGE type={update.effective_message.text if update.effective_message else '?'}", flush=True)
    logger.warning("!!! ANY_MESSAGE received")
    # Don't process commands here
    if update.message and update.message.text and update.message.text.startswith('/'):
        return


async def callback_route(update: Update, context):
    data = update.callback_query.data
    print(f"PRINT: callback data={data}", flush=True)
    logger.warning("!!! CALLBACK: %s", data)
    try:
        if data == "student":
            from bot.handlers.student.browse import show_lessons
            await show_lessons(update, context)
        elif data == "admin":
            from bot.handlers.admin.auth import admin_entry_direct
            await admin_entry_direct(update, context)
        elif data.startswith("sl_"):
            from bot.handlers.student.browse import show_lesson
            await show_lesson(update, context, int(data[3:]))
        elif data.startswith("sc_"):
            parts = data[3:].split("_", 1)
            from bot.handlers.student.content import show_category
            await show_category(update, context, int(parts[0]), parts[1])
        elif data.startswith(("gstart_","gv_","gm_","gs_","glb_","ga_","gq_")):
            from bot.handlers.student.content import handle_game
            await handle_game(update, context, data)
        elif data == "a_main":
            from bot.handlers.admin.lessons import _show_main
            await _show_main(update, context)
        elif data == "a_logout":
            from bot.handlers.admin.auth import admin_logout
            await admin_logout(update, context)
        elif data == "a_analytics":
            from bot.handlers.admin.analytics import show_analytics
            await show_analytics(update, context)
        elif data == "a_leaderboard":
            from bot.handlers.admin.analytics import show_leaderboard
            await show_leaderboard(update, context)
        elif data == "a_lessons":
            from bot.handlers.admin.lessons import show_lessons as al
            await al(update, context)
        elif data == "a_new":
            from bot.handlers.admin.lessons import new_lesson_start
            await new_lesson_start(update, context)
        elif data.startswith("al_"):
            from bot.handlers.admin.lessons import show_lesson as asl
            await asl(update, context, int(data[3:]))
        elif data.startswith("aup_"):
            from bot.handlers.admin.lessons import upload_start
            await upload_start(update, context, int(data[4:]))
        elif data.startswith("aec_"):
            from bot.handlers.admin.content import show_cats
            await show_cats(update, context, int(data[4:]))
        elif data.startswith("aren_"):
            lid = int(data[5:])
            await update.callback_query.answer()
            await update.callback_query.edit_message_text("✏️ Send the new lesson title:")
            context.user_data["rename_lid"] = lid
        elif data.startswith("adel_confirm_"):
            from bot.handlers.admin.content import delete_lesson_exec
            await delete_lesson_exec(update, context, int(data[13:]))
        elif data.startswith("adel_"):
            from bot.handlers.admin.content import delete_lesson_confirm
            await delete_lesson_confirm(update, context, int(data[5:]))
        elif data.startswith("aqs_"):
            from bot.handlers.admin.analytics import show_quiz_stats
            await show_quiz_stats(update, context, int(data[4:]))
        elif data.startswith("acat_"):
            rest = data[5:]; lid, cat = rest.split("_", 1)
            from bot.handlers.admin.content import show_cat
            await show_cat(update, context, int(lid), cat)
        elif data.startswith("aadd_"):
            rest = data[5:]; lid, cat = rest.split("_", 1)
            from bot.handlers.admin.content import add_content_start
            await add_content_start(update, context, int(lid), cat)
        elif data.startswith("aclr_"):
            rest = data[5:]; lid, cat = rest.split("_", 1)
            from bot.handlers.admin.content import clear_cat
            await clear_cat(update, context, int(lid), cat)
        elif data.startswith("aeit_"):
            from bot.handlers.admin.content import edit_item_start
            await edit_item_start(update, context, int(data[5:]))
        elif data.startswith("adit_"):
            from bot.handlers.admin.content import del_item
            await del_item(update, context, int(data[5:]))
        else:
            await update.callback_query.answer()
    except Exception as e:
        logger.exception("Callback error '%s': %s", data, e)
        try: await update.callback_query.answer("⚠️ Error. Try again.")
        except: pass


async def text_msg(update: Update, context):
    if not update.message or not update.message.text:
        return
    print(f"PRINT: text_msg '{update.message.text[:30]}'", flush=True)
    try:
        if context.user_data.get("waiting_login_pass"):
            from bot.handlers.admin.auth import process_password
            await process_password(update, context)
        elif context.user_data.get("waiting_login_user"):
            from bot.handlers.admin.auth import process_username
            await process_username(update, context)
            elif context.user_data.get("waiting_new_lesson"):
              context.user_data.pop("waiting_new_lesson", None)
             from bot.handlers.admin.lessons import new_lesson_save
             await new_lesson_save(update, context)
        elif context.user_data.get("rename_lid"):
            from bot.handlers.admin.lessons import rename_lesson
            await rename_lesson(update, context)
        elif context.user_data.get("edit_cid") or context.user_data.get("add_content"):
            from bot.handlers.admin.content import save_content
            await save_content(update, context)
    except Exception as e:
        logger.exception("text_msg error: %s", e)


async def doc_msg(update: Update, context):
    if context.user_data.get("upload_lid"):
        from bot.handlers.admin.lessons import receive_doc
        await receive_doc(update, context)


async def error_handler(update: object, context) -> None:
    logger.error("PTB Error:", exc_info=context.error)


async def post_init(app):
    print("PRINT: post_init called", flush=True)
    # Check webhook status
    try:
        info = await app.bot.get_webhook_info()
        print(f"PRINT: webhook_url='{info.url}' pending={info.pending_update_count}", flush=True)
        logger.warning("!!! WEBHOOK INFO: url='%s' pending=%s", info.url, info.pending_update_count)
        if info.url:
            logger.warning("!!! WEBHOOK IS SET — DELETING IT NOW")
            await app.bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        logger.error("Webhook check error: %s", e)

    # Get bot info
    try:
        me = await app.bot.get_me()
        print(f"PRINT: bot username=@{me.username} id={me.id}", flush=True)
        logger.warning("!!! BOT: @%s (id=%s)", me.username, me.id)
    except Exception as e:
        logger.error("get_me error: %s", e)

    db.init_db()
    print("PRINT: DB initialized", flush=True)

    from telegram import BotCommand, MenuButtonCommands
    try:
        await app.bot.set_my_commands([
            BotCommand("start", "Welcome"),
            BotCommand("help",  "Help"),
        ])
        await app.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    except Exception as e:
        logger.warning("Commands/menu error: %s", e)
    print("PRINT: post_init DONE", flush=True)


def build():
    app = (Application.builder()
           .token(BOT_TOKEN)
           .post_init(post_init)
           .build())
    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help",  cmd_start))
    app.add_handler(CallbackQueryHandler(callback_route))
    app.add_handler(MessageHandler(filters.Document.ALL, doc_msg))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_msg))
    return app


if __name__ == "__main__":
    print("PRINT: Starting bot...", flush=True)
    logger.warning("!!! Lingua Bot starting - DIAGNOSTIC MODE")
    build().run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )
