import json
import sqlite3
from contextlib import closing
from pathlib import Path


class KnowledgeDB:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.initialize()

    def connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self):
        with closing(self.connect()) as db, db:
            db.execute("""CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY, source TEXT NOT NULL, chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL, embedding TEXT NOT NULL,
                UNIQUE(source, chunk_index))""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source)")

    def replace_source(self, source: str, chunks: list[str], embeddings: list[list[float]]):
        with closing(self.connect()) as db, db:
            db.execute("DELETE FROM chunks WHERE source = ?", (source,))
            db.executemany(
                "INSERT INTO chunks(source, chunk_index, content, embedding) VALUES (?, ?, ?, ?)",
                [(source, i + 1, chunk, json.dumps(vector)) for i, (chunk, vector) in enumerate(zip(chunks, embeddings))],
            )

    def retain_sources(self, sources: set[str]):
        """Remove stale index rows when the documents directory is re-indexed."""
        with closing(self.connect()) as db, db:
            if not sources:
                db.execute("DELETE FROM chunks")
                return
            placeholders = ",".join("?" for _ in sources)
            db.execute(f"DELETE FROM chunks WHERE source NOT IN ({placeholders})", tuple(sorted(sources)))

    def all_chunks(self) -> list[dict]:
        with closing(self.connect()) as db:
            rows = db.execute("SELECT id, source, chunk_index, content, embedding FROM chunks").fetchall()
        return [{**dict(row), "embedding": json.loads(row["embedding"])} for row in rows]

    def latest_source_chunks(self, limit: int = 4) -> list[dict]:
        """Return the opening chunks of the most recently indexed source."""
        with closing(self.connect()) as db:
            latest = db.execute("SELECT source FROM chunks ORDER BY id DESC LIMIT 1").fetchone()
            if not latest:
                return []
            rows = db.execute(
                "SELECT id, source, chunk_index, content, embedding FROM chunks WHERE source = ? ORDER BY chunk_index LIMIT ?",
                (latest["source"], limit),
            ).fetchall()
        return [{**dict(row), "embedding": json.loads(row["embedding"])} for row in rows]

    def stats(self) -> dict:
        with closing(self.connect()) as db:
            row = db.execute("SELECT COUNT(*) chunks, COUNT(DISTINCT source) sources FROM chunks").fetchone()
        return dict(row)
