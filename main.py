"""Lingua Bot — main entry point."""

import logging
import sys

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
    MenuButtonCommands,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from core.config import BOT_TOKEN, DB_PATH
from core import database as db


logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
    force=True,
)

logger = logging.getLogger(__name__)


def _is_admin(update):
    try:
        return db.is_admin(update.effective_chat.id)
    except Exception:
        return False


async def _deny(update):
    try:
        await update.callback_query.answer(
            "⛔ Access denied.",
            show_alert=True,
        )
    except Exception:
        pass


def _clear_admin_states(context):
    keys = [
        "waiting_new_lesson",
        "rename_lid",
        "upload_lid",
        "add_content",
        "edit_cid",
        "add_link_lid",
        "waiting_login_user",
        "waiting_login_pass",
    ]

    for key in keys:
        context.user_data.pop(key, None)


def _clear_edit_states(context):
    keys = [
        "waiting_new_lesson",
        "rename_lid",
        "edit_cid",
        "add_link_lid",
    ]

    for key in keys:
        context.user_data.pop(key, None)


async def cmd_start(update, context):
    _clear_admin_states(context)

    u = update.effective_user

    try:
        db.upsert_student(
            u.id,
            u.username or "",
            f"{u.first_name or ''} {u.last_name or ''}".strip(),
        )
    except Exception as e:
        logger.error("DB: %s", e)

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "👨‍💼 Admin Panel",
                callback_data="admin",
            ),

            InlineKeyboardButton(
                "📚 Student Zone",
                callback_data="student",
            ),
        ]
    ])

    await update.message.reply_text(
        f"👋 *Hello, {u.first_name}!*\n\n"
        f"*Lingua Bot* 🎓\n"
        f"Choose your role:",
        parse_mode="Markdown",
        reply_markup=kb,
    )


async def callback_route(update, context):
    query = update.callback_query
    data = query.data

    logger.info("CB: %s from %s", data, update.effective_chat.id)

    try:
        try:
            await query.answer()
        except Exception:
            pass

        if data in ("student", "admin", "a_main", "a_lessons"):
            _clear_admin_states(context)

        elif data.startswith(("al_", "aec_", "acat_", "alc_")):
            _clear_edit_states(context)

        elif data.startswith("aup_"):
            _clear_edit_states(context)
            context.user_data.pop("add_content", None)

        elif data.startswith("aadd_"):
            context.user_data.pop("upload_lid", None)
            context.user_data.pop("waiting_new_lesson", None)
            context.user_data.pop("rename_lid", None)
            context.user_data.pop("add_link_lid", None)
            context.user_data.pop("edit_cid", None)

        elif data.startswith("aeit_"):
            context.user_data.pop("upload_lid", None)
            context.user_data.pop("waiting_new_lesson", None)
            context.user_data.pop("rename_lid", None)
            context.user_data.pop("add_link_lid", None)
            context.user_data.pop("add_content", None)

        elif data.startswith("aren_"):
            _clear_admin_states(context)

        elif data.startswith("alca_"):
            _clear_admin_states(context)

        # =========================
        # STUDENT
        # =========================

        if data == "student":
            from bot.handlers.student.browse import show_lessons
            return await show_lessons(update, context)

        elif data == "my_profile":
            from bot.handlers.student.register import show_profile
            return await show_profile(update, context)

        elif data.startswith("sl_"):
            from bot.handlers.student.browse import show_lesson

            lid = int(data.replace("sl_", ""))

            return await show_lesson(update, context, lid)

        elif data.startswith("sc_"):
            p = data[3:].split("_", 1)

            from bot.handlers.student.content import show_category

            return await show_category(
                update,
                context,
                int(p[0]),
                p[1],
            )

        elif data.startswith((
            "gstart_",
            "gv_",
            "gm_",
            "gs_",
            "glb_",
            "ga_",
            "gq_",
            "task_submit_",
        )):
            from bot.handlers.student.content import handle_game

            return await handle_game(update, context, data)

        # =========================
        # ADMIN
        # =========================

        elif data == "admin":
            from bot.handlers.admin.auth import admin_entry_direct
            return await admin_entry_direct(update, context)

        elif data == "a_logout":
            _clear_admin_states(context)

            from bot.handlers.admin.auth import admin_logout

            return await admin_logout(update, context)

        elif data == "a_main":

            if not _is_admin(update):
                return await _deny(update)

            from bot.handlers.admin.lessons import _show_main

            return await _show_main(update, context)

        elif data == "a_lessons":

            if not _is_admin(update):
                return await _deny(update)

            from bot.handlers.admin.lessons import show_lessons as al

            return await al(update, context)

        elif data == "a_new":

            if not _is_admin(update):
                return await _deny(update)

            _clear_admin_states(context)

            from bot.handlers.admin.lessons import new_lesson_start

            return await new_lesson_start(update, context)

        elif data == "a_analytics":

            if not _is_admin(update):
                return await _deny(update)

            from bot.handlers.admin.analytics import show_analytics

            return await show_analytics(update, context)

        elif data == "a_leaderboard":

            if not _is_admin(update):
                return await _deny(update)

            from bot.handlers.admin.analytics import show_leaderboard

            return await show_leaderboard(update, context)

        elif data.startswith("al_"):

            if not _is_admin(update):
                return await _deny(update)

            lid = int(data.replace("al_", ""))

            from bot.handlers.admin.lessons import show_lesson

            return await show_lesson(update, context, lid)

        elif data.startswith("aup_"):

            if not _is_admin(update):
                return await _deny(update)

            lid = int(data.replace("aup_", ""))

            from bot.handlers.admin.lessons import upload_start

            return await upload_start(update, context, lid)

        elif data.startswith("aren_"):

            if not _is_admin(update):
                return await _deny(update)

            lid = int(data.replace("aren_", ""))

            from bot.handlers.admin.lessons import rename_lesson_start

            return await rename_lesson_start(update, context, lid)

        elif data.startswith("adel_confirm_"):

            if not _is_admin(update):
                return await _deny(update)

            lid = int(data.replace("adel_confirm_", ""))

            from bot.handlers.admin.content import delete_lesson_exec

            return await delete_lesson_exec(update, context, lid)

        elif data.startswith("adel_"):

            if not _is_admin(update):
                return await _deny(update)

            lid = int(data.replace("adel_", ""))

            from bot.handlers.admin.content import delete_lesson_confirm

            return await delete_lesson_confirm(update, context, lid)

        elif data.startswith("aqs_"):

            if not _is_admin(update):
                return await _deny(update)

            lid = int(data.replace("aqs_", ""))

            from bot.handlers.admin.analytics import show_quiz_stats

            return await show_quiz_stats(update, context, lid)

        elif data.startswith("aec_"):

            if not _is_admin(update):
                return await _deny(update)

            lid = int(data.replace("aec_", ""))

            from bot.handlers.admin.content import show_cats

            return await show_cats(update, context, lid)

        elif data.startswith("acat_"):

            if not _is_admin(update):
                return await _deny(update)

            rest = data.replace("acat_", "")
            lid, cat = rest.split("_", 1)

            from bot.handlers.admin.content import show_cat

            return await show_cat(
                update,
                context,
                int(lid),
                cat,
            )

        elif data.startswith("aadd_"):

            if not _is_admin(update):
                return await _deny(update)

            rest = data.replace("aadd_", "")
            lid, cat = rest.split("_", 1)

            from bot.handlers.admin.content import add_content_start

            return await add_content_start(
                update,
                context,
                int(lid),
                cat,
            )

        elif data.startswith("aclr_"):

            if not _is_admin(update):
                return await _deny(update)

            rest = data.replace("aclr_", "")
            lid, cat = rest.split("_", 1)

            from bot.handlers.admin.content import clear_cat

            return await clear_cat(
                update,
                context,
                int(lid),
                cat,
            )

        elif data.startswith("aeit_"):

            if not _is_admin(update):
                return await _deny(update)

            cid = int(data.replace("aeit_", ""))

            from bot.handlers.admin.content import edit_item_start

            return await edit_item_start(update, context, cid)

        elif data.startswith("adit_"):

            if not _is_admin(update):
                return await _deny(update)

            cid = int(data.replace("adit_", ""))

            from bot.handlers.admin.content import del_item

            return await del_item(update, context, cid)

        elif data.startswith("alc_"):

            if not _is_admin(update):
                return await _deny(update)

            lid = int(data.replace("alc_", ""))

            from bot.handlers.admin.links_mgr import show_links

            return await show_links(update, context, lid)

        elif data.startswith("alca_"):

            if not _is_admin(update):
                return await _deny(update)

            lid = int(data.replace("alca_", ""))

            from bot.handlers.admin.links_mgr import add_link_start

            return await add_link_start(update, context, lid)

        elif data.startswith("alcd_"):

            if not _is_admin(update):
                return await _deny(update)

            cid = int(data.replace("alcd_", ""))

            from bot.handlers.admin.links_mgr import del_link

            return await del_link(update, context, cid)

    except Exception as e:

        logger.exception(
            "CB error '%s': %s",
            data,
            e,
        )

        try:
            await query.answer(
                "⚠️ Error. Please try again.",
                show_alert=True,
            )
        except Exception:
            pass


async def text_msg(update, context):

    if not update.message or not update.message.text:
        return

    try:

        if context.user_data.get("waiting_login_pass"):
            from bot.handlers.admin.auth import process_password
            return await process_password(update, context)

        if context.user_data.get("waiting_login_user"):
            from bot.handlers.admin.auth import process_username
            return await process_username(update, context)

        if context.user_data.get("waiting_new_lesson"):
            from bot.handlers.admin.lessons import new_lesson_save
            return await new_lesson_save(update, context)

        if context.user_data.get("rename_lid"):
            from bot.handlers.admin.lessons import rename_lesson
            return await rename_lesson(update, context)

        if context.user_data.get("add_link_lid"):
            from bot.handlers.admin.links_mgr import save_link
            return await save_link(update, context)

        if context.user_data.get("edit_cid") or context.user_data.get("add_content"):
            from bot.handlers.admin.content import save_content
            return await save_content(update, context)

        from bot.handlers.student.register import handle_registration_text

        if await handle_registration_text(update, context):
            return

        from bot.handlers.student.content import handle_task_answer

        if await handle_task_answer(update, context):
            return

    except Exception as e:
        logger.exception("text_msg: %s", e)

        await update.message.reply_text(
            "⚠️ Error. Please try again."
        )


async def doc_msg(update, context):

    try:

        if context.user_data.get("upload_lid"):
            from bot.handlers.admin.lessons import receive_doc
            return await receive_doc(update, context)

        if context.user_data.get("add_content"):
            from bot.handlers.admin.content import save_document_content
            return await save_document_content(update, context)

        await update.message.reply_text(
            "⚠️ Please first choose:\n"
            "Admin Panel → Lessons → Lesson → Upload Document\n\n"
            "or\n\n"
            "Admin Panel → Lessons → Lesson → Edit Content → Category → Add Content"
        )

    except Exception as e:
        logger.exception("doc_msg: %s", e)

        await update.message.reply_text(
            "⚠️ Document upload error. Please try again."
        )


async def audio_msg(update, context):

    try:

        if context.user_data.get("add_content"):
            from bot.handlers.admin.content import save_audio_content
            return await save_audio_content(update, context)

        await update.message.reply_text(
            "⚠️ Please choose Add Content first."
        )

    except Exception as e:
        logger.exception("audio_msg: %s", e)

        await update.message.reply_text(
            "⚠️ Audio upload error. Please try again."
        )


async def error_handler(update, context):
    logger.error(
        "PTB:",
        exc_info=context.error,
    )


async def post_init(app):

    try:
        info = await app.bot.get_webhook_info()

        if info.url:
            await app.bot.delete_webhook(
                drop_pending_updates=True
            )

    except Exception as e:
        logger.error("Webhook: %s", e)

    db.init_db()

    logger.info("DB at %s", DB_PATH)

    try:

        await app.bot.set_my_commands([
            BotCommand("start", "Home"),
            BotCommand("help", "Help"),
        ])

        await app.bot.set_chat_menu_button(
            menu_button=MenuButtonCommands()
        )

    except Exception as e:
        logger.warning("Commands: %s", e)


def build():

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .read_timeout(60)
        .write_timeout(60)
        .connect_timeout(60)
        .pool_timeout(60)
        .build()
    )

    app.add_error_handler(error_handler)

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))

    app.add_handler(
        CallbackQueryHandler(callback_route)
    )

    app.add_handler(
        MessageHandler(filters.Document.ALL, doc_msg)
    )

    app.add_handler(
        MessageHandler(filters.AUDIO | filters.VOICE, audio_msg)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_msg,
        )
    )

    return app


if __name__ == "__main__":

    logger.info("Lingua Bot starting…")

    build().run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )
