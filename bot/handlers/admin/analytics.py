"""Admin analytics, leaderboard, quiz stats."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from core import database as db
from core.config import CATEGORIES

CAT_LABEL = {key: lbl for lbl, key in CATEGORIES}
MEDALS = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
BACK = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="a_main")]])
BACK_REFRESH = lambda cb: InlineKeyboardMarkup([[
    InlineKeyboardButton("⬅️ Back", callback_data="a_main"),
    InlineKeyboardButton("🔄 Refresh", callback_data=cb)]])


async def show_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    students  = db.all_students()
    pop_less  = db.popular_lessons()
    pop_cats  = db.popular_categories()
    recent    = db.recent_activity(15)

    lines = [f"📊 *Analytics Dashboard*\n\n👥 *Total students: {len(students)}*\n"]

    if students:
        lines.append("*Recent students:*")
        for s in students[:5]:
            name = s["full_name"] or s["username"] or "Anonymous"
            lines.append(f"  • {name[:20]} — {s['last_seen'][:10]}")

    if pop_less:
        lines.append("\n📈 *Most viewed lessons:*")
        for i, r in enumerate(pop_less):
            lines.append(f"  {i+1}. {r['title'][:30]} — {r['views']} views")

    if pop_cats:
        lines.append("\n🗂 *Popular sections:*")
        for r in pop_cats[:5]:
            lbl = CAT_LABEL.get(r["category"], r["category"])
            lines.append(f"  • {lbl}: {r['cnt']} opens")

    if recent:
        lines.append("\n⏱ *Recent activity:*")
        for r in recent[:8]:
            name   = r["full_name"] or r["username"] or "Anon"
            lesson = r["lesson_title"] or "—"
            cat    = CAT_LABEL.get(r["category"], r["category"] or "browse")
            lines.append(f"  • {name[:12]} → {lesson[:18]} / {cat}")

    text = "\n".join(lines)
    if len(text) > 4000: text = text[:3950] + "\n…"
    await update.callback_query.edit_message_text(
        text, parse_mode=ParseMode.MARKDOWN, reply_markup=BACK_REFRESH("a_analytics"))


async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    scores = db.global_leaderboard(10)
    if not scores:
        await update.callback_query.edit_message_text(
            "🏆 *Global Leaderboard*\n\nNo quiz scores yet!",
            parse_mode=ParseMode.MARKDOWN, reply_markup=BACK); return
    lines = ["🏆 *Global Leaderboard*\n"]
    for i, r in enumerate(scores):
        name  = r["full_name"] or r["username"] or f"Student {i+1}"
        medal = MEDALS[i] if i < len(MEDALS) else "🔹"
        pct   = round(r["avg_pct"] or 0, 1)
        lines.append(f"{medal} *{name[:20]}* — avg {pct}% ({r['quiz_count']} quizzes)")
    await update.callback_query.edit_message_text(
        "\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=BACK_REFRESH("a_leaderboard"))


async def show_quiz_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, lid: int):
    await update.callback_query.answer()
    lesson = db.get_lesson(lid)
    scores = db.lesson_leaderboard(lid, 10)
    from bot.keyboards import admin_lesson
    back   = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"al_{lid}")]])
    if not scores:
        await update.callback_query.edit_message_text(
            f"📊 *Quiz Stats — {lesson['title']}*\n\nNo scores yet!",
            parse_mode=ParseMode.MARKDOWN, reply_markup=back); return
    lines = [f"📊 *Quiz Stats — {lesson['title']}*\n"]
    for i, r in enumerate(scores):
        name  = r["full_name"] or r["username"] or f"Student {i+1}"
        medal = MEDALS[i] if i < len(MEDALS) else "🔹"
        lines.append(f"{medal} *{name[:20]}* — {r['score']}/{r['total']} ({r['pct']}%)")
    await update.callback_query.edit_message_text(
        "\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=back)
