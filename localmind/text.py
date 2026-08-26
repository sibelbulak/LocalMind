import re
from pathlib import Path


def chunk_text(text: str, size: int = 900, overlap: int = 120) -> list[str]:
    """Split text at paragraph/sentence boundaries with a small overlap."""
    clean = re.sub(r"[ \t]+", " ", text.replace("\r", "")).strip()
    if not clean:
        return []
    units = [u.strip() for u in re.split(r"\n{2,}|(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ])", clean) if u.strip()]
    chunks, current = [], ""
    for unit in units:
        if len(unit) > size:
            pieces = [unit[i:i + size] for i in range(0, len(unit), size - overlap)]
        else:
            pieces = [unit]
        for piece in pieces:
            candidate = f"{current} {piece}".strip()
            if current and len(candidate) > size:
                chunks.append(current)
                current = f"{current[-overlap:]} {piece}".strip()
            else:
                current = candidate
    if current:
        chunks.append(current)
    return chunks


def read_document(path: Path) -> str:
    if path.suffix.lower() in {".txt", ".md"}:
        return path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("PDF için 'pip install pypdf' çalıştırın.") from exc
        return "\n\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    raise ValueError(f"Desteklenmeyen dosya: {path.name}")
