"""All Telegram keyboards — premium design."""
from telegram import InlineKeyboardButton as Btn, InlineKeyboardMarkup as Kb
from core.config import CATEGORIES

CAT_MAP = {key: lbl for lbl, key in CATEGORIES}

# ── Category display config ──────────────────────────────────────────────────
CAT_EMOJI = {
    "links":      "🔗",
    "visuals":    "🖼",
    "vocabulary": "📖",
    "speaking":   "🗣",
    "listening":  "🎧",
    "reading":    "📚",
    "writing":    "✍️",
    "games":      "🎮",
    "homework":   "📝",
    "test_quiz":  "📋",
}

# ── Start ────────────────────────────────────────────────────────────────────
def start_kb():
    return Kb([[
        Btn("👨‍💼 Admin Panel",  callback_data="admin"),
        Btn("📚 Student Zone", callback_data="student"),
    ]])

# ── Admin main ───────────────────────────────────────────────────────────────
def admin_main():
    return Kb([
        [Btn("📂 Lessons",     callback_data="a_lessons"),
         Btn("➕ New Lesson",  callback_data="a_new")],
        [Btn("📊 Analytics",   callback_data="a_analytics"),
         Btn("🏆 Leaderboard", callback_data="a_leaderboard")],
        [Btn("🚪 Logout",      callback_data="a_logout")],
    ])

def admin_lessons(lessons):
    btns = []
    for l in lessons:
        mark = "✅" if l.get("has_content") else "⚠️"
        btns.append([Btn(f"{mark} {l['emoji']} {l['title']}", callback_data=f"al_{l['id']}")])
    btns.append([Btn("⬅️ Back", callback_data="a_main")])
    return Kb(btns)

def admin_lesson(lid):
    return Kb([
        [Btn("📤 Upload Doc",  callback_data=f"aup_{lid}"),
         Btn("📋 Edit Content",callback_data=f"aec_{lid}")],
        [Btn("✏️ Rename",      callback_data=f"aren_{lid}"),
         Btn("🗑 Delete",      callback_data=f"adel_{lid}")],
        [Btn("📊 Quiz Stats",  callback_data=f"aqs_{lid}"),
         Btn("⬅️ Back",       callback_data="a_lessons")],
    ])

def admin_cats(lid):
    btns = [[Btn(lbl, callback_data=f"acat_{lid}_{key}")] for lbl, key in CATEGORIES]
    btns.append([Btn("⬅️ Back", callback_data=f"al_{lid}")])
    return Kb(btns)

def admin_cat_actions(lid, cat):
    lbl = CAT_MAP.get(cat, cat)
    return Kb([
        [Btn("➕ Add content",   callback_data=f"aadd_{lid}_{cat}"),
         Btn("🗑 Clear all",    callback_data=f"aclr_{lid}_{cat}")],
        [Btn(f"⬅️ Back to {lbl}", callback_data=f"aec_{lid}")],
    ])

def admin_content_item(cid, lid, cat):
    return Kb([
        [Btn("✏️ Edit", callback_data=f"aeit_{cid}"),
         Btn("🗑 Delete", callback_data=f"adit_{cid}")],
        [Btn("⬅️ Back", callback_data=f"acat_{lid}_{cat}")],
    ])

def confirm(yes, no):
    return Kb([[Btn("✅ Yes, delete", callback_data=yes),
                Btn("❌ Cancel",     callback_data=no)]])

# ── Student ──────────────────────────────────────────────────────────────────
def student_lessons(lessons):
    btns = [[Btn(f"{l['emoji']} {l['title']}", callback_data=f"sl_{l['id']}")] for l in lessons]
    return Kb(btns)

def student_cats(lid, available: list[str]):
    """Show categories that have content; links & games always shown."""
    always   = {"links", "games"}
    ordered  = [key for _, key in CATEGORIES if key in available or key in always]

    btns, row = [], []
    for key in ordered:
        emoji = CAT_EMOJI.get(key, "📄")
        lbl   = CAT_MAP.get(key, key)
        row.append(Btn(f"{emoji} {lbl}", callback_data=f"sc_{lid}_{key}"))
        if len(row) == 2:
            btns.append(row); row = []
    if row:
        btns.append(row)
    btns.append([Btn("🏠 All Lessons", callback_data="student")])
    return Kb(btns)

def back_to_lesson(lid):
    return Kb([[Btn("📚 Back to Topics", callback_data=f"sl_{lid}")]])

def back_to_lessons():
    return Kb([[Btn("🏠 All Lessons", callback_data="student")]])
