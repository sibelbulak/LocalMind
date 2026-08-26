from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "knowledge.db"
DOCUMENTS_PATH = ROOT / "documents"
STATIC_PATH = ROOT / "static"
EMBEDDING_MODEL = "qwen3-embedding-0.6b"
CHAT_MODEL = "qwen2.5-0.5b"
TOP_K = 3
MIN_SCORE = 0.08
