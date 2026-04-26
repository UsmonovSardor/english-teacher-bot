"""Interactive quiz games — built from real lesson content."""
import re, random, logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from core import database as db

logger = logging.getLogger(__name__)
MEDALS = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]


# ── Extractors ────────────────────────────────────────────────────────────────

def _all_blocks(lesson_id: int) -> list[str]:
    return [r["body"] for r in db.lesson_content(lesson_id)]

def _blocks_for(*cats, lesson_id: int) -> list[str]:
    rows = []
    for cat in cats:
        rows += db.category_content(lesson_id, cat)
    return [r["body"] for r in rows]

def _answer_key(blocks: list[str]) -> dict[int, str]:
    """Extract answer key — prefers blocks near answer key headings."""
    all_keys = []
    cur = {}
    ANS = re.compile(r"^[\*]*(answer\s*key|listening\s*task\s*\d+|task\s*\d+\s*[-–]|reading\s*answers?)[\*]*$", re.I)
    for block in blocks:
        for line in block.split("\n"):
            s = line.strip().strip("*").strip()
            if ANS.match(s):
                if cur: all_keys.append(dict(cur))
                cur = {}
                continue
            m = re.match(r"^(\d+)\s*[–\-]\s*([a-zA-Z])\s*$", s)
            if m:
                cur[int(m.group(1))] = m.group(2).lower()
    if cur: all_keys.append(cur)
    return max(all_keys, key=len) if all_keys else {}

def _mc_questions(blocks: list[str], key: dict) -> list[dict]:
    qs, cur_q, cur_n, opts = [], None, 0, []

    def flush():
        if cur_q and len(opts) >= 2:
            ans = 0
            if cur_n in key:
                idx = ord(key[cur_n]) - ord('a')
                if 0 <= idx < len(opts): ans = idx
            qs.append({"num": cur_n, "q": cur_q, "opts": opts[:], "ans": ans})

    for block in blocks:
        for line in block.split("\n"):
            s = line.strip().strip("*").strip()
            if not s: continue
            if re.match(r"^\d+\s*[–\-]\s*[a-zA-Z]\s*$", s): continue  # skip answer lines
            m = re.match(r"^(\d+)\s+(.{5,})", s)
            if m:
                flush(); cur_n = int(m.group(1))
                q_text = re.sub(r"[…\.]{2,}$","",m.group(2)).strip()
                if any(c.isalpha() for c in q_text) and len(q_text) > 4:
                    cur_q = q_text; opts = []; continue
            m2 = re.match(r"^([a-eA-E])[\.\)]\s*(.+)", s)
            if m2 and cur_q:
                opts.append(m2.group(2).strip()); continue
    flush()
    return qs

def _vocab_pairs(blocks: list[str]) -> list[tuple]:
    SKIP = {"department","word","term","vocabulary","category","english","uzbek","definition",
            "data","type","name","column","row","header","table"}
    pairs = []
    for b in blocks:
        for line in b.split("\n"):
            if "|" in line:
                parts = [p.strip() for p in line.strip().strip("|").split("|")]
                if len(parts) >= 2 and parts[0] and parts[1]:
                    if parts[0].lower() not in SKIP and len(parts[0]) > 1:
                        pairs.append((parts[0], parts[1]))
    return pairs

def _match_exercise(blocks: list[str], key: dict) -> list[dict]:
    items, choices = {}, {}
    for b in blocks:
        for line in b.split("\n"):
            s = line.strip()
            if re.match(r"^\d+\s*[–\-]\s*[a-zA-Z]\s*$", s): continue
            m = re.match(r"^(\d+)\s+([A-Za-z].{2,40})$", s)
            if m: items[int(m.group(1))] = m.group(2).strip()
            m2 = re.match(r"^([a-hA-H])[\)\.]?\s+(.{3,})", s)
            if m2: choices[m2.group(1).lower()] = m2.group(2).strip()
    qs = []
    for num, word in sorted(items.items()):
        if num in key and key[num] in choices:
            qs.append({"num": num, "q": word, "opts": list(choices.values()),
                       "ans": list(choices.keys()).index(key[num])})
    return qs


# ── Quiz builders ─────────────────────────────────────────────────────────────

def build_quiz(lesson_id: int, title: str) -> dict | None:
    """Best quiz from lesson — tries MC first, then vocab match."""
    # 1. Listening MC (most common)
    lb = _blocks_for("listening", "test_quiz", lesson_id=lesson_id)
    if lb:
        key = _answer_key(lb)
        qs  = _mc_questions(lb, key)
        if len(qs) >= 3:
            random.shuffle(qs)
            return _make_state("mc_quiz", lesson_id, title, qs[:10])

    # 2. Speaking MC
    sb = _blocks_for("speaking", lesson_id=lesson_id)
    if sb:
        key = _answer_key(sb); qs = _mc_questions(sb, key)
        if len(qs) >= 3:
            random.shuffle(qs)
            return _make_state("mc_quiz", lesson_id, title, qs[:8])

    # 3. Matching exercise
    vb = _blocks_for("vocabulary", "test_quiz", lesson_id=lesson_id)
    if vb:
        key = _answer_key(vb); qs = _match_exercise(vb, key)
        if len(qs) >= 3:
            random.shuffle(qs)
            return _make_state("mc_quiz", lesson_id, title, qs[:8])

    # 4. Vocab pair fallback
    return build_vocab_quiz(lesson_id, title)

def build_vocab_quiz(lesson_id: int, title: str) -> dict | None:
    pairs = _vocab_pairs(_all_blocks(lesson_id))
    if len(pairs) < 3: return None
    random.shuffle(pairs)
    return _make_state("vocab_match", lesson_id, title, pairs[:8])

def build_scramble(lesson_id: int, title: str) -> dict | None:
    pairs = _vocab_pairs(_blocks_for("vocabulary", lesson_id=lesson_id))
    words = [(w.split()[0] if " " in w else w, d)
             for w, d in pairs if 4 <= len(w.split()[0] if " " in w else w) <= 15]
    if len(words) < 3: return None
    random.shuffle(words)
    qs = []
    for word, defn in words[:8]:
        w, letters = word.lower(), list(word.lower())
        for _ in range(15):
            random.shuffle(letters)
            if "".join(letters) != w: break
        qs.append({"word": w, "scrambled": "".join(letters), "hint": defn})
    return _make_state("scramble", lesson_id, title, qs)

def _make_state(gtype, lid, title, qs) -> dict:
    return {"type": gtype, "lesson_id": lid, "lesson_title": title,
            "questions": qs, "current": 0, "score": 0, "total": len(qs)}


# ── Renderers ─────────────────────────────────────────────────────────────────

LABELS = ["🅰","🅱","🆎","🆑"]

def _bar(s, t):
    f = round(s/t*10) if t else 0
    return "🟩"*f + "⬜"*(10-f)

def render_question(state: dict) -> tuple[str, InlineKeyboardMarkup]:
    gtype = state["type"]
    if gtype == "vocab_match": return _render_vocab(state)
    if gtype == "mc_quiz":     return _render_mc(state)
    if gtype == "scramble":    return _render_scramble(state)
    raise ValueError(f"Unknown game type: {gtype}")

def _render_vocab(s):
    idx = s["current"]
    word, correct = s["questions"][idx]
    all_defs = [q[1] for q in s["questions"]]
    opts = [correct] + random.sample([d for d in all_defs if d != correct], min(3, len(all_defs)-1))
    random.shuffle(opts)
    cp = opts.index(correct)
    lid = s["lesson_id"]
    text = (f"📚 *Vocabulary Match*\n📘 _{s['lesson_title']}_\n\n"
            f"{_bar(s['score'],s['total'])}  Q{idx+1}/{s['total']} · Score *{s['score']}*\n\n"
            f"🔤 What does **{word.upper()}** mean?")
    btns = [[InlineKeyboardButton(f"{LABELS[i]} {o[:40]}{'…' if len(o)>40 else ''}",
             callback_data=f"gv_{i}_{cp}_{lid}")] for i,o in enumerate(opts)]
    btns.append([InlineKeyboardButton("❌ Quit", callback_data=f"gq_{lid}")])
    return text, InlineKeyboardMarkup(btns)

def _render_mc(s):
    idx = s["current"]
    q = s["questions"][idx]
    indexed = list(enumerate(q["opts"])); random.shuffle(indexed)
    cn = next(i for i,(old,_) in enumerate(indexed) if old == q["ans"])
    lid = s["lesson_id"]
    text = (f"🎯 *Quiz Time!*\n📘 _{s['lesson_title']}_\n\n"
            f"{_bar(s['score'],s['total'])}  Q{idx+1}/{s['total']} · Score *{s['score']}*\n\n"
            f"❓ {q['q']}")
    btns = [[InlineKeyboardButton(f"{LABELS[i]} {o[:40]}{'…' if len(o)>40 else ''}",
             callback_data=f"gm_{i}_{cn}_{lid}")] for i,(_,o) in enumerate(indexed)]
    btns.append([InlineKeyboardButton("❌ Quit", callback_data=f"gq_{lid}")])
    return text, InlineKeyboardMarkup(btns)

def _render_scramble(s):
    idx = s["current"]
    q = s["questions"][idx]
    w = q["word"]
    cands = list(dict.fromkeys(c for c in [w[1:]+w[0], w[-1]+w[:-1], w[::-1],
             w[0]+w[2]+w[1]+w[3:] if len(w)>3 else w+"ed"] if c != w))
    opts = [w] + cands[:3]; random.shuffle(opts); cp = opts.index(w)
    lid = s["lesson_id"]
    hint = " ".join(q["hint"].split()[:5]) + ("…" if len(q["hint"].split())>5 else "")
    text = (f"🔀 *Word Scramble!*\n📘 _{s['lesson_title']}_\n\n"
            f"{_bar(s['score'],s['total'])}  Q{idx+1}/{s['total']} · Score *{s['score']}*\n\n"
            f"💡 _{hint}_\n\n🔠 Unscramble:\n```\n{q['scrambled'].upper()}\n```")
    btns = [[InlineKeyboardButton(f"{LABELS[i]} {o.capitalize()}",
             callback_data=f"gs_{i}_{cp}_{lid}")] for i,o in enumerate(opts)]
    btns.append([InlineKeyboardButton("❌ Quit", callback_data=f"gq_{lid}")])
    return text, InlineKeyboardMarkup(btns)

def render_result(s: dict) -> tuple[str, InlineKeyboardMarkup]:
    score, total = s["score"], s["total"]
    pct = round(score/total*100) if total else 0
    emoji, msg, stars = (
        ("🏆","Outstanding! Perfect!","⭐⭐⭐⭐⭐") if pct>=90 else
        ("🌟","Excellent work!","⭐⭐⭐⭐") if pct>=75 else
        ("👍","Good job!","⭐⭐⭐") if pct>=60 else
        ("💪","Keep practicing!","⭐⭐") if pct>=40 else
        ("📖","Study more!","⭐"))
    lid = s["lesson_id"]
    text = (f"{emoji} *Quiz Complete!*\n📘 _{s['lesson_title']}_\n\n"
            f"{_bar(score,total)}\nScore: *{score}/{total}* ({pct}%)\n{stars}\n\n_{msg}_")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Play Again", callback_data=f"ga_{lid}"),
         InlineKeyboardButton("🏅 Leaderboard", callback_data=f"glb_{lid}")],
        [InlineKeyboardButton("⬅️ Back to Lesson", callback_data=f"sl_{lid}")],
    ])
    return text, kb

async def send_game_menu(update: Update, lesson_id: int, title: str):
    text = (f"🎮 *Games & Quiz*\n📘 _{title}_\n\n"
            f"🎯 *Quick Quiz* — MC questions from lesson\n"
            f"📚 *Vocab Match* — Match words to meanings\n"
            f"🔀 *Word Scramble* — Unscramble vocabulary\n"
            f"🏅 *Leaderboard* — Top scorers")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Quick Quiz",    callback_data=f"gstart_mc_{lesson_id}"),
         InlineKeyboardButton("📚 Vocab Match",   callback_data=f"gstart_vocab_{lesson_id}")],
        [InlineKeyboardButton("🔀 Word Scramble", callback_data=f"gstart_sc_{lesson_id}"),
         InlineKeyboardButton("🏅 Leaderboard",   callback_data=f"glb_{lesson_id}")],
        [InlineKeyboardButton("⬅️ Back", callback_data=f"sl_{lesson_id}")],
    ])
    msg = update.callback_query
    try:
        await msg.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    except Exception:
        await update.effective_chat.send_message(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
