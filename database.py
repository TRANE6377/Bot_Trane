import sqlite3
from config import DATABASE_PATH


def get_conn():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS news_sources (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            url         TEXT NOT NULL,
            source_type TEXT NOT NULL CHECK(source_type IN ('rss', 'telegram')),
            category    TEXT,
            active      INTEGER NOT NULL DEFAULT 1,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    defaults = {
        "morning_time": "08:00",
        "evening_time": "20:00",
        "timezone": "Europe/Moscow",
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    conn.commit()
    conn.close()


def get_setting(key: str, default: str = "") -> str:
    conn = get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key: str, value: str):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


def get_active_sources(source_type: str | None = None) -> list[dict]:
    conn = get_conn()
    if source_type:
        rows = conn.execute(
            "SELECT * FROM news_sources WHERE active = 1 AND source_type = ? ORDER BY name",
            (source_type,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM news_sources WHERE active = 1 ORDER BY source_type, name"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_sources() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM news_sources ORDER BY source_type, name"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_source(name: str, url: str, source_type: str, category: str | None = None) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO news_sources (name, url, source_type, category) VALUES (?, ?, ?, ?)",
        (name, url, source_type, category),
    )
    new_id = cur.lastrowid
    conn.commit()
    conn.close()
    return new_id


def delete_source(source_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM news_sources WHERE id = ?", (source_id,))
    conn.commit()
    conn.close()


def toggle_source(source_id: int):
    conn = get_conn()
    conn.execute(
        "UPDATE news_sources SET active = CASE WHEN active = 1 THEN 0 ELSE 1 END WHERE id = ?",
        (source_id,),
    )
    conn.commit()
    conn.close()


def get_source(source_id: int) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM news_sources WHERE id = ?", (source_id,)).fetchone()
    conn.close()
    return dict(row) if row else None
