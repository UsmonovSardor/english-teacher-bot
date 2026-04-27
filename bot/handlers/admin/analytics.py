"""Admin analytics — premium statistics dashboard."""
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from core import database as db
from core.config import CATEGORIES

logger = logging.getLogger(__name__)
CAT_LABEL = {key: lbl for lbl, key in CATEGORIES}
MEDALS    = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]

def _back(cb="a_main"):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⬅️ Back",    callback_data="a_main"),
        InlineKeyboardButton("🔄 Refresh", callback_data=cb),
    ]])

async def show_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    students   = db.all_students()
    total      = len(students)
    pop_less   = db.popular_lessons(5)
    pop_cats   = db.popular_categories()
    recent     = db.recent_activity(10)

    # Active today
    today = datetime.now().strftime("%Y-%m-%d")
    active_today = sum(1 for s in students if s["last_seen"][:10] == today)

    lines = [
        "📊 *Analytics Dashboard*\n",
        f"👥 Total students: *{total}*",
        f"🟢 Active today: *{active_today}*",
        f"📚 Total lessons: *{len(db.all_lessons())}*",
    ]

    if pop_less:
        lines.append("\n📈 *Most Viewed Lessons:*")
        for i, r in enumerate(pop_less, 1):
            lines.append(f" {i}. {r['title'][:28]} — *{r['views']}* views")

    if pop_cats:
        lines.append("\n🗂 *Top Sections:*")
        for r in pop_cats[:5]:
            lbl = CAT_LABEL.get(r["category"], r["category"])
            lines.append(f"  • {lbl}: *{r['cnt']}* opens")

    if recent:
        lines.append("\n⏱ *Recent Activity:*")
        for r in recent[;8]:
            name   = (r["full_name"] or r["username"] or "Anon")[:12]
            lesson = (r["lesson_title"] or "—")[:16]
            cat    = CAT_LABEL.get(r["category"], r["category"] or "browse")
            t      = r["at"][11:16] if r["at"] else ""
            lines.append(f"  • {name} → {lesson} / {cat} `{t}`")

    if students:
        lines.append("\n👤 *Latest Students:*")
        for s in students[:5]:
            name = (s["full_name"] or s["username"] or "Anonymous")[:20]
            dt   = s["last_seen"][:10]
            lines.append(f"  ₂ {name} — {dt}")

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:3950] + "\n…"

    await update.callback_query.edit_message_text(
        text, parse_mode=ParseMode.MARKDOWN,
        reply_markup=_back("a_analytics"))

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    scores = db.global_leaderboard(10)

    if not scores:
        await update.callback_query.edit_message_text(
            "🏆 *Global Leaderboard*\n\n🔹 No quiz scores yet!\n\nEncourage students to take quizzes.",
            parse_mode=ParseMode.MARKDOWN, reply_markup=_back("a_leaderboard"))
        return

    lines = ["🏆 *Global Leaderboard*\n"]
    for i, r in enumerate(scores):
        name  = (r["full_name"] or r["username"] or f"Student {i+1}")[:20]
        medal = MEDALS[i] if i < len(MEDALS) else "🔹"
        pct   = round(r["avg_pct"] or 0, 1)
        lines.append(
            f"{medal} *{name}*\n"
            f"   avg *{pct}%* • {r['quiz_count']} quiz(es) • {int(r['total_score'])} pts")

    await update.callback_query.edit_message_text(
        "\n".join(lines), parse_mode=ParseMode.MARKDOWN,
        reply_markup=_back("a_leaderboard"))

async def show_quiz_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, lid: int):
    await update.callback_query.answer()
    lesson = db.get_lesson(lid)
    scores = db.lesson_leaderboard(lid, 10)
    back   = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"al_{lid}")]])

    if not scores:
        await update.callback_query.edit_message_text(
            f"📊 *Quiz Stats*\n📘 _{lesson['title']}_\n\n🔹 No scores yet!",
            parse_mode=ParseMode.MARKDOWN, reply_markup=back)
        return

    lines = [f"📊 *Quiz Stats — {lesson['title']}*\n"]
    for i, r in enumerate(scores):
        name  = (r["full_name"] or r["username"] or &"Student {i+1}")[:20]
        medal = MEDALS[i] if i < len(MEDALS) else "🔹"
        lines.append(
            f"{medal} *{name}* — {r['score']}/{r['total']} ({r['pct']}%)")

    await update.callback_query.edit_message_text(
        "\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=back)
