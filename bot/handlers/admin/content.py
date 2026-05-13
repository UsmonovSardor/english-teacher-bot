"""Admin content CRUD."""

import os
import tempfile

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from core import database as db
from core.config import State, CATEGORIES
from core.parser import parse_document
from bot.keyboards import (
    admin_cats,
    admin_cat_actions,
    admin_content_item,
    admin_lesson,
    admin_main,
    confirm,
)

CAT_LABEL = {key: lbl for lbl, key in CATEGORIES}


def _split_text(text: str, max_len: int = 3500):
    text = (text or "").strip()
    if not text:
        return []

    parts = []

    while len(text) > max_len:
        cut = text.rfind("\n\n", 0, max_len)

        if cut == -1:
            cut = text.rfind("\n", 0, max_len)

        if cut == -1:
            cut = max_len

        parts.append(text[:cut].strip())
        text = text[cut:].strip()

    if text:
        parts.append(text)

    return parts


def _read_pdf_text(path: str) -> str:
    try:
        import fitz

        pdf = fitz.open(path)
        pages = []

        for page in pdf:
            txt = page.get_text("text")

            if txt and txt.strip():
                pages.append(txt.strip())

        pdf.close()

        return "\n\n".join(pages).strip()

    except Exception:
        return ""


def _read_docx_text(path: str) -> str:
    try:
        from docx import Document

        document = Document(path)
        paragraphs = []

        for p in document.paragraphs:
            if p.text and p.text.strip():
                paragraphs.append(p.text.strip())

        return "\n\n".join(paragraphs).strip()

    except Exception:
        return ""


async def show_cats(update: Update, context: ContextTypes.DEFAULT_TYPE, lid: int):
    await update.callback_query.answer()

    lesson = db.get_lesson(lid)

    if not lesson:
        await update.callback_query.answer("Lesson not found.", show_alert=True)
        return

    await update.callback_query.edit_message_text(
        f"📋 *Edit Content — {lesson['title']}*\n\nChoose a category:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_cats(lid),
    )


async def show_cat(update: Update, context: ContextTypes.DEFAULT_TYPE, lid: int, cat: str):
    await update.callback_query.answer()

    rows = db.category_content(lid, cat)
    label = CAT_LABEL.get(cat, cat)

    await update.callback_query.edit_message_text(
        f"{label} — *{len(rows)} item(s)*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_cat_actions(lid, cat),
    )

    for row in rows:
        body = row["body"]

        if body.startswith("[AUDIO]"):
            preview = "🎧 Audio file"

        elif body.startswith("[VOICE]"):
            preview = "🎙 Voice message"

        elif body.startswith("[FILE]"):
            try:
                _file_id, file_name = body[6:].split("|", 1)
            except ValueError:
                file_name = "document"

            preview = f"📎 File: {file_name}"

        else:
            preview = body[:400] + ("…" if len(body) > 400 else "")

        try:
            await update.effective_chat.send_message(
                f"```\n{preview}\n```",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=admin_content_item(row["id"], lid, cat),
            )
        except Exception:
            await update.effective_chat.send_message(
                preview,
                reply_markup=admin_content_item(row["id"], lid, cat),
            )


async def add_content_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    lid: int,
    cat: str,
):
    context.user_data["add_content"] = {"lid": lid, "cat": cat}

    await update.callback_query.answer()

    await update.callback_query.edit_message_text(
        f"➕ *Add to {CAT_LABEL.get(cat, cat)}*\n\n"
        f"Type/paste content or send PDF/DOCX/audio/voice file:",
        parse_mode=ParseMode.MARKDOWN,
    )

    return State.EDIT_CONTENT


async def save_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = context.user_data.pop("edit_cid", None)

    if cid:
        row = db.get_content(cid)

        if not row:
            await update.message.reply_text("⚠️ Content not found.")
            return ConversationHandler.END

        db.update_content(cid, update.message.text.strip())

        await update.message.reply_text(
            "✅ Updated!",
            reply_markup=admin_lesson(row["lesson_id"]),
        )

        return ConversationHandler.END

    info = context.user_data.pop("add_content", None)

    if info:
        text = update.message.text.strip() if update.message.text else ""

        if not text:
            await update.message.reply_text("⚠️ Please send text content.")
            return ConversationHandler.END

        db.clear_category(info["lid"], info["cat"])
        db.add_content(info["lid"], info["cat"], text)

        lbl = CAT_LABEL.get(info["cat"], info["cat"])

        await update.message.reply_text(
            f"✅ Added to *{lbl}*!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_cat_actions(info["lid"], info["cat"]),
        )

        return ConversationHandler.END

    return ConversationHandler.END


async def save_document_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = context.user_data.pop("add_content", None)

    if not info:
        await update.message.reply_text("⚠️ Please choose Add Content first.")
        return ConversationHandler.END

    doc = update.message.document

    if not doc:
        await update.message.reply_text("⚠️ Please send PDF or DOCX file.")
        return ConversationHandler.END

    file_name_original = doc.file_name or "document"
    file_name = file_name_original.lower()

    if not (file_name.endswith(".pdf") or file_name.endswith(".docx")):
        await update.message.reply_text("⚠️ Please send only PDF or DOCX file.")
        return ConversationHandler.END

    msg = await update.message.reply_text("⏳ Reading document...")

    tmp = None

    try:
        ext = ".pdf" if file_name.endswith(".pdf") else ".docx"
        tg_file = await context.bot.get_file(doc.file_id)

        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as t:
            tmp = t.name

        await tg_file.download_to_drive(tmp)

        selected_cat = info["cat"]
        blocks = []

        try:
            parsed, _title = parse_document(tmp)
        except Exception:
            parsed = {}

        if parsed:
            blocks = parsed.get(selected_cat, [])

            if not blocks:
                for _cat, cat_blocks in parsed.items():
                    blocks.extend(cat_blocks)

        if not blocks:
            raw_text = _read_pdf_text(tmp) if ext == ".pdf" else _read_docx_text(tmp)
            blocks = _split_text(raw_text)

        clean_blocks = [
            str(block).strip()
            for block in blocks
            if block and str(block).strip()
        ]

        lbl = CAT_LABEL.get(selected_cat, selected_cat)

        if clean_blocks:
            db.clear_category(info["lid"], selected_cat)

            for block in clean_blocks:
                db.add_content(info["lid"], selected_cat, block)

            await msg.edit_text(
                f"✅ File text added to *{lbl}*!\n\n"
                f"📦 {len(clean_blocks)} block(s) saved.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=admin_cat_actions(info["lid"], selected_cat),
            )

            return ConversationHandler.END

        db.clear_category(info["lid"], selected_cat)

        file_body = f"[FILE]{doc.file_id}|{file_name_original}"
        db.add_content(info["lid"], selected_cat, file_body)

        await msg.edit_text(
            f"✅ File added to *{lbl}*!\n\n"
            f"📎 PDF/DOCX text o‘qilmadi, lekin fayl sifatida saqlandi.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_cat_actions(info["lid"], selected_cat),
        )

    except Exception as e:
        await msg.edit_text(
            f"❌ Error while reading document:\n`{e}`",
            parse_mode=ParseMode.MARKDOWN,
        )

    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)

    return ConversationHandler.END


async def save_audio_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = context.user_data.pop("add_content", None)

    if not info:
        return ConversationHandler.END

    audio = update.message.audio
    voice = update.message.voice

    if not audio and not voice:
        await update.message.reply_text("⚠️ Please send an audio or voice file.")
        return ConversationHandler.END

    body = f"[AUDIO]{audio.file_id}" if audio else f"[VOICE]{voice.file_id}"

    db.clear_category(info["lid"], info["cat"])
    db.add_content(info["lid"], info["cat"], body)

    lbl = CAT_LABEL.get(info["cat"], info["cat"])

    await update.message.reply_text(
        f"✅ Audio added to *{lbl}*!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_cat_actions(info["lid"], info["cat"]),
    )

    return ConversationHandler.END


async def clear_cat(update: Update, context: ContextTypes.DEFAULT_TYPE, lid: int, cat: str):
    db.clear_category(lid, cat)

    await update.callback_query.answer("Cleared!")

    await update.callback_query.edit_message_text(
        f"🗑 *{CAT_LABEL.get(cat, cat)}* cleared.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_cat_actions(lid, cat),
    )


async def del_item(update: Update, context: ContextTypes.DEFAULT_TYPE, cid: int):
    row = db.get_content(cid)
    lid = row["lesson_id"] if row else 0

    db.delete_content(cid)

    await update.callback_query.answer("Deleted!")

    await update.callback_query.edit_message_text(
        "🗑 Item deleted.",
        reply_markup=admin_lesson(lid) if lid else None,
    )


async def edit_item_start(update: Update, context: ContextTypes.DEFAULT_TYPE, cid: int):
    row = db.get_content(cid)

    if not row:
        await update.callback_query.answer("Not found.")
        return ConversationHandler.END

    context.user_data["edit_cid"] = cid

    await update.callback_query.answer()

    await update.callback_query.edit_message_text(
        f"✏️ *Edit Content*\n\nCurrent:\n```\n{row['body'][:500]}\n```\nSend new text:",
        parse_mode=ParseMode.MARKDOWN,
    )

    return State.EDIT_CONTENT


async def delete_lesson_confirm(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    lid: int,
):
    await update.callback_query.answer()

    lesson = db.get_lesson(lid)

    if not lesson:
        await update.callback_query.answer("Lesson not found.", show_alert=True)
        return

    await update.callback_query.edit_message_text(
        f"⚠️ Delete *'{lesson['title']}'*?\n\nThis removes ALL content permanently!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=confirm(f"adel_confirm_{lid}", f"al_{lid}"),
    )


async def delete_lesson_exec(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    lid: int,
):
    db.delete_lesson(lid)

    await update.callback_query.answer("Deleted!")

    await update.callback_query.edit_message_text(
        "🗑 Lesson deleted.",
        reply_markup=admin_main(),
    )
