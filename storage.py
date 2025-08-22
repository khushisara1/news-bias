import sqlite3
from typing import Optional, List, Tuple, Dict
from contextlib import closing

DB_PATH = "digests.db"

def init_db():
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS saved_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT,
            title TEXT,
            url TEXT,
            source TEXT,
            author TEXT,
            published_at TEXT,
            category TEXT,
            summary TEXT,
            rating INTEGER DEFAULT 0
        )
        """)

def save_item(item: Dict):
    fields = ("slug","title","url","source","author","published_at","category","summary","rating")
    values = tuple(item.get(k) for k in fields)
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        conn.execute(f"""
            INSERT INTO saved_items ({",".join(fields)})
            VALUES ({",".join(["?"]*len(fields))})
        """, values)

def list_items(category: Optional[str] = None) -> List[Tuple]:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        if category and category != "All":
            cur = conn.execute("SELECT * FROM saved_items WHERE category=? ORDER BY id DESC", (category,))
        else:
            cur = conn.execute("SELECT * FROM saved_items ORDER BY id DESC")
        return cur.fetchall()

def update_rating(item_id: int, rating: int):
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        conn.execute("UPDATE saved_items SET rating=? WHERE id=?", (rating, item_id))

def delete_item(item_id: int):
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        conn.execute("DELETE FROM saved_items WHERE id=?", (item_id,))
