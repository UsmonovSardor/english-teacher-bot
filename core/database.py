"""Database layer — full analytics, registration, task submissions."""
import sqlite3, logging
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
        yield conn; conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()

def init_db():
    with _db() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL, topic TEXT DEFAULT '',
                emoji TEXT DEFAULT '📘',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lesson_id INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
                category TEXT NOT NULL, body TEXT NOT NULL,
                order_num INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS students (
                chat_id INTEGER PRIMARY KEY,
                username TEXT DEFAULT '', full_name TEXT DEFAULT '',
                group_name TEXT DEFAULT '', registered INTEGER DEFAULT 0,
                joined_at TEXT DEFAULT (datetime('now')),
                last_seen TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL, lesson_id INTEGER,
                category TEXT DEFAULT '', action TEXT DEFAULT 'view',
                at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS quiz_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL, lesson_id INTEGER NOT NULL,
                score INTEGER DEFAULT 0, total INTEGER DEFAULT 0,
                at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS task_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL, lesson_id INTEGER NOT NULL,
                category TEXT NOT NULL, started_at TEXT,
                submitted_at TEXT DEFAULT (datetime('now')),
                duration_seconds INTEGER DEFAULT 0, answer_text TEXT DEFAULT ''
            );
        """)
        for sql in [
            "ALTER TABLE students ADD COLUMN group_name TEXT DEFAULT ''",
            "ALTER TABLE students ADD COLUMN registered INTEGER DEFAULT 0",
        ]:
            try: c.execute(sql)
            except: pass
    logger.info("DB ready: %s", DB_PATH)

def is_admin(chat_id): return chat_id in _ADMIN_SESSIONS
def set_admin(chat_id, v):
    if v: _ADMIN_SESSIONS.add(chat_id)
    else: _ADMIN_SESSIONS.discard(chat_id)

def upsert_student(chat_id, username, full_name):
    now = datetime.now().isoformat()
    with _db() as c:
        c.execute("""INSERT INTO students(chat_id,username,full_name,joined_at,last_seen)
                     VALUES(?,?,?,?,?) ON CONFLICT(chat_id) DO UPDATE SET
                     username=excluded.username,last_seen=excluded.last_seen""",
                  (chat_id, username or "", full_name or "", now, now))

def get_student(chat_id):
    with _db() as c: return c.execute("SELECT * FROM students WHERE chat_id=?", (chat_id,)).fetchone()

def is_registered(chat_id):
    r = get_student(chat_id); return bool(r and r["registered"])

def register_student(chat_id, full_name, group_name):
    now = datetime.now().isoformat()
    with _db() as c:
        c.execute("""INSERT INTO students(chat_id,full_name,group_name,registered,joined_at,last_seen)
                     VALUES(?,?,?,1,?,?) ON CONFLICT(chat_id) DO UPDATE SET
                     full_name=excluded.full_name,group_name=excluded.group_name,
                     registered=1,last_seen=excluded.last_seen""",
                  (chat_id, full_name or "", group_name or "", now, now))

def all_students():
    with _db() as c: return c.execute("SELECT * FROM students ORDER BY last_seen DESC").fetchall()

def student_count():
    with _db() as c: return c.execute("SELECT COUNT(*) FROM students").fetchone()[0]

def group_stats():
    with _db() as c:
        return c.execute("""SELECT group_name, COUNT(*) cnt FROM students
            WHERE registered=1 AND group_name!=''
            GROUP BY group_name ORDER BY cnt DESC""").fetchall()

def log(chat_id, lesson_id=None, category="", action="view"):
    now = datetime.now().isoformat()
    with _db() as c:
        c.execute("INSERT INTO activity(chat_id,lesson_id,category,action,at) VALUES(?,?,?,?,?)",
                  (chat_id, lesson_id, category, action, now))
        c.execute("UPDATE students SET last_seen=? WHERE chat_id=?", (now, chat_id))

def recent_activity(limit=25):
    with _db() as c:
        return c.execute("""SELECT a.*,s.username,s.full_name,s.group_name,l.title lesson_title
            FROM activity a LEFT JOIN students s ON a.chat_id=s.chat_id
            LEFT JOIN lessons l ON a.lesson_id=l.id ORDER BY a.at DESC LIMIT ?""", (limit,)).fetchall()

def popular_lessons(limit=5):
    with _db() as c:
        return c.execute("""SELECT l.title,COUNT(*) views FROM activity a
            JOIN lessons l ON a.lesson_id=l.id WHERE a.action='view'
            GROUP BY l.id ORDER BY views DESC LIMIT ?""", (limit,)).fetchall()

def popular_categories():
    with _db() as c:
        return c.execute("""SELECT category,COUNT(*) cnt FROM activity
            WHERE category!='' GROUP BY category ORDER BY cnt DESC""").fetchall()

def save_task(chat_id, lesson_id, category, started_at, duration, answer):
    with _db() as c:
        c.execute("""INSERT INTO task_submissions(chat_id,lesson_id,category,
                     started_at,submitted_at,duration_seconds,answer_text)
                     VALUES(?,?,?,?,datetime('now'),?,?)""",
                  (chat_id, lesson_id, category, started_at, duration, answer))

def all_submissions(limit=30):
    with _db() as c:
        return c.execute("""SELECT ts.*,s.full_name,s.username,s.group_name,l.title lesson_title
            FROM task_submissions ts LEFT JOIN students s ON ts.chat_id=s.chat_id
            LEFT JOIN lessons l ON ts.lesson_id=l.id
            ORDER BY ts.submitted_at DESC LIMIT ?""", (limit,)).fetchall()

def lesson_submissions(lesson_id, limit=20):
    with _db() as c:
        return c.execute("""SELECT ts.*,s.full_name,s.username,s.group_name
            FROM task_submissions ts LEFT JOIN students s ON ts.chat_id=s.chat_id
            WHERE ts.lesson_id=? ORDER BY ts.submitted_at DESC LIMIT ?""", (lesson_id, limit)).fetchall()

def submission_count():
    with _db() as c: return c.execute("SELECT COUNT(*) FROM task_submissions").fetchone()[0]

def save_score(chat_id, lesson_id, score, total):
    with _db() as c:
        c.execute("INSERT INTO quiz_scores(chat_id,lesson_id,score,total) VALUES(?,?,?,?)",
                  (chat_id, lesson_id, score, total))

def lesson_leaderboard(lesson_id, limit=10):
    with _db() as c:
        return c.execute("""SELECT s.full_name,s.username,s.group_name,q.score,q.total,
            ROUND(CAST(q.score AS FLOAT)/q.total*100,1) pct,q.at
            FROM quiz_scores q JOIN students s ON q.chat_id=s.chat_id
            WHERE q.lesson_id=? AND q.total>0 ORDER BY pct DESC,q.at ASC LIMIT ?""",
                         (lesson_id, limit)).fetchall()

def global_leaderboard(limit=10):
    with _db() as c:
        return c.execute("""SELECT s.full_name,s.username,s.group_name,
            COUNT(q.id) quiz_count,AVG(CAST(q.score AS FLOAT)/q.total*100) avg_pct,SUM(q.score) total_score
            FROM quiz_scores q JOIN students s ON q.chat_id=s.chat_id
            WHERE q.total>0 GROUP BY q.chat_id ORDER BY avg_pct DESC LIMIT ?""", (limit,)).fetchall()

def student_stats(chat_id):
    with _db() as c:
        views = c.execute("SELECT COUNT(*) FROM activity WHERE chat_id=?", (chat_id,)).fetchone()[0]
        tasks = c.execute("SELECT COUNT(*) FROM task_submissions WHERE chat_id=?", (chat_id,)).fetchone()[0]
        r = c.execute("""SELECT COUNT(*),AVG(CAST(score AS FLOAT)/total*100)
            FROM quiz_scores WHERE chat_id=? AND total>0""", (chat_id,)).fetchone()
        return {"views":views,"tasks":tasks,"quiz_count":r[0] or 0,"avg_score":round(r[1] or 0,1)}

def create_lesson(title, topic="", emoji="📘"):
    with _db() as c:
        return c.execute("INSERT INTO lessons(title,topic,emoji) VALUES(?,?,?)",
                         (title, topic, emoji)).lastrowid

def all_lessons():
    with _db() as c: return c.execute("SELECT * FROM lessons ORDER BY created_at DESC").fetchall()

def get_lesson(lid):
    with _db() as c: return c.execute("SELECT * FROM lessons WHERE id=?", (lid,)).fetchone()

def update_lesson(lid, title, topic="", emoji="📘"):
    with _db() as c:
        c.execute("UPDATE lessons SET title=?,topic=?,emoji=?,updated_at=datetime('now') WHERE id=?",
                  (title, topic, emoji, lid))

def delete_lesson(lid):
    with _db() as c: c.execute("DELETE FROM lessons WHERE id=?", (lid,))

def lesson_has_content(lid):
    with _db() as c:
        return c.execute("SELECT COUNT(*) FROM content WHERE lesson_id=?", (lid,)).fetchone()[0] > 0

def add_content(lesson_id, category, body, order_num=0):
    with _db() as c:
        c.execute("INSERT INTO content(lesson_id,category,body,order_num) VALUES(?,?,?,?)",
                  (lesson_id, category, body, order_num))

def lesson_content(lesson_id):
    with _db() as c:
        return c.execute("SELECT * FROM content WHERE lesson_id=? ORDER BY category,order_num",
                         (lesson_id,)).fetchall()

def category_content(lesson_id, category):
    with _db() as c:
        return c.execute("SELECT * FROM content WHERE lesson_id=? AND category=? ORDER BY order_num",
                         (lesson_id, category)).fetchall()

def get_content(cid):
    with _db() as c: return c.execute("SELECT * FROM content WHERE id=?", (cid,)).fetchone()

def update_content(cid, body):
    with _db() as c: c.execute("UPDATE content SET body=? WHERE id=?", (body, cid))

def delete_content(cid):
    with _db() as c: c.execute("DELETE FROM content WHERE id=?", (cid,))

def clear_category(lesson_id, category):
    with _db() as c: c.execute("DELETE FROM content WHERE lesson_id=? AND category=?", (lesson_id, category))

def available_categories(lesson_id):
    with _db() as c:
        return [r["category"] for r in c.execute(
            "SELECT DISTINCT category FROM content WHERE lesson_id=?", (lesson_id,)).fetchall()]
