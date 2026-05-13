
"""Central configuration."""

import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "english2024")

_data_dir = os.getenv("DATA_DIR", "/data")
os.makedirs(_data_dir, exist_ok=True)

DB_PATH = os.getenv("DB_PATH", os.path.join(_data_dir, "lingua.db"))

os.makedirs(
    os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".",
    exist_ok=True,
)

CATEGORIES = [
    ("🔗 Links", "links"),
    ("🖼 Visuals", "visuals"),
    ("📖 Vocabulary", "vocabulary"),
    ("📘 Grammar", "grammar"),
    ("🗣 Speaking", "speaking"),
    ("🎧 Listening", "listening"),
    ("📚 Reading", "reading"),
    ("✍️ Writing", "writing"),
    ("🎮 Games", "games"),
    ("📝 Homework", "homework"),
    ("📋 Test & Quiz", "test_quiz"),
]

CATEGORY_KEYWORDS = {
    "links": [
        "link", "url", "http", "website", "www",
    ],
    "visuals": [
        "image", "picture", "photo", "diagram", "chart", "visual", "video",
    ],
    "vocabulary": [
        "vocabulary", "vocab", "words", "glossary", "terms",
        "match the words", "word list", "key words", "definitions",
    ],
    "grammar": [
        "grammar", "grammatical", "tense", "tenses", "present simple",
        "present continuous", "past simple", "past continuous",
        "future simple", "will", "going to", "modal verbs", "modals",
        "can", "could", "should", "must", "have to",
        "conditionals", "first conditional", "second conditional",
        "passive voice", "active voice", "reported speech",
        "direct speech", "indirect speech", "articles",
        "prepositions", "conjunctions", "adjectives", "adverbs",
        "comparatives", "superlatives", "pronouns", "nouns",
        "verbs", "auxiliary verbs", "to be", "there is", "there are",
        "sentence structure", "word order", "question forms",
    ],
    "speaking": [
        "speaking", "speak", "discussion", "discuss", "case study",
        "warm up", "role play", "group work", "pair work",
        "debate", "presentation",
    ],
    "listening": [
        "listening task", "listening:", "audio", "listen",
        "recording", "listening activity", "track",
    ],
    "reading": [
        "reading task", "reading:", "read the text", "reading passage",
        "comprehension", "read and answer", "reading activity",
        "text:", "passage:", "article:", "read the following",
    ],
    "writing": [
        "writing", "write", "essay", "paragraph", "compose",
        "writing task", "write a", "composition",
    ],
    "games": [
        "game", "puzzle", "quiz game", "bingo", "fun activity", "crossword",
    ],
    "homework": [
        "homework", "home task", "assignment", "at home", "home work",
    ],
    "test_quiz": [
        "test", "quiz", "exam", "answer key",
        "reading answers", "listening answers",
    ],
}


class State:
    LOGIN_USER = 0
    LOGIN_PASS = 1
    ADD_LESSON = 2
    EDIT_CONTENT = 3
    RENAME_LESSON = 4
    UPLOAD_DOC = 5
