"""
SQLite 持久化层：生词本 (vocabulary) + 翻译历史 (history)。

设计要点：
- WAL 模式，读写不互相阻塞
- threading.RLock 保护所有写操作，防止 SSE 自动保存与 REST API 并发冲突
- sqlite3.Row 行工厂，查询返回字典式行对象
- 生词 upsert 去重累加 encounter_count，历史记录 INSERT OR REPLACE
"""

import os
import sqlite3
import threading


class VocabDB:
    """
    基于 sqlite3 的生词与历史记录持久化。

    使用单连接 + RLock 方案而非连接池，原因：
    1. FastAPI async 单线程事件循环中，同步 sqlite3 调用天然串行
    2. RLock 只需防范 SSE 回调与 REST handler 之间的协程切换并发
    3. 零额外依赖，适合个人工具和小规模部署
    """
    def __init__(self, db_path: str):
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._lock = threading.RLock()
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
        """
        插入或更新生词。
        - 新词：INSERT，encounter_count = 1
        - 已有词：UPDATE，encounter_count + 1，更新 context
        返回生词的 id（新增或已有）。
        """
        with self._lock:
            cur = self._conn.execute("""
                INSERT INTO vocabulary (word, translation, context)
                VALUES (?, ?, ?)
                ON CONFLICT(word) DO UPDATE SET
                    encounter_count = encounter_count + 1,
                    last_seen_at = datetime('now','localtime'),
                    context = excluded.context
                RETURNING id
            """, (word, translation, context))
            row = cur.fetchone()
            self._conn.commit()
            return row[0]

    def get_mastered_words(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT word FROM vocabulary WHERE mastered = 1 ORDER BY word"
        ).fetchall()
        return [row["word"] for row in rows]

    def list_vocabulary(
        self,
        search: str = "",
        mastered: int | None = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[list[dict], int]:
        """
        查询生词列表。
        - mastered=0: 未掌握，按 encounter_count 降序
        - mastered=1: 已掌握，按 mastered_at 降序
        - None: 全部
        返回 (items, total) 元组。
        """
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
        """标记生词为已掌握或取消掌握，同时更新 mastered_at 时间戳。"""
        with self._lock:
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

    def get_vocab_by_id(self, vocab_id: int) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM vocabulary WHERE id = ?", (vocab_id,)
        ).fetchone()
        return dict(row) if row else None

    def set_mastered_by_word(self, word: str, mastered: bool) -> bool:
        """
        按单词标记已掌握/取消掌握。
        返回是否找到该词（False 表示词不存在，调用方可提示用户）。
        """
        with self._lock:
            row = self._conn.execute(
                "SELECT id FROM vocabulary WHERE word = ?", (word,)
            ).fetchone()
            if not row:
                return False
            self.set_mastered(row["id"], mastered)
            return True

    def delete_vocabulary(self, vocab_id: int):
        """删除指定生词（同时从生词本和已掌握列表中移除）。"""
        with self._lock:
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
        """
        保存翻译历史。标题取原文首行前 80 字符。
        同一 task_id 重复保存时覆盖（INSERT OR REPLACE）。
        """
        with self._lock:
            title = original_text.strip().split("\n")[0][:80]
            self._conn.execute("""
                INSERT OR REPLACE INTO history (id, original_text, annotated_text, title)
                VALUES (?, ?, ?, ?)
            """, (task_id, original_text, annotated_text, title))
            self._conn.commit()

    def list_history(self, limit: int = 20, offset: int = 0) -> tuple[list[dict], int]:
        total = self._conn.execute("SELECT COUNT(*) as cnt FROM history").fetchone()["cnt"]
        rows = self._conn.execute(
            "SELECT id, title, created_at FROM history ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()
        return [dict(row) for row in rows], total

    def get_history(self, task_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM history WHERE id = ?", (task_id,)
        ).fetchone()
        return dict(row) if row else None

    def delete_history(self, task_id: str):
        with self._lock:
            self._conn.execute(
                "DELETE FROM history WHERE id = ?", (task_id,)
            )
            self._conn.commit()
