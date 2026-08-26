import math
import re
from pathlib import Path
from .text import chunk_text, read_document


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norms = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(x * x for x in b))
    return dot / norms if norms else 0.0


class RAGService:
    def __init__(self, db, backend, top_k=3, min_score=0.08):
        self.db, self.backend, self.top_k, self.min_score = db, backend, top_k, min_score

    def ingest_path(self, path: Path) -> dict:
        is_directory = path.is_dir()
        files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.suffix.lower() in {".txt", ".md", ".pdf"})
        total, indexed_files, skipped = 0, 0, []
        active_sources = set()
        for file in files:
            try:
                chunks = chunk_text(read_document(file))
            except (OSError, UnicodeError, RuntimeError, ValueError) as exc:
                # A missing optional PDF reader must not prevent TXT/MD documents
                # from being indexed for the dependency-free demo.
                skipped.append({"source": file.name, "reason": str(exc)})
                continue
            if chunks:
                self.db.replace_source(file.name, chunks, self.backend.embed_many(chunks))
                active_sources.add(file.name)
                total += len(chunks)
                indexed_files += 1
        if is_directory:
            self.db.retain_sources(active_sources)
        return {"files": indexed_files, "chunks": total, "skipped": skipped}

    def ensure_index_compatible(self, documents_path: Path) -> bool:
        """Rebuild the index when it was created by a different embedding model."""
        chunks = self.db.all_chunks()
        if not chunks:
            self.ingest_path(documents_path)
            return True
        expected_dimensions = len(self.backend.embed("embedding boyut kontrolü"))
        if any(len(chunk["embedding"]) != expected_dimensions for chunk in chunks):
            self.ingest_path(documents_path)
            return True
        return False

    def retrieve(self, question: str) -> list[dict]:
        query_vector = self.backend.embed(question)
        results = []
        for chunk in self.db.all_chunks():
            result = {k: v for k, v in chunk.items() if k != "embedding"}
            result["score"] = cosine_similarity(query_vector, chunk["embedding"])
            results.append(result)
        return sorted(results, key=lambda item: item["score"], reverse=True)[:self.top_k]

    def ask(self, question: str) -> dict:
        question = question.strip()
        if not question:
            raise ValueError("Lütfen bir soru yazın.")
        normalized = re.sub(r"[^a-zçğıöşü0-9 ]", "", question.lower())
        help_phrases = (
            "ne sorabilirim", "neler sorabilirim", "hangi soruları sorabilirim",
            "hangi konular var", "belgelerde ne var", "yardım", "anlamıyorum",
            "anlamadım", "nasıl kullanılır", "nasıl kullanacağım",
        )
        if any(phrase in normalized for phrase in help_phrases):
            stats = self.db.stats()
            sources = sorted({item["source"] for item in self.db.all_chunks()})
            examples = [
                "• Foundry Local nedir ve hangi avantajları sağlar?",
                "• RAG hangi adımlardan oluşur?",
                "• Embedding ve cosine benzerliği ne işe yarar?",
                "• SQLite neden bu projede kullanılıyor?",
                "• Yüklediğim belgenin ana konusu nedir?",
            ]
            source_text = ", ".join(sources[:5])
            answer = (f"Bilgi tabanında {stats['sources']} kaynak ve {stats['chunks']} bilgi parçası var. "
                      f"Şunları sorabilirsin:\n" + "\n".join(examples) +
                      f"\n\nYüklü kaynaklar: {source_text}")
            return {"answer": answer, "sources": [], "backend": self.backend.name}
        summary_phrases = (
            "ne anlatıyor", "ne analatıyor", "ne anlatiyor", "neyi anlatıyor",
            "konusu ne", "konusu nedir", "özetle", "ozetle", "özet çıkar",
            "belgeyi özetle", "dokümanı özetle",
        )
        if any(phrase in normalized for phrase in summary_phrases):
            latest = self.db.latest_source_chunks()
            if not latest:
                return {"answer": "Özetlenecek bir belge bulunmuyor.", "sources": [], "backend": self.backend.name}
            answer = self.backend.summarize(latest)
            sources = [{"source": r["source"], "chunk": r["chunk_index"], "score": 1.0, "excerpt": r["content"][:220]} for r in latest[:3]]
            return {"answer": answer, "sources": sources, "backend": self.backend.name}
        results = self.retrieve(question)
        if not results or results[0]["score"] < self.min_score:
            answer = "Bu bilgi yüklenen belgelerde bulunmuyor."
            results = []
        else:
            answer = self.backend.answer(question, results)
            if answer.strip().lower().startswith("bu bilgi yüklenen belgelerde bulunmuyor"):
                results = []
            else:
                cited = []
                for index, result in enumerate(results, 1):
                    foundry_marker = f"[Kaynak {index}]"
                    local_marker = f"[{result['source']} · parça {result['chunk_index']}]"
                    if foundry_marker in answer or local_marker in answer:
                        cited.append(result)
                # Do not display retrieved candidates that the answer did not use.
                results = cited or results[:1]
        sources = [{"source": r["source"], "chunk": r["chunk_index"], "score": round(r["score"], 3), "excerpt": r["content"][:220]} for r in results]
        return {"answer": answer, "sources": sources, "backend": self.backend.name}
