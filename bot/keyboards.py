"""All Telegram keyboards in one place."""
from telegram import InlineKeyboardButton as Btn, InlineKeyboardMarkup as Kb, ReplyKeyboardMarkup
from core.config import CATEGORIES

CAT_MAP = {key: lbl for lbl, key in CATEGORIES}

# ── Start ─────────────────────────────────────────────────────────────────────
def start_kb():
    return Kb([[Btn("👨‍💼 Admin Panel", callback_data="admin"),
                Btn("📚 Student Zone", callback_data="student")]])

# ── Admin main ────────────────────────────────────────────────────────────────
def admin_main():
    return Kb([
        [Btn("📂 Lessons",    callback_data="a_lessons"),
         Btn("➕ New Lesson", callback_data="a_new")],
        [Btn("📊 Analytics",  callback_data="a_analytics"),
         Btn("🏆 Leaderboard",callback_data="a_leaderboard")],
        [Btn("🚪 Logout",     callback_data="a_logout")],
    ])

def admin_lessons(lessons):
    btns = []
    for l in lessons:
        cnt_emoji = "✅" if l.get("has_content", True) else "⚠️"
        btns.append([Btn(f"{cnt_emoji} {l['emoji']} {l['title']}", callback_data=f"al_{l['id']}")])
    btns.append([Btn("⬅️ Back", callback_data="a_main")])
    return Kb(btns)

def admin_lesson(lid):
    return Kb([
        [Btn("📤 Upload Doc",   callback_data=f"aup_{lid}"),
         Btn("📋 Edit Content", callback_data=f"aec_{lid}")],
        [Btn("✏️ Rename",       callback_data=f"aren_{lid}"),
         Btn("🗑 Delete",        callback_data=f"adel_{lid}")],
        [Btn("📊 Quiz Stats",   callback_data=f"aqs_{lid}"),
         Btn("⬅️ Back",         callback_data="a_lessons")],
    ])

def admin_cats(lid):
    btns = [[Btn(lbl, callback_data=f"acat_{lid}_{key}")] for lbl, key in CATEGORIES]
    btns.append([Btn("⬅️ Back", callback_data=f"al_{lid}")])
    return Kb(btns)

def admin_cat_actions(lid, cat):
    return Kb([
        [Btn("➕ Add",   callback_data=f"aadd_{lid}_{cat}"),
         Btn("🗑 Clear", callback_data=f"aclr_{lid}_{cat}")],
        [Btn("⬅️ Back",  callback_data=f"aec_{lid}")],
    ])

def admin_content_item(cid, lid, cat):
    return Kb([
        [Btn("✏️ Edit",  callback_data=f"aeit_{cid}"),
         Btn("🗑 Delete",callback_data=f"adit_{cid}")],
        [Btn("⬅️ Back", callback_data=f"acat_{lid}_{cat}")],
    ])

def confirm(yes, no):
    return Kb([[Btn("✅ Yes", callback_data=yes), Btn("❌ No", callback_data=no)]])

# ── Student ───────────────────────────────────────────────────────────────────
def student_lessons(lessons):
    btns = [[Btn(f"{l['emoji']} {l['title']}", callback_data=f"sl_{l['id']}")] for l in lessons]
    return Kb(btns)

def student_cats(lid, available: list[str]):
    """Show all relevant categories; Links & Games always visible."""
    always = {"links", "games"}
    ordered = [key for _, key in CATEGORIES if key in available or key in always]
    btns, row = [], []
    for key in ordered:
        lbl = CAT_MAP.get(key, key)
        row.append(Btn(lbl, callback_data=f"sc_{lid}_{key}"))
        if len(row) == 2:
            btns.append(row); row = []
    if row: btns.append(row)
    btns.append([Btn("🏠 All Lessons", callback_data="student")])
    return Kb(btns)

def back_to_lesson(lid):
    return Kb([[Btn("⬅️ Back to Topics", callback_data=f"sl_{lid}")]])
