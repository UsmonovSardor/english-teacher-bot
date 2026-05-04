"""All Telegram keyboards — premium design."""
from telegram import InlineKeyboardButton as Btn, InlineKeyboardMarkup as Kb
from core.config import CATEGORIES

CAT_MAP = {
    "links": "Links",
    "visuals": "Visuals",
    "vocabulary": "Vocabulary",
    "speaking": "Speaking",
    "listening": "Listening",
    "reading": "Reading",
    "writing": "Writing",
    "games": "Games",
    "homework": "Homework",
    "test_quiz": "Test & Quiz",
}

CAT_EMOJI = {
    "links": "🔗",
    "visuals": "🖼",
    "vocabulary": "📖",
    "speaking": "🗣",
    "listening": "🎧",
    "reading": "📚",
    "writing": "✍️",
    "games": "🎮",
    "homework": "📝",
    "test_quiz": "📋",
}


def student_lessons(lessons):
    return Kb([
        [Btn(f"{l['emoji']} {l['title']}", callback_data=f"sl_{l['id']}")]
        for l in lessons
    ])


def student_cats(lid, available):
    always = {"links", "games"}
    ordered = [key for _, key in CATEGORIES if key in available or key in always]

    btns, row = [], []

    for key in ordered:
        row.append(
            Btn(
                f"{CAT_EMOJI.get(key, '📄')} {CAT_MAP.get(key, key.title())}",
                callback_data=f"sc_{lid}_{key}",
            )
        )

        if len(row) == 2:
            btns.append(row)
            row = []

    if row:
        btns.append(row)

    btns.append([Btn("🏠 All Lessons", callback_data="student")])

    return Kb(btns)


def back_to_lesson(lid):
    return Kb([[Btn("📚 Back to Lesson", callback_data=f"sl_{lid}")]])


def back_to_lessons():
    return Kb([[Btn("🏠 All Lessons", callback_data="student")]])


def admin_main():
    return Kb([
        [
            Btn("📂 Lessons", callback_data="a_lessons"),
            Btn("➕ New Lesson", callback_data="a_new"),
        ],
        [
            Btn("📊 Analytics", callback_data="a_analytics"),
            Btn("🏆 Leaderboard", callback_data="a_leaderboard"),
        ],
        [Btn("🚪 Logout", callback_data="a_logout")],
    ])


def admin_lessons(lessons):
    btns = [
        [
            Btn(
                f"{'✅' if l.get('has_content') else '⚠️'} {l['emoji']} {l['title']}",
                callback_data=f"al_{l['id']}",
            )
        ]
        for l in lessons
    ]

    btns.append([Btn("⬅️ Back", callback_data="a_main")])

    return Kb(btns)


def admin_lesson(lid):
    return Kb([
        [
            Btn("📤 Upload Document", callback_data=f"aup_{lid}"),
            Btn("📋 Edit Content", callback_data=f"aec_{lid}"),
        ],
        [
            Btn("🔗 Manage Links", callback_data=f"alc_{lid}"),
            Btn("📊 Quiz Stats", callback_data=f"aqs_{lid}"),
        ],
        [
            Btn("✏️ Rename", callback_data=f"aren_{lid}"),
            Btn("🗑 Delete", callback_data=f"adel_{lid}"),
        ],
        [Btn("⬅️ Back to Lessons", callback_data="a_lessons")],
    ])


def admin_cats(lid):
    btns = [
        [
            Btn(
                f"{CAT_EMOJI.get(key, '📄')} {CAT_MAP.get(key, key.title())}",
                callback_data=f"acat_{lid}_{key}",
            )
        ]
        for _, key in CATEGORIES
    ]

    btns.append([Btn("⬅️ Back", callback_data=f"al_{lid}")])

    return Kb(btns)


def admin_cat_actions(lid, cat):
    return Kb([
        [
            Btn("➕ Add Content", callback_data=f"aadd_{lid}_{cat}"),
            Btn("🗑 Clear All", callback_data=f"aclr_{lid}_{cat}"),
        ],
        [Btn("⬅️ Back", callback_data=f"aec_{lid}")],
    ])


def admin_content_item(cid, lid, cat):
    return Kb([
        [
            Btn("✏️ Edit", callback_data=f"aeit_{cid}"),
            Btn("🗑 Delete", callback_data=f"adit_{cid}"),
        ],
        [Btn("⬅️ Back", callback_data=f"acat_{lid}_{cat}")],
    ])


def confirm(yes, no):
    return Kb([
        [
            Btn("✅ Yes, Delete", callback_data=yes),
            Btn("❌ Cancel", callback_data=no),
        ]
    ])


def admin_links(lid, link_items):
    btns = []

    for cid, label, url in link_items:
        btns.append([
            Btn(f"🔗 {label[:20]}", url=url),
            Btn("🗑 Delete", callback_data=f"alcd_{cid}"),
        ])

    btns.append([Btn("➕ Add Link", callback_data=f"alca_{lid}")])
    btns.append([Btn("⬅️ Back", callback_data=f"al_{lid}")])

    return Kb(btns)
