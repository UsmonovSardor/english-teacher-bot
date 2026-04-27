"""Admin custom links manager per lesson."""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from core import database as db
from bot.keyboards import admin_links

logger = logging.getLogger(__name__)

def _parse_link_items(lid):
    rows = db.category_content(lid, "links")
    items = []
    for row in rows:
        body = row["body"].strip()
        if "|" in body:
            p = body.split("|",1); label = p[0].strip(); url = p[1].strip().split()[0]
        else:
            url = body.strip().split()[0] if body.strip() else body; label = url[:25]
        if url.startswith("http"):
            items.append((row["id"], label, url))
    return items

async def show_links(update, context, lid):
    await update.callback_query.answer()
    lesson = db.get_lesson(lid)
    if not lesson:
        await update.callback_query.answer("Lesson not found.", show_alert=True); return
    lesson = dict(lesson)
    items = _parse_link_items(lid)
    text = (f"🔗 *Custom Links — {lesson['title']}*\n\n"
            + (f"📭 No custom links yet.\n" if not items else f"✅ {len(items)} link(s) configured.\n")
            + "\n_Tap 🗑 to delete • 🔗 to open_\n\n"
            "*Format to add:* `Name | https://url.com`")
    await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_links(lid, items))

async def add_link_start(update, context, lid):
    await update.callback_query.answer()
    context.user_data["add_link_lid"] = lid
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("❌ Cancel", callback_data=f"alc_{lid}")
    ]])
    await update.callback_query.edit_message_text(
        "🔗 *Add Custom Link*\n\n"
        "Send in this format:\n`Name | https://url.com`\n\n"
        "📌 *Examples:*\n"
        "`YouTube Lesson | https://youtube.com/watch?v=...`\n"
        "`Quizlet Set | https://quizlet.com/...`\n"
        "`Grammar Guide | https://grammarly.com`\n\n"
        "_Or tap Cancel to go back._",
        parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

async def save_link(update, context):
    lid = context.user_data.pop("add_link_lid", None)
    if not lid: return
    text = update.message.text.strip()
    if "|" not in text:
        context.user_data["add_link_lid"] = lid
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data=f"alc_{lid}")]])
        await update.message.reply_text(
            "⚠️ Wrong format!\n\nUse: `Name | https://url.com`\n\nTry again:",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb); return
    p = text.split("|",1); label = p[0].strip(); url = p[1].strip().split()[0]
    if not url.startswith("http"):
        context.user_data["add_link_lid"] = lid
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data=f"alc_{lid}")]])
        await update.message.reply_text("⚠️ URL must start with http:\n\nTry again:", reply_markup=kb); return
    db.add_content(lid, "links", f"{label} | {url}")
    items = _parse_link_items(lid)
    await update.message.reply_text(
        f"✅ *Link added!*\n🔗 {label}\n{url}\n\nTotal: {len(items)} link(s)",
        parse_mode=ParseMode.MARKDOWN, reply_markup=admin_links(lid, items))

async def del_link(update, context, cid):
    row = db.get_content(cid); lid = row["lesson_id"] if row else 0
    db.delete_content(cid); await update.callback_query.answer("Deleted! ✅")
    items = _parse_link_items(lid); lesson = db.get_lesson(lid)
    lesson = dict(lesson) if lesson else {}
    text = (f"🔗 *Custom Links — {lesson.get('title','')}*\n\n"
            + (f"📭 No custom links yet." if not items else f"✅ {len(items)} link(s) configured."))
    await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_links(lid, items))
