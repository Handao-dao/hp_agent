import sqlite3
import os
from typing import List, Optional, Tuple


class VocabDB:
    def __init__(self, db_path: str):
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._init_tables()

    def _init_tables(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS vocabulary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL UNIQUE,
                translation TEXT NOT NULL,
                context TEXT DEFAULT '',
                encounter_count INTEGER DEFAULT 1,
                mastered INTEGER DEFAULT 0,
                first_seen_at TEXT DEFAULT (datetime('now','localtime')),
                last_seen_at TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS history (
                id TEXT PRIMARY KEY,
                original_text TEXT NOT NULL,
                annotated_text TEXT NOT NULL,
                title TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE INDEX IF NOT EXISTS idx_vocab_word ON vocabulary(word);
            CREATE INDEX IF NOT EXISTS idx_vocab_mastered ON vocabulary(mastered);
            CREATE INDEX IF NOT EXISTS idx_history_created ON history(created_at DESC);
        """)
        self._conn.commit()

        # 兼容已有数据库：如果 mastered_at 列不存在则添加
        try:
            self._conn.execute("""
                ALTER TABLE vocabulary ADD COLUMN mastered_at TEXT DEFAULT NULL
            """)
            self._conn.commit()
        except sqlite3.OperationalError:
            pass  # 列已存在

    def close(self):
        self._conn.close()

    # ==============================
    # 生词操作
    # ==============================

    def upsert_vocabulary(self, word: str, translation: str, context: str = "") -> int:
        cur = self._conn.execute("""
            INSERT INTO vocabulary (word, translation, context)
            VALUES (?, ?, ?)
            ON CONFLICT(word) DO UPDATE SET
                encounter_count = encounter_count + 1,
                last_seen_at = datetime('now','localtime'),
                context = excluded.context
        """, (word, translation, context))
        self._conn.commit()
        cur = self._conn.execute("SELECT id FROM vocabulary WHERE word = ?", (word,))
        return cur.fetchone()[0]

    def get_mastered_words(self) -> List[str]:
        rows = self._conn.execute(
            "SELECT word FROM vocabulary WHERE mastered = 1 ORDER BY word"
        ).fetchall()
        return [row["word"] for row in rows]

    def list_vocabulary(
        self,
        search: str = "",
        mastered: Optional[int] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[dict], int]:
        where = []
        params = []

        if search:
            where.append("word LIKE ?")
            params.append(f"%{search}%")

        if mastered is not None:
            where.append("mastered = ?")
            params.append(mastered)

        where_clause = f"WHERE {' AND '.join(where)}" if where else ""
        count_sql = f"SELECT COUNT(*) as cnt FROM vocabulary {where_clause}"
        total = self._conn.execute(count_sql, params).fetchone()["cnt"]

        if mastered == 1:
            order = "ORDER BY mastered_at DESC"
        else:
            order = "ORDER BY encounter_count DESC, last_seen_at DESC"

        data_sql = f"""
            SELECT * FROM vocabulary {where_clause}
            {order}
            LIMIT ? OFFSET ?
        """
        rows = self._conn.execute(data_sql, params + [limit, offset]).fetchall()
        items = [dict(row) for row in rows]
        return items, total

    def set_mastered(self, vocab_id: int, mastered: bool):
        if mastered:
            self._conn.execute(
                "UPDATE vocabulary SET mastered = 1, mastered_at = datetime('now','localtime') WHERE id = ?",
                (vocab_id,)
            )
        else:
            self._conn.execute(
                "UPDATE vocabulary SET mastered = 0, mastered_at = NULL WHERE id = ?",
                (vocab_id,)
            )
        self._conn.commit()

    def get_vocab_by_id(self, vocab_id: int) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT * FROM vocabulary WHERE id = ?", (vocab_id,)
        ).fetchone()
        return dict(row) if row else None

    def delete_vocabulary(self, vocab_id: int):
        self._conn.execute("DELETE FROM vocabulary WHERE id = ?", (vocab_id,))
        self._conn.commit()

    # ==============================
    # 历史记录操作
    # ==============================

    def save_history(
        self,
        task_id: str,
        original_text: str,
        annotated_text: str,
    ):
        title = original_text.strip().split("\n")[0][:80]
        self._conn.execute("""
            INSERT OR REPLACE INTO history (id, original_text, annotated_text, title)
            VALUES (?, ?, ?, ?)
        """, (task_id, original_text, annotated_text, title))
        self._conn.commit()

    def list_history(self, limit: int = 20, offset: int = 0) -> Tuple[List[dict], int]:
        total = self._conn.execute("SELECT COUNT(*) as cnt FROM history").fetchone()["cnt"]
        rows = self._conn.execute(
            "SELECT id, title, created_at FROM history ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()
        return [dict(row) for row in rows], total

    def get_history(self, task_id: str) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT * FROM history WHERE id = ?", (task_id,)
        ).fetchone()
        return dict(row) if row else None

    def delete_history(self, task_id: str):
        self._conn.execute(
            "DELETE FROM history WHERE id = ?", (task_id,)
        )
        self._conn.commit()
