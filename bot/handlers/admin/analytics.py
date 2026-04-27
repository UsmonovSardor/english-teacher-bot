"""Admin analytics — premium dashboard with tasks, groups, leaderboard."""
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from core import database as db
from core.config import CATEGORIES

CAT_LABEL = {key: lbl for lbl, key in CATEGORIES}
MEDALS = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]

def _back(cb="a_analytics"):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⬅️ Orqaga", callback_data="a_main"),
        InlineKeyboardButton("🔄 Yangilash", callback_data=cb),
    ]])

async def show_analytics(update, context):
    await update.callback_query.answer()
    students = db.all_students()
    total = len(students)
    today = datetime.now().strftime("%Y-%m-%d")
    active_today = sum(1 for s in students if (s["last_seen"] or "")[:10] == today)
    registered = sum(1 for s in students if s["registered"])
    tasks = db.submission_count()
    pop_less = db.popular_lessons(5)
    pop_cats = db.popular_categories()
    recent = db.recent_activity(10)
    groups = db.group_stats()

    lines = ["📊 *Analytics Dashboard*\n",
             f"👥 Jami talabalar: *{total}*",
             f"✅ Ro'yxatdan o'tgan: *{registered}*",
             f"🟢 Bugun faol: *{active_today}*",
             f"📚 Darslar: *{len(db.all_lessons())}*",
             f"📝 Topshirilgan vazifalar: *{tasks}*"]

    if groups:
        lines.append("\n📚 *Guruhlar:*")
        for g in groups[:6]: lines.append(f"  • {g['group_name']}: *{g['cnt']}* talaba")

    if pop_less:
        lines.append("\n📈 *Ko'p ko'rilgan darslar:*")
        for i,r in enumerate(pop_less,1): lines.append(f"  {i}. {r['title'][:25]} — *{r['views']}*")

    if pop_cats:
        lines.append("\n🗂 *Faol bo'limlar:*")
        for r in pop_cats[:5]:
            lbl = CAT_LABEL.get(r["category"], r["category"])
            lines.append(f"  • {lbl}: *{r['cnt']}*")

    if recent:
        lines.append("\n⏱ *So'nggi faoliyat:*")
        for r in recent[:8]:
            name = (r["full_name"] or r["username"] or "Anon")[:12]
            grp  = f"({r['group_name']}) " if r["group_name"] else ""
            les  = (r["lesson_title"] or "—")[:15]
            cat  = CAT_LABEL.get(r["category"], r["category"] or "browse")
            t    = (r["at"] or "")[11:16]
            lines.append(f"  • {name} {grp}→ {les} [{cat}] `{t}`")

    text = "\n".join(lines)
    if len(text) > 4000: text = text[:3950] + "\n…"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Vazifalar", callback_data="a_submissions"),
         InlineKeyboardButton("🏆 Reyting",   callback_data="a_leaderboard")],
        [InlineKeyboardButton("⬅️ Orqaga",    callback_data="a_main"),
         InlineKeyboardButton("🔄 Yangilash", callback_data="a_analytics")],
    ])
    await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

async def show_submissions(update, context):
    await update.callback_query.answer()
    subs = db.all_submissions(20)
    if not subs:
        await update.callback_query.edit_message_text(
            "📝 *Topshirilgan vazifalar*\n\nHali hech qanday vazifa topshirilmagan.",
            parse_mode=ParseMode.MARKDOWN, reply_markup=_back("a_submissions")); return
    lines = ["📝 *So'nggi vazifalar*\n"]
    for r in subs:
        name = (r["full_name"] or r["username"] or "Anon")[:15]
        grp  = f"({r['group_name']}) " if r["group_name"] else ""
        les  = (r["lesson_title"] or "—")[:15]
        cat  = CAT_LABEL.get(r["category"], r["category"])
        dur  = r["duration_seconds"] or 0
        m,s  = divmod(dur, 60)
        t_s  = f"{m}d{s}s" if m else f"{s}s"
        dt   = (r["submitted_at"] or "")[:10]
        lines.append(f"• *{name}* {grp}\n  📘 {les} | {cat} | ⏱{t_s} | {dt}")
    text = "\n".join(lines)
    if len(text) > 4000: text = text[:3950] + "\n…"
    await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
        reply_markup=_back("a_submissions"))

async def show_leaderboard(update, context):
    await update.callback_query.answer()
    scores = db.global_leaderboard(10)
    if not scores:
        await update.callback_query.edit_message_text(
            "🏆 *Global Reyting*\n\nHali quiz natijalari yo'q!",
            parse_mode=ParseMode.MARKDOWN, reply_markup=_back("a_leaderboard")); return
    lines = ["🏆 *Global Reyting*\n"]
    for i,r in enumerate(scores):
        name  = (r["full_name"] or r["username"] or f"Talaba {i+1}")[:18]
        grp   = f"\n   📚 {r['group_name']}" if r["group_name"] else ""
        medal = MEDALS[i] if i < len(MEDALS) else "🔹"
        pct   = round(r["avg_pct"] or 0, 1)
        lines.append(f"{medal} *{name}*{grp}\n   avg *{pct}%* • {r['quiz_count']} quiz • {int(r['total_score'])} ball")
    await update.callback_query.edit_message_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN,
        reply_markup=_back("a_leaderboard"))

async def show_quiz_stats(update, context, lid):
    await update.callback_query.answer()
    lesson = db.get_lesson(lid)
    scores = db.lesson_leaderboard(lid, 10)
    back   = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Orqaga", callback_data=f"al_{lid}")]])
    if not scores:
        await update.callback_query.edit_message_text(
            f"📊 *Quiz natijalari*\n📘 _{dict(lesson)['title']}_\n\nHali natijalar yo'q!",
            parse_mode=ParseMode.MARKDOWN, reply_markup=back); return
    lines = [f"📊 *Quiz — {dict(lesson)['title']}*\n"]
    for i,r in enumerate(scores):
        name  = (r["full_name"] or r["username"] or f"Talaba {i+1}")[:18]
        grp   = f" ({r['group_name']})" if r["group_name"] else ""
        medal = MEDALS[i] if i < len(MEDALS) else "🔹"
        lines.append(f"{medal} *{name}*{grp} — {r['score']}/{r['total']} ({r['pct']}%)")
    await update.callback_query.edit_message_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=back)
