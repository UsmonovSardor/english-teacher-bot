"""Lingua Bot — main entry point."""
import logging, sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from core.config import BOT_TOKEN
from core import database as db

logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO, stream=sys.stdout, force=True)
logger = logging.getLogger(__name__)

def _is_admin(update): return db.is_admin(update.effective_chat.id)
async def _deny(update): await update.callback_query.answer("⛔ Ruxsat yo'q.", show_alert=True)

async def cmd_start(update, context):
    u = update.effective_user
    try: db.upsert_student(u.id, u.username or "", f"{u.first_name or ''} {u.last_name or ''}".strip())
    except Exception as e: logger.error("DB: %s", e)
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("👨‍💼 Admin Panel", callback_data="admin"),
        InlineKeyboardButton("📚 Student Zone", callback_data="student"),
    ]])
    await update.message.reply_text(
        f"👋 *Salom, {u.first_name}!*\n\n*Lingua Bot* 🎓\nRolingizni tanlang:",
        parse_mode="Markdown", reply_markup=kb)

async def callback_route(update, context):
    data = update.callback_query.data
    logger.info("CB: %s from %s", data, update.effective_chat.id)
    try:
        if data == "student":
            from bot.handlers.student.browse import show_lessons; await show_lessons(update, context)
        elif data == "my_profile":
            from bot.handlers.student.register import show_profile; await show_profile(update, context)
        elif data.startswith("sl_"):
            from bot.handlers.student.browse import show_lesson; await show_lesson(update, context, int(data[3:]))
        elif data.startswith("sc_"):
            p = data[3:].split("_",1)
            from bot.handlers.student.content import show_category; await show_category(update, context, int(p[0]), p[1])
        elif data.startswith(("gstart_","gv_","gm_","gs_","glb_","ga_","gq_","task_submit_")):
            from bot.handlers.student.content import handle_game; await handle_game(update, context, data)
        elif data == "admin":
            from bot.handlers.admin.auth import admin_entry_direct; await admin_entry_direct(update, context)
        elif data == "a_logout":
            from bot.handlers.admin.auth import admin_logout; await admin_logout(update, context)
        elif data == "a_main":
            if not _is_admin(update): return await _deny(update)
            from bot.handlers.admin.lessons import _show_main; await _show_main(update, context)
        elif data == "a_lessons":
            if not _is_admin(update): return await _deny(update)
            from bot.handlers.admin.lessons import show_lessons as al; await al(update, context)
        elif data == "a_new":
            if not _is_admin(update): return await _deny(update)
            from bot.handlers.admin.lessons import new_lesson_start; await new_lesson_start(update, context)
        elif data == "a_analytics":
            if not _is_admin(update): return await _deny(update)
            from bot.handlers.admin.analytics import show_analytics; await show_analytics(update, context)
        elif data == "a_leaderboard":
            if not _is_admin(update): return await _deny(update)
            from bot.handlers.admin.analytics import show_leaderboard; await show_leaderboard(update, context)
        elif data == "a_submissions":
            if not _is_admin(update): return await _deny(update)
            from bot.handlers.admin.analytics import show_submissions; await show_submissions(update, context)
        elif data.startswith("al_"):
            if not _is_admin(update): return await _deny(update)
            from bot.handlers.admin.lessons import show_lesson as asl; await asl(update, context, int(data[3:]))
        elif data.startswith("aup_"):
            if not _is_admin(update): return await _deny(update)
            from bot.handlers.admin.lessons import upload_start; await upload_start(update, context, int(data[4:]))
        elif data.startswith("aren_"):
            if not _is_admin(update): return await _deny(update)
            lid=int(data[5:]); await update.callback_query.answer()
            await update.callback_query.edit_message_text("✏️ *Dars nomini o'zgartirish*\n\nYangi nomni yuboring:", parse_mode="Markdown")
            context.user_data["rename_lid"]=lid
        elif data.startswith("adel_confirm_"):
            if not _is_admin(update): return await _deny(update)
            from bot.handlers.admin.content import delete_lesson_exec; await delete_lesson_exec(update, context, int(data[13:]))
        elif data.startswith("adel_"):
            if not _is_admin(update): return await _deny(update)
            from bot.handlers.admin.content import delete_lesson_confirm; await delete_lesson_confirm(update, context, int(data[5:]))
        elif data.startswith("aqs_"):
            if not _is_admin(update): return await _deny(update)
            from bot.handlers.admin.analytics import show_quiz_stats; await show_quiz_stats(update, context, int(data[4:]))
        elif data.startswith("aec_"):
            if not _is_admin(update): return await _deny(update)
            from bot.handlers.admin.content import show_cats; await show_cats(update, context, int(data[4:]))
        elif data.startswith("acat_"):
            if not _is_admin(update): return await _deny(update)
            rest=data[5:]; lid,cat=rest.split("_",1)
            from bot.handlers.admin.content import show_cat; await show_cat(update, context, int(lid), cat)
        elif data.startswith("aadd_"):
            if not _is_admin(update): return await _deny(update)
            rest=data[5:]; lid,cat=rest.split("_",1)
            from bot.handlers.admin.content import add_content_start; await add_content_start(update, context, int(lid), cat)
        elif data.startswith("aclr_"):
            if not _is_admin(update): return await _deny(update)
            rest=data[5:]; lid,cat=rest.split("_",1)
            from bot.handlers.admin.content import clear_cat; await clear_cat(update, context, int(lid), cat)
        elif data.startswith("aeit_"):
            if not _is_admin(update): return await _deny(update)
            from bot.handlers.admin.content import edit_item_start; await edit_item_start(update, context, int(data[5:]))
        elif data.startswith("adit_"):
            if not _is_admin(update): return await _deny(update)
            from bot.handlers.admin.content import del_item; await del_item(update, context, int(data[5:]))
        elif data.startswith("alc_"):
            if not _is_admin(update): return await _deny(update)
            from bot.handlers.admin.links_mgr import show_links; await show_links(update, context, int(data[4:]))
        elif data.startswith("alca_"):
            if not _is_admin(update): return await _deny(update)
            from bot.handlers.admin.links_mgr import add_link_start; await add_link_start(update, context, int(data[5:]))
        elif data.startswith("alcd_"):
            if not _is_admin(update): return await _deny(update)
            from bot.handlers.admin.links_mgr import del_link; await del_link(update, context, int(data[5:]))
        else:
            await update.callback_query.answer()
    except Exception as e:
        logger.exception("CB error '%s': %s", data, e)
        try: await update.callback_query.answer("⚠️ Xato. Qayta urinib ko'ring.", show_alert=True)
        except: pass

async def text_msg(update, context):
    if not update.message or not update.message.text: return
    try:
        from bot.handlers.student.register import handle_registration_text
        if await handle_registration_text(update, context): return
        from bot.handlers.student.content import handle_task_answer
        if await handle_task_answer(update, context): return
        if context.user_data.get("waiting_login_pass"):
            from bot.handlers.admin.auth import process_password; await process_password(update, context)
        elif context.user_data.get("waiting_login_user"):
            from bot.handlers.admin.auth import process_username; await process_username(update, context)
        elif context.user_data.get("waiting_new_lesson"):
            context.user_data.pop("waiting_new_lesson",None)
            from bot.handlers.admin.lessons import new_lesson_save; await new_lesson_save(update, context)
        elif context.user_data.get("rename_lid"):
            from bot.handlers.admin.lessons import rename_lesson; await rename_lesson(update, context)
        elif context.user_data.get("add_link_lid"):
            from bot.handlers.admin.links_mgr import save_link; await save_link(update, context)
        elif context.user_data.get("edit_cid") or context.user_data.get("add_content"):
            from bot.handlers.admin.content import save_content; await save_content(update, context)
    except Exception as e: logger.exception("text_msg: %s", e)

async def doc_msg(update, context):
    if context.user_data.get("upload_lid"):
        from bot.handlers.admin.lessons import receive_doc; await receive_doc(update, context)

async def error_handler(update, context): logger.error("PTB:", exc_info=context.error)

async def post_init(app):
    try:
        info = await app.bot.get_webhook_info()
        if info.url: await app.bot.delete_webhook(drop_pending_updates=True)
    except Exception as e: logger.error("Webhook: %s", e)
    db.init_db(); logger.info("DB at %s", db.DB_PATH)
    try:
        from telegram import BotCommand, MenuButtonCommands
        await app.bot.set_my_commands([BotCommand("start","Bosh sahifa"),BotCommand("help","Yordam")])
        await app.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    except Exception as e: logger.warning("Commands: %s", e)

def build():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))
    app.add_handler(CallbackQueryHandler(callback_route))
    app.add_handler(MessageHandler(filters.Document.ALL, doc_msg))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_msg))
    return app

if __name__ == "__main__":
    logger.info("Lingua Bot starting…")
    build().run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
