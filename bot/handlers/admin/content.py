"""Admin content CRUD."""
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
from core import database as db
from core.config import State, CATEGORIES
from bot.keyboards import admin_cats, admin_cat_actions, admin_content_item, admin_lesson, admin_main, confirm

CAT_LABEL = {key: lbl for lbl, key in CATEGORIES}


async def show_cats(update: Update, context: ContextTypes.DEFAULT_TYPE, lid: int):
    await update.callback_query.answer()
    lesson = db.get_lesson(lid)
    if not lesson:
        await update.callback_query.answer("Lesson not found.", show_alert=True)
        return
    await update.callback_query.edit_message_text(
        f"📋 *Edit Content — {lesson['title']}*\n\nChoose a category:",
        parse_mode=ParseMode.MARKDOWN, reply_markup=admin_cats(lid))


async def show_cat(update: Update, context: ContextTypes.DEFAULT_TYPE, lid: int, cat: str):
    await update.callback_query.answer()
    rows = db.category_content(lid, cat)
    label = CAT_LABEL.get(cat, cat)
    await update.callback_query.edit_message_text(
        f"{label} — *{len(rows)} item(s)*",
        parse_mode=ParseMode.MARKDOWN, reply_markup=admin_cat_actions(lid, cat))
    for row in rows:
        preview = row["body"][:400] + ("…" if len(row["body"]) > 400 else "")
        try:
            await update.effective_chat.send_message(
                f"```\n{preview}\n```", parse_mode=ParseMode.MARKDOWN,
                reply_markup=admin_content_item(row["id"], lid, cat))
        except Exception:
            await update.effective_chat.send_message(
                preview, reply_markup=admin_content_item(row["id"], lid, cat))


async def add_content_start(update: Update, context: ContextTypes.DEFAULT_TYPE, lid: int, cat: str):
    context.user_data["add_content"] = {"lid": lid, "cat": cat}
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        f"➕ *Add to {CAT_LABEL.get(cat, cat)}*\n\nType or paste content:",
        parse_mode=ParseMode.MARKDOWN)
    return State.EDIT_CONTENT


async def save_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = context.user_data.pop("edit_cid", None)
    f"➕ *Add to {CAT_LABEL.get(cat, cat)}*\n\nType/paste content or send an audio/voice file:",
    if cid:
        row = db.get_content(cid)
        if not row:
            await update.message.reply_text("⚠️ Content not found.")
            return ConversationHandler.END
        db.update_content(cid, update.message.text.strip())
        await update.message.reply_text("✅ Updated!", reply_markup=admin_lesson(row["lesson_id"]))
        return ConversationHandler.END
    info = context.user_data.pop("add_content", None)
    if info:
        db.add_content(info["lid"], info["cat"], update.message.text.strip())
        lbl = CAT_LABEL.get(info["cat"], info["cat"])
        await update.message.reply_text(
            f"✅ Added to *{lbl}*!", parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_cat_actions(info["lid"], info["cat"]))
        return ConversationHandler.END


async def clear_cat(update: Update, context: ContextTypes.DEFAULT_TYPE, lid: int, cat: str):
    db.clear_category(lid, cat)
    await update.callback_query.answer("Cleared!")
    await update.callback_query.edit_message_text(
        f"🗑 *{CAT_LABEL.get(cat, cat)}* cleared.",
        parse_mode=ParseMode.MARKDOWN, reply_markup=admin_cat_actions(lid, cat))
async def save_audio_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = context.user_data.pop("add_content", None)
    if not info:
        return ConversationHandler.END

    audio = update.message.audio
    voice = update.message.voice

    if not audio and not voice:
        await update.message.reply_text("⚠️ Please send an audio or voice file.")
        return ConversationHandler.END

    if audio:
        body = f"[AUDIO]{audio.file_id}"
    else:
        body = f"[VOICE]{voice.file_id}"

    db.add_content(info["lid"], info["cat"], body)

    lbl = CAT_LABEL.get(info["cat"], info["cat"])
    await update.message.reply_text(
        f"✅ Audio added to *{lbl}*!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_cat_actions(info["lid"], info["cat"])
    )

    return ConversationHandler.END

async def del_item(update: Update, context: ContextTypes.DEFAULT_TYPE, cid: int):
    row = db.get_content(cid)
    lid = row["lesson_id"] if row else 0
    db.delete_content(cid)
    await update.callback_query.answer("Deleted!")
    await update.callback_query.edit_message_text(
        "🗑 Item deleted.", reply_markup=admin_lesson(lid) if lid else None)


async def edit_item_start(update: Update, context: ContextTypes.DEFAULT_TYPE, cid: int):
    row = db.get_content(cid)
    if not row:
        await update.callback_query.answer("Not found."); return ConversationHandler.END
    context.user_data["edit_cid"] = cid
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        f"✏️ *Edit Content*\n\nCurrent:\n```\n{row['body'][:500]}\n```\nSend new text:",
        parse_mode=ParseMode.MARKDOWN)
    return State.EDIT_CONTENT


async def delete_lesson_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, lid: int):
    await update.callback_query.answer()
    lesson = db.get_lesson(lid)
    if not lesson:
        await update.callback_query.answer("Lesson not found.", show_alert=True)
        return
    await update.callback_query.edit_message_text(
        f"⚠️ Delete *'{lesson['title']}'*?\n\nThis removes ALL content permanently!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=confirm(f"adel_confirm_{lid}", f"al_{lid}"))


async def delete_lesson_exec(update: Update, context: ContextTypes.DEFAULT_TYPE, lid: int):
    db.delete_lesson(lid)
    await update.callback_query.answer("Deleted!")
    await update.callback_query.edit_message_text(
        "🗑 Lesson deleted.", reply_markup=admin_main())
