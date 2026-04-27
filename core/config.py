"""Central configuration — all constants in one place."""
import os
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN Railway Variables ichida yo’q")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "english2024")

_data_dir = os.getenv("DATA_DIR", ".")
os.makedirs(_data_dir, exist_ok=True)
DB_PATH = os.path.join(_data_dir, "lingua.db")

CATEGORIES: list[tuple[str, str]] = [
    ("🔢 Links",       "links"),
    ("🖸 Visuals",     "visuals"),
    ("🔖 Vocabulary",  "vocabulary"),
    ("📣 Speaking",    "speaking"),
    ("🎇 Listening",   "listening"),
    ("🔚 Reading",     "reading"),
    ("✏️ Writing",     "writing"),
    ("🎉‍🎠 Games",       "games"),
    ("📝 Homework",    "homework"),
    ("🐛‖ Test & Quiz", "test_quiz"),
]

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "links":      ["link", "url", "http", "website", "www"],
    "visuals":    ["image", "picture", "photo", "diagram", "chart", "visual", "video"],
    "vocabulary": ["vocabulary", "vocab", "words", "glossary", "terms", "definitions",
                   "match the words", "task 1. match", "word list", "key words"],
    "speaking":   ["speaking", "speak", "discussion", "discuss", "case study",
                   "warm up", "role play", "group work", "smartfit", "foodexpress",
                   "pair work", "debate", "presentation"],
    "listening":  ["listening task", "listening:", "audio", "listen", "recording",
                   "listening activity", "track"],
    "reading":    ["reading task", "reading:", "read the text", "reading passage",
                   "comprehension", "read and answer", "reading activity",
                   "text:", "passage:", "article:", "read the following"],
    "writing":    ["writing", "write", "essay", "paragraph", "compose",
                   "writing task", "write a", "composition"],
    "games":      ["game", "puzzle", "quiz game", "bingo", "fun activity", "crossword"],
    "homework":   ["homework", "home task", "assignment", "at home", "home work"],
    "test_quiz":  ["test", "quiz", "exam", "answer key",
                   "reading answers", "listening answers", "reading task"],
}

class State:
    LOGIN_USER   = 0
    LOGIN_PASS   = 1
    ADD_LESSON   = 2
    EDIT_CONTENT = 3
    RENAME_LESSON = 4
