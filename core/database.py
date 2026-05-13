"""Database layer — full analytics, registration, task submissions."""

import sqlite3
import logging
from datetime import datetime
from contextlib import contextmanager
from core.config import DB_PATH

logger = logging.getLogger(__name__)

_ADMIN_SESSIONS = set()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        yield conn
        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def init_db():
    with _db() as c:

        c.executescript("""
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                topic TEXT DEFAULT '',
                emoji TEXT DEFAULT '📘',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lesson_id INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
                category TEXT NOT NULL,
                body TEXT NOT NULL,
                order_num INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS students (
                chat_id INTEGER PRIMARY KEY,
                username TEXT DEFAULT '',
                full_name TEXT DEFAULT '',
                group_name TEXT DEFAULT '',
                registered INTEGER DEFAULT 0,
                joined_at TEXT DEFAULT (datetime('now')),
                last_seen TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                lesson_id INTEGER,
                category TEXT DEFAULT '',
                action TEXT DEFAULT 'view',
                at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS quiz_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                lesson_id INTEGER NOT NULL,
                score INTEGER DEFAULT 0,
                total INTEGER DEFAULT 0,
                at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS task_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                lesson_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                started_at TEXT,
                submitted_at TEXT DEFAULT (datetime('now')),
                duration_seconds INTEGER DEFAULT 0,
                answer_text TEXT DEFAULT ''
            );
        """)

        for sql in [
            "ALTER TABLE students ADD COLUMN group_name TEXT DEFAULT ''",
            "ALTER TABLE students ADD COLUMN registered INTEGER DEFAULT 0",
        ]:
            try:
                c.execute(sql)
            except:
                pass

    logger.info("DB ready: %s", DB_PATH)


def is_admin(chat_id):
    return chat_id in _ADMIN_SESSIONS


def set_admin(chat_id, value):
    if value:
        _ADMIN_SESSIONS.add(chat_id)
    else:
        _ADMIN_SESSIONS.discard(chat_id)


def upsert_student(chat_id, username, full_name):
    now = datetime.now().isoformat()

    with _db() as c:
        c.execute("""
            INSERT INTO students(
                chat_id,
                username,
                full_name,
                joined_at,
                last_seen
            )
            VALUES(?,?,?,?,?)

            ON CONFLICT(chat_id)
            DO UPDATE SET
                username=excluded.username,
                last_seen=excluded.last_seen
        """, (
            chat_id,
            username or "",
            full_name or "",
            now,
            now,
        ))


def get_student(chat_id):
    with _db() as c:
        return c.execute(
            "SELECT * FROM students WHERE chat_id=?",
            (chat_id,),
        ).fetchone()


def is_registered(chat_id):
    row = get_student(chat_id)
    return bool(row and row["registered"])


def register_student(chat_id, full_name, group_name):
    now = datetime.now().isoformat()

    with _db() as c:
        c.execute("""
            INSERT INTO students(
                chat_id,
                full_name,
                group_name,
                registered,
                joined_at,
                last_seen
            )
            VALUES(?,?,?,1,?,?)

            ON CONFLICT(chat_id)
            DO UPDATE SET
                full_name=excluded.full_name,
                group_name=excluded.group_name,
                registered=1,
                last_seen=excluded.last_seen
        """, (
            chat_id,
            full_name or "",
            group_name or "",
            now,
            now,
        ))


def all_students():
    with _db() as c:
        return c.execute("""
            SELECT *
            FROM students
            ORDER BY last_seen DESC
        """).fetchall()


def student_count():
    with _db() as c:
        return c.execute(
            "SELECT COUNT(*) FROM students"
        ).fetchone()[0]


def create_lesson(title, topic="", emoji="📘"):
    with _db() as c:

        lesson_id = c.execute("""
            INSERT INTO lessons(
                title,
                topic,
                emoji
            )
            VALUES(?,?,?)
        """, (
            title,
            topic,
            emoji,
        )).lastrowid

        return lesson_id


def all_lessons():
    with _db() as c:
        return c.execute("""
            SELECT *
            FROM lessons
            ORDER BY updated_at DESC
        """).fetchall()


def get_lesson(lid):
    with _db() as c:
        return c.execute(
            "SELECT * FROM lessons WHERE id=?",
            (lid,),
        ).fetchone()


def update_lesson(lid, title, topic="", emoji="📘"):
    with _db() as c:

        c.execute("""
            UPDATE lessons
            SET
                title=?,
                topic=?,
                emoji=?,
                updated_at=datetime('now')
            WHERE id=?
        """, (
            title,
            topic,
            emoji,
            lid,
        ))


def delete_lesson(lid):
    with _db() as c:
        c.execute(
            "DELETE FROM lessons WHERE id=?",
            (lid,),
        )


def lesson_has_content(lid):
    with _db() as c:

        count = c.execute("""
            SELECT COUNT(*)
            FROM content
            WHERE lesson_id=?
        """, (
            lid,
        )).fetchone()[0]

        return count > 0


def add_content(lesson_id, category, body, order_num=0):
    with _db() as c:

        if not order_num:
            row = c.execute("""
                SELECT COALESCE(MAX(order_num), 0) + 1
                FROM content
                WHERE lesson_id=? AND category=?
            """, (
                lesson_id,
                category,
            )).fetchone()

            order_num = row[0] if row else 1

        c.execute("""
            INSERT INTO content(
                lesson_id,
                category,
                body,
                order_num
            )
            VALUES(?,?,?,?)
        """, (
            lesson_id,
            category,
            body,
            order_num,
        ))

        c.execute("""
            UPDATE lessons
            SET updated_at=datetime('now')
            WHERE id=?
        """, (
            lesson_id,
        ))


def lesson_content(lesson_id):
    with _db() as c:
        return c.execute("""
            SELECT *
            FROM content
            WHERE lesson_id=?
            ORDER BY category, order_num
        """, (
            lesson_id,
        )).fetchall()


def category_content(lesson_id, category):
    with _db() as c:
        return c.execute("""
            SELECT *
            FROM content
            WHERE lesson_id=? AND category=?
            ORDER BY order_num
        """, (
            lesson_id,
            category,
        )).fetchall()


def get_content(cid):
    with _db() as c:
        return c.execute(
            "SELECT * FROM content WHERE id=?",
            (cid,),
        ).fetchone()


def update_content(cid, body):
    with _db() as c:

        row = c.execute("""
            SELECT lesson_id
            FROM content
            WHERE id=?
        """, (
            cid,
        )).fetchone()

        c.execute("""
            UPDATE content
            SET body=?
            WHERE id=?
        """, (
            body,
            cid,
        ))

        if row:
            c.execute("""
                UPDATE lessons
                SET updated_at=datetime('now')
                WHERE id=?
            """, (
                row["lesson_id"],
            ))


def delete_content(cid):
    with _db() as c:

        row = c.execute("""
            SELECT lesson_id
            FROM content
            WHERE id=?
        """, (
            cid,
        )).fetchone()

        c.execute("""
            DELETE FROM content
            WHERE id=?
        """, (
            cid,
        ))

        if row:
            c.execute("""
                UPDATE lessons
                SET updated_at=datetime('now')
                WHERE id=?
            """, (
                row["lesson_id"],
            ))


def clear_category(lesson_id, category):
    with _db() as c:

        c.execute("""
            DELETE FROM content
            WHERE lesson_id=? AND category=?
        """, (
            lesson_id,
            category,
        ))

        c.execute("""
            UPDATE lessons
            SET updated_at=datetime('now')
            WHERE id=?
        """, (
            lesson_id,
        ))


def available_categories(lesson_id):
    with _db() as c:

        rows = c.execute("""
            SELECT DISTINCT category
            FROM content
            WHERE lesson_id=?
        """, (
            lesson_id,
        )).fetchall()

        return [r["category"] for r in rows]
