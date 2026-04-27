"""Admin lesson management: list, create, upload, rename."""
import os, tempfile, logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
from core import database as db
from core.config import State
from core.parser import parse_document
from bot.keyboards import admin_main, admin_lessons, admin_lesson, admin_cats
from core.config import CATEGORIES

logger = logging.getLogger(__name__)
CAT_LABEL = {key: lbl for lbl, key in CATEGORIES}


async def _show_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cnt = db.student_count()
    text = (f"👨‍💼 *Admin Panel — Lingua Bot*\n\n"
            f"👥 Students: *{cnt}*\n\n"
            f"Choose an action:")
    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_text(
                text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_main())
        except Exception:
            await update.effective_chat.send_message(
                text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_main())
    else:
        await update.effective_message.reply_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_main())


async def show_lessons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    lessons = db.all_lessons()
    if not lessons:
        await update.callback_query.edit_message_text(
            "📂 No lessons yet.\n\nTap *➕ New Lesson* to create one.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_main())
        return
    lesson_list = []
    for l in lessons:
        d = dict(l)
        d["has_content"] = db.lesson_has_content(l["id"])
        lesson_list.append(d)
    await update.callback_query.edit_message_text(
        f"📂 *Lessons* ({len(lessons)})\n\nSelect a lesson to manage:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_lessons(lesson_list))


async def show_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE, lid: int):
    await update.callback_query.answer()
    lesson = db.get_lesson(lid)
    if not lesson:
        await update.callback_query.edit_message_text("⚠️ Lesson not found.")
        return
    cats = db.available_categories(lid)
    has = f"✅ {len(cats)} categories" if cats else "⚠️ No content"
    scores = db.lesson_leaderboard(lid, 3)
    lb_txt = ""
    if scores:
        MEDALS = ["🥇", "🥈", "🥉"]
        lb_txt = "\n\n🏆 *Top scores:*\n"
        for i, r in enumerate(scores):
            name = r["full_name"] or r["username"] or "Student"
            lb_txt += f" {MEDAE�Q}i]} {name[:18]} — {r['pct']}%\n"
    await update.callback_query.edit_message_text(
        f"{lesson['emoji]} *{lesson['title']}*\n"
        f"📌 {lesson['topic'] or 'No topic set'}\n"
        f"📅 {lesson['created_at'][:10]}\n"
        f"Status: {has}{lb_txt}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_lesson(lid))


async def new_lesson_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "📝 *New Lesson*1\n\nEnter the lesson title:",
        parse_mode=ParseMode.MARKDOWN)
    context.user_data["waiting_new_lesson"] = True
    return State.ADD_LESSON


async def new_lesson_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = update.message.text.strip()
    if not title:
        await update.message.reply_text("⚠️ Title required.")
        return State.ADD_LESSON
    lid = db.create_lesson(title)
    await update.message.reply_text(
        f"✅ Lesson *{title}* created!\n\nWhat would you like to do?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_lesson(lid))
    return ConversationHandler.END


async def upload_start(update: Update, context: ContextTypes.DEFAULT_TYPE, lid: int):
    context.user_data["upload_lid"] = lid
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "📤 *Upload Document*\n\n"
        "Send a *.docx* file — I'll auto-parse it into:\n"
        "_Links • Visuals • Vocabulary • Speaking • Listening •\n"
        "Reading • Writing • Games • Homework • Test & Quiz_\n\n"
        "⚡ You can upload multiple files — content will be appended.",
        parse_mode=ParseMode.MARKDOWN)


async def receive_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lid = context.user_data.get("upload_lid")
    if not lid:
        return
    doc = update.message.document
    if not doc or not doc.file_name.lower().endswith(".docx"):
        await update.message.reply_text("⚠️ Please send a *.docx* file.", parse_mode=ParseMode.MARKDOWN)
        return
    msg = await update.message.reply_text("⏳ Parsing document…")
    tmp = None
    try:
        f = await context.bot.get_file(doc.file_id)
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as t:
            tmp = t.name
        await f.download_to_drive(tmp)
        parsed, title = parse_document(tmp)
        if not parsed:
            await msg.edit_text("⚠️ No recognizable content found.")
            return
        total = 0
        for cat, blocks in parsed.items():
            for i, b in enumerate(blocks):
                db.add_content(lid, cat, b, i)
                total += 1
        lesson = db.get_lesson(lid)
        if title and lesson["title"] in ("Lesson", "New Lesson"):
            db.update_lesson(lid, title, lesson["topic"] or "")
        lines = ["✅ *Parsed successfully!*\n"]
        for cat, blocks in sorted(parsed.items()):
            lines.append(f" {CAT_LABEL.get(cat, cat)}: {len(blocks)} block(s)")
        lines.append(f"\n📦 *{total} content blocks* added")
        await msg.edit_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN,
                            reply_markup=admin_lesson(lid))
        context.user_data.pop("upload_lid", None)
    except Exception as e:
        logger.exception("Parse error")
        await msg.edit_text(f"❌ Error: {e}")
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)


async def rename_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lid = context.user_data.pop("rename_lid", None)
    if not lid:
        return ConversationHandler.END
    new_title = update.message.text.strip()
    lesson = db.get_lesson(lid)
    db.update_lesson(lid, new_title, lesson["topic"] or "", lesson["emoji"] or "📘")
    await update.message.reply_text(
        f"✅ Renamed to *{new_title}*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_lesson(lid))
    return ConversationHandler.END
