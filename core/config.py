"""Central configuration — all constants in one place."""
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN      = os.getenv("BOT_TOKEN", "8631656745:AAEYLy5GMFc-PlJWQdiLrCHS3rNyepuoE2A")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "english2024")

_data_dir = os.getenv("DATA_DIR", ".")
os.makedirs(_data_dir, exist_ok=True)
DB_PATH = os.path.join(_data_dir, "lingua.db")

# Content categories shown to students (order matters)
CATEGORIES: list[tuple[str, str]] = [
    ("🔗 Links",       "links"),
    ("🖼 Visuals",     "visuals"),
    ("📖 Vocabulary",  "vocabulary"),
    ("🗣 Speaking",    "speaking"),
    ("🎧 Listening",   "listening"),
    ("✍️ Writing",     "writing"),
    ("🎮 Games",       "games"),
    ("📝 Homework",    "homework"),
    ("📋 Test & Quiz", "test_quiz"),
]

# Parser: which keywords map to which category
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "links":      ["link", "url", "http", "website", "www"],
    "visuals":    ["image", "picture", "photo", "diagram", "chart", "visual", "video"],
    "vocabulary": ["vocabulary", "vocab", "words", "glossary", "terms", "definitions",
                   "match the words", "task 1. match"],
    "speaking":   ["speaking", "speak", "discussion", "discuss", "case study",
                   "warm up", "role play", "group work", "smartfit", "foodexpress"],
    "listening":  ["listening task", "listening:", "audio", "listen", "recording"],
    "writing":    ["writing", "write", "essay", "paragraph", "compose"],
    "games":      ["game", "puzzle", "quiz game", "bingo", "fun activity"],
    "homework":   ["homework", "home task", "assignment", "at home"],
    "test_quiz":  ["test", "quiz", "exam", "answer key", "reading answers",
                   "reading:", "reading task"],
}

# ConversationHandler state IDs
class State:
    LOGIN_USER    = 0
    LOGIN_PASS    = 1
    ADD_LESSON    = 2
    EDIT_CONTENT  = 3
    RENAME_LESSON = 4
