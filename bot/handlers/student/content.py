"""Student content delivery — PDF (no answers), interactive quiz, links, games."""
import os, re, logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from core import database as db
from core.config import CATEGORIES
from bot.keyboards import back_to_lesson
from features.pdf_generator import generate_lesson_pdf
from features.links import send_links
from features import games as G

logger = logging.getLogger(__name__)
CAT_LABEL = {key: lbl for lbl, key in CATEGORIES}

_ANS_HDR = re.compile(
    r"^[\*\s]*(answer\s*key|reading\s*answers?|listening\s*task\s*\d+\s*[-–:]?)[\*\s]*$", re.I)
_ANS_LINE = re.compile(r"^\d+\s*[–\-]\s*[a-zA-Z]\s*$")


def _strip_answers(text: str) -> str:
    lines, out, skip = text.split("\n"), [], False
    for line in lines:
        s = line.strip().strip("*").strip()
        if _ANS_HDR.match(s):
            skip = True; continue
        if skip and s.startswith("**") and not _ANS_HDR.match(s.strip("*").strip()):
            skip = False
        if skip or _ANS_LINE.match(s):
            continue
        out.append(line)
    return "\n".join(out)


def _register(u):
    if u:
        name = f"{u.first_name or ''} {u.last_name or ''}".strip()
        db.upsert_student(u.id, u.username or "", name)


async def show_category(update: Update, context: ContextTypes.DEFAULT_TYPE, lid: int, cat: str):
    _register(update.effective_user)
    lesson = db.get_lesson(lid)
    if not lesson:
        await update.callback_query.answer("Lesson not found."); return

    if cat == "links":
        await send_links(update, lid)
        db.log(update.effective_user.id, lid, cat, "links"); return

    if cat == "games":
        await G.send_game_menu(update, lid, lesson["title"])
        db.log(update.effective_user.id, lid, cat, "games"); return

    if cat == "test_quiz":
        await update.callback_query.answer("Building quiz…")
        db.log(update.effective_user.id, lid, cat, "quiz")
        state = G.build_quiz(lid, lesson["title"])
        if state:
            context.user_data["game"] = state
            await _send_q(update, context)
        else:
            await update.callback_query.edit_message_text(
                f"🎯 *Test & Quiz*\n📘 _{lesson['title']}_\n\n"
                "Not enough quiz content yet. Try a game instead:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📚 Vocab Match", callback_data=f"gstart_vocab_{lid}"),
                     InlineKeyboardButton("🔀 Scramble",   callback_data=f"gstart_sc_{lid}")],
                    [InlineKeyboardButton("⬅️ Back", callback_data=f"sl_{lid}")],
                ]))
        return

    # PDF delivery
    await _send_pdf(update, context, lesson, lid, cat)


async def _send_pdf(update, context, lesson, lid, cat):
    label = CAT_LABEL.get(cat, cat.capitalize())
    await update.callback_query.answer("Preparing PDF…")
    rows = db.category_content(lid, cat)
    if not rows:
        await update.callback_query.edit_message_text(
            f"{label}\n\nNo content yet.", reply_markup=back_to_lesson(lid))
        return

    # Show preparing message (will be replaced by PDF)
    prep = await update.effective_chat.send_message(
        f"📄 *Preparing {label}...*\n📘 _{lesson['title']}_\n\n⏳ Please wait...",
        parse_mode=ParseMode.MARKDOWN)

    # Delete the old message from callback
    try:
        await update.callback_query.message.delete()
    except Exception:
        pass

    db.log(update.effective_user.id, lid, cat, "pdf")
    tmp = None
    try:
        blocks = [_strip_answers(r["body"]) for r in rows]
        blocks = [b for b in blocks if b.strip()]
        if not blocks:
            await prep.edit_text("⚠️ No content.", reply_markup=back_to_lesson(lid)); return

        tmp = generate_lesson_pdf(lesson["title"], cat, label, blocks)
        fname = f"{lesson['title'].replace(' ','_')[:25]}_{cat}.pdf"

        # Delete the "preparing" message, send PDF directly
        await prep.delete()

        with open(tmp, "rb") as f:
            await update.effective_chat.send_document(
                document=f, filename=fname,
                caption=(f"📘 *{lesson['title']}*\n{label}\n\n"
                         "_Lingua Bot — your English learning assistant_ 🎓"),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=back_to_lesson(lid))
    except Exception as e:
        logger.exception("PDF error")
        try: await prep.delete()
        except: pass
        await update.effective_chat.send_message(
            f"⚠️ PDF error: {e}", reply_markup=back_to_lesson(lid))
    finally:
        if tmp and os.path.exists(tmp): os.unlink(tmp)


async def handle_game(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    _register(update.effective_user)
    cq  = update.callback_query
    uid = update.effective_user.id

    # Start game
    if data.startswith("gstart_"):
        parts = data.split("_")
        gtype, lid = parts[1], int(parts[2])
        lesson = db.get_lesson(lid)
        state = (G.build_quiz(lid, lesson["title"])    if gtype == "mc"    else
                 G.build_vocab_quiz(lid, lesson["title"]) if gtype == "vocab" else
                 G.build_scramble(lid, lesson["title"]))
        if not state:
            await cq.answer("Not enough content for this game yet!", show_alert=True); return
        context.user_data["game"] = state
        db.log(uid, lid, "games", f"start_{gtype}")
        await _send_q(update, context); return

    # Answer
    prefix_map = {"gv_": "vocab", "gm_": "mc", "gs_": "sc"}
    for pfx in prefix_map:
        if data.startswith(pfx):
            state = context.user_data.get("game")
            if not state:
                await cq.answer("Session expired. Start a new game!", show_alert=True); return
            parts   = data.split("_")
            chosen, correct = int(parts[1]), int(parts[2])
            state["score"] += (chosen == correct)
            await cq.answer("✅ Correct! 🎉" if chosen == correct else "❌ Wrong!")
            state["current"] += 1
            if state["current"] >= state["total"]:
                db.save_score(uid, state["lesson_id"], state["score"], state["total"])
                db.log(uid, state["lesson_id"], "games", f"finish_{state['score']}/{state['total']}")
                text, kb = G.render_result(state)
                context.user_data.pop("game", None)
                await cq.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
            else:
                await _send_q(update, context)
            return

    # Leaderboard
    if data.startswith("glb_"):
        lid = int(data.split("_")[-1])
        lesson = db.get_lesson(lid)
        scores = db.lesson_leaderboard(lid, 10)
        await cq.answer()
        if not scores:
            await cq.answer("No scores yet! Be the first!", show_alert=True); return
        MEDALS = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
        lines = [f"🏅 *Leaderboard*\n📘 _{lesson['title']}_\n"]
        for i, r in enumerate(scores):
            name = r["full_name"] or r["username"] or f"Student {i+1}"
            lines.append(f"{MEDALS[i]} *{name[:20]}* — {r['score']}/{r['total']} ({r['pct']}%)")
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("🎮 Play Now", callback_data=f"sc_{lid}_games"),
            InlineKeyboardButton("⬅️ Back",     callback_data=f"sl_{lid}")]])
        await cq.edit_message_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        return

    # Play again / quit
    if data.startswith("ga_"):
        lid = int(data.split("_")[-1])
        lesson = db.get_lesson(lid)
        await cq.answer()
        await G.send_game_menu(update, lid, lesson["title"]); return

    if data.startswith("gq_"):
        lid = int(data.split("_")[-1])
        context.user_data.pop("game", None)
        await cq.answer("Game quit.")
        lesson = db.get_lesson(lid)
        await G.send_game_menu(update, lid, lesson["title"]); return


async def _send_q(update, context):
    state = context.user_data.get("game")
    if not state: return
    text, kb = G.render_question(state)
    try:
        await update.callback_query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    except Exception:
        await update.effective_chat.send_message(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
