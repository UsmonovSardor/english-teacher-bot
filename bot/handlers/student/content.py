"""Student content — PDF tasks with timer, quiz, games."""
import os, re, logging
from datetime import datetime

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
_TASK_CATS = {"reading", "listening", "writing"}

_ANS_HDR = re.compile(
    r"^[\*\s]*(answer\s*key|reading\s*answers?|listening\s*answers?)[\*\s]*$",
    re.I,
)
_ANS_LINE = re.compile(r"^\d+\s*[–\-]\s*[a-zA-Z]\s*$")


def _strip_answers(text):
    lines, out, skip = text.split("\n"), [], False

    for line in lines:
        s = line.strip().strip("*").strip()

        if _ANS_HDR.match(s):
            skip = True
            continue

        if skip and s.startswith("**") and not _ANS_HDR.match(s.strip("*").strip()):
            skip = False

        if skip or _ANS_LINE.match(s):
            continue

        out.append(line)

    return "\n".join(out)


def _fmt_dur(secs):
    m, s = divmod(int(secs), 60)
    return f"{m} min {s} sec" if m else f"{s} sec"


def _is_media_body(body: str) -> bool:
    return body.startswith("[AUDIO]") or body.startswith("[VOICE]")


async def _send_media_rows(chat, rows):
    for row in rows:
        body = row["body"]

        if body.startswith("[AUDIO]"):
            await chat.send_audio(body.replace("[AUDIO]", "", 1))

        elif body.startswith("[VOICE]"):
            await chat.send_voice(body.replace("[VOICE]", "", 1))


async def show_category(update, context, lid, cat):
    lesson = db.get_lesson(lid)

    if not lesson:
        await update.callback_query.answer("Lesson not found.", show_alert=True)
        return

    lesson = dict(lesson)

    if cat == "links":
        await send_links(update, lid)
        db.log(update.effective_user.id, lid, cat, "links")
        return

    if cat == "games":
        await G.send_game_menu(update, lid, lesson["title"])
        db.log(update.effective_user.id, lid, cat, "games")
        return

    if cat == "test_quiz":
        await _start_quiz(update, context, lid, lesson)
        return

    if cat in _TASK_CATS:
        await _send_task_pdf(update, context, lesson, lid, cat)
        return

    await _send_pdf(update, context, lesson, lid, cat)


async def _send_task_pdf(update, context, lesson, lid, cat):
    label = CAT_LABEL.get(cat, cat.capitalize())

    await update.callback_query.answer("Preparing task…")

    rows = db.category_content(lid, cat)

    if not rows:
        await update.callback_query.edit_message_text(
            f"📄 *{label}*\n\nNo content has been added yet.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_to_lesson(lid),
        )
        return

    media_rows = [r for r in rows if _is_media_body(r["body"])]
    text_rows = [r for r in rows if not _is_media_body(r["body"])]

    blocks = [_strip_answers(r["body"]) for r in text_rows]
    blocks = [b for b in blocks if b.strip()]

    if media_rows:
        await _send_media_rows(update.effective_chat, media_rows)

    if not blocks:
        await update.callback_query.edit_message_text(
            f"📄 *{label}*\n\nAudio has been sent. No text task was added.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_to_lesson(lid),
        )
        return

    prep = await update.effective_chat.send_message(
        f"⏳ *Preparing {label}...*",
        parse_mode=ParseMode.MARKDOWN,
    )

    try:
        await update.callback_query.message.delete()
    except Exception:
        pass

    tmp = None

    try:
        tmp = generate_lesson_pdf(lesson["title"], cat, label, blocks)
        fname = f"{lesson['title'].replace(' ', '_')[:20]}_{cat}.pdf"

        started = datetime.now().isoformat()
        context.user_data[f"task_{lid}_{cat}"] = {
            "started": started,
            "lesson_id": lid,
            "category": cat,
        }

        await prep.delete()

        db.log(update.effective_user.id, lid, cat, "task_start")

        with open(tmp, "rb") as f:
            await update.effective_chat.send_document(
                document=f,
                filename=fname,
                caption=(
                    f"📘 *{lesson['title']}*\n"
                    f"{label} task\n\n"
                    f"⏱ *Timer started!*\n"
                    f"Send your answer after completing the task.\n"
                    f"_Lingua Bot_ 🎓"
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "✅ Submit my answer",
                                callback_data=f"task_submit_{lid}_{cat}",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "📚 Back to lesson",
                                callback_data=f"sl_{lid}",
                            )
                        ],
                    ]
                ),
            )

    except Exception as e:
        logger.exception("Task PDF error")

        try:
            await prep.delete()
        except Exception:
            pass

        await update.effective_chat.send_message(
            f"⚠️ Error: {e}",
            reply_markup=back_to_lesson(lid),
        )

    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)


async def handle_task_submit(update, context, data):
    parts = data.split("_")
    lid = int(parts[2])
    cat = "_".join(parts[3:])

    await update.callback_query.answer()

    context.user_data["pending_task_submit"] = f"{lid}_{cat}"

    await update.callback_query.edit_message_text(
        "✏️ *Send your answer*\n\nSend your task answer as text:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("❌ Cancel", callback_data=f"sl_{lid}")]]
        ),
    )


async def handle_task_answer(update, context):
    key = context.user_data.get("pending_task_submit")

    if not key:
        return False

    lid_str, cat = key.split("_", 1)
    lid = int(lid_str)

    task = context.user_data.pop(f"task_{lid}_{cat}", {})
    context.user_data.pop("pending_task_submit", None)

    answer = update.message.text.strip()
    started = task.get("started")
    duration = 0

    if started:
        try:
            duration = int(
                (datetime.now() - datetime.fromisoformat(started)).total_seconds()
            )
        except Exception:
            pass

    db.save_task(update.effective_user.id, lid, cat, started, duration, answer)
    db.log(update.effective_user.id, lid, cat, "task_submit")

    label = CAT_LABEL.get(cat, cat)
    lesson = db.get_lesson(lid)
    l_title = dict(lesson).get("title", "") if lesson else ""

    await update.message.reply_text(
        f"✅ *Task submitted!*\n\n"
        f"📘 Lesson: *{l_title}*\n"
        f"📂 Section: *{label}*\n"
        f"⏱ Time: *{_fmt_dur(duration)}*\n\n"
        f"Your result has been sent to the teacher.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("📚 Back to lessons", callback_data="student")]]
        ),
    )

    return True


async def _send_pdf(update, context, lesson, lid, cat):
    label = CAT_LABEL.get(cat, cat.capitalize())

    await update.callback_query.answer("Preparing PDF…")

    rows = db.category_content(lid, cat)

    if not rows:
        await update.callback_query.edit_message_text(
            f"📄 *{label}*\n\nNo content has been added yet.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_to_lesson(lid),
        )
        return

    media_rows = [r for r in rows if _is_media_body(r["body"])]
    text_rows = [r for r in rows if not _is_media_body(r["body"])]

    if media_rows:
        await _send_media_rows(update.effective_chat, media_rows)

    prep = await update.effective_chat.send_message(
        f"📄 *Preparing {label}...*\n⏳ Please wait...",
        parse_mode=ParseMode.MARKDOWN,
    )

    try:
        await update.callback_query.message.delete()
    except Exception:
        pass

    db.log(update.effective_user.id, lid, cat, "pdf")

    tmp = None

    try:
        blocks = [_strip_answers(r["body"]) for r in text_rows]
        blocks = [b for b in blocks if b.strip()]

        if not blocks:
            await prep.edit_text(
                "⚠️ No text content.",
                reply_markup=back_to_lesson(lid),
            )
            return

        tmp = generate_lesson_pdf(lesson["title"], cat, label, blocks)
        fname = f"{lesson['title'].replace(' ', '_')[:20]}_{cat}.pdf"

        await prep.delete()

        with open(tmp, "rb") as f:
            await update.effective_chat.send_document(
                document=f,
                filename=fname,
                caption=f"📘 *{lesson['title']}*\n{label}\n\n_Lingua Bot_ 🎓",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=back_to_lesson(lid),
            )

    except Exception as e:
        logger.exception("PDF error")

        try:
            await prep.delete()
        except Exception:
            pass

        await update.effective_chat.send_message(
            f"⚠️ Error: {e}",
            reply_markup=back_to_lesson(lid),
        )

    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)


async def _start_quiz(update, context, lid, lesson):
    await update.callback_query.answer("Loading quiz…")

    db.log(update.effective_user.id, lid, "test_quiz", "quiz")

    state = G.build_quiz(lid, lesson["title"])

    if state:
        context.user_data["game"] = state
        await _send_q(update, context)

    else:
        await update.callback_query.edit_message_text(
            f"🎯 *Test & Quiz*\n"
            f"📘 _{lesson['title']}_\n\n"
            f"Not enough questions. Try a game:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "📚 Vocab",
                            callback_data=f"gstart_vocab_{lid}",
                        ),
                        InlineKeyboardButton(
                            "🔀 Scramble",
                            callback_data=f"gstart_sc_{lid}",
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            "📚 Back to lesson",
                            callback_data=f"sl_{lid}",
                        )
                    ],
                ]
            ),
        )


async def handle_game(update, context, data):
    cq = update.callback_query
    uid = update.effective_user.id

    if data.startswith("task_submit_"):
        await handle_task_submit(update, context, data)
        return

    if data.startswith("gstart_"):
        p = data.split("_")
        gtype, lid = p[1], int(p[2])
        lesson = db.get_lesson(lid)

        state = (
            G.build_quiz(lid, lesson["title"])
            if gtype == "mc"
            else G.build_vocab_quiz(lid, lesson["title"])
            if gtype == "vocab"
            else G.build_scramble(lid, lesson["title"])
        )

        if not state:
            await cq.answer("Not enough content!", show_alert=True)
            return

        context.user_data["game"] = state
        db.log(uid, lid, "games", f"start_{gtype}")
        await _send_q(update, context)
        return

    for pfx in ("gv_", "gm_", "gs_"):
        if data.startswith(pfx):
            state = context.user_data.get("game")

            if not state:
                await cq.answer("Session ended! Start a new game.", show_alert=True)
                return

            p = data.split("_")
            chosen, correct = int(p[1]), int(p[2])

            state["score"] += chosen == correct

            await cq.answer("✅ Correct! 🎉" if chosen == correct else "❌ Incorrect!")

            state["current"] += 1

            if state["current"] >= state["total"]:
                db.save_score(
                    uid,
                    state["lesson_id"],
                    state["score"],
                    state["total"],
                )

                text, kb = G.render_result(state)
                context.user_data.pop("game", None)

                await cq.edit_message_text(
                    text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=kb,
                )

            else:
                await _send_q(update, context)

            return

    if data.startswith("glb_"):
        lid = int(data.split("_")[-1])
        lesson = db.get_lesson(lid)
        scores = db.lesson_leaderboard(lid, 10)

        await cq.answer()

        if not scores:
            await cq.answer("No results yet!", show_alert=True)
            return

        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        lines = [f"🏅 *Results*\n📘 _{dict(lesson)['title']}_\n"]

        for i, r in enumerate(scores):
            name = r["full_name"] or r["username"] or f"Student {i + 1}"
            grp = f" ({r['group_name']})" if r["group_name"] else ""
            lines.append(
                f"{medals[i]} *{name[:18]}*{grp} — "
                f"{r['score']}/{r['total']} ({r['pct']}%)"
            )

        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("🎮 Play", callback_data=f"sc_{lid}_games"),
                    InlineKeyboardButton(
                        "📚 Back to lesson",
                        callback_data=f"sl_{lid}",
                    ),
                ]
            ]
        )

        await cq.edit_message_text(
            "\n".join(lines),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb,
        )
        return

    if data.startswith("ga_"):
        lid = int(data.split("_")[-1])
        lesson = db.get_lesson(lid)

        await cq.answer()
        await G.send_game_menu(update, lid, dict(lesson)["title"])
        return

    if data.startswith("gq_"):
        lid = int(data.split("_")[-1])
        context.user_data.pop("game", None)

        await cq.answer("Game ended.")

        lesson = db.get_lesson(lid)
        await G.send_game_menu(update, lid, dict(lesson)["title"])
        return


async def _send_q(update, context):
    state = context.user_data.get("game")

    if not state:
        return

    text, kb = G.render_question(state)

    try:
        await update.callback_query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb,
        )

    except Exception:
        await update.effective_chat.send_message(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb,
        )
